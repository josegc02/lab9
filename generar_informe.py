"""Genera el informe LaTeX usando exclusivamente resultados medidos."""

import csv
import json
from pathlib import Path


ROOT = Path(__file__).parent
OUT = ROOT / "resultados"


def read_csv(name):
    with (OUT / name).open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def esc(text):
    return (str(text).replace("\\", r"\textbackslash{}")
            .replace("&", r"\&").replace("%", r"\%")
            .replace("_", r"\_").replace("#", r"\#"))


def main():
    validation = json.loads((OUT / "validacion.json").read_text(encoding="utf-8"))
    meta = json.loads((OUT / "metodologia.json").read_text(encoding="utf-8"))
    averages = read_csv("promedios.csv")
    builds = read_csv("construccion_indice.csv")
    lookup = {(int(r["documents"]), r["kind"], r["method"]): float(r["seconds"])
              for r in averages}
    sizes = meta["sizes"]
    first = sizes[0]
    last = sizes[-1]
    def value(n, kind, method):
        return lookup[(n, kind, method)]

    boolean_table = []
    for i, row in enumerate(validation["boolean"], 1):
        boolean_table.append(f'{i} & {esc(row["query"])} & {row["count"]} & Sí ' + r'\\')
    cosine_table = []
    for row in validation["cosine"][:3]:
        ids = ", ".join(str(x[0]) for x in row["top5"])
        scores = ", ".join(f'{x[1]:.4f}' for x in row["top5"])
        cosine_table.append(f'{esc(row["query"])} & {ids} & {scores} ' + r'\\')
    timing_table = []
    for n in sizes:
        timing_table.append(
            f'{n} & {value(n,"boolean","linear"):.6f} & '
            f'{value(n,"boolean","index"):.6f} & '
            f'{value(n,"cosine","linear"):.6f} & '
            f'{value(n,"cosine","index"):.6f} ' + r'\\')
    build_table = []
    for row in builds:
        build_table.append(f'{row["documents"]} & {float(row["build_seconds"]):.5f} & '
                           f'{row["terms"]} & {row["postings"]} ' + r'\\')
    breakpoints = {}
    for kind in ("boolean", "cosine"):
        winning = [n for n in sizes if value(n, kind, "index") < value(n, kind, "linear")]
        breakpoints[kind] = str(winning[0]) if winning else "ninguno en el rango medido"
    b_ratio = value(last, "boolean", "linear") / value(last, "boolean", "index")
    c_ratio = value(last, "cosine", "linear") / value(last, "cosine", "index")
    first_build = float(builds[0]["build_seconds"])
    last_build = float(builds[-1]["build_seconds"])
    analysis = rf"""
La búsqueda booleana lineal recorre todos los documentos y evalúa cada consulta sobre su
diccionario de términos. Para una consulta de longitud fija su costo es $O(N)$; si se
explicita el número $q$ de términos, es $O(Nq)$. La búsqueda booleana con índice lee las
listas de los términos solicitados y combina identificadores ordenados: su costo de
consulta depende de las longitudes de esas listas, aproximadamente
$O(\sum_{{t\in Q}} |L(t)|)$, más la ordenación de la salida cuando corresponde. No es
independiente de $N$: un término muy común puede producir una lista casi tan grande
como la colección. En {first} documentos medimos {value(first,'boolean','linear'):.6f} s
para el recorrido lineal y {value(first,'boolean','index'):.6f} s para el índice; en
{last} documentos, {value(last,'boolean','linear'):.6f} s y
{value(last,'boolean','index'):.6f} s, respectivamente. La tendencia favorece al índice,
aunque pequeñas oscilaciones entre tamaños muestran que no debemos interpretar cada
punto como una ley exacta del tiempo de ejecución.

El coseno lineal también visita los $N$ documentos. Con los pesos y normas
precalculados, su trabajo por consulta es $O(Nq)$; el coseno con índice visita solo
las listas de los términos de la consulta y acumula los candidatos, con costo cercano
a $O(\sum_{{t\in Q}} |L(t)| + C\log C)$ por el ordenamiento de $C$ candidatos.
En {first} documentos sus promedios fueron {value(first,'cosine','linear'):.6f} s y
{value(first,'cosine','index'):.6f} s; en {last}, {value(last,'cosine','linear'):.6f} s y
{value(last,'cosine','index'):.6f} s. En el tamaño mayor, los cocientes lineal/índice
son {b_ratio:.2f} para booleana y {c_ratio:.2f} para coseno. Estos cocientes describen
solo las consultas y la máquina medidas, no una mejora universal.

El primer tamaño ensayado donde el índice ganó fue {breakpoints['boolean']} documentos
para booleana y {breakpoints['cosine']} para coseno. Por tanto, en esta muestra los puntos
observados coinciden; no podemos ubicar un punto de quiebre más preciso por debajo del
primer tamaño. La construcción del índice quedó fuera de las curvas de consulta y se
midió aparte: {first_build:.5f} s para {first} documentos y {last_build:.5f} s para
{last}. Para una colección pequeña o una sola consulta, ese costo puede superar el
ahorro de búsqueda. Además, el tiempo de construcción fluctúa por carga del sistema,
asignación de memoria y ejecución de Python; por ello no debe sumarse silenciosamente
a una sola curva. Si se reutiliza el índice para muchas consultas, el costo inicial
se amortiza. El BoW y las estadísticas IDF/norma también se prepararon antes de medir
ambas rutas de coseno, de modo que las curvas comparan únicamente la consulta.

En los seis tamaños, las seis consultas booleanas devolvieron exactamente los mismos
identificadores. Las tres consultas de coseno devolvieron el mismo top 5 en el mismo
orden, con scores iguales dentro de tolerancia absoluta y relativa $10^{{-12}}$.
No observamos diferencias de ranking ni de resultados. Una variación minúscula de
coma flotante sería posible si cambia el orden de suma: el índice acumula aportes por
lista, mientras el recorrido lineal suma por documento. El desempate fija score
descendente e identificador ascendente. Consultas sin términos compartidos devuelven
una lista vacía y un $k$ mayor que los candidatos devuelve solo los candidatos existentes.

El índice completo contiene {builds[-1]['terms']} términos distintos y
{builds[-1]['postings']} entradas documento--frecuencia. Si la colección creciera
100 veces con distribución comparable, las entradas podrían acercarse a
{100 * int(builds[-1]['postings']):,}, además de diccionarios, cadenas, pesos y texto;
el uso de RAM, las pausas de memoria y el tiempo de reconstrucción serían problemas
prácticos. Una alternativa es guardar las listas invertidas en un índice persistente
en disco, por ejemplo una tabla PostgreSQL de término, documento y frecuencia con
índice B-tree, o un motor de búsqueda especializado. Allí se pueden actualizar
documentos por lotes y consultar sin cargar todas las listas en memoria. La elección
exigiría medir también el costo de E/S y mantenimiento del índice.
""".replace(",", ",")
    # La coma de miles no es un separador decimal en la prosa española.
    analysis = analysis.replace(f"{100 * int(builds[-1]['postings']):,}",
                                str(100 * int(builds[-1]['postings'])))
    template = r"""\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[spanish]{babel}
\usepackage{lmodern}
\usepackage{geometry}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{amsmath}
\usepackage{float}
\usepackage{xcolor}
\usepackage{hyperref}
\geometry{margin=2.4cm}
\hypersetup{colorlinks=true,linkcolor=blue,urlcolor=blue}
\newcommand{\codigo}[1]{\texttt{#1}}
\title{Laboratorio 09\\Bag of Words, similitud de coseno e índice invertido}
\author{Juan Marcos Guerrero Cueva\\Base de Datos II\\Prof. Heider Sánchez}
\date{16 de octubre de 2026}
\begin{document}
\maketitle
\begin{abstract}
Se implementaron y compararon cuatro rutas de recuperación textual sobre __DOCUMENTS__
noticias reales. El informe presenta el preprocesamiento, la validación de resultados,
mediciones repetidas sobre seis tamaños de colección y un análisis sustentado por los CSV
entregados con el código.
\end{abstract}
\tableofcontents
\clearpage

\section{P1. Configuración y carga de datos}
Se utilizó PostgreSQL __POSTGRES__ en __PLATFORM__, Python __PYTHON__, pandas
__PANDAS__, NLTK __NLTK__ y Matplotlib __MATPLOTLIB__. La tabla
\codigo{noticias} tiene columnas \codigo{id}, \codigo{url}, \codigo{contenido},
\codigo{categoria} y \codigo{bag\_of\_words JSONB}; \codigo{stopwords} tiene
\codigo{id} y \codigo{word UNIQUE}. \codigo{crear\_bd.py} crea las tablas si no
existen y \codigo{carga.py} importa \codigo{news\_es.csv} y \codigo{stoplist.txt}
solo cuando las tablas están vacías. Se verificaron __DOCUMENTS__ noticias y
608 stopwords. Los identificadores de noticias van de 1 a __DOCUMENTS__. No se
duplicó la carga ya presente. La conexión se toma de \codigo{.env}, que Git ignora.

\section{P2. Preprocesamiento y Bag of Words}
\codigo{preprocess(text)} pasa a minúsculas, extrae secuencias de letras Unicode,
elimina las stopwords leídas de PostgreSQL y aplica \codigo{SnowballStemmer}
en español. Se conservan las tildes; signos y números se descartan. \codigo{NULL}
y texto vacío producen una lista vacía. \codigo{compute\_bow(text)} cuenta cada
término resultante. Por ejemplo, ``Banco, banco! 123'' produce
\codigo{\{'banc': 2\}}. La misma función normaliza documentos y consultas.
\codigo{update\_bow\_in\_db(dataframe)} guarda cada diccionario como JSONB
con parámetros SQL y una transacción. La función \codigo{fetch\_data\_bow()}
lee \codigo{noticias}; el comentario del enunciado sobre \codigo{noticias\_bow}
no corresponde a una tabla creada. Se verificó que los __DOCUMENTS__ BoW son no nulos.
\begin{verbatim}
tokens = preprocess(text)
bow = dict(Counter(tokens))
UPDATE noticias SET bag_of_words = %s WHERE id = %s
\end{verbatim}
El script de ejecución muestra las primeras diez filas abreviadas. La validación
incluye el texto vacío, una frecuencia conocida y una consulta sin términos presentes.

\section{P3. Búsqueda booleana}
\codigo{boolean\_search\_linear} evalúa cada BoW. \codigo{InvertedIndex}
construye listas \codigo{(doc\_id, tf)} y resuelve \codigo{AND}, \codigo{OR}
y \codigo{AND\_NOT} mediante intersección, unión y diferencia de IDs. El analizador
acepta paréntesis y da prioridad a \codigo{AND} y \codigo{AND-NOT} sobre
\codigo{OR}. Ambos métodos devuelven IDs únicos ordenados de forma ascendente.
\begin{table}[H]\centering\small
\begin{tabular}{p{0.6cm}p{8.8cm}rr}\toprule
Nº & Consulta & Coincidencias & ¿Iguales?\\\midrule
__BOOLEAN_TABLE__
\bottomrule\end{tabular}
\caption{Seis pruebas booleanas sobre los __DOCUMENTS__ documentos.}
\end{table}

\section{P4. Similitud de coseno}
Para un término $t$ en una colección de $N$ documentos se usó
$\mathrm{idf}(t)=\ln((N+1)/(\mathrm{df}(t)+1))+1$ y
$w_{t,d}=\mathrm{tf}(t,d)\,\mathrm{idf}(t)$.
El score es $\sum_t w_{t,q}w_{t,d}/(\lVert q\rVert_2\lVert d\rVert_2)$.
Las dos rutas comparten IDF y normas. La lineal examina todos los BoW; la del
índice acumula solamente documentos en las listas de términos de la consulta.
Se ordena por score descendente e ID ascendente. Si no hay coincidencias o la
norma es cero, se devuelve lista vacía. Un \codigo{top\_k} grande devuelve los
candidatos existentes.
\begin{table}[H]\centering\footnotesize
\begin{tabular}{p{4.5cm}p{4.2cm}p{5cm}}\toprule
Consulta & IDs top 5 & Scores top 5\\\midrule
__COSINE_TABLE__
\bottomrule\end{tabular}
\caption{Resultados reales; ambas rutas dieron los mismos IDs y scores con tolerancia $10^{-12}$.}
\end{table}

\section{P5. Experimento y gráficos}
Se tomaron los primeros $N$ documentos por ID ascendente, con tamaños
__SIZES__. Para cada tamaño se construyó un índice propio sobre exactamente el
mismo subconjunto usado por la ruta lineal. Se verificó la igualdad de resultados
antes de medir. Se hizo un calentamiento y luego __REPEATS__ repeticiones de cada
una de las seis consultas booleanas y tres de coseno. Se midió con
\codigo{time.perf\_counter()}; el CSV crudo guarda una fila por ejecución.
Cada punto es el promedio de todas las consultas y repeticiones del tipo indicado.
El tiempo de construcción se informa aparte. El BoW, IDF y normas estaban
preparados antes de cronometrar consultas. El orden de ejecución fue fijo;
las variaciones del sistema pueden afectar los microtiempos.
\begin{table}[H]\centering\small
\begin{tabular}{rrrrr}\toprule
$N$ & Booleano lineal & Booleano índice & Coseno lineal & Coseno índice\\\midrule
__TIMING_TABLE__
\bottomrule\end{tabular}
\caption{Tiempo promedio por consulta en segundos; fuente: \codigo{resultados/promedios.csv}.}
\end{table}
\begin{table}[H]\centering\small
\begin{tabular}{rrrr}\toprule
$N$ & Construcción (s) & Términos & Postings\\\midrule
__BUILD_TABLE__
\bottomrule\end{tabular}
\caption{Costo y tamaño del índice en memoria; fuente: \codigo{resultados/construccion\_indice.csv}.}
\end{table}
\begin{figure}[H]\centering
\includegraphics[width=0.95\linewidth]{resultados/booleana.png}
\caption{Tiempo promedio de la búsqueda booleana; construcción excluida.}
\end{figure}
\begin{figure}[H]\centering
\includegraphics[width=0.95\linewidth]{resultados/coseno.png}
\caption{Tiempo promedio de similitud de coseno; construcción excluida.}
\end{figure}

\section{P6. Análisis de resultados}
__ANALYSIS__

\section{Reproducción}
Desde PowerShell, en la carpeta del proyecto, ejecutar en orden:
\begin{verbatim}
.\.venv\Scripts\python.exe crear_bd.py
.\.venv\Scripts\python.exe carga.py
.\.venv\Scripts\python.exe -m unittest -v test_laboratorio.py
.\.venv\Scripts\python.exe ejecutar_lab.py all --repeats __REPEATS__
.\.venv\Scripts\python.exe generar_informe.py
\end{verbatim}
El primer comando comprueba o crea el esquema; el segundo carga los archivos
si las tablas están vacías; el tercero verifica casos pequeños; el cuarto
actualiza BoW faltantes, comprueba equivalencia y mide; el quinto reconstruye
este informe a partir de los CSV. Para compilar en Overleaf, subir este \codigo{.tex}
y la carpeta \codigo{resultados} con los dos PNG. Los datos crudos y el
script permiten repetir y auditar el experimento.
\end{document}
"""
    replacements = {
        "__DOCUMENTS__": str(validation["documents"]),
        "__POSTGRES__": esc(meta["postgresql"]),
        "__PLATFORM__": esc(meta["platform"]).replace("-", r"-\allowbreak{}"),
        "__PYTHON__": esc(meta["python"]),
        "__PANDAS__": esc(meta["pandas"]),
        "__NLTK__": esc(meta["nltk"]),
        "__MATPLOTLIB__": esc(meta["matplotlib"]),
        "__BOOLEAN_TABLE__": "\n".join(boolean_table),
        "__COSINE_TABLE__": "\n".join(cosine_table),
        "__SIZES__": ", ".join(map(str, sizes)),
        "__REPEATS__": str(meta["repeats"]),
        "__TIMING_TABLE__": "\n".join(timing_table),
        "__BUILD_TABLE__": "\n".join(build_table),
        "__ANALYSIS__": analysis,
    }
    for key, value in replacements.items():
        template = template.replace(key, value)
    target = ROOT / "lab09_overleaf.tex"
    target.write_text(template, encoding="utf-8")
    print("Generado:", target.name)
    print("Palabras del análisis:", len(analysis.split()))


if __name__ == "__main__":
    main()
