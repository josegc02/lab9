# Laboratorio 09 — recuperación de información

Implementación del enunciado con PostgreSQL, Python y un informe reproducible. Los datos reales son `news_es.csv` (1217 noticias) y `stoplist.txt` (608 stopwords). El informe descargable está en `lab09_overleaf.pdf` y su fuente, lista para Overleaf, en `lab09_overleaf.tex`.

## Ejecutar en PowerShell

1. Copiar las variables `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` y `DB_PORT` al archivo local `.env`. Este archivo está ignorado por Git. Activar o instalar las dependencias de `requirements.txt` en `.venv` si hace falta.
2. `\.venv\Scripts\python.exe crear_bd.py` comprueba o crea la base y las tablas.
3. `\.venv\Scripts\python.exe carga.py` importa noticias y stopwords solo si las tablas están vacías. Confirma los totales al terminar.
4. `\.venv\Scripts\python.exe -m unittest -v test_laboratorio.py` prueba operaciones booleanas, coseno y casos vacíos con documentos pequeños.
5. `\.venv\Scripts\python.exe ejecutar_lab.py all --repeats 30` actualiza solo los BoW pendientes, comprueba la equivalencia de las dos rutas y mide seis tamaños de colección. Comprueba los totales y las primeras diez filas en la salida.
6. `\.venv\Scripts\python.exe generar_informe.py` reconstruye el `.tex` a partir de los resultados medidos. Los gráficos se generan en `resultados/`.

Para revisar la base directamente: `psql -U <usuario> -d <base>` abre PostgreSQL; dentro de `psql`, `\dt` enumera tablas, `\d noticias` muestra el esquema y `SELECT COUNT(*), COUNT(bag_of_words) FROM noticias;` confirma que cada noticia tiene BoW. Usar el usuario y la base de `.env`; no pasar la contraseña en la línea de comandos.

Para compilar el informe con Tectonic: `tectonic lab09_overleaf.tex`. En Overleaf, subir `lab09_overleaf.tex` y los dos PNG de `resultados/`, conservando esa carpeta. El PDF del repositorio ya está compilado.

`resultados/tiempos_crudos.csv` guarda cada repetición; `promedios.csv` contiene los puntos de los gráficos; `construccion_indice.csv` separa el costo de preparar el índice; `validacion.json` guarda las consultas y los resultados comprobados; `metodologia.json` documenta el entorno y la selección de documentos.
