import random
import pandas as pd
import streamlit as st

# ==========================================
# CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(page_title="Sistema Métrico Curricular", page_icon="📝", layout="wide")
st.title("📝 Sistema Métrico Curricular")

# ==========================================
# 1. LA BÓVEDA DE DATOS (BACKEND PURO)
# ==========================================
# Aquí mantenemos tus clases de Python intactas. Es la lógica de negocio pura.

class materia:
    def __init__(self, nombre, horario):
        self.nombre = nombre
        self.horario = horario

materia1 = materia("Biología", "7:50/9:15")
materia2 = materia("Física", "10:30/11:45")

class enciclopedia:
    def __init__(self, página, tema):
        self.página = página
        self.tema = tema 

enciclopediabiologia = enciclopedia(121, "Esqueleto humano")
enciclopediafisica = enciclopedia(22, "Masa y aceleración")

class alumno:
    def __init__(self, nombre, cursa, nota):
        self.nombre = nombre
        self.cursa = cursa
        self.nota = nota

# Instanciamos los 54 alumnos
alumno1 = alumno("Hugo", "biologia", 9); alumno2 = alumno("Paco", "biologia", 8); alumno3 = alumno("Isabel", "fisica", 8)
alumno4 = alumno("Maria", "fisica", 9); alumno5 = alumno("Lucia", "quimica", 7); alumno6 = alumno("Sofia", "quimica", 6)
alumno7 = alumno("Diego", "matematicas", 3); alumno8 = alumno("Alvaro", "matematicas", 4); alumno9 = alumno("Sandra", "historia", 7)
alumno10 = alumno("Marta", "historia", 8); alumno11 = alumno("Jorge", "geografia", 5); alumno12 = alumno("Sara", "geografia", 6)
alumno13 = alumno("Ricardo", "ingles", 9); alumno14 = alumno("Clara", "tecnologia", 2); alumno15 = alumno("Manuel", "arte", 10)
alumno16 = alumno("Lucia", "musica", 10); alumno17 = alumno("Alberto", "educacion fisica", 4); alumno18 = alumno("Marta", "filosofia", 5)
alumno19 = alumno("Sofia", "biologia", 8); alumno20 = alumno("Pablo", "fisica", 7); alumno21 = alumno("Laura", "quimica", 6)
alumno22 = alumno("David", "matematicas", 5); alumno23 = alumno("Sara", "historia", 7); alumno24 = alumno("Jorge", "geografia", 6)
alumno25 = alumno("Marta", "ingles", 9); alumno26 = alumno("Alvaro", "arte", 10); alumno27 = alumno("Lucia", "musica", 10)
alumno28 = alumno("Diego", "tecnologia", 3); alumno29 = alumno("Sofia", "educacion fisica", 4); alumno30 = alumno("Alberto", "filosofia", 5)
alumno31 = alumno("Marta", "biologia", 8); alumno32 = alumno("Pablo", "fisica", 7); alumno33 = alumno("Laura", "quimica", 6)
alumno34 = alumno("David", "matematicas", 5); alumno35 = alumno("Sara", "historia", 7); alumno36 = alumno("Jorge", "geografia", 6)
alumno37 = alumno("Marta", "ingles", 9); alumno38 = alumno("Alvaro", "arte", 10); alumno39 = alumno("Lucia", "musica", 10)
alumno40 = alumno("Diego", "tecnologia", 3); alumno41 = alumno("Sofia", "educacion fisica", 4); alumno42 = alumno("Alberto", "filosofia", 5)
alumno43 = alumno("Marta", "biologia", 8); alumno44 = alumno("Pablo", "fisica", 7); alumno45 = alumno("Laura", "quimica", 6)
alumno46 = alumno("David", "matematicas", 5); alumno47 = alumno("Sara", "historia", 7); alumno48 = alumno("Jorge", "geografia", 6)
alumno49 = alumno("Marta", "ingles", 9); alumno50 = alumno("Alvaro", "arte", 10); alumno51 = alumno("Lucia", "musica", 10)
alumno52 = alumno("Diego", "tecnologia", 3); alumno53 = alumno("Sofia", "educacion fisica", 4); alumno54 = alumno("Alberto", "filosofia", 5)

lista_alumnos = [alumno1, alumno2, alumno3, alumno4, alumno5, alumno6, alumno7, alumno8, alumno9, alumno10,
alumno11, alumno12, alumno13, alumno14, alumno15, alumno16, alumno17, alumno18, alumno19, alumno20,
alumno21, alumno22, alumno23, alumno24, alumno25, alumno26, alumno27, alumno28, alumno29, alumno30,
alumno31, alumno32, alumno33, alumno34, alumno35, alumno36, alumno37, alumno38, alumno39, alumno40,
alumno41, alumno42, alumno43, alumno44, alumno45, alumno46, alumno47, alumno48, alumno49,
alumno50, alumno51, alumno52, alumno53, alumno54]

class libro:
    def __init__(self, numero, asignatura):
        self.numero = numero
        self.asignatura = asignatura

# Generamos 54 libros de forma rápida usando listas de comprensión
asignaturas_libros = ["biologia", "fisica", "quimica", "matematicas", "historia", "geografia", "ingles", "arte", "musica", "tecnologia", "educacion fisica", "filosofia"] * 5
lista_libros = [libro(i+1, asignaturas_libros[i]) for i in range(54)]


# ==========================================
# 2. EL FRONTEND (INTERFAZ VISUAL EN STREAMLIT)
# ==========================================

# ------------------------------------------
# SECCIÓN: Horarios
# [TRADUCCIÓN]: print() -> st.info() usando st.columns() para diseño web
# ------------------------------------------
st.header("🕒 Materias de esta mañana")
col1, col2 = st.columns(2)
with col1:
    st.info(f"**{materia1.nombre}**: {materia1.horario}")
with col2:
    st.info(f"**{materia2.nombre}**: {materia2.horario}")

st.divider()

# ------------------------------------------
# SECCIÓN: Prueba de Lógica
# [TRADUCCIÓN]: input() -> st.selectbox()
# ------------------------------------------
st.header("🧠 Prueba Lógica Por Asignatura")
st.write("Selecciona una materia para ver la recomendación del sistema: ")

input_value = st.selectbox("Elige la materia:", ["biologia", "fisica", "quimica", "matematicas"])

if input_value == "biologia":
    st.success(f"**{alumno1.nombre}** del curso de {alumno1.cursa} debería tener la enciclopedia de '{enciclopediabiologia.tema}' para poder estudiar.")
elif input_value == "fisica":
    st.warning(f"**{alumno1.nombre}** debería cambiar de asiento con **{alumno3.nombre}** para poder estudiar su enciclopedia.")

st.divider()

# ------------------------------------------
# SECCIÓN: Sorteo de Evaluación
# [TRADUCCIÓN]: for ... print() -> st.button() + random.choice() + st.success()
# ------------------------------------------
st.header("📚 Sorteo de Evaluación")
st.markdown("Presiona el botón para elegir un libro al azar de la biblioteca.")

if st.button("🎲 Generar Libro Aleatorio", type="primary"):
    select = random.choice(lista_libros)
    st.success(f"El libro de la evaluación es el número **{select.numero}** de la asignatura **{select.asignatura.capitalize()}**.")

st.divider()

# ------------------------------------------
# SECCIÓN: Búsqueda Robusta y DataFrames
# [TRADUCCIÓN]: Búsqueda con loop for + print() -> Filtrado de Pandas + st.dataframe()
# ------------------------------------------
st.header("📊 Análisis del Alumnado")

# Convertimos la lista de objetos de Python a un DataFrame tabular de Pandas
df_alumnos = pd.DataFrame([
    {"Nombre": alumno.nombre, "Asignatura": alumno.cursa.capitalize(), "Nota": alumno.nota}
    for alumno in lista_alumnos
])

# Creamos un filtro dinámico extrayendo las materias únicas directamente del DataFrame
asignaturas_disponibles = df_alumnos["Asignatura"].unique().tolist()
input_value2 = st.selectbox("¿De cuál asignatura quieres ver los resultados?", asignaturas_disponibles)

# El motor de Pandas filtra instantáneamente sin necesidad de bucles 'for'
df_filtrado = df_alumnos[df_alumnos["Asignatura"] == input_value2]

aprobados = df_filtrado[df_filtrado["Nota"] >= 7]
desaprobados = df_filtrado[df_filtrado["Nota"] < 7]

# Mostramos los resultados en paralelo
colA, colB = st.columns(2)
with colA:
    st.subheader("✅ Aprobados")
    st.dataframe(aprobados, use_container_width=True, hide_index=True)

with colB:
    st.subheader("❌ Suspendidos")
    st.dataframe(desaprobados, use_container_width=True, hide_index=True)

# ------------------------------------------
# SECCIÓN: Estadísticas Generales (Agrupaciones)
# [TRADUCCIÓN]: st.table(promedios) apilados -> st.tabs() para ahorrar espacio vertical
# ------------------------------------------
st.subheader("📈 Estadísticas Generales")
tab1, tab2, tab3 = st.tabs(["Promedios Generales", "Volumen por Materia", "Cuadro de Honor"])

with tab1:
    promedios = df_alumnos.groupby("Asignatura")["Nota"].mean().reset_index()
    promedios["Nota"] = promedios["Nota"].round(2) # Redondeamos a 2 decimales
    st.dataframe(promedios, use_container_width=True, hide_index=True)

with tab2:
    cantidad = df_alumnos["Asignatura"].value_counts().reset_index()
    cantidad.columns = ["Asignatura", "Cantidad de Alumnos"]
    st.dataframe(cantidad, use_container_width=True, hide_index=True)

with tab3:
    mejores = df_alumnos.loc[df_alumnos.groupby("Asignatura")["Nota"].idxmax()]
    st.dataframe(mejores, use_container_width=True, hide_index=True)
