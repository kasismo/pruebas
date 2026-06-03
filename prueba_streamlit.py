import streamlit as st
import pandas as pd
import numpy as np
import datetime
import time

# 1. CONFIGURACIÓN DE LA PÁGINA (Debe ser el primer comando de Streamlit)
st.set_page_config(
    page_title="Cheat Sheet de Streamlit",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. BARRA LATERAL (Sidebar)
st.sidebar.title("Menú Lateral")
st.sidebar.write("Puedes usar `st.sidebar` para colocar cualquier elemento aquí.")
modo = st.sidebar.radio("Tema preferido:", ["Claro", "Oscuro", "Automático"])
st.sidebar.divider() # Línea divisoria

# 3. TÍTULO Y DESCRIPCIÓN
st.title("🌟 Mega Demostración de Streamlit")
st.write("Este dashboard utiliza la gran mayoría de los comandos de la librería para que veas cómo funcionan en vivo.")

# 4. CONTENEDORES Y LAYOUTS (Pestañas)
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📝 Texto", "📊 Datos y Gráficos", "🖱️ Inputs (Formularios)", "🖼️ Multimedia", "⚙️ Estado y Layouts"
])

# --- PESTAÑA 1: ELEMENTOS DE TEXTO ---
with tab1:
    st.header("Comandos de Texto")
    st.subheader("Esto es un subtítulo (st.subheader)")
    st.markdown("Puedes usar **Markdown** para texto en *cursiva*, **negrita** o añadir [enlaces](https://streamlit.io).")
    st.caption("Esto es un 'caption' (texto pequeño ideal para notas al pie).")
    
    st.write("El comando `st.write()` es la navaja suiza. Intenta adivinar qué le pasas y lo renderiza.")
    
    st.code("""
    # Esto es un bloque de código (st.code)
    def hola_mundo():
        print("Hola Streamlit!")
    """, language="python")
    
    st.latex(r"\int_{a}^{b} x^2 \,dx") # Fórmulas matemáticas

# --- PESTAÑA 2: DATOS Y GRÁFICOS ---
with tab2:
    st.header("Visualización de Datos")
    
    # Generamos datos de prueba
    df = pd.DataFrame(
        np.random.randn(10, 3),
        columns=['Columna A', 'Columna B', 'Columna C']
    )
    
    col_data1, col_data2 = st.columns(2)
    
    with col_data1:
        st.subheader("Dataframe Interactivo")
        st.dataframe(df, use_container_width=True) # Permite ordenar y redimensionar
        
    with col_data2:
        st.subheader("Tabla Estática")
        st.table(df.head(3)) # Muestra todo sin scroll
        
    st.subheader("Métricas y JSON")
    m1, m2, m3 = st.columns(3)
    m1.metric(label="Ventas", value="$12,500", delta="$500")
    m2.metric(label="Temperatura", value="24 °C", delta="-1.2 °C", delta_color="inverse")
    m3.metric(label="Usuarios", value="1,200", delta="0")
    
    st.json({"usuario": "admin", "rol": "super admin", "permisos": [1, 2, 3]})
    
    st.subheader("Gráficos Nativos")
    st.line_chart(df)
    st.bar_chart(df)
    st.area_chart(df)

# --- PESTAÑA 3: WIDGETS DE ENTRADA ---
with tab3:
    st.header("Interacción del Usuario")
    
    c1, c2 = st.columns(2)
    
    with c1:
        boton = st.button("¡Haz clic en st.button!")
        if boton:
            st.write("¡Botón presionado!")
            
        check = st.checkbox("Acepto los términos (st.checkbox)")
        radio = st.radio("Elige una opción (st.radio):", ["Opción A", "Opción B"])
        select = st.selectbox("Selecciona un país (st.selectbox):", ["México", "Argentina", "España", "Colombia"])
        multi = st.multiselect("Selecciona tus colores favoritos (st.multiselect):", ["Rojo", "Verde", "Azul", "Amarillo"])
        slider = st.slider("Selecciona un rango (st.slider):", 0, 100, (25, 75))
        select_slider = st.select_slider("Talla (st.select_slider):", options=["S", "M", "L", "XL"])

    with c2:
        texto = st.text_input("Ingresa tu nombre (st.text_input):", placeholder="Ej. Juan Pérez")
        area = st.text_area("Deja un comentario (st.text_area):")
        numero = st.number_input("Ingresa tu edad (st.number_input):", min_value=0, max_value=120, step=1)
        fecha = st.date_input("Fecha de nacimiento (st.date_input):", datetime.date(2000, 1, 1))
        hora = st.time_input("Hora de la reunión (st.time_input):", datetime.time(14, 30))
        color = st.color_picker("Elige un color (st.color_picker):", "#FF4B4B")
        
    st.divider()
    archivo = st.file_uploader("Sube un archivo (st.file_uploader)", type=["csv", "txt", "pdf"])
    foto = st.camera_input("Toma una foto con tu cámara (st.camera_input)")

# --- PESTAÑA 4: MULTIMEDIA ---
with tab4:
    st.header("Elementos Multimedia")
    st.write("*(Para ver estos en acción necesitas rutas locales o URLs válidas de archivos)*")
    
    st.info("Imagen:")
    # st.image("ruta_a_tu_imagen.jpg", caption="Un paisaje hermoso")
    st.code('st.image("https://loremflickr.com/640/360", caption="Imagen de ejemplo")')
    
    st.info("Audio:")
    # st.audio("ruta_a_tu_audio.mp3", format="audio/mp3")
    st.code('st.audio("audio.mp3")')
    
    st.info("Video:")
    # st.video("ruta_a_tu_video.mp4")
    st.code('st.video("video.mp4")')

# --- PESTAÑA 5: ESTADO, MENSAJES Y OTROS LAYOUTS ---
with tab5:
    st.header("Mensajes de Estado")
    
    st.success("Operación exitosa (st.success)")
    st.info("Información a tener en cuenta (st.info)")
    st.warning("Advertencia, cuidado (st.warning)")
    st.error("Ha ocurrido un error (st.error)")
    
    st.subheader("Efectos Visuales")
    col_ef1, col_ef2, col_ef3 = st.columns(3)
    if col_ef1.button("Globos (st.balloons)"):
        st.balloons()
    if col_ef2.button("Nieve (st.snow)"):
        st.snow()
    if col_ef3.button("Notificación (st.toast)"):
        st.toast("¡Proceso finalizado correctamente!", icon="✅")

    st.subheader("Más Layouts")
    
    with st.expander("Haz clic para expandir esto (st.expander)"):
        st.write("Aquí puedes ocultar información extensa o secundaria para mantener limpia la interfaz principal.")
        st.image("https://streamlit.io/images/brand/streamlit-mark-color.png", width=100)

    st.subheader("Simulación de Carga (st.progress y st.spinner)")
    if st.button("Iniciar proceso largo"):
        with st.spinner("Procesando datos por favor espera... (st.spinner)"):
            barra = st.progress(0)
            for i in range(100):
                time.sleep(0.02)
                barra.progress(i + 1)
        st.success("¡Listo!")
