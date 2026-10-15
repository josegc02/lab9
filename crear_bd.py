"""Crea la base indicada en .env y las dos tablas del Laboratorio 09."""

import os
from pathlib import Path

import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv


load_dotenv(Path(__file__).parent / ".env")

variables = ["DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT"]
faltantes = [nombre for nombre in variables if not os.getenv(nombre)]
if faltantes:
    raise ValueError(f"Faltan variables en .env: {', '.join(faltantes)}")

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

config = {
    "user": DB_USER,
    "password": DB_PASSWORD,
    "host": DB_HOST,
    "port": DB_PORT,
}


def crear_base():
    # Nos conectamos primero a 'postgres', porque nuestra base todavía puede no existir.
    conn = psycopg2.connect(dbname="postgres", **config)
    try:
        conn.autocommit = True  # CREATE DATABASE no puede ejecutarse en una transacción.
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
            if cur.fetchone() is None:
                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
                print(f"Base de datos {DB_NAME} creada")
            else:
                print(f"Base de datos {DB_NAME} ya existe")
    finally:
        conn.close()


def crear_tablas():
    conn = psycopg2.connect(dbname=DB_NAME, **config)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS noticias (
                        id SERIAL PRIMARY KEY,
                        url TEXT,
                        contenido TEXT,
                        categoria VARCHAR(50),
                        bag_of_words JSONB
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS stopwords (
                        id SERIAL PRIMARY KEY,
                        word TEXT UNIQUE NOT NULL
                    )
                """)
        print("Tablas noticias y stopwords listas")
    finally:
        conn.close()


if __name__ == "__main__":
    crear_base()
    crear_tablas()
