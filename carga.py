"""Carga news_es.csv y stoplist.txt en la base indicada en .env."""

import csv
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


CARPETA = Path(__file__).parent
load_dotenv(CARPETA / ".env")

variables = ["DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT"]
faltantes = [nombre for nombre in variables if not os.getenv(nombre)]
if faltantes:
    raise ValueError(f"Faltan variables en .env: {', '.join(faltantes)}")


def cargar_noticias(cur):
    cur.execute("SELECT COUNT(*) FROM noticias")
    if cur.fetchone()[0] > 0:
        print("Noticias ya tiene datos; se omite el CSV para no duplicarlos")
        return

    cantidad = 0
    with (CARPETA / "news_es.csv").open(encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo)
        columnas = set(lector.fieldnames or [])
        esperadas = {'url', 'news', 'Type'}
        if not esperadas.issubset(columnas):
            raise ValueError(
                f"El CSV debe tener las columnas {sorted(esperadas)}. "
                f"Encontré: {lector.fieldnames}"
            )

        for fila in lector:
            cur.execute(
                "INSERT INTO noticias (url, contenido, categoria) VALUES (%s, %s, %s)",
                (fila["url"], fila["news"], fila["Type"]),
            )
            cantidad += 1
    print(f"Noticias cargadas: {cantidad}")


def cargar_stopwords(cur):
    cur.execute("SELECT COUNT(*) FROM stopwords")
    if cur.fetchone()[0] > 0:
        print("Stopwords ya tiene datos; se omite el TXT")
        return

    cantidad = 0
    with (CARPETA / "stoplist.txt").open(encoding="utf-8-sig") as archivo:
        for linea in archivo:
            palabra = linea.strip()
            if palabra:
                cur.execute(
                    "INSERT INTO stopwords (word) VALUES (%s) ON CONFLICT (word) DO NOTHING",
                    (palabra,),
                )
                cantidad += cur.rowcount
    print(f"Stopwords cargadas: {cantidad}")


def main():
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
    )
    try:
        with conn:
            with conn.cursor() as cur:
                cargar_noticias(cur)
                cargar_stopwords(cur)
                cur.execute("SELECT COUNT(*) FROM noticias")
                print("Total noticias:", cur.fetchone()[0])
                cur.execute("SELECT COUNT(*) FROM stopwords")
                print("Total stopwords:", cur.fetchone()[0])
    finally:
        conn.close()


if __name__ == "__main__":
    main()
