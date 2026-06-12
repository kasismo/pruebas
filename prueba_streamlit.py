import streamlit as st
from supabase import create_client, Client
import datetime
import requests
import re
import random
from datetime import timedelta
import google.generativeai as genai
from PIL import Image

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

# Configurar Gemini (Asegúrate de tener GEMINI_API_KEY en tus secrets)
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

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
    
    perfil = obtener_perfil()
    semana_actual = perfil.get('semana_actual', 1)
    barra_desbloqueada = perfil.get('barra_calistenia_desbloqueada', False)
    
    # 1. Consultar el historial exacto de ayer
    res_ayer = supabase.table("misiones_diarias").select("*").eq("jugador_id", jugador_id).eq("fecha", ayer).execute()
    
    zonas_fatigadas = []
    hizo_caminata_ayer = False
    
    for m in res_ayer.data:
        zona = m.get('zona_muscular')
        # Anotamos qué músculos se fatigaron ayer
        if zona in ['pecho', 'espalda', 'piernas', 'core', 'general']:
            zonas_fatigadas.append(zona)
        # Verificamos si ayer hubo caminata
        if zona == 'caminata':
            hizo_caminata_ayer = True
            
    # 2. Traer catálogo de misiones
    res_catalogo = supabase.table("diccionario_misiones").select("*").execute()
    catalogo = res_catalogo.data
    misiones_asignadas = []
    
    entrenamiento_pesado_asignado = False # El candado de seguridad: Solo 1 rutina física diaria
    
    for mision in catalogo:
        tit = mision['titulo']
        zona = mision.get('zona_muscular', 'general')
        
        # --- RAMA 1: INTELECTO Y UNIVERSIDAD ---
        # El estudio no tiene restricciones de fatiga física.
        if zona == 'intelecto':
            probabilidad = float(mision['probabilidad_aparicion'])
            if random.random() <= probabilidad:
                misiones_asignadas.append(mision)
            continue
            
        # --- RAMA 2: CAMPAÑA DE CAMINATA ---
        if zona == 'caminata':
            # Filtro de Semanas
            if "Semana 1" in tit and semana_actual != 1: continue
            if "Semana 2" in tit and semana_actual != 2: continue
            if "Semana 3" in tit and semana_actual != 3: continue
            
            # Filtro de Descanso (Cada 2 días en Semana 1 y 2)
            if semana_actual in [1, 2] and hizo_caminata_ayer:
                continue 
                
            misiones_asignadas.append(mision)
            continue
            
        # --- RAMA 3: ENTRENAMIENTO FÍSICO PESADO ---
        if "Suspensión" in tit and not barra_desbloqueada: continue
        
        if zona in zonas_fatigadas:
            continue # Descartada: Músculo en recuperación
            
        if entrenamiento_pesado_asignado:
            continue # Descartada: Ya tienes una misión física hoy
            
        probabilidad = float(mision['probabilidad_aparicion'])
        if random.random() <= probabilidad:
            misiones_asignadas.append(mision)
            entrenamiento_pesado_asignado = True # Cerramos el candado por hoy

    # 3. Inserción en la Base de Datos
    for m in misiones_asignadas:
        supabase.table("misiones_diarias").insert({
            "jugador_id": jugador_id,
            "titulo": m['titulo'],
            "descripcion": m['descripcion'],
            "categoria": m['categoria'],
            "rango": m['rango'],
            "zona_muscular": m.get('zona_muscular', 'general'),
            "fecha": hoy_str,
            "estado": "pendiente" 
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

def otorgar_xp(jugador_id, cantidad_xp, zona_muscular=None):
    res = supabase.table("perfil_jugador").select("*").eq("id", jugador_id).execute()
    perfil = res.data[0]
    
    xp_actual = perfil['xp_actual'] + cantidad_xp
    nivel = perfil['nivel']
    xp_siguiente = perfil['xp_siguiente_nivel']
    puntos_libres = perfil.get('puntos_atributo', 0)
    
    # 1. Chequeo de Level Up General
    hubo_level_up = False
    while xp_actual >= xp_siguiente:
        xp_actual -= xp_siguiente 
        nivel += 1
        xp_siguiente = int(xp_siguiente * 1.1) 
        puntos_libres += 3 
        hubo_level_up = True
        
    datos_a_actualizar = {
        "nivel": nivel, 
        "xp_actual": int(xp_actual), 
        "xp_siguiente_nivel": xp_siguiente, 
        "puntos_atributo": puntos_libres
    }
    
    # 2. Inyección de XP Muscular Específica
    if zona_muscular:
        # Normalizamos el nombre de la columna (ej: 'pecho' -> 'exp_pecho')
        columna_zona = f"exp_{zona_muscular.lower()}"
        if columna_zona in perfil:
            xp_zona_actual = perfil[columna_zona] or 0
            datos_a_actualizar[columna_zona] = xp_zona_actual + cantidad_xp

    supabase.table("perfil_jugador").update(datos_a_actualizar).eq("id", jugador_id).execute()
    
    return hubo_level_up, nivel

def analizar_fisico(imagen, peso_actual):
    # Compresión preventiva de la imagen para optimizar la petición
    imagen.thumbnail((800, 800))
    
    # Invocamos al modelo Flash nativo de Gemini (rápido y con visión)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    Actúa estrictamente como un Sistema RPG de entrenamiento físico. 
    Analiza esta imagen de referencia deportiva del Jugador.
    El usuario pesa {peso_actual} kg y está entrenando calistenia. Su objetivo principal es la Misión de Clase S: lograr 25 dominadas (pull-ups) estrictas consecutivas.
    Brinda un breve reporte motivacional estilo videojuego que incluya:
    1. Observación de la musculatura visible enfocada en el rendimiento de tracción vertical (espalda/dorsales, bíceps, core y postura).
    2. Un consejo técnico y constructivo sobre qué cadena muscular priorizar para lograr traccionar sus {peso_actual} kg repetidas veces en la barra sin balanceo.
    3. Cierra con una frase épica del Sistema.
    """
    
    # Con Gemini, enviamos la imagen directamente en la lista junto al texto
    response = model.generate_content([prompt, imagen])
    return response.text

# -----------------------------------------------------------------------------
# INTERFAZ DE USUARIO (UI)
# -----------------------------------------------------------------------------
st.title("STATUS PANEL")
st.markdown("---")

# --- SISTEMA DE ALARMA: LEVEL UP ---
if st.session_state.get('play_level_up', False):
    st.audio("level_up.mp3", autoplay=True)
    st.balloons()
    st.session_state['play_level_up'] = False # Apagamos el interruptor

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

# --- Sección 2: Análisis Estructural y Escáner IA ---
st.subheader("ANÁLISIS ESTRUCTURAL AVANZADO")

tab_svg, tab_ia = st.tabs(["Holograma de Progreso", "Escáner del Sistema (IA)"])

with tab_svg:
    # 1. Leer experiencia de las distintas zonas
    META_MUSCULO = 1000.0
    
    xp_inte = perfil.get('exp_intelecto', 0)
    xp_pecho = perfil.get('exp_pecho', 0)
    xp_espal = perfil.get('exp_espalda', 0)
    xp_core = perfil.get('exp_core', 0)
    xp_pier = perfil.get('exp_piernas', 0)

    # 2. Fórmula matemática de brillo: A más XP, mayor opacidad y brillo.
    op_inte = min(0.2 + (xp_inte / META_MUSCULO), 1.0)
    op_pecho = min(0.2 + (xp_pecho / META_MUSCULO), 1.0)
    op_espal = min(0.2 + (xp_espal / META_MUSCULO), 1.0)
    op_core = min(0.2 + (xp_core / META_MUSCULO), 1.0)
    op_pier = min(0.2 + (xp_pier / META_MUSCULO), 1.0)

    # 3. Diseño del Esqueleto Poligonal (Wireframe)
    svg_cuerpo = f"""
    <svg viewBox="0 0 200 400" width="100%" height="350" xmlns="http://www.w3.org/2000/svg">
      <style>
        .glow {{ stroke: #00ffff; stroke-width: 1.5; fill: #00ffcc; transition: all 1s ease; }}
        #intelecto {{ opacity: {op_inte}; filter: drop-shadow(0 0 {op_inte * 10}px #00ffcc); }}
        #pecho {{ opacity: {op_pecho}; filter: drop-shadow(0 0 {op_pecho * 10}px #00ffcc); }}
        #espalda {{ opacity: {op_espal}; filter: drop-shadow(0 0 {op_espal * 10}px #00ffcc); }}
        #core {{ opacity: {op_core}; filter: drop-shadow(0 0 {op_core * 10}px #00ffcc); }}
        #piernas {{ opacity: {op_pier}; filter: drop-shadow(0 0 {op_pier * 10}px #00ffcc); }}
      </style>
      
      <polygon id="intelecto" class="glow" points="90,10 110,10 115,35 100,50 85,35" />
      
      <polygon id="espalda" class="glow" points="55,55 145,55 135,90 125,65 75,65 65,90" />
      <polygon id="espalda" class="glow" points="60,65 70,95 65,160 50,160 50,100" /> 
      <polygon id="espalda" class="glow" points="140,65 130,95 135,160 150,160 150,100" /> 
      <polygon id="pecho" class="glow" points="70,60 130,60 125,95 100,105 75,95" />
      
      <polygon id="core" class="glow" points="80,100 120,100 115,150 100,165 85,150" />
      
      <polygon id="piernas" class="glow" points="80,160 100,170 100,220 85,340 70,340 75,220" /> 
      <polygon id="piernas" class="glow" points="120,160 100,170 100,220 115,340 130,340 125,220" /> 
    </svg>
    """
    
    col_barras, col_grafico = st.columns([1, 1])
    with col_barras:
        st.caption("DENSIDAD ESTRUCTURAL")
        st.progress(min(xp_inte / META_MUSCULO, 1.0), text=f"Intelecto: {xp_inte} XP")
        st.progress(min(xp_espal / META_MUSCULO, 1.0), text=f"Espalda: {xp_espal} XP")
        st.progress(min(xp_pecho / META_MUSCULO, 1.0), text=f"Pecho: {xp_pecho} XP")
        st.progress(min(xp_core / META_MUSCULO, 1.0), text=f"Core: {xp_core} XP")
        st.progress(min(xp_pier / META_MUSCULO, 1.0), text=f"Piernas: {xp_pier} XP")
    with col_grafico:
        st.markdown(svg_cuerpo, unsafe_allow_html=True)

with tab_ia:
    st.write("Sube una actualización visual para que el Sistema recalcule tus umbrales de esfuerzo.")
    foto_subida = st.file_uploader("Subir foto del torso", type=['jpg', 'jpeg', 'png'])
    peso_input = st.number_input("Peso actual (kg):", min_value=50.0, max_value=150.0, value=102.0)
    
    if foto_subida and st.button("👁️ Iniciar Escaneo"):
        with st.spinner("El Sistema está analizando tu composición a través de Gemini Vision..."):
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
                # Encendemos la alarma en la memoria del sistema
                st.session_state['play_level_up'] = True
                st.success(f"¡LEVEL UP! Nivel {nuevo_nivel} alcanzado. +3 Puntos de Atributo disponibles.")
            else:
                st.success(f"¡Registro actualizado! {nuevas_horas} horas añadidas. +{xp_ganada} XP.")
            
            st.rerun()
        else:
            st.info("No se detectaron nuevos entrenamientos en la lista.")

st.markdown("---")

# --- Sección 4: Misiones Diarias (QUEST BOARD) ---
st.subheader("📜 QUEST BOARD")
st.caption("DAILY QUEST - SURVIVE AND LEVEL UP")

misiones_hoy = obtener_misiones_hoy(perfil['id'])

if not misiones_hoy:
    st.info("El Sistema aún no ha asignado las misiones de hoy.")
    if st.button("🎲 Extraer Misiones del Sistema", use_container_width=True):
        with st.spinner("Calculando fatiga y probabilidades..."):
            generar_misiones_del_dia(perfil['id'])
            st.rerun()
else:
    # Separar en pendientes y completadas para mejorar la UI
    pendientes = [m for m in misiones_hoy if m.get('estado', 'pendiente') == 'pendiente']
    completadas = [m for m in misiones_hoy if m.get('estado', '') == 'completada']
    
    # 1. RENDERIZAR MISIONES PENDIENTES
    if pendientes:
        st.write("### ⚠️ MISIONES ACTIVAS")
        for mision in pendientes:
            # st.container(border=True) crea una tarjeta visualmente atractiva
            with st.container(border=True):
                # El Rango [D], [C]... destaca en el título
                st.markdown(f"#### [{mision['rango']}] {mision['titulo']}")
                st.caption(f"ZONA DE IMPACTO: **{mision.get('zona_muscular', 'N/A').upper()}**")
                st.write(mision['descripcion'])
                
                st.divider()
                
                # Botones de Acción (Aceptar vs Rechazar)
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Aceptar y Completar", key=f"comp_{mision['id']}", use_container_width=True):
                        # 1. Buscar la XP que da esta misión
                        res_dic = supabase.table("diccionario_misiones").select("xp_recompensa").eq("titulo", mision['titulo']).execute()
                        xp_ganada = res_dic.data[0]['xp_recompensa'] if res_dic.data else 20
                        
                        # 2. ENVIAR LA XP A LA ZONA CORRESPONDIENTE
                        zona_trabajada = mision.get('zona_muscular', None)
                        if zona_trabajada == 'caminata': zona_trabajada = 'piernas' # La caminata sube piernas
                        
                        level_up, nuevo_nivel = otorgar_xp(perfil['id'], xp_ganada, zona_trabajada)
                        
                        # 3. Guardar como completada
                        supabase.table("misiones_diarias").update({"estado": "completada"}).eq("id", mision['id']).execute()
                        
                        # Activar alarma si hubo level up
                        if level_up:
                            st.session_state['play_level_up'] = True
                            st.toast(f"¡SUBIDA DE NIVEL! Ganaste +{xp_ganada} XP.")
                        else:
                            st.toast(f"Misión Cumplida. +{xp_ganada} XP añadida a tu barra.")
                            
                        st.rerun() # Obliga a la app a recargar y mostrar los gráficos llenos
                        
                with col2:
                    if st.button("❌ Rechazar", key=f"rech_{mision['id']}", use_container_width=True):
                        # Eliminamos la misión de hoy si no la vas a hacer
                        supabase.table("misiones_diarias").delete().eq("id", mision['id']).execute()
                        st.toast("Misión rechazada y eliminada del panel.")
                        st.rerun()
                        
    # 2. RENDERIZAR MISIONES COMPLETADAS (Solo un registro visual)
    if completadas:
        st.write("### 🏆 REGISTRO DE VICTORIAS HOY")
        for mision in completadas:
            with st.container(border=True):
                st.markdown(f"~~[{mision['rango']}] {mision['titulo']}~~")
                st.success("Misión Completada")
