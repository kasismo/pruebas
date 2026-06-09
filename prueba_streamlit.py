import streamlit as st
from supabase import create_client, Client
import datetime
import requests
import re

# -----------------------------------------------------------------------------
# CONFIGURACIÓN VISUAL
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Solo Leveling: System",
    page_icon="🗡️",
    layout="centered"
)

st.markdown("""
    <style>
    /* Acento rojo oscuro para la XP del jugador */
    .stProgress > div > div > div > div {
        background-color: #E50914; 
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# CONEXIÓN A BASE DE DATOS
# -----------------------------------------------------------------------------
@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# -----------------------------------------------------------------------------
# LÓGICA DE DATOS
# -----------------------------------------------------------------------------
def obtener_perfil():
    respuesta = supabase.table("perfil_jugador").select("*").limit(1).execute()
    if respuesta.data:
        return respuesta.data[0]
    else:
        nuevo_perfil = supabase.table("perfil_jugador").insert({}).execute()
        return nuevo_perfil.data[0]

def obtener_misiones_hoy(jugador_id):
    hoy = datetime.date.today().isoformat()
    respuesta = supabase.table("misiones_diarias")\
        .select("*")\
        .eq("jugador_id", jugador_id)\
        .eq("fecha", hoy)\
        .execute()
    return respuesta.data

def obtener_horas_totales_youtube(jugador_id):
    # Sumamos todas las horas registradas en el historial
    respuesta = supabase.table("historial_youtube").select("duracion_horas").eq("jugador_id", jugador_id).execute()
    if not respuesta.data:
        return 0.0
    return sum(item['duracion_horas'] for item in respuesta.data)

def sincronizar_radar(jugador_id):
    api_key = st.secrets["YOUTUBE_API_KEY"]
    playlist_id = st.secrets["YOUTUBE_PLAYLIST_ID"]
    
    # 1. Obtener los videos de la lista
    url_playlist = f"https://www.googleapis.com/youtube/v3/playlistItems?part=contentDetails&maxResults=50&playlistId={playlist_id}&key={api_key}"
    res_playlist = requests.get(url_playlist).json()
    
    if "items" not in res_playlist:
        return 0 
        
    video_ids = [item['contentDetails']['videoId'] for item in res_playlist['items']]
    
    # 2. Consultar qué videos ya procesamos en Supabase
    res_db = supabase.table("historial_youtube").select("video_id").execute()
    videos_procesados = [fila['video_id'] for fila in res_db.data]
    
    # Filtrar solo los nuevos
    videos_nuevos = [vid for vid in video_ids if vid not in videos_procesados]
    
    if not videos_nuevos:
        return 0 
        
    # 3. Obtener la duración de los videos nuevos
    ids_string = ",".join(videos_nuevos)
    url_videos = f"https://www.googleapis.com/youtube/v3/videos?part=contentDetails,snippet&id={ids_string}&key={api_key}"
    res_videos = requests.get(url_videos).json()
    
    horas_totales_nuevas = 0
    
    for item in res_videos.get('items', []):
        vid_id = item['id']
        titulo = item['snippet']['title']
        duracion_iso = item['contentDetails']['duration']
        
        horas = re.search(r'(\d+)H', duracion_iso)
        minutos = re.search(r'(\d+)M', duracion_iso)
        segundos = re.search(r'(\d+)S', duracion_iso)
        
        h = int(horas.group(1)) if horas else 0
        m = int(minutos.group(1)) if minutos else 0
        s = int(segundos.group(1)) if segundos else 0
        
        duracion_decimal = h + (m / 60) + (s / 3600)
        horas_totales_nuevas += duracion_decimal
        
        # Guardar en base de datos
        supabase.table("historial_youtube").insert({
            "video_id": vid_id,
            "titulo": titulo,
            "duracion_horas": duracion_decimal,
            "jugador_id": jugador_id
        }).execute()
        
    return round(horas_totales_nuevas, 2)

def otorgar_xp(jugador_id, cantidad_xp):
    res = supabase.table("perfil_jugador").select("*").eq("id", jugador_id).execute()
    perfil = res.data[0]
    
    xp_actual = perfil['xp_actual'] + cantidad_xp
    nivel = perfil['nivel']
    xp_siguiente = perfil['xp_siguiente_nivel']
    puntos_libres = perfil['puntos_atributo'] # Leemos los puntos actuales
    
    hubo_level_up = False
    
    while xp_actual >= xp_siguiente:
        xp_actual -= xp_siguiente
        nivel += 1
        xp_siguiente = int(xp_siguiente * 1.1)
        puntos_libres += 3 # Ganas 3 Puntos Libres por cada nivel
        hubo_level_up = True
        
    supabase.table("perfil_jugador").update({
        "nivel": nivel,
        "xp_actual": int(xp_actual),
        "xp_siguiente_nivel": xp_siguiente,
        "puntos_atributo": puntos_libres # Guardamos los puntos
    }).eq("id", jugador_id).execute()
    
    return hubo_level_up, nivel
    
    # 2. Lógica de Level Up (puede ocurrir múltiples veces si ganas mucha XP junta)
    while xp_actual >= xp_siguiente:
        xp_actual -= xp_siguiente # Guardamos el sobrante de XP
        nivel += 1
        # Escalado progresivo: cada nivel requiere 10% más XP que el anterior
        xp_siguiente = int(xp_siguiente * 1.1) 
        inteligencia += 1 # Ganas +1 de INT permanente al subir de nivel
        hubo_level_up = True
        
    # 3. Guardar el progreso en el servidor
    supabase.table("perfil_jugador").update({
        "nivel": nivel,
        "xp_actual": int(xp_actual),
        "xp_siguiente_nivel": xp_siguiente,
        "inteligencia": inteligencia
    }).eq("id", jugador_id).execute()
    
    return hubo_level_up, nivel
# -----------------------------------------------------------------------------
# INTERFAZ DE USUARIO (UI)
# -----------------------------------------------------------------------------
st.title("STATUS PANEL")
st.markdown("---")

perfil = obtener_perfil()

# Sección 1: Estadísticas Base
col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    st.subheader(f"[{perfil['nombre']}]")
    st.write(f"**Nivel:** {perfil['nivel']}")

with col2:
    progreso_xp = perfil['xp_actual'] / perfil['xp_siguiente_nivel']
    st.progress(progreso_xp, text=f"XP: {perfil['xp_actual']} / {perfil['xp_siguiente_nivel']}")

# (Dentro de la Sección 1 de tu código, reemplaza la col3 actual por esto)

with col3:
    st.write(f"💪 STR: {perfil['fuerza']}")
    st.write(f"🧠 INT: {perfil['inteligencia']}")
    st.write(f"⚡ AGI: {perfil['agilidad']}")
    
    # Si hay puntos libres, mostramos el panel de distribución
    if perfil.get('puntos_atributo', 0) > 0:
        st.info(f"✨ Puntos Disponibles: {perfil['puntos_atributo']}")
        
        # Botones para asignar puntos
        c_str, c_int, c_agi = st.columns(3)
        with c_str:
            if st.button("+ STR"):
                supabase.table("perfil_jugador").update({
                    "fuerza": perfil['fuerza'] + 1,
                    "puntos_atributo": perfil['puntos_atributo'] - 1
                }).eq("id", perfil['id']).execute()
                st.rerun()
        with c_int:
            if st.button("+ INT"):
                supabase.table("perfil_jugador").update({
                    "inteligencia": perfil['inteligencia'] + 1,
                    "puntos_atributo": perfil['puntos_atributo'] - 1
                }).eq("id", perfil['id']).execute()
                st.rerun()
        with c_agi:
            if st.button("+ AGI"):
                supabase.table("perfil_jugador").update({
                    "agilidad": perfil['agilidad'] + 1,
                    "puntos_atributo": perfil['puntos_atributo'] - 1
                }).eq("id", perfil['id']).execute()
                st.rerun()
st.markdown("---")

# Sección 2: El Camino del Desarrollador (10k Horas)
st.subheader("MASTER DEV PATH")
horas_totales = obtener_horas_totales_youtube(perfil['id'])
META_HORAS = 10000
# Evitar que la barra pase de 1.0 (100%)
progreso_horas = min(horas_totales / META_HORAS, 1.0) 

st.progress(progreso_horas, text=f"Progreso 10.000 Horas: {round(horas_totales, 2)} / {META_HORAS}")

# El Botón de Acción del Radar
if st.button("📡 Sincronizar Radar de YouTube"):
    with st.spinner("Escaneando registro de entrenamiento..."):
        nuevas_horas = sincronizar_radar(perfil['id'])
        
        if nuevas_horas > 0:
            # Tu regla matemática: 5 XP por hora
            xp_ganada = int(nuevas_horas * 5)
            
            # Disparamos la función de recompensas
            level_up, nuevo_nivel = otorgar_xp(perfil['id'], xp_ganada)
            
            if level_up:
                st.balloons() # Streamlit tira globos en la pantalla
                st.success(f"¡LEVEL UP! El Sistema reconoce tu crecimiento. Nivel {nuevo_nivel} alcanzado. INT +1.")
            else:
                st.success(f"¡Registro actualizado! {nuevas_horas} horas añadidas. +{xp_ganada} XP.")
            
            st.rerun() # Recarga para que la barra amarilla de XP se actualice al instante
        else:
            st.info("No se detectaron nuevos entrenamientos en la lista.")

st.markdown("---")

# Sección 3: Misiones Diarias
st.subheader("QUEST INFO")
st.caption("DAILY QUEST - TRAIN TO BECOME A FORMIDABLE DEVELOPER")

misiones_hoy = obtener_misiones_hoy(perfil['id'])

if not misiones_hoy:
    st.info("El Sistema aún no ha asignado las misiones de hoy. Iniciando algoritmo de generación...")
else:
    for mision in misiones_hoy:
        with st.container():
            st.markdown(f"**{mision['titulo']}** [{mision['rango']}]")
            st.write(mision['descripcion'])
            st.divider()
