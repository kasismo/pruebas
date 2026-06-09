import streamlit as st
from supabase import create_client, Client
import datetime # Agrega esto

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
    # Obtenemos la fecha de hoy en formato 'YYYY-MM-DD'
    hoy = datetime.date.today().isoformat()
    
    # Hacemos el fetch con la fecha correcta
    respuesta = supabase.table("misiones_diarias")\
        .select("*")\
        .eq("jugador_id", jugador_id)\
        .eq("fecha", hoy)\
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

def extraer_xp_de_youtube(jugador_id):
    api_key = st.secrets["YOUTUBE_API_KEY"]
    playlist_id = st.secrets["YOUTUBE_PLAYLIST_ID"]
    
    # 1. Obtener los videos de la lista de reproducción
    url_playlist = f"https://www.googleapis.com/youtube/v3/playlistItems?part=contentDetails&maxResults=50&playlistId={playlist_id}&key={api_key}"
    res_playlist = requests.get(url_playlist).json()
    
    if "items" not in res_playlist:
        return 0 # Si la lista está vacía o hay error
        
    video_ids = [item['contentDetails']['videoId'] for item in res_playlist['items']]
    
    # 2. Consultar qué videos ya procesamos en Supabase
    res_db = supabase.table("historial_youtube").select("video_id").execute()
    videos_procesados = [fila['video_id'] for fila in res_db.data]
    
    # Filtrar solo los videos nuevos
    videos_nuevos = [vid for vid in video_ids if vid not in videos_procesados]
    
    if not videos_nuevos:
        return 0 # No hay videos nuevos para procesar
        
    # 3. Obtener la duración de los videos nuevos
    ids_string = ",".join(videos_nuevos)
    url_videos = f"https://www.googleapis.com/youtube/v3/videos?part=contentDetails,snippet&id={ids_string}&key={api_key}"
    res_videos = requests.get(url_videos).json()
    
    horas_totales_nuevas = 0
    
    for item in res_videos['items']:
        vid_id = item['id']
        titulo = item['snippet']['title']
        duracion_iso = item['contentDetails']['duration']
        
        # Parsear PT1H2M10S a horas decimales
        horas = re.search(r'(\d+)H', duracion_iso)
        minutos = re.search(r'(\d+)M', duracion_iso)
        segundos = re.search(r'(\d+)S', duracion_iso)
        
        h = int(horas.group(1)) if horas else 0
        m = int(minutos.group(1)) if minutos else 0
        s = int(segundos.group(1)) if segundos else 0
        
        duracion_decimal = h + (m / 60) + (s / 3600)
        horas_totales_nuevas += duracion_decimal
        
        # Insertar registro en Supabase para no volver a contarlo
        supabase.table("historial_youtube").insert({
            "video_id": vid_id,
            "titulo": titulo,
            "duracion_horas": duracion_decimal,
            "jugador_id": jugador_id
        }).execute()
        
    return round(horas_totales_nuevas, 2)
