"""Casos pequeños con resultado conocido; requiere la tabla stopwords local."""

import math
import unittest

import pandas as pd

from laboratorio import (AND, AND_NOT, OR, InvertedIndex, boolean_search_linear,
                         compute_bow, load_stopwords)


class SearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_stopwords()
        cls.data = pd.DataFrame([
            (1, "banca digital banca", compute_bow("banca digital banca")),
            (2, "banca inflación", compute_bow("banca inflación")),
            (3, "tecnología digital", compute_bow("tecnología digital")),
            (4, "", compute_bow(None)),
        ], columns=["id", "contenido", "bag_of_words"])
        cls.idx = InvertedIndex()
        cls.idx.build_from_dataframe(cls.data)

    def test_boolean_operations_and_parentheses(self):
        expected = {
            "banca AND digital": [1],
            "banca OR tecnología": [1, 2, 3],
            "banca AND-NOT inflación": [1],
            "digital AND (banca OR tecnología)": [1, 3],
            "banca AND zzzinexistente": [],
        }
        for query, ids in expected.items():
            with self.subTest(query=query):
                self.assertEqual(boolean_search_linear(query, self.data), ids)
                self.assertEqual(self.idx.boolean_search(query), ids)

    def test_posting_operations(self):
        a, b = [(1, 2), (2, 1)], [(2, 3), (3, 1)]
        self.assertEqual([x[0] for x in AND(a, b)], [2])
        self.assertEqual([x[0] for x in OR(a, b)], [1, 2, 3])
        self.assertEqual([x[0] for x in AND_NOT(a, b)], [1])

    def test_cosine_and_empty_queries(self):
        for query in ("banca digital", "inflación", "tecnología banca"):
            a = self.idx.cosine_search_linear(query, top_k=10)
            b = self.idx.cosine_search(query, top_k=10)
            self.assertEqual([x[0] for x in a], [x[0] for x in b])
            self.assertTrue(all(math.isclose(x[1], y[1], abs_tol=1e-12)
                                for x, y in zip(a, b)))
        self.assertEqual(self.idx.cosine_search("zzzinexistente"), [])
        self.assertEqual(self.idx.cosine_search_linear(""), [])
        self.assertEqual(self.idx.cosine_search("banca", top_k=0), [])


if __name__ == "__main__":
    unittest.main()
