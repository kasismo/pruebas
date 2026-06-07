import random
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sistema metrico curricular", page_icon="📝")


#--------------------
# MATERIA Y HORARIOS
#--------------------
class materia:
    def __init__(self, nombre, horario):
        self.nombre = nombre
        self.horario = horario

materia1 = materia("Biologia", "7:50/9:15")
materia2 = materia("Fisica", "10:30/11:45")

print("Las materias que se cursaron ésta mañana son; \n")
print(materia1.nombre, materia1.horario)
print(materia2.nombre, materia2.horario)

st.write(materia1.nombre, materia1.horario)
st.write(materia2.nombre, materia2.horario)

#--------------
# BIBLIOGRAFIA
#--------------
class enciclopedia:
    def __init__(self, página, tema):
        self.página = página
        self.tema = tema 

enciclopediabiologia = enciclopedia(121, "Esqueleto humano")
enciclopediafisica = enciclopedia(22, "Masa y aceleración")

#-------------------------
# ALUMNADO, NOTAS Y DEMÁS
#-------------------------
class alumno:
    def __init__(self, nombre, cursa, nota):
        self.nombre = nombre
        self.cursa = cursa
        self.nota = nota


alumno1 = alumno("Hugo", "biologia", 9)
alumno2 = alumno("Paco", "biologia", 8)
alumno3 = alumno("Isabel", "fisica", 8)
alumno4 = alumno("Maria", "fisica", 9)
alumno5 = alumno("Lucia", "quimica", 7)
alumno6 = alumno("Sofia", "quimica", 6)
alumno7 = alumno("Diego", "matematicas", 3)
alumno8 = alumno("Alvaro", "matematicas", 4)
alumno9 = alumno("Sandra", "historia", 7)
alumno10 = alumno("Marta", "historia", 8)
alumno11 = alumno("Jorge", "geografia", 5)
alumno12 = alumno("Sara", "geografia", 6)
alumno13 = alumno("Ricardo", "ingles", 9)
alumno14 = alumno("Clara", "tecnologia", 2)
alumno15 = alumno("Manuel", "arte", 10)
alumno16 = alumno("Lucia", "musica", 10)
alumno17 = alumno("Alberto", "educacion fisica", 4)
alumno18 = alumno("Marta", "filosofia", 5)
alumno19 = alumno("Sofia", "biologia", 8)
alumno20 = alumno("Pablo", "fisica", 7)
alumno21 = alumno("Laura", "quimica", 6)
alumno22 = alumno("David", "matematicas", 5)
alumno23 = alumno("Sara", "historia", 7)
alumno24 = alumno("Jorge", "geografia", 6)
alumno25 = alumno("Marta", "ingles", 9)
alumno26 = alumno("Alvaro", "arte", 10)
alumno27 = alumno("Lucia", "musica", 10)
alumno28 = alumno("Diego", "tecnologia", 3)
alumno29 = alumno("Sofia", "educacion fisica", 4)
alumno30 = alumno("Alberto", "filosofia", 5)
alumno31 = alumno("Marta", "biologia", 8)
alumno32 = alumno("Pablo", "fisica", 7)
alumno33 = alumno("Laura", "quimica", 6)
alumno34 = alumno("David", "matematicas", 5)
alumno35 = alumno("Sara", "historia", 7)
alumno36 = alumno("Jorge", "geografia", 6)
alumno37 = alumno("Marta", "ingles", 9)
alumno38 = alumno("Alvaro", "arte", 10)
alumno39 = alumno("Lucia", "musica", 10)
alumno40 = alumno("Diego", "tecnologia", 3)
alumno41 = alumno("Sofia", "educacion fisica", 4)
alumno42 = alumno("Alberto", "filosofia", 5)
alumno43 = alumno("Marta", "biologia", 8)
alumno44 = alumno("Pablo", "fisica", 7)
alumno45 = alumno("Laura", "quimica", 6)
alumno46 = alumno("David", "matematicas", 5)
alumno47 = alumno("Sara", "historia", 7)
alumno48 = alumno("Jorge", "geografia", 6)
alumno49 = alumno("Marta", "ingles", 9)
alumno50 = alumno("Alvaro", "arte", 10)
alumno51 = alumno("Lucia", "musica", 10)
alumno52 = alumno("Diego", "tecnologia", 3)
alumno53 = alumno("Sofia", "educacion fisica", 4)
alumno54 = alumno("Alberto", "filosofia", 5)

lista_alumnos = [alumno1, alumno2, alumno3, alumno4, alumno5, alumno6, alumno7, alumno8, alumno9, alumno10,
alumno11, alumno12, alumno13, alumno14, alumno15, alumno16, alumno17, alumno18, alumno19, alumno20,
alumno21, alumno22, alumno23, alumno24, alumno25, alumno26, alumno27, alumno28, alumno29, alumno30,
alumno31, alumno32, alumno33, alumno34, alumno35, alumno36, alumno37, alumno38, alumno39, alumno40,
alumno41, alumno42, alumno43, alumno44, alumno45, alumno46, alumno47, alumno48, alumno49,
alumno50, alumno51, alumno52, alumno53, alumno54]


#---------------------------------------------
# PRUEBA DE LOGICA, ESTILO ASIGNATURA Y SALÓN
#---------------------------------------------

input_value = input("El alumno qué cursa: ")
if input_value == "biologia":
    print(alumno1.nombre, (f"del curso de {alumno1.cursa} debería tener la enciclopedia del {enciclopediabiologia.tema} para poder estudiar"))

elif input_value == "fisica":
    print(alumno1.nombre, (f"Debería de cambiar de asiento con {alumno3.nombre} para poder estudiar su enciclopedia"))

st.write()

#----------------------------------
# LIBRO DISTRIBUICIÓN X ASIGNATURA
#----------------------------------
class libro:
    def __init__(self, numero, asignatura):
        self.numero = numero
        self.asignatura = asignatura


libro1 = libro(1, "biologia")
libro2 = libro(2, "fisica")
libro3 = libro(3, "quimica")
libro4 = libro(4, "matematicas")
libro5 = libro(5, "historia")
libro6 = libro(6, "geografia")
libro7 = libro(7, "ingles")
libro8 = libro(8, "arte")
libro9 = libro(9, "musica")
libro10 = libro(10, "tecnologia")
libro11 = libro(11, "educacion fisica")
libro12 = libro(12, "filosofia")
libro13 = libro(13, "biologia")
libro14 = libro(14, "fisica")
libro15 = libro(15, "quimica")
libro16 = libro(16, "matematicas")
libro17 = libro(17, "historia")
libro18 = libro(18, "geografia")
libro19 = libro(19, "ingles")
libro20 = libro(20, "arte")
libro21 = libro(21, "musica")
libro22 = libro(22, "tecnologia")
libro23 = libro(23, "biologia")
libro24 = libro(24, "fisica")
libro25 = libro(25, "quimica")
libro26 = libro(26, "matematicas")
libro27 = libro(27, "historia")
libro28 = libro(28, "geografia")
libro29 = libro(29, "ingles")
libro30 = libro(30, "arte")
libro31 = libro(31, "musica")
libro32 = libro(32, "tecnologia")
libro33 = libro(33, "musica")
libro34 = libro(34, "tecnologia")
libro35 = libro(35, "educacion fisica")
libro36 = libro(36, "filosofia")
libro37 = libro(37, "biologia")
libron38 = libro(38, "fisica")
libro39 = libro(39, "quimica")
libro40 = libro(40, "matematicas")
libro41 = libro(41, "historia")
libro42 = libro(42, "botánica")
libro43 = libro(43, "geografia")
libro44 = libro(44, "ingles")
libro45 = libro(45, "arte")
libro46 = libro(46, "musica")
libro47 = libro(47, "tecnologia")
libro48 = libro(48, "educacion fisica")
libro49 = libro(49, "filosofia")
libro50 = libro(50, "biologia")
libro51 = libro(51, "fisica")
libro52 = libro(52, "quimica")
libro53 = libro(53, "matematicas")
libro54 = libro(54, "historia")


lista_libros = [libro1, libro2, libro3, libro4, libro5, libro6, libro7, libro8, libro9, libro10,
libro11, libro12, libro13, libro14, libro15, libro16, libro17, libro18, libro19, libro20,
libro21, libro22, libro23, libro24, libro25, libro26, libro27, libro28, libro29, libro30,
libro31, libro32, libro33, libro34, libro35, libro36, libro37, libron38, libro39, libro40,
libro41, libro42, libro43, libro44, libro45, libro46, libro47, libro48, libro49, libro50,
libro51, libro52, libro53, libro54]

#-------------------------------------
# PATRÓN ALEATORIA DE LIBRO X MATERIA
#-------------------------------------
for numero in lista_libros:
    select = random.choice(lista_libros)

print(f"El libro de la evaluación es el número {select.numero} de la asignatura {select.asignatura}")

#----------------------------------------------
# BUSCADOR DE ALUMNOS APROBADOS O DESAPROBADOS
#----------------------------------------------
for cursa in lista_alumnos:
    if cursa.cursa == "arte" and cursa.nota >= 7:
        print(f"El alumno {cursa.nombre} cursa {cursa.cursa} y ha aprobado la materia con un {cursa.nota}")

#--------------------------------
# SEGUNDA FASE, BUSQUEDA ROBUSTA
#--------------------------------
input_value2 = input("¿En cuál asignatura cursa el alumno? ")
if input_value2 in ["biologia", "fisica", "quimica", "matematicas", "historia", "geografia", "ingles", "arte", "musica", "tecnologia", "educacion fisica", "filosofia"]:
    for cursa in lista_alumnos:
        if cursa.cursa == input_value2 and cursa.nota >= 7:
            print(f"El alumno {cursa.nombre} cursa {cursa.cursa} y ha aprobado la materia con un {cursa.nota}")

        elif cursa.cursa == input_value2 and cursa.nota < 7:
            print(f"El alumno {cursa.nombre} cursa {cursa.cursa} y ha suspendido la materia con un {cursa.nota}")

print(len(lista_libros))

df_alumnos = pd.DataFrame([
    {
        "nombre": alumno.nombre,
        "cursa": alumno.cursa,
        "nota": alumno.nota
    }
    for alumno in lista_alumnos
])

print(df_alumnos.head())


promedios = df_alumnos.groupby("cursa")["nota"].mean()

print(promedios)

cantidad = df_alumnos["cursa"].value_counts()

print(cantidad)

aprobados = df_alumnos[df_alumnos["nota"] >= 7]



desaprobados = df_alumnos.query("nota < 7")


mejores = df_alumnos.loc[
    df_alumnos.groupby("cursa")["nota"].idxmax()
]

print(mejores)

