"""Ejecuta P2-P5 y conserva evidencia reproducible en resultados/."""

import argparse
import csv
import json
import math
import platform
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nltk
import pandas as pd

from laboratorio import (InvertedIndex, boolean_search_linear, compute_bow,
                         connect_db, fetch_data, fetch_data_bow, load_stopwords,
                         update_bow_in_db)


OUT = Path(__file__).parent / "resultados"
BOOLEAN_QUERIES = [
    "economía AND inflación",
    "banca OR finanzas",
    "tecnología AND-NOT inflación",
    "sostenibilidad AND ambiente AND renovables",
    "tecnología AND (banca OR finanzas)",
    "economía AND-NOT inflación",
]
COSINE_QUERIES = [
    "innovaciones en banca digital y tecnología financiera",
    "inflación y crecimiento económico",
    "sostenibilidad y energías renovables",
]


def prepare():
    load_stopwords()
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM noticias WHERE bag_of_words IS NULL")
            missing = cur.fetchone()[0]
    if missing:
        data = fetch_data()
        print(f"Actualizando BoW de {missing} noticias sin procesar...")
        # Evita sobrescribir BoW ya calculados por el estudiante.
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM noticias WHERE bag_of_words IS NULL")
                ids = {row[0] for row in cur.fetchall()}
        print("Actualizadas:", update_bow_in_db(data[data.id.isin(ids)]))
    else:
        print("Todos los BoW ya están guardados")
    data = fetch_data_bow()
    print("Primeras 10 filas (id, contenido abreviado, BoW abreviado):")
    for row in data.head(10).itertuples(index=False):
        print(row.id, str(row.contenido)[:65], list((row.bag_of_words or {}).items())[:6])
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*), COUNT(bag_of_words) FROM noticias")
            print("Noticias y BoW:", cur.fetchone())
            cur.execute("SELECT COUNT(*) FROM stopwords")
            print("Stopwords:", cur.fetchone()[0])
    return data


def validate(data):
    assert compute_bow(None) == {}
    assert compute_bow("¡Banco, banco! 123") == {"banc": 2}
    idx = InvertedIndex()
    idx.build_from_dataframe(data)
    boolean_results, cosine_results = [], []
    for query in BOOLEAN_QUERIES:
        linear = boolean_search_linear(query, data)
        indexed = idx.boolean_search(query)
        assert linear == indexed, f"Diferencia booleana: {query}"
        boolean_results.append({"query": query, "count": len(linear),
                                "first_ids": linear[:10], "equal": True})
        print("Booleana:", query, "=>", len(linear), "resultados; iguales")
    for query in COSINE_QUERIES + ["zzzinexistente"]:
        linear = idx.cosine_search_linear(query)
        indexed = idx.cosine_search(query)
        assert [x[0] for x in linear] == [x[0] for x in indexed], query
        assert all(math.isclose(a[1], b[1], rel_tol=1e-12, abs_tol=1e-12)
                   for a, b in zip(linear, indexed)), query
        cosine_results.append({"query": query, "top5": linear,
                               "equal_ids_and_scores": True})
        print("Coseno:", query, "=>", linear)
    assert idx.cosine_search("zzzinexistente") == []
    assert idx.cosine_search_linear("zzzinexistente") == []
    assert idx.cosine_search("economía", top_k=0) == []
    OUT.mkdir(exist_ok=True)
    evidence = {"documents": len(data), "boolean": boolean_results,
                "cosine": cosine_results}
    (OUT / "validacion.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    return evidence


def sizes_for(n):
    sizes = sorted({max(1, round(n * fraction))
                    for fraction in (0.1, 0.25, 0.4, 0.6, 0.8, 1.0)})
    if len(sizes) < 5:
        raise ValueError("Se necesitan al menos cinco documentos/tamaños distintos")
    return sizes


def measure(data, repeats=20):
    OUT.mkdir(exist_ok=True)
    raw = []
    builds = []
    for n in sizes_for(len(data)):
        subset = data.iloc[:n].copy()
        start = time.perf_counter()
        idx = InvertedIndex()
        idx.build_from_dataframe(subset)
        build_time = time.perf_counter() - start
        builds.append({"documents": n, "build_seconds": build_time,
                       "terms": len(idx.index),
                       "postings": sum(len(x) for x in idx.index.values())})
        for query in BOOLEAN_QUERIES:
            assert boolean_search_linear(query, subset) == idx.boolean_search(query)
        for query in COSINE_QUERIES:
            linear = idx.cosine_search_linear(query)
            indexed = idx.cosine_search(query)
            assert [x[0] for x in linear] == [x[0] for x in indexed]
            assert all(math.isclose(a[1], b[1], rel_tol=1e-12, abs_tol=1e-12)
                       for a, b in zip(linear, indexed))
        # Calentamiento; no se registra ni se suma al promedio.
        for query in BOOLEAN_QUERIES:
            boolean_search_linear(query, subset)
            idx.boolean_search(query)
        for query in COSINE_QUERIES:
            idx.cosine_search_linear(query)
            idx.cosine_search(query)
        for repeat in range(1, repeats + 1):
            for query in BOOLEAN_QUERIES:
                for method, function in (
                    ("linear", lambda q=query: boolean_search_linear(q, subset)),
                    ("index", lambda q=query: idx.boolean_search(q)),
                ):
                    start = time.perf_counter()
                    function()
                    raw.append({"documents": n, "kind": "boolean", "method": method,
                                "query": query, "repeat": repeat,
                                "seconds": time.perf_counter() - start})
            for query in COSINE_QUERIES:
                for method, function in (
                    ("linear", lambda q=query: idx.cosine_search_linear(q)),
                    ("index", lambda q=query: idx.cosine_search(q)),
                ):
                    start = time.perf_counter()
                    function()
                    raw.append({"documents": n, "kind": "cosine", "method": method,
                                "query": query, "repeat": repeat,
                                "seconds": time.perf_counter() - start})
        print(f"{n} documentos: índice {build_time:.4f} s; {len(idx.index)} términos")
    with (OUT / "tiempos_crudos.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=raw[0])
        writer.writeheader()
        writer.writerows(raw)
    averages = (pd.DataFrame(raw).groupby(["documents", "kind", "method"],
                                         as_index=False)["seconds"].mean())
    averages.to_csv(OUT / "promedios.csv", index=False, float_format="%.10f")
    pd.DataFrame(builds).to_csv(OUT / "construccion_indice.csv", index=False,
                                float_format="%.10f")
    for kind, title, filename in (
        ("boolean", "Búsqueda booleana", "booleana.png"),
        ("cosine", "Similitud de coseno", "coseno.png"),
    ):
        fig, ax = plt.subplots(figsize=(9, 5))
        for method, label in (("linear", "Lineal"), ("index", "Índice invertido")):
            rows = averages[(averages.kind == kind) & (averages.method == method)]
            ax.plot(rows.documents, rows.seconds, marker="o", label=label)
            for x, y in zip(rows.documents, rows.seconds):
                ax.annotate(f"{y:.5f}", (x, y), xytext=(0, 7),
                            textcoords="offset points", ha="center", fontsize=8)
        ax.set(title=title, xlabel="Número de documentos",
               ylabel="Tiempo promedio por consulta (segundos)")
        ax.grid(alpha=0.3)
        ax.legend()
        fig.tight_layout()
        fig.savefig(OUT / filename, dpi=180)
        plt.close(fig)
    meta = {"repeats": repeats, "sizes": sizes_for(len(data)),
            "selection": "primeros N documentos por id ascendente",
            "boolean_queries": BOOLEAN_QUERIES, "cosine_queries": COSINE_QUERIES,
            "timing": "solo ejecución de consulta; construcción separada; calentamiento previo",
            "python": sys.version.split()[0], "postgresql": None,
            "platform": platform.platform(), "pandas": pd.__version__,
            "matplotlib": matplotlib.__version__, "nltk": nltk.__version__}
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SHOW server_version")
            meta["postgresql"] = cur.fetchone()[0]
    (OUT / "metodologia.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                                           encoding="utf-8")
    return averages, builds


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("prepare", "validate", "experiment", "all"))
    parser.add_argument("--repeats", type=int, default=20)
    args = parser.parse_args()
    if args.repeats < 2:
        parser.error("--repeats debe ser al menos 2")
    if args.phase in ("prepare", "all"):
        data = prepare()
    else:
        load_stopwords()
        data = fetch_data_bow()
    if data.bag_of_words.isna().any():
        raise RuntimeError("Hay BoW NULL; ejecutar primero 'prepare'")
    if args.phase in ("validate", "all"):
        validate(data)
    if args.phase in ("experiment", "all"):
        measure(data, args.repeats)


if __name__ == "__main__":
    main()
