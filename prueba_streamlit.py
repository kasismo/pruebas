import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client, Client
import datetime
import requests
import re
import random
from datetime import timedelta
import google.generativeai as genai
from PIL import Image

# -----------------------------------------------------------------------------
# CONFIGURACIÓN VISUAL Y MEMORIA DEL SISTEMA
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

# Inicialización de la memoria a corto plazo del panel
if 'play_level_up' not in st.session_state:
    st.session_state['play_level_up'] = False
if 'mision_activa' not in st.session_state:
    st.session_state['mision_activa'] = None
if 'hora_inicio_mision' not in st.session_state:
    st.session_state['hora_inicio_mision'] = None

# -----------------------------------------------------------------------------
# CONEXIÓN A BASES DE DATOS Y APIs
# -----------------------------------------------------------------------------
@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# Configuración estricta de tu versión de Gemini
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# -----------------------------------------------------------------------------
# LÓGICA DE DATOS Y MOTORES DE INTELIGENCIA
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
    
    # Smart Scheduler: Consultar historial de fatiga de ayer
    res_ayer = supabase.table("misiones_diarias").select("*").eq("jugador_id", jugador_id).eq("fecha", ayer).execute()
    
    zonas_fatigadas = []
    hizo_caminata_ayer = False
    
    for m in res_ayer.data:
        zona = m.get('zona_muscular')
        if zona in ['pecho', 'espalda', 'piernas', 'core', 'general']:
            zonas_fatigadas.append(zona)
        if zona == 'caminata':
            hizo_caminata_ayer = True
            
    res_catalogo = supabase.table("diccionario_misiones").select("*").execute()
    catalogo = res_catalogo.data
    misiones_asignadas = []
    
    entrenamiento_pesado_asignado = False
    
    for mision in catalogo:
        tit = mision['titulo']
        zona = mision.get('zona_muscular', 'general')
        
        # Rama Intelectual
        if zona == 'intelecto':
            if random.random() <= float(mision['probabilidad_aparicion']):
                misiones_asignadas.append(mision)
            continue
            
        # Rama de Caminatas Intercaladas
        if zona == 'caminata':
            if "Semana 1" in tit and semana_actual != 1: continue
            if "Semana 2" in tit and semana_actual != 2: continue
            if "Semana 3" in tit and semana_actual != 3: continue
            
            if semana_actual in [1, 2] and hizo_caminata_ayer:
                continue 
                
            misiones_asignadas.append(mision)
            continue
            
        # Rama Física Pesada
        if "Suspensión" in tit and not barra_desbloqueada: continue
        if zona in zones_fatigadas: continue
        if entrenamiento_pesado_asignado: continue
            
        if random.random() <= float(mision['probabilidad_aparicion']):
            misiones_asignadas.append(mision)
            entrenamiento_pesado_asignado = True

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
    
    if zona_muscular:
        columna_zona = f"exp_{zona_muscular.lower()}"
        if columna_zona in perfil:
            xp_zona_actual = perfil[columna_zona] or 0
            datos_a_actualizar[columna_zona] = xp_zona_actual + cantidad_xp

    supabase.table("perfil_jugador").update(datos_a_actualizar).eq("id", jugador_id).execute()
    return hubo_level_up, nivel

def analizar_fisico(imagen, peso_actual):
    imagen.thumbnail((800, 800))
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
    
    response = model.generate_content([prompt, imagen])
    return response.text

# -----------------------------------------------------------------------------
# INTERFAZ DE USUARIO (UI CORES)
# -----------------------------------------------------------------------------
perfil = obtener_perfil()
verificar_progreso_campana(perfil['id'], perfil)

# --- SISTEMA DE ALARMA: LEVEL UP ---
if st.session_state['play_level_up']:
    st.audio("level_up.mp3", autoplay=True)
    st.balloons()
    st.session_state['play_level_up'] = False

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
    META_MUSCULO = 1000.0
    
    xp_inte = perfil.get('exp_intelecto', 0)
    xp_pecho = perfil.get('exp_pecho', 0)
    xp_espal = perfil.get('exp_espalda', 0)
    xp_core = perfil.get('exp_core', 0)
    xp_pier = perfil.get('exp_piernas', 0)

    op_inte = min(0.2 + (xp_inte / META_MUSCULO), 1.0)
    op_pecho = min(0.2 + (xp_pecho / META_MUSCULO), 1.0)
    op_espal = min(0.2 + (xp_espal / META_MUSCULO), 1.0)
    op_core = min(0.2 + (xp_core / META_MUSCULO), 1.0)
    op_pier = min(0.2 + (xp_pier / META_MUSCULO), 1.0)

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
                st.session_state['play_level_up'] = True
                st.success(f"¡LEVEL UP! Nivel {nuevo_nivel} alcanzado. +3 Puntos de Atributo disponibles.")
            else:
                st.success(f"¡Registro actualizado! {nuevas_horas} horas añadidas. +{xp_ganada} XP.")
            st.rerun()
        else:
            st.info("No se detectaron nuevos entrenamientos en la lista.")

st.markdown("---")

# --- Sección 4: Misiones Diarias (QUEST BOARD & EVOLUTION PROTOCOL) ---
mision_activa = st.session_state.get('mision_activa')

if mision_activa:
    # ==========================================
    # ⚔️ MODO DE COMBATE ACTIVO (VENTANA PRINCIPAL DE MISIÓN)
    # ==========================================
    st.subheader("⚔️ MODO DE COMBATE ACTIVO")
    
    with st.container(border=True):
        st.markdown(f"### {mision_activa['titulo']}")
        st.caption(f"ZONA DE IMPACTO: **{mision_activa.get('zona_muscular', 'N/A').upper()}**")
        st.write(mision_activa['descripcion'])
    
    # Cronómetro holográfico inyectado en la pantalla vía JavaScript
    timer_html = """
    <div style="background-color: #0e1117; padding: 15px; border-radius: 10px; text-align: center; border: 2px solid #E50914;">
        <p style="color: #888; font-family: sans-serif; margin: 0 0 5px 0; font-weight: bold;">TIEMPO DE ENFRENTAMIENTO</p>
        <div id="stopwatch" style="font-size: 3.5rem; font-family: monospace; color: #00ffcc; font-weight: bold;">00:00:00</div>
    </div>
    <script>
        let start = Date.now();
        setInterval(function() {
            let delta = Date.now() - start;
            let hrs = Math.floor(delta / 3600000).toString().padStart(2, '0');
            let mins = Math.floor((delta % 3600000) / 60000).toString().padStart(2, '0');
            let secs = Math.floor((delta % 60000) / 1000).toString().padStart(2, '0');
            document.getElementById('stopwatch').innerText = hrs + ":" + mins + ":" + secs;
        }, 1000);
    </script>
    """
    components.html(timer_html, height=130)
    st.divider()
    
    # DESLIZADOR RETROSPECTIVO DE EVALUACIÓN POST-MISIÓN
    esfuerzo_seleccionado = st.select_slider(
        "📊 Evaluación del Esfuerzo (Completa la tarea y selecciona cómo se sintió para mutar el Sistema):",
        options=['Muy Fácil', 'Un poco fácil', 'Adecuada', 'Un poco compleja', 'Compleja'],
        value='Adecuada'
    )
    
    col_fin1, col_fin2 = st.columns(2)
    with col_fin1:
        if st.button("🛑 FINALIZAR Y EVOLUCIONAR", use_container_width=True):
            tiempo_final = datetime.datetime.now()
            segundos_tardados = int((tiempo_final - st.session_state['hora_inicio_mision']).total_seconds())
            
            # 1. Traer datos base actuales del Diccionario de Misiones
            res_dic = supabase.table("diccionario_misiones").select("*").eq("titulo", mision_activa['titulo']).execute()
            
            if res_dic.data:
                mision_base = res_dic.data[0]
                desc_original = mision_base['descripcion']
                xp_base_original = mision_base['xp_recompensa']
                
                # Definición de Multiplicadores Permanentes y de Sesión
                mult_texto_perm = {'Muy Fácil': 1.25, 'Un poco fácil': 1.10, 'Adecuada': 1.0, 'Un poco compleja': 1.0, 'Compleja': 0.85}
                mult_xp_perm = {'Muy Fácil': 1.15, 'Un poco fácil': 1.05, 'Adecuada': 1.0, 'Un poco compleja': 1.0, 'Compleja': 0.95}
                mult_xp_hoy = {'Muy Fácil': 1.0, 'Un poco fácil': 1.0, 'Adecuada': 1.0, 'Un poco compleja': 1.10, 'Compleja': 1.20}
                
                m_texto = mult_texto_perm[esfuerzo_seleccionado]
                m_xp = mult_xp_perm[esfuerzo_seleccionado]
                
                # RECALIBRACIÓN MEDIANTE REGEX DE TEXTO (Afecta repeticiones, minutos y segundos)
                def rep_reps(match):
                    val = int(match.group(1))
                    return f"x{max(1, int(val * m_texto))}"
                desc_evolucionada = re.sub(r'x(\d+)', rep_reps, desc_original)
                
                def rep_mins(match):
                    val = int(match.group(1))
                    return f"{max(5, int(val * m_texto))} minutos"
                desc_evolucionada = re.sub(r'(\d+)\s*minutos', rep_mins, desc_evolucionada)
                
                def rep_times(match):
                    segs = int(match.group(1))
                    new_segs = min(max(5, int(segs * m_texto)), 59)
                    return f"00:{new_segs:02d}"
                desc_evolucionada = re.sub(r'00:(\d{2})', rep_times, desc_evolucionada)
                
                xp_base_evolucionada = max(5, int(xp_base_original * m_xp))
                
                # 2. EJECUTAR EL UPDATE PERMANENTE (SOBRECARGA PROGRESIVA EN BD)
                if esfuerzo_seleccionado != 'Adecuada':
                    supabase.table("diccionario_misiones").update({
                        "descripcion": desc_evolucionada,
                        "xp_recompensa": xp_base_evolucionada
                    }).eq("titulo", mision_activa['titulo']).execute()
                    st.toast(f"✨ ¡SISTEMA RECALIBRADO! La misión ha evolucionado de forma permanente.")
                
                # 3. Otorgar Recompensas de hoy
                xp_final_hoy = int(xp_base_original * mult_xp_hoy[esfuerzo_seleccionado])
                
                zona_trabajada = mision_activa.get('zona_muscular', None)
                if zona_trabajada == 'caminata': zona_trabajada = 'piernas'
                
                level_up, nuevo_nivel = otorgar_xp(perfil['id'], xp_final_hoy, zona_trabajada)
                
                # 4. Cerrar registro diario
                supabase.table("misiones_diarias").update({
                    "estado": "completada",
                    "tiempo_segundos": segundos_tardados,
                    "nivel_esfuerzo": esfuerzo_seleccionado
                }).eq("id", mision_activa['id']).execute()
                
                if level_up:
                    st.session_state['play_level_up'] = True
                    st.toast(f"🚀 ¡LEVEL UP! +{xp_final_hoy} XP conseguidos.")
                else:
                    st.toast(f"✅ Misión finalizada. Reclamados +{xp_final_hoy} XP.")
                    
            # Resetear estados de combate
            st.session_state['mision_activa'] = None
            st.session_state['hora_inicio_mision'] = None
            st.rerun()
            
    with col_fin2:
        if st.button("↩️ Abortar y Volver", use_container_width=True):
            st.session_state['mision_activa'] = None
            st.session_state['hora_inicio_mision'] = None
            st.rerun()

else:
    # ==========================================
    # 📜 TABLERO NORMAL (QUEST BOARD PRINCIPAL)
    # ==========================================
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
        pendientes = [m for m in misiones_hoy if m.get('estado', 'pendiente') == 'pendiente']
        completadas = [m for m in misiones_hoy if m.get('estado', '') == 'completada']
        
        if pendientes:
            st.write("### ⚠️ MISIONES ACTIVAS")
            for mision in pendientes:
                with st.container(border=True):
                    st.markdown(f"#### [{mision['rango']}] {mision['titulo']}")
                    st.caption(f"ZONA DE IMPACTO: **{mision.get('zona_muscular', 'N/A').upper()}**")
                    st.write(mision['descripcion'])
                    
                    st.divider()
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("▶️ INICIAR MISIÓN", key=f"iniciar_{mision['id']}", use_container_width=True):
                            st.session_state['mision_activa'] = mision
                            st.session_state['hora_inicio_mision'] = datetime.datetime.now()
                            st.rerun()
                    with col2:
                        if st.button("❌ Rechazar", key=f"rech_{mision['id']}", use_container_width=True):
                            supabase.table("misiones_diarias").delete().eq("id", mision['id']).execute()
                            st.toast("Misión rechazada y eliminada del panel.")
                            st.rerun()
                            
        if completadas:
            st.write("### 🏆 REGISTRO DE VICTORIAS HOY")
            for mision in completadas:
                with st.container(border=True):
                    st.markdown(f"~~[{mision['rango']}] {mision['titulo']}~~")
                    tiempo_texto = ""
                    if mision.get('tiempo_segundos'):
                        m, s = divmod(mision['tiempo_segundos'], 60)
                        tiempo_texto = f" | ⏱️ {m}m {s}s | 🔥 {mision.get('nivel_esfuerzo', '')}"
                    st.success(f"Misión Completada {tiempo_texto}")
