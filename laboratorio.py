"""Preprocesamiento y búsquedas del Laboratorio 09."""

import math
import os
import re
from collections import Counter
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from nltk.stem.snowball import SnowballStemmer
from psycopg2.extras import Json, execute_batch


load_dotenv(Path(__file__).parent / ".env")
STEMMER = SnowballStemmer("spanish")
WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
QUERY_RE = re.compile(r"AND-NOT|AND|OR|\(|\)|[^\W\d_]+", re.IGNORECASE)
_stopwords = None


def connect_db():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"), user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"), host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
    )


def load_stopwords():
    global _stopwords
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT word FROM stopwords")
            _stopwords = {row[0].lower() for row in cur.fetchall()}
    return _stopwords


def preprocess(text):
    """Minúsculas, palabras Unicode, stopwords de BD y stemming español.

    NULL/vacío => []; signos y números se omiten; las tildes se conservan.
    """
    global _stopwords
    if _stopwords is None:
        load_stopwords()
    if text is None or pd.isna(text):
        return []
    return [STEMMER.stem(w) for w in WORD_RE.findall(str(text).lower())
            if w not in _stopwords]


def compute_bow(text):
    return dict(Counter(preprocess(text)))


def fetch_data():
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, contenido FROM noticias ORDER BY id")
            return pd.DataFrame(cur.fetchall(), columns=["id", "contenido"])


def update_bow_in_db(dataframe):
    """Actualiza únicamente las filas recibidas, en una transacción."""
    rows = [(Json(compute_bow(row.contenido)), int(row.id))
            for row in dataframe.itertuples(index=False)]
    with connect_db() as conn:
        with conn.cursor() as cur:
            execute_batch(cur, "UPDATE noticias SET bag_of_words = %s WHERE id = %s", rows)
    return len(rows)


def fetch_data_bow():
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, contenido, bag_of_words FROM noticias ORDER BY id")
            return pd.DataFrame(cur.fetchall(),
                                columns=["id", "contenido", "bag_of_words"])


def parse_boolean(query):
    """AND y AND-NOT preceden a OR; paréntesis cambian la precedencia."""
    tokens = QUERY_RE.findall(query)
    if not tokens:
        raise ValueError("Consulta booleana vacía")
    operators = {"OR": 1, "AND": 2, "AND-NOT": 2}
    output, stack = [], []
    for token in tokens:
        upper = token.upper()
        if token == "(":
            stack.append(token)
        elif token == ")":
            while stack and stack[-1] != "(":
                output.append(stack.pop())
            if not stack:
                raise ValueError("Paréntesis desbalanceados")
            stack.pop()
        elif upper in operators:
            while stack and stack[-1] != "(" and operators[stack[-1]] >= operators[upper]:
                output.append(stack.pop())
            stack.append(upper)
        else:
            terms = preprocess(token)
            output.append(("TERM", terms[0] if terms else None))
    while stack:
        op = stack.pop()
        if op == "(":
            raise ValueError("Paréntesis desbalanceados")
        output.append(op)
    tree = []
    for item in output:
        if isinstance(item, tuple):
            tree.append(item)
        else:
            if len(tree) < 2:
                raise ValueError("Consulta booleana incompleta")
            right, left = tree.pop(), tree.pop()
            tree.append((item, left, right))
    if len(tree) != 1:
        raise ValueError("Falta un operador booleano")
    return tree[0]


def _evaluate(tree, terms):
    op = tree[0]
    if op == "TERM":
        return tree[1] is not None and tree[1] in terms
    a, b = _evaluate(tree[1], terms), _evaluate(tree[2], terms)
    if op == "AND":
        return a and b
    if op == "OR":
        return a or b
    return a and not b


def boolean_search_linear(query, dataframe):
    tree = parse_boolean(query)
    return sorted(int(row.id) for row in dataframe.itertuples(index=False)
                  if _evaluate(tree, row.bag_of_words or {}))


def AND(list1, list2):
    a, b = dict(list1), dict(list2)
    return [(doc, a[doc]) for doc in sorted(a.keys() & b.keys())]


def OR(list1, list2):
    a, b = dict(list1), dict(list2)
    return [(doc, a.get(doc, b.get(doc))) for doc in sorted(a.keys() | b.keys())]


def AND_NOT(list1, list2):
    a, b = dict(list1), dict(list2)
    return [(doc, a[doc]) for doc in sorted(a.keys() - b.keys())]


class InvertedIndex:
    def __init__(self):
        self.index = {}
        self.idf = {}
        self.length = {}
        self._docs = {}
        self._bow = {}

    def build_from_db(self):
        self.build_from_dataframe(fetch_data_bow())

    def build_from_dataframe(self, dataframe):
        self.__init__()
        for row in dataframe.itertuples(index=False):
            doc_id = int(row.id)
            bow = row.bag_of_words or {}
            self._docs[doc_id] = row.contenido or ""
            self._bow[doc_id] = bow
            for term, tf in bow.items():
                self.index.setdefault(term, []).append((doc_id, int(tf)))
        n = len(self._bow)
        self.idf = {term: math.log((n + 1) / (len(postings) + 1)) + 1
                    for term, postings in self.index.items()}
        self.length = {
            doc_id: math.sqrt(sum((tf * self.idf[term]) ** 2
                                  for term, tf in bow.items()))
            for doc_id, bow in self._bow.items()
        }

    def L(self, word):
        terms = preprocess(word)
        return self.index.get(terms[0], []) if len(terms) == 1 else []

    def showDocument(self, doc_id, max_chars=80):
        return self._docs.get(doc_id, "")[:max_chars] + "..."

    def showDocuments(self, posting_list, max_chars=80):
        return [self.showDocument(doc_id, max_chars) for doc_id, *_ in posting_list]

    def boolean_search(self, query):
        tree = parse_boolean(query)

        def evaluate(node):
            if node[0] == "TERM":
                return self.index.get(node[1], []) if node[1] else []
            a, b = evaluate(node[1]), evaluate(node[2])
            return {"AND": AND, "OR": OR, "AND-NOT": AND_NOT}[node[0]](a, b)

        return [doc_id for doc_id, _ in evaluate(tree)]

    def _query_weights(self, query):
        terms = Counter(preprocess(query))
        weights = {term: tf * self.idf[term] for term, tf in terms.items()
                   if term in self.idf}
        norm = math.sqrt(sum(weight ** 2 for weight in weights.values()))
        return weights, norm

    @staticmethod
    def _top(scores, top_k):
        return sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:max(0, top_k)]

    def cosine_search_linear(self, query, top_k=5):
        weights, qnorm = self._query_weights(query)
        if not qnorm:
            return []
        scores = {}
        for doc_id, bow in self._bow.items():
            dot = sum(bow.get(term, 0) * self.idf[term] * weight
                      for term, weight in weights.items())
            if dot and self.length[doc_id]:
                scores[doc_id] = dot / (self.length[doc_id] * qnorm)
        return self._top(scores, top_k)

    def cosine_search(self, query, top_k=5):
        weights, qnorm = self._query_weights(query)
        if not qnorm:
            return []
        dots = {}
        for term, weight in weights.items():
            for doc_id, tf in self.index[term]:
                dots[doc_id] = dots.get(doc_id, 0.0) + tf * self.idf[term] * weight
        scores = {doc_id: dot / (self.length[doc_id] * qnorm)
                  for doc_id, dot in dots.items() if dot and self.length[doc_id]}
        return self._top(scores, top_k)
