# Plan de trabajo — Laboratorio 09 de Base de Datos II

## Objetivo

Implementar, comprobar y documentar completamente el laboratorio **Bag of Words, Similitud de Coseno e Índice Invertido**. El trabajo debe permitir comparar, sobre los mismos documentos, cuatro búsquedas: booleana lineal, booleana con índice invertido, coseno lineal y coseno con índice invertido. Las mediciones, los gráficos y el informe deben basarse en ejecuciones reales; no inventar tiempos ni resultados.

## Contexto y forma de trabajar

- **Responsabilidad de Codex:** realizar el laboratorio de principio a fin: comprobar el entorno, ejecutar o ajustar los scripts de creación y carga, implementar las búsquedas, correr pruebas y experimentos, generar CSV y gráficos, **redactar y completar el informe LaTeX**, y verificar su compilación. No pedir al estudiante que cree tablas, importe datos ni ejecute SQL en pgAdmin. pgAdmin no es necesario; los scripts de Python se conectan directamente al servidor PostgreSQL.
- **Intervención del estudiante:** solo aportar archivos o datos de conexión si no están disponibles y atender un bloqueo real de acceso a su computadora o credenciales. Si Codex opera en un entorno distinto del PC donde está PostgreSQL, debe completar allí lo que pueda y proporcionar un procedimiento automatizado para ejecutar lo restante en el PC; no simular resultados ni declarar completo un informe con datos pendientes.
- Proyecto del estudiante en Windows/PowerShell: `C:\Users\juanl\jose_utec\bd2\lab9`. Trabajar sobre los archivos que realmente existan allí, sin sobrescribir cambios del estudiante.
- Python 3.14, PostgreSQL local, entorno virtual `.venv`. Dependencias instaladas: `psycopg2-binary`, `nltk`, `pandas`, `matplotlib`, `python-dotenv`.
- Ya existen `crear_bd.py` y `carga.py` para crear `lab9`, crear las tablas y cargar `news_es.csv` y `stoplist_es.txt`. **Inspeccionar estos archivos y comprobar los datos reales antes de modificar nada.** Puede existir una base ya creada y con datos.
- La conexión se configura con `.env`: `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`. Nunca imprimir la contraseña, escribirla en código ni subir `.env` a Git.
- Preferencia del estudiante: código sencillo y legible, con funciones reconocibles del enunciado, sin optimizaciones innecesarias. Explicar cada etapa, los comandos de terminal y por qué se usan, aunque Codex ejecute los pasos técnicos.
- Ya hay una plantilla `lab09_overleaf.tex` basada en el estilo del Lab 06. **Usarla y completarla** con metodología, código relevante, capturas o salidas verificadas cuando correspondan, dos gráficos, tablas de datos y análisis; conservar portada e índice y actualizar las rutas de imágenes según los archivos generados.

## 0. Inventario y comprobación inicial

1. Leer el PDF del enunciado y los archivos existentes (`crear_bd.py`, `carga.py`, `requirements.txt`, `.gitignore`, scripts de búsqueda si los hubiera). Verificar la estructura real del CSV y del TXT; no asumir cabeceras ni separadores sin inspección.
2. Confirmar si están presentes `news_es.csv` y `stoplist_es.txt`. Si faltan, avanzar con implementación y pruebas pequeñas sintéticas, pero dejar señalada la ejecución real pendiente; no fingir que se ejecutó el dataset completo.
3. Comprobar que `.gitignore` excluye `.env`, `.venv/`, `__pycache__/`, `*.pyc` y, si se generan, datos sensibles o archivos locales que no se deban publicar. Revisar `git status` antes de agregar o publicar archivos.
4. Mostrar comandos de verificación, por ejemplo `python --version`, `python -m pip list`, `psql -U postgres -d lab9`, `\dt`, `\d noticias`, `\d stopwords`, `SELECT COUNT(*) FROM noticias;`, `SELECT COUNT(*) FROM stopwords;`. Adaptar usuario y base a `.env`, sin exponer la contraseña.

**Resultado esperado:** conocer cantidad de noticias y stopwords, esquema y forma de los datos, y saber si hay BoW previamente guardados.

## 1. Base de datos y carga

1. Mantener la separación simple: `crear_bd.py` crea base/tablas; `carga.py` importa los archivos. Reutilizar lo que ya funciona.
2. Esquema requerido:
   - `noticias(id SERIAL PRIMARY KEY, url TEXT, contenido TEXT, categoria VARCHAR(50), bag_of_words JSONB)`.
   - `stopwords(id SERIAL PRIMARY KEY, word TEXT UNIQUE NOT NULL)`.
3. Si es necesario ejecutar la carga, verificar antes si las tablas ya tienen filas para no duplicarlas. Los `id` se generan con `SERIAL` cuando se insertan filas sin indicar `id`.
4. Comprobar una muestra con `SELECT id, url, categoria, LEFT(contenido, 80) FROM noticias LIMIT 5;` y `SELECT * FROM stopwords LIMIT 10;`.

**Resultado esperado:** tablas pobladas una sola vez y consultas de muestra correctas.

## 2. Preprocesamiento y Bag of Words (3 puntos)

1. Implementar `preprocess(text)`: minúsculas, tokenización, eliminación de stopwords **obtenidas de la tabla** y stemming. Definir explícitamente qué se hace con `NULL`, signos, números y tildes. Usar exactamente el mismo procesamiento para documentos, búsquedas booleanas y consultas de coseno.
2. Implementar `compute_bow(text)`: diccionario `{termino: frecuencia}` tras preprocesar.
3. Implementar `update_bow_in_db(dataframe)`: actualizar `noticias.bag_of_words` como `JSONB` mediante consultas parametrizadas y transacción; no convertirlo a texto con concatenación SQL.
4. Implementar `fetch_data_bow()`: recuperar `id`, `contenido` y `bag_of_words` de `noticias`, enseñar las primeras diez filas. **El enunciado menciona `noticias_bow` en un comentario pero solo crea la tabla `noticias`; usar la columna de `noticias` salvo que el esquema real indique otra cosa.**
5. Validar uno o dos textos cortos manualmente y consultar filas de PostgreSQL para confirmar frecuencias y formato JSONB.

**Resultado esperado:** cada noticia procesada tiene BoW consultable y las mismas reglas de normalización se aplican a las búsquedas.

## 3. Búsqueda booleana (3 puntos)

1. Implementar `boolean_search_linear(query, dataframe)` recorriendo todos los documentos y comprobando sus BoW. Soportar `AND`, `OR`, `AND-NOT` según las consultas del enunciado. Devolver identificadores de documentos con un orden estable.
2. Implementar `InvertedIndex.build_from_db()`: leer BoW y contenido desde PostgreSQL y construir en memoria `index` con listas de `(doc_id, tf)`, `_docs`, `idf` y `length`. Definir y documentar la fórmula IDF y de la norma que también usarán ambas versiones de coseno.
3. Implementar `L(word)`, `AND`, `OR` y `AND_NOT` sobre las listas invertidas. Normalizar los términos de entrada con la misma función de preprocesamiento. Evitar duplicados y mantener un orden determinista.
4. Comparar resultados lineales y con índice. Incluir **al menos cinco pruebas** que combinen operaciones; el PDF ofrece tres ejemplos con sostenibilidad/ambiente/renovables, tecnología/banca/finanzas y economía/inflación, y pide agregar tres más.

**Resultado esperado:** ambas rutas devuelven los mismos IDs para cada prueba; registrar diferencias y corregirlas antes de medir tiempos.

## 4. Similitud de coseno (3 puntos)

1. Implementar `cosine_search_linear(query, top_k=5)` calculando TF-IDF y coseno contra todos los documentos de la colección activa, sin consultar el índice para seleccionar candidatos.
2. Implementar `cosine_search(query, top_k=5)` con índice invertido: calcular scores solo para documentos que aparezcan en listas de términos de la consulta. Usar **la misma fórmula TF-IDF, IDF, norma y tratamiento de casos vacíos** en ambas rutas.
3. Hacer desempates reproducibles (por ejemplo, score descendente y luego `doc_id` ascendente). Aclarar qué hacer si una consulta no comparte términos con ningún documento o si `top_k` supera el número de resultados.
4. Comparar IDs y scores con tolerancia numérica para las tres consultas indicadas en el PDF:
   - `innovaciones en banca digital y tecnología financiera`
   - `inflación y crecimiento económico`
   - `sostenibilidad y energías renovables`

**Resultado esperado:** los mismos documentos en el mismo orden, con scores equivalentes hasta error de coma flotante. Resolver cualquier discrepancia antes del experimento.

## 5. Experimento reproducible (3 puntos)

1. Crear un script claro para medir las cuatro búsquedas con `time.perf_counter()`. Fijar consultas, tamaños, número de repeticiones, orden de selección de noticias y, si hay muestreo, semilla aleatoria. Usar **al menos cinco tamaños de colección**, sin pedir más documentos de los disponibles.
2. Para cada tamaño, construir la colección y el índice correspondientes, y ejecutar ambos enfoques **sobre exactamente el mismo subconjunto**. Separar y reportar el tiempo de construcción del índice del tiempo de consulta; decir claramente qué incluye cada curva. No aprovechar accidentalmente un índice global construido para toda la colección si se mide un subconjunto.
3. Repetir cada búsqueda varias veces y calcular tiempos promedio en segundos. Comprobar exactitud de resultados para cada tamaño. Guardar datos crudos y promedios, por ejemplo en CSV, para poder reproducir los gráficos.
4. Generar **dos gráficos** con `matplotlib`: uno para booleana y otro para coseno. En cada uno: X = número de documentos, Y = tiempo promedio en segundos, curvas lineal e índice, título, ejes, leyenda y valores sobre los puntos. Guardar imágenes para incluirlas en Overleaf.
5. Registrar el equipo/entorno, versiones relevantes, consultas, repeticiones y metodología; evitar declarar una mejora que los datos no muestren.

**Resultado esperado:** dos gráficos reales, mediciones trazables y comparación justa de cuatro enfoques.

## 6. Material para el análisis (8 puntos)

Redactar en el informe un análisis de **al menos 300 palabras**, sustentado con una tabla de observaciones y números reales del experimento, que responda:

1. Complejidad teórica de los cuatro métodos y consistencia con las curvas medidas.
2. Primer tamaño medido donde el índice supera a la versión lineal para búsqueda booleana y para coseno; indicar si los puntos difieren. Si no hay cruce entre los tamaños probados, decirlo expresamente.
3. Posible costo adicional para colecciones pequeñas, distinguiendo construcción de índice de tiempo de consulta.
4. Exactitud de IDs, ranking y scores; explicar cualquier diferencia realmente observada.
5. Implicaciones de una colección 100 veces mayor para el índice en RAM y una alternativa de almacenamiento persistente.

Incluir este análisis en `lab09_overleaf.tex` y verificar que los valores mencionados concuerdan con el CSV y los gráficos. Si las mediciones reales no están disponibles, dejar esa sección claramente pendiente de datos reales y explicar exactamente cómo obtenerlos, sin fabricar conclusiones.

## 7. Informe LaTeX y Overleaf

1. Completar `lab09_overleaf.tex` con todas las partes P1–P6 siguiendo el estilo del Lab 06: portada, índice, secciones, bloques de código, tablas, figuras con leyenda y explicación de resultados. Sustituir todas las marcas «Escribe aquí» cuando haya datos suficientes.
2. Insertar los dos gráficos experimentales y resumir resultados de las pruebas booleanas y de coseno con salidas reales, sin pegar enormes volcados de datos. Explicar elecciones de normalización, TF-IDF, fórmulas y metodología de tiempos.
3. Asegurar que el análisis P6 tiene al menos 300 palabras, responde las cinco preguntas y cita números efectivamente medidos.
4. Compilar dos veces con `pdflatex` o el compilador disponible para actualizar el índice y revisar que no falten imágenes, tablas ni referencias. Entregar el `.tex` y sus imágenes con rutas listas para subir a Overleaf; si es viable, entregar también el PDF compilado.

## Verificación y entrega del trabajo de Codex

- Dar un comando PowerShell para ejecutar cada fase y otro para comprobar su resultado (`psql`, `python ...`, `git status` cuando aplique). Explicar brevemente **qué hace cada comando y por qué**.
- Mantener las funciones y nombres reconocibles del enunciado, con código de nivel estudiante y comentarios donde aclaren decisiones reales.
- Probar casos pequeños conocidos (incluidos textos vacíos, términos ausentes, uniones/intersecciones/diferencias) y luego correr el dataset completo solo si los archivos y PostgreSQL están disponibles.
- Entregar scripts, CSV de mediciones, PNG de gráficos, `lab09_overleaf.tex` completo y, si se puede compilar, el PDF. Indicar qué falta ejecutar en la computadora del estudiante si este entorno no tiene acceso a su PostgreSQL/dataset; en tal caso no presentar el informe como finalizado.
- No subir nada a GitHub sin una solicitud expresa posterior.

## Criterio de terminado

El laboratorio está terminado cuando la carga y el BoW están verificados en PostgreSQL, la búsqueda booleana y la de coseno dan resultados equivalentes entre enfoques, las mediciones cubren cinco o más tamaños con varias repeticiones, hay dos gráficos respaldados por los datos guardados y el informe LaTeX completo compila e incluye el análisis de 300 palabras o más. Si falta el dataset o acceso a PostgreSQL, terminar todo lo que se pueda probar localmente y dejar comandos exactos para completar la ejecución real; marcar el informe como pendiente de mediciones, sin presentar datos inventados.
