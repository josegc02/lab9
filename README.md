# Laboratorio 09: Bag of Words, Similitud de Coseno e Índice Invertido

Integrantes: Juan Marcos Guerrero Cueva, Adrian Urbina Mendoza y Hector Huaman Puiquin.

## Entregables
- `lab09.ipynb`: el notebook con el código y las salidas de las partes 1 a 6.
- `informe_lab09.pdf`: el informe (fuente en `informe_lab09.tex`).
- `resultados/`: `tiempos.csv` y los gráficos `booleana.png` y `coseno.png`.

## Cómo ejecutar
1. `pip install -r requirements.txt`
2. Crear un archivo `.env` junto al notebook (Git lo ignora):
   ```
   DB_NAME=lab9
   DB_USER=postgres
   DB_PASSWORD='tu_contraseña'
   DB_HOST=localhost
   DB_PORT=5432
   ```
3. Abrir `lab09.ipynb` y ejecutar todas las celdas. La primera celda crea la base, las tablas y carga los datos si están vacías.
4. Para recompilar el informe: `pdflatex informe_lab09.tex` (dos veces, para que se genere el índice).
