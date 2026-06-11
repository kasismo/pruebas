import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client, Client
import datetime
import requests
import re
import random
from datetime import timedelta
from PIL import Image
import base64
from io import BytesIO
from groq import Groq

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
    .stProgress > div > div > div > div {
        background-color: #E50914; 
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# CONEXIÓN A BASES DE DATOS Y APIs
# -----------------------------------------------------------------------------
@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# Configurar el cliente de Groq (Extrae la llave directamente de los secrets)
groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])

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

def verificar_progreso_campana(jugador_id, perfil_actual):
    res_caminatas = supabase.table("misiones_diarias")\
        .select("id")\
        .eq("jugador_id", jugador_id)\
        .eq("titulo", "Dominio del Terreno: Semana 3")\
        .eq("estado", "completada")\
        .execute()
    
    cantidad_completadas = len(res_caminatas.data)
    
    if cantidad_completadas >= 7 and not perfil_actual.get('barra_calistenia_desbloqueada', False):
        supabase.table("perfil_jugador").update({
            "barra_calistenia_desbloqueada": True,
            "semana_actual": 4
        }).eq("id", jugador_id).execute()
        st.balloons()
        st.success("🎉 ¡ALERTA DEL SISTEMA: MAPA ACTUALIZADO! Has desbloqueado el acceso a las misiones de barra de calistenia.")

def obtener_misiones_hoy(jugador_id):
    hoy = datetime.date.today().isoformat()
    respuesta = supabase.table("misiones_diarias")\
        .select("*")\
        .eq("jugador_id", jugador_id)\
        .eq("fecha", hoy)\
        .execute()
    return respuesta.data

def generar_misiones_del_dia(jugador_id):
    hoy = datetime.date.today()
    ayer = (hoy - timedelta(days=1)).isoformat()
    hoy_str = hoy.isoformat()
    
    res_ayer = supabase.table("misiones_diarias")\
        .select("zona_muscular")\
        .eq("jugador_id", jugador_id)\
        .eq("fecha", ayer)\
        .execute()
    
    zonas_fatigadas = [m['zona_muscular'] for m in res_ayer.data if m['zona_muscular'] not in ['caminata', 'general', None]]
    res_catalogo = supabase.table("diccionario_misiones").select("*").execute()
    catalogo = res_catalogo.data
    misiones_asignadas = []
    
    for mision in catalogo:
        if mision.get('zona_muscular') in zonas_fatigadas:
            continue
            
        probabilidad = float(mision['probabilidad_aparicion'])
        if random.random() <= probabilidad:
            misiones_asignadas.append(mision)
            if mision.get('zona_muscular') in ['pecho', 'espalda', 'piernas', 'core']:
                zonas_fatigadas.extend(['pecho', 'espalda', 'piernas', 'core'])

    for m in misiones_asignadas:
        supabase.table("misiones_diarias").insert({
            "jugador_id": jugador_id,
            "titulo": m['titulo'],
            "descripcion": m['descripcion'],
            "categoria": m['categoria'],
            "rango": m['rango'],
            "zona_muscular": m.get('zona_muscular', 'general'),
            "fecha": hoy_str
        }).execute()
        
    return misiones_asignadas

def obtener_horas_totales_youtube(jugador_id):
    respuesta = supabase.table("historial_youtube").select("duracion_horas").eq("jugador_id", jugador_id).execute()
    if not respuesta.data:
        return 0.0
    return sum(item['duracion_horas'] for item in respuesta.data)

def sincronizar_radar(jugador_id):
    api_key = st.secrets["YOUTUBE_API_KEY"]
    playlist_id = st.secrets["YOUTUBE_PLAYLIST_ID"]
    
    url_playlist = f"https://www.googleapis.com/youtube/v3/playlistItems?part=contentDetails&maxResults=50&playlistId={playlist_id}&key={api_key}"
    res_playlist = requests.get(url_playlist).json()
    
    if "items" not in res_playlist:
        return 0 
        
    video_ids = [item['contentDetails']['videoId'] for item in res_playlist['items']]
    res_db = supabase.table("historial_youtube").select("video_id").execute()
    videos_procesados = [fila['video_id'] for fila in res_db.data]
    videos_nuevos = [vid for vid in video_ids if vid not in videos_procesados]
    
    if not videos_nuevos:
        return 0 
        
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
        
        supabase.table("historial_youtube").insert({
            "video_id": vid_id, "titulo": titulo, "duracion_horas": duracion_decimal, "jugador_id": jugador_id
        }).execute()
        
    return round(horas_totales_nuevas, 2)

def otorgar_xp(jugador_id, cantidad_xp):
    res = supabase.table("perfil_jugador").select("*").eq("id", jugador_id).execute()
    perfil = res.data[0]
    
    xp_actual = perfil['xp_actual'] + cantidad_xp
    nivel = perfil['nivel']
    xp_siguiente = perfil['xp_siguiente_nivel']
    puntos_libres = perfil.get('puntos_atributo', 0)
    
    hubo_level_up = False
    
    while xp_actual >= xp_siguiente:
        xp_actual -= xp_siguiente 
        nivel += 1
        xp_siguiente = int(xp_siguiente * 1.1) 
        puntos_libres += 3 
        hubo_level_up = True
        
    supabase.table("perfil_jugador").update({
        "nivel": nivel, "xp_actual": int(xp_actual), "xp_siguiente_nivel": xp_siguiente, "puntos_atributo": puntos_libres 
    }).eq("id", jugador_id).execute()
    
    return hubo_level_up, nivel

def analizar_fisico(imagen, peso_actual):
    # Convertir la imagen a Base64 para que la API de Groq la pueda interpretar
    buffered = BytesIO()
    imagen.convert('RGB').save(buffered, format="JPEG")
    base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    prompt = f"""
    Actúa como el 'Sistema' de Solo Leveling evaluando al Jugador. 
    El Jugador acaba de subir una actualización visual de su torso. 
    Actualmente pesa {peso_actual} kg y está ejecutando un protocolo de calistenia pesada. Su objetivo principal es desbloquear la Misión Clase S: 25 flexiones consecutivas perfectas.
    Analiza la imagen de su tren superior. Dame un reporte táctico, objetivo y altamente motivador. 
    1. Evalúa la estructura visible (densidad de hombros, pecho, core).
    2. Da una advertencia constructiva sobre qué fortalecer para lograr las 25 flexiones soportando sus {peso_actual} kg.
    3. Cierra con una frase épica de nivel RPG.
    """
    
    # Petición a LLaMA 3.2 Vision alojado en los LPU de Groq
    response = groq_client.chat.completions.create(
        model="llama-3.2-11b-vision-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                        },
                    },
                ],
            }
        ],
    )
    return response.choices[0].message.content

# -----------------------------------------------------------------------------
# INTERFAZ DE USUARIO (UI)
# -----------------------------------------------------------------------------
st.title("STATUS PANEL")
st.markdown("---")

perfil = obtener_perfil()
verificar_progreso_campana(perfil['id'], perfil)

# --- Sección 1: Estadísticas Base ---
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
    
    if perfil.get('puntos_atributo', 0) > 0:
        st.info(f"✨ Puntos Disponibles: {perfil['puntos_atributo']}")
        c_str, c_int, c_agi = st.columns(3)
        with c_str:
            if st.button("+ STR"):
                supabase.table("perfil_jugador").update({"fuerza": perfil['fuerza'] + 1, "puntos_atributo": perfil['puntos_atributo'] - 1}).eq("id", perfil['id']).execute()
                st.rerun()
        with c_int:
            if st.button("+ INT"):
                supabase.table("perfil_jugador").update({"inteligencia": perfil['inteligencia'] + 1, "puntos_atributo": perfil['puntos_atributo'] - 1}).eq("id", perfil['id']).execute()
                st.rerun()
        with c_agi:
            if st.button("+ AGI"):
                supabase.table("perfil_jugador").update({"agilidad": perfil['agilidad'] + 1, "puntos_atributo": perfil['puntos_atributo'] - 1}).eq("id", perfil['id']).execute()
                st.rerun()

st.markdown("---")

# --- Sección 2: Análisis Físico y Holograma SVG ---
st.subheader("ANÁLISIS MUSCULAR AVANZADO")

tab_svg, tab_ia = st.tabs(["Holograma de XP", "Escáner del Sistema (IA)"])

with tab_svg:
    exp_pecho = perfil.get('exp_pecho', 0)
    exp_piernas = perfil.get('exp_piernas', 0)

    color_pecho = "#00ffcc" if exp_pecho > 100 else "#004433"
    color_piernas = "#00ffcc" if exp_piernas > 100 else "#004433"

    svg_cuerpo = f"""
    <svg viewBox="0 0 200 400" width="100%" height="300">
      <path id="pecho" d="M 60 100 Q 100 120 140 100 Q 100 80 60 100" fill="{color_pecho}" opacity="0.8" />
      <path id="piernas" d="M 80 200 L 80 350 M 120 200 L 120 350" stroke="{color_piernas}" stroke-width="20" opacity="0.8" />
    </svg>
    <style>
        #pecho, #piernas {{
            filter: drop-shadow(0px 0px 5px {color_pecho});
            transition: fill 0.5s ease;
        }}
    </style>
    """
    col_svg1, col_svg2 = st.columns([1, 2])
    with col_svg1:
        st.write("**ZONA DE ENFOQUE**")
        st.progress(min(exp_pecho / 500.0, 1.0), text=f"Pectoral: {exp_pecho}/500 XP")
        st.progress(min(exp_piernas / 500.0, 1.0), text=f"Piernas: {exp_piernas}/500 XP")
    with col_svg2:
        components.html(svg_cuerpo, height=350)

with tab_ia:
    st.write("Sube una actualización visual para que el Sistema recalcule tus umbrales de esfuerzo.")
    foto_subida = st.file_uploader("Subir foto del torso", type=['jpg', 'jpeg', 'png'])
    peso_input = st.number_input("Peso actual (kg):", min_value=50.0, max_value=150.0, value=102.0)
    
    if foto_subida and st.button("👁️ Iniciar Escaneo"):
        with st.spinner("El Sistema está analizando tu composición a través de los servidores de Groq..."):
            img = Image.open(foto_subida)
            feedback = analizar_fisico(img, peso_input)
            st.markdown(f"> *{feedback}*")

st.markdown("---")

# --- Sección 3: El Camino del Desarrollador (10k Horas) ---
st.subheader("MASTER DEV PATH")
horas_totales = obtener_horas_totales_youtube(perfil['id'])
META_HORAS = 10000
progreso_horas = min(horas_totales / META_HORAS, 1.0) 

st.progress(progreso_horas, text=f"Progreso 10.000 Horas: {round(horas_totales, 2)} / {META_HORAS}")

if st.button("📡 Sincronizar Radar de YouTube"):
    with st.spinner("Escaneando registro de entrenamiento..."):
        nuevas_horas = sincronizar_radar(perfil['id'])
        if nuevas_horas > 0:
            xp_ganada = int(nuevas_horas * 5)
            level_up, nuevo_nivel = otorgar_xp(perfil['id'], xp_ganada)
            if level_up:
                # 🔊 REPRODUCTOR DEL BASS DROP OCULTO
                st.audio("level_up.mp3", autoplay=True)
                st.balloons()
                st.success(f"¡LEVEL UP! Nivel {nuevo_nivel} alcanzado. +3 Puntos de Atributo disponibles.")
            else:
                st.success(f"¡Registro actualizado! {nuevas_horas} horas añadidas. +{xp_ganada} XP.")
            st.rerun() 
        else:
            st.info("No se detectaron nuevos entrenamientos en la lista.")

st.markdown("---")

# --- Sección 4: Misiones Diarias ---
st.subheader("QUEST INFO")
st.caption("DAILY QUEST - SURVIVE AND LEVEL UP")

misiones_hoy = obtener_misiones_hoy(perfil['id'])

if not misiones_hoy:
    st.info("El Sistema aún no ha asignado las misiones de hoy.")
    if st.button("🎲 Extraer Misiones del Sistema"):
        with st.spinner("Calculando fatiga y probabilidades..."):
            generar_misiones_del_dia(perfil['id'])
            st.rerun()
else:
    for mision in misiones_hoy:
        with st.container():
            st.markdown(f"**{mision['titulo']}** [{mision['rango']}] - Zona: {mision.get('zona_muscular', 'N/A').upper()}")
            st.write(mision['descripcion'])
            
            if mision['estado'] == 'pendiente':
                if st.button(f"Completar Misión", key=mision['id']):
                    st.toast("XP guardada.")
            else:
                st.success("Misión Completada")
            st.divider()
