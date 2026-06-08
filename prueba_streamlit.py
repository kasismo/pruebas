import streamlit as st
from supabase import create_client, Client

# Configuración de página: minimalista y oscura
st.set_page_config(
    page_title="Solo Leveling: System",
    page_icon="🗡️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Inyectar un poco de CSS para acentos de color limpios
st.markdown("""
    <style>
    .stProgress > div > div > div > div {
        background-color: #E50914; /* Acento rojo para la XP */
    }
    </style>
""", unsafe_allow_html=True)

# Tu función (con o sin el @st.cache_resource, como la tengas ahora)
def init_connection() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# 👇 ESTA ES LA LÍNEA VITAL QUE FALTA O SE BORRÓ 👇
supabase = init_connection()

# -----------------------------------------------------------------------------
# LÓGICA DE DATOS
# -----------------------------------------------------------------------------

def obtener_perfil():
    # Asumimos que hay un solo jugador por ahora
    respuesta = supabase.table("perfil_jugador").select("*").limit(1).execute()
    if respuesta.data:
        return respuesta.data[0]
    else:
        # Si no existe, lo creamos con el default
        nuevo_perfil = supabase.table("perfil_jugador").insert({}).execute()
        return nuevo_perfil.data[0]

def obtener_misiones_hoy(jugador_id):
    # Fetch de las misiones del día actual
    respuesta = supabase.table("misiones_diarias")\
        .select("*")\
        .eq("jugador_id", jugador_id)\
        .eq("fecha", "CURRENT_DATE")\
        .execute()
    return respuesta.data

# -----------------------------------------------------------------------------
# INTERFAZ DE USUARIO (UI)
# -----------------------------------------------------------------------------

st.title("STATUS PANEL")
st.markdown("---")

perfil = obtener_perfil()

# Sección de Estadísticas del Jugador
col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    st.subheader(f"[{perfil['nombre']}]")
    st.write(f"**Nivel:** {perfil['nivel']}")

with col2:
    progreso_xp = perfil['xp_actual'] / perfil['xp_siguiente_nivel']
    st.progress(progreso_xp, text=f"XP: {perfil['xp_actual']} / {perfil['xp_siguiente_nivel']}")

with col3:
    st.write(f"💪 STR: {perfil['fuerza']}")
    st.write(f"🧠 INT: {perfil['inteligencia']}")
    st.write(f"⚡ AGI: {perfil['agilidad']}")

st.markdown("---")

# Sección de Misiones Diarias
st.subheader("QUEST INFO")
st.caption("DAILY QUEST - TRAIN TO BECOME A FORMIDABLE DEVELOPER")

misiones_hoy = obtener_misiones_hoy(perfil['id'])

if not misiones_hoy:
    st.info("El Sistema aún no ha asignado las misiones de hoy. Iniciando algoritmo de generación...")
    # Aquí irá el botón o la lógica automática que saca misiones del diccionario
else:
    for mision in misiones_hoy:
        with st.container():
            st.markdown(f"**{mision['titulo']}** [{mision['rango']}]")
            st.write(mision['descripcion'])
            # Aquí irá la lógica de check y feedback (sencillo, adecuado, etc.)
            st.divider()
