import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client, Client
import datetime
import requests
import re
import random
import json
from datetime import timedelta
import google.generativeai as genai
from PIL import Image

# -----------------------------------------------------------------------------
# CONFIGURACIÓN VISUAL Y MEMORIA DEL SISTEMA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Solo Leveling: System",
    page_icon="🗡️",
    layout="wide"
)

st.markdown("""
    <style>
    .stProgress > div > div > div > div {
        background-color: #E50914; 
    }
    </style>
""", unsafe_allow_html=True)

if 'play_level_up' not in st.session_state:
    st.session_state['play_level_up'] = False
if 'mision_activa' not in st.session_state:
    st.session_state['mision_activa'] = None
if 'hora_inicio_mision' not in st.session_state:
    st.session_state['hora_inicio_mision'] = None

# --- PARCHE DE ZONA HORARIA (ARGENTINA UTC-3) ---
def get_fecha_hoy():
    return (datetime.datetime.utcnow() - timedelta(hours=3)).date()

# -----------------------------------------------------------------------------
# CONEXIÓN A BASES DE DATOS Y APIs
# -----------------------------------------------------------------------------
@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# -----------------------------------------------------------------------------
# MOTORES LÓGICOS: TÍTULOS Y RACHAS
# -----------------------------------------------------------------------------
def calcular_rango_it(xp):
    if xp < 300: return "Novato de UTN"
    if xp < 800: return "Estudiante de Sistemas Avanzado"
    if xp < 1500: return "Desarrollador Backend Junior"
    if xp < 3000: return "Desarrollador Semi-Senior"
    if xp < 5000: return "Arquitecto de Software (Senior)"
    if xp < 8000: return "Ingeniero IA / White Hacker"
    return "CEO de IT (Clase S)"

def calcular_rango_fisico(xp_total):
    if xp_total < 300: return "Civil en Acondicionamiento"
    if xp_total < 800: return "Entusiasta de la Calistenia"
    if xp_total < 1500: return "Atleta Disciplinado"
    if xp_total < 3000: return "Guerrero de Hierro"
    if xp_total < 5000: return "Fisicoculturista / Elite"
    if xp_total < 8000: return "Campeón Olímpico"
    return "Monarca Físico (Clase S)"

def actualizar_racha(jugador_id, perfil):
    hoy = get_fecha_hoy()
    ultima = perfil.get('ultima_conexion')
    racha_actual = perfil.get('racha_dias', 0)
    
    if ultima:
        ultima_fecha = datetime.datetime.strptime(ultima, '%Y-%m-%d').date()
        diferencia = (hoy - ultima_fecha).days
        
        if diferencia == 1:
            racha_actual += 1
        elif diferencia > 1:
            racha_actual = 1
    else:
        racha_actual = 1

    if ultima != hoy.isoformat():
        supabase.table("perfil_jugador").update({
            "racha_dias": racha_actual,
            "ultima_conexion": hoy.isoformat()
        }).eq("id", jugador_id).execute()
        
    return racha_actual

# -----------------------------------------------------------------------------
# LÓGICA DE DATOS Y ORÁCULO IA
# -----------------------------------------------------------------------------
def obtener_perfil():
    respuesta = supabase.table("perfil_jugador").select("*").limit(1).execute()
    if respuesta.data:
        return respuesta.data[0]
    else:
        nuevo_perfil = supabase.table("perfil_jugador").insert({}).execute()
        return nuevo_perfil.data[0]

def obtener_misiones_activas(jugador_id):
    hoy = get_fecha_hoy().isoformat()
    respuesta = supabase.table("misiones_diarias").select("*").eq("jugador_id", jugador_id).execute()
    
    misiones_mostrar = []
    for m in respuesta.data:
        if m.get('tipo_mision') == 'epica' and m.get('estado') == 'pendiente':
            misiones_mostrar.append(m)
        elif m.get('tipo_mision') == 'diaria' and m['fecha'] == hoy:
            misiones_mostrar.append(m)
        elif m.get('estado') == 'completada' and m['fecha'] == hoy:
            misiones_mostrar.append(m) 
            
    return misiones_mostrar

def generar_misiones_del_dia(jugador_id):
    hoy = get_fecha_hoy()
    ayer = (hoy - timedelta(days=1)).isoformat()
    hoy_str = hoy.isoformat()
    
    perfil = obtener_perfil()
    semana_actual = perfil.get('semana_actual', 1)
    barra_desbloqueada = perfil.get('barra_calistenia_desbloqueada', False)
    
    misiones_actuales = obtener_misiones_activas(jugador_id)
    hay_epica_intelecto = any(m.get('tipo_mision') == 'epica' and m.get('zona_muscular') == 'intelecto' and m.get('estado') == 'pendiente' for m in misiones_actuales)
    
    # Leemos ayer y hoy para evitar duplicados en el mismo día
    res_recientes = supabase.table("misiones_diarias").select("*").eq("jugador_id", jugador_id).in_("fecha", [ayer, hoy_str]).execute()
    
    zonas_fatigadas = [m.get('zona_muscular') for m in res_recientes.data if m.get('zona_muscular') in ['pecho', 'espalda', 'piernas', 'core'] and m.get('fecha') == ayer]
    hizo_caminata_reciente = any(m.get('zona_muscular') == 'caminata' for m in res_recientes.data if m.get('fecha') == ayer)
    
    # Registro de lo que ya se generó HOY para no repetirlo
    misiones_ya_generadas_hoy = [m['titulo'] for m in res_recientes.data if m.get('fecha') == hoy_str]
            
    res_catalogo = supabase.table("diccionario_misiones").select("*").execute()
    misiones_asignadas = []
    
    # Bloqueamos rutina física si ya se asignó una hoy
    entrenamiento_pesado_asignado = any(m.get('zona_muscular') in ['pecho', 'espalda', 'piernas', 'core'] for m in res_recientes.data if m.get('fecha') == hoy_str)
    
    for mision in res_catalogo.data:
        tit = mision['titulo']
        zona = mision.get('zona_muscular', 'general')
        
        # Filtro Anti-Spam: Si ya sacaste esta misión hoy, no la repite
        if tit in misiones_ya_generadas_hoy: continue
        
        if zona == 'intelecto':
            if hay_epica_intelecto: continue
            if random.random() <= float(mision['probabilidad_aparicion']):
                misiones_asignadas.append(mision)
            continue
            
        if zona == 'caminata':
            if "Semana 1" in tit and semana_actual != 1: continue
            if "Semana 2" in tit and semana_actual != 2: continue
            if "Semana 3" in tit and semana_actual != 3: continue
            if semana_actual in [1, 2] and hizo_caminata_reciente: continue 
            misiones_asignadas.append(mision)
            continue
            
        if "Suspensión" in tit and not barra_desbloqueada: continue
        if zona in zonas_fatigadas: continue
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
            "estado": "pendiente",
            "tipo_mision": "diaria"
        }).execute()
        
    return misiones_asignadas

def crear_mision_epica_ia(jugador_id, contexto_usuario):
    model = genai.GenerativeModel('gemini-2.5-flash')
    prompt = f"""
    Actúa estrictamente como el Sistema de Solo Leveling. El jugador solicita una Misión Épica a largo plazo basada en este objetivo: "{contexto_usuario}"
    Crea una misión de alta jerarquía. Debes estructurar la respuesta en un formato JSON plano y limpio.
    
    Genera exactamente este esquema JSON (asegúrate de escapar comillas internas):
    {{
      "titulo": "[MISIÓN ÉPICA] Nombre creativo y épico",
      "descripcion": "Descripción detallada estilo RPG, desglosando los objetivos.",
      "rango": "S",
      "zona_muscular": "intelecto",
      "xp_recompensa": 500
    }}
    
    Responde únicamente el objeto JSON, sin envoltorios de código markdown ni texto adicional.
    """
    response = model.generate_content(prompt)
    try:
        texto_api = response.text.strip()
        if "```" in texto_api:
            texto_api = texto_api.split("```")[1]
            if texto_api.startswith("json"):
                texto_api = texto_api[4:]
        texto_api = texto_api.strip()
        datos_mision = json.loads(texto_api)
        
        supabase.table("misiones_diarias").insert({
            "jugador_id": jugador_id,
            "titulo": datos_mision['titulo'],
            "descripcion": datos_mision['descripcion'],
            "categoria": "especial",
            "rango": datos_mision.get('rango', 'A'),
            "zona_muscular": datos_mision.get('zona_muscular', 'intelecto'),
            "fecha": get_fecha_hoy().isoformat(),
            "estado": "pendiente",
            "tipo_mision": "epica"
        }).execute()
        return True
    except Exception as e:
        print(f"Error crítico en Oráculo: {e} | Texto recibido: {response.text}")
        return False

def obtener_horas_totales_youtube(jugador_id):
    respuesta = supabase.table("historial_youtube").select("duracion_horas").eq("jugador_id", jugador_id).execute()
    if not respuesta.data: return 0.0
    return sum(item['duracion_horas'] for item in respuesta.data)

def sincronizar_radar(jugador_id):
    api_key = st.secrets["YOUTUBE_API_KEY"]
    playlist_id = st.secrets["YOUTUBE_PLAYLIST_ID"]
    url_playlist = f"https://www.googleapis.com/youtube/v3/playlistItems?part=contentDetails&maxResults=50&playlistId={playlist_id}&key={api_key}"
    res_playlist = requests.get(url_playlist).json()
    if "items" not in res_playlist: return 0 
    video_ids = [item['contentDetails']['videoId'] for item in res_playlist['items']]
    res_db = supabase.table("historial_youtube").select("video_id").execute()
    videos_procesados = [fila['video_id'] for fila in res_db.data]
    videos_nuevos = [vid for vid in video_ids if vid not in videos_procesados]
    if not videos_nuevos: return 0 
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
        supabase.table("historial_youtube").insert({"video_id": vid_id, "titulo": titulo, "duracion_horas": duracion_decimal, "jugador_id": jugador_id}).execute()
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
    datos_a_actualizar = {"nivel": nivel, "xp_actual": int(xp_actual), "xp_siguiente_nivel": xp_siguiente, "puntos_atributo": puntos_libres}
    if zona_muscular:
        columna_zona = f"exp_{zona_muscular.lower()}"
        if columna_zona in perfil:
            xp_zona_actual = perfil[columna_zona] or 0
            datos_a_actualizar[columna_zona] = xp_zona_actual + cantidad_xp
    supabase.table("perfil_jugador").update(datos_a_actualizar).eq("id", jugador_id).execute()
    return hubo_level_up, nivel

def aplicar_modificador_esfuerzo(texto, esfuerzo):
    mult = 1.0
    if esfuerzo == 'Muy Fácil': mult = 0.7
    elif esfuerzo == 'Un poco fácil': mult = 0.85
    elif esfuerzo == 'Adecuada': mult = 1.0
    elif esfuerzo == 'Un poco compleja': mult = 1.15
    elif esfuerzo == 'Compleja': mult = 1.30
    def rep_replacer(match):
        return f"x{max(1, int(int(match.group(1)) * mult))}"
    texto_mod = re.sub(r'x(\d+)', rep_replacer, texto)
    def time_replacer(match):
        new_segs = min(max(5, int(int(match.group(1)) * mult)), 59)
        return f"00:{new_segs:02d}"
    texto_mod = re.sub(r'00:(\d{2})', time_replacer, texto_mod)
    return texto_mod

def analizar_fisico(imagen, peso_actual):
    imagen.thumbnail((800, 800))
    model = genai.GenerativeModel('gemini-2.5-flash')
    prompt = f"""
    Actúa estrictamente como un Sistema RPG de entrenamiento físico. Analiza esta imagen.
    El usuario pesa {peso_actual} kg y está entrenando calistenia para dominar 25 dominadas estrictas.
    Reporte: 1. Musculatura visible (tracción). 2. Consejo técnico. 3. Frase épica.
    """
    response = model.generate_content([prompt, imagen])
    return response.text

# -----------------------------------------------------------------------------
# INTERFAZ DE USUARIO (UI)
# -----------------------------------------------------------------------------
perfil = obtener_perfil()
racha_dias = actualizar_racha(perfil['id'], perfil)

rango_it = calcular_rango_it(perfil.get('exp_intelecto', 0))
xp_total_fisica = perfil.get('exp_pecho',0) + perfil.get('exp_espalda',0) + perfil.get('exp_piernas',0) + perfil.get('exp_core',0)
rango_fisico = calcular_rango_fisico(xp_total_fisica)

col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.title("STATUS PANEL")
with col_head2:
    st.markdown(f"<h3 style='text-align: right; color: #E50914;'>🔥 Racha: {racha_dias} Días</h3>", unsafe_allow_html=True)
st.markdown("---")

if st.session_state['play_level_up']:
    st.audio("level_up.mp3", autoplay=True)
    st.balloons()
    st.session_state['play_level_up'] = False

col1, col2, col3 = st.columns([1, 2, 1])
with col1:
    st.subheader(f"[{perfil['nombre']}]")
    st.write(f"**Nivel:** {perfil['nivel']}")
    st.caption(f"💻 {rango_it}")
    st.caption(f"⚔️ {rango_fisico}")

with col2:
    progreso_xp = perfil['xp_actual'] / perfil['xp_siguiente_nivel']
    st.progress(progreso_xp, text=f"XP: {perfil['xp_actual']} / {perfil['xp_siguiente_nivel']}")

with col3:
    st.write(f"💪 STR: {perfil['fuerza']} | 🧠 INT: {perfil['inteligencia']} | ⚡ AGI: {perfil['agilidad']}")
    if perfil.get('puntos_atributo', 0) > 0:
        st.info(f"✨ Puntos Disponibles: {perfil['puntos_atributo']}")
        c_str, c_int, c_agi = st.columns(3)
        with c_str:
            if st.button("+ STR"):
                supabase.table("perfil_jugador").update({"fuerza": perfil['fuerza'] + 1, "puntos_atributo": perfil['puntos_atributo'] - 1}).eq("id", perfil['id']).execute(); st.rerun()
        with c_int:
            if st.button("+ INT"):
                supabase.table("perfil_jugador").update({"inteligencia": perfil['inteligencia'] + 1, "puntos_atributo": perfil['puntos_atributo'] - 1}).eq("id", perfil['id']).execute(); st.rerun()
        with c_agi:
            if st.button("+ AGI"):
                supabase.table("perfil_jugador").update({"agilidad": perfil['agilidad'] + 1, "puntos_atributo": perfil['puntos_atributo'] - 1}).eq("id", perfil['id']).execute(); st.rerun()

st.markdown("---")

with st.expander("🔮 ORÁCULO DEL SISTEMA (Forjar Misión Especial)"):
    st.write("Solicita una misión a largo plazo. El Sistema suprimirá las tareas diarias menores de esa rama.")
    prompt_mision = st.text_area("Contexto de la Misión:", placeholder="Ej: Tengo que estudiar 3 libros de 25 páginas...")
    if st.button("⚡ Forjar Misión con IA"):
        if prompt_mision:
            with st.spinner("La IA está calculando la jerarquía..."):
                exito = crear_mision_epica_ia(perfil['id'], prompt_mision)
                if exito:
                    st.success("Misión Épica registrada.")
                    st.rerun()
                else:
                    st.error("Error de conexión con el Oráculo.")

st.markdown("---")

st.subheader("ANÁLISIS ESTRUCTURAL AVANZADO")
tab_svg, tab_ia = st.tabs(["Holograma", "Escáner (IA)"])

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
    <svg viewBox="0 0 200 400" width="100%" height="300" xmlns="http://www.w3.org/2000/svg">
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
    col_b, col_g = st.columns([1, 1])
    with col_b:
        st.progress(min(xp_inte/META_MUSCULO, 1.0), text=f"Intelecto: {xp_inte}")
        st.progress(min(xp_espal/META_MUSCULO, 1.0), text=f"Espalda: {xp_espal}")
        st.progress(min(xp_pecho/META_MUSCULO, 1.0), text=f"Pecho: {xp_pecho}")
        st.progress(min(xp_core/META_MUSCULO, 1.0), text=f"Core: {xp_core}")
        st.progress(min(xp_pier/META_MUSCULO, 1.0), text=f"Piernas: {xp_pier}")
    with col_g:
        st.markdown(svg_cuerpo, unsafe_allow_html=True)

with tab_ia:
    foto_subida = st.file_uploader("Subir foto del torso", type=['jpg', 'jpeg', 'png'])
    peso_input = st.number_input("Peso actual (kg):", min_value=50.0, max_value=150.0, value=102.0)
    if foto_subida and st.button("👁️ Iniciar Escaneo"):
        with st.spinner("Analizando composición..."):
            st.markdown(f"> *{analizar_fisico(Image.open(foto_subida), peso_input)}*")

st.markdown("---")

# -----------------------------------------------------------------------------
# Sección 4: Misiones Diarias & Modo Combate (UI REESCRITA)
# -----------------------------------------------------------------------------
mision_activa = st.session_state.get('mision_activa')

if mision_activa:
    st.subheader("⚔️ MODO DE COMBATE ACTIVO")
    
    esfuerzo_seleccionado = st.select_slider(
        "Ajuste Táctico (Modificador en vivo):",
        options=['Muy Fácil', 'Un poco fácil', 'Adecuada', 'Un poco compleja', 'Compleja'],
        value='Adecuada'
    )
    texto_modificado = aplicar_modificador_esfuerzo(mision_activa['descripcion'], esfuerzo_seleccionado)
    
    with st.container(border=True):
        st.markdown(f"### {mision_activa['titulo']}")
        st.caption(f"ZONA DE IMPACTO: **{mision_activa.get('zona_muscular', 'N/A').upper()}**")
        st.write(texto_modificado)
    
    timer_html = """
    <div style="background-color: #0e1117; padding: 15px; border-radius: 10px; text-align: center; border: 2px solid #E50914;">
        <p style="color: #888; margin: 0 0 5px 0; font-weight: bold;">TIEMPO DE EJECUCIÓN</p>
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
    
    col_fin1, col_fin2 = st.columns(2)
    with col_fin1:
        if st.button("🛑 FINALIZAR Y RECLAMAR", use_container_width=True):
            tiempo_final = datetime.datetime.now()
            segundos_tardados = int((tiempo_final - st.session_state['hora_inicio_mision']).total_seconds())
            
            base_xp = mision_activa.get('xp_recompensa', 50)
            mult_xp = {'Muy Fácil': 0.7, 'Un poco fácil': 0.85, 'Adecuada': 1.0, 'Un poco compleja': 1.15, 'Compleja': 1.3}
            xp_final = int(base_xp * mult_xp[esfuerzo_seleccionado])
            
            zona_trabajada = mision_activa.get('zona_muscular', None)
            if zona_trabajada == 'caminata': zona_trabajada = 'piernas'
            
            level_up, nuevo_nivel = otorgar_xp(perfil['id'], xp_final, zona_trabajada)
            
            # Si era misión épica y se finaliza
            if mision_activa.get('tipo_mision') == 'epica':
                supabase.table("misiones_diarias").update({
                    "estado": "completada",
                    "tiempo_segundos": segundos_tardados,
                    "nivel_esfuerzo": esfuerzo_seleccionado
                }).eq("id", mision_activa['id']).execute()
            else:
                # Misión diaria con Sobrecarga Progresiva
                res_dic = supabase.table("diccionario_misiones").select("*").eq("titulo", mision_activa['titulo']).execute()
                if res_dic.data and esfuerzo_seleccionado != 'Adecuada':
                    m_base = res_dic.data[0]
                    mult_texto = {'Muy Fácil': 1.25, 'Un poco fácil': 1.10, 'Un poco compleja': 1.0, 'Compleja': 0.85}[esfuerzo_seleccionado]
                    desc_evo = re.sub(r'x(\d+)', lambda m: f"x{max(1, int(int(m.group(1)) * mult_texto))}", m_base['descripcion'])
                    desc_evo = re.sub(r'00:(\d{2})', lambda m: f"00:{min(max(5, int(int(m.group(1)) * mult_texto)), 59):02d}", desc_evo)
                    supabase.table("diccionario_misiones").update({"descripcion": desc_evo}).eq("titulo", mision_activa['titulo']).execute()

                supabase.table("misiones_diarias").update({
                    "estado": "completada",
                    "tiempo_segundos": segundos_tardados,
                    "nivel_esfuerzo": esfuerzo_seleccionado
                }).eq("id", mision_activa['id']).execute()
            
            if level_up:
                st.session_state['play_level_up'] = True
                st.toast(f"¡SUBIDA DE NIVEL! Ganaste {xp_final} XP.")
            else:
                st.toast(f"Misión Cumplida. +{xp_final} XP.")
            
            st.session_state['mision_activa'] = None
            st.session_state['hora_inicio_mision'] = None
            st.rerun()
            
    with col_fin2:
        if st.button("↩️ Abortar y Volver", use_container_width=True):
            st.session_state['mision_activa'] = None
            st.session_state['hora_inicio_mision'] = None
            st.rerun()

else:
    st.subheader("📜 QUEST BOARD")
    misiones_activas = obtener_misiones_activas(perfil['id'])

    epicas = [m for m in misiones_activas if m.get('tipo_mision') == 'epica' and m.get('estado') == 'pendiente']
    diarias = [m for m in misiones_activas if m.get('tipo_mision') == 'diaria' and m.get('estado') == 'pendiente']
    completadas = [m for m in misiones_activas if m.get('estado') == 'completada' and m.get('fecha') == get_fecha_hoy().isoformat()]

    if epicas:
        st.write("### 👑 CAMPAÑAS ACTIVAS (LARGO PLAZO)")
        for mision in epicas:
            with st.container(border=True):
                st.markdown(f"<h4 style='color: #FFD700;'>[{mision['rango']}] {mision['titulo']}</h4>", unsafe_allow_html=True)
                st.caption(f"ZONA DE IMPACTO: **{mision.get('zona_muscular', 'N/A').upper()}**")
                st.write(mision['descripcion'])
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("▶️ CONTINUAR / FINALIZAR", key=f"iniciar_epica_{mision['id']}", use_container_width=True):
                        st.session_state['mision_activa'] = mision
                        st.session_state['hora_inicio_mision'] = datetime.datetime.now()
                        st.rerun()
                with col2:
                    if st.button("❌ Abandonar Campaña", key=f"rech_epica_{mision['id']}", use_container_width=True):
                        supabase.table("misiones_diarias").delete().eq("id", mision['id']).execute()
                        st.rerun()
                        
    st.write("### ⚠️ MISIONES DIARIAS")
    if diarias:
        for mision in diarias:
            with st.container(border=True):
                st.markdown(f"#### [{mision['rango']}] {mision['titulo']}")
                st.caption(f"ZONA DE IMPACTO: **{mision.get('zona_muscular', 'N/A').upper()}**")
                st.write(mision['descripcion'])
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("▶️ INICIAR MISIÓN", key=f"iniciar_{mision['id']}", use_container_width=True):
                        st.session_state['mision_activa'] = mision
                        st.session_state['hora_inicio_mision'] = datetime.datetime.now()
                        st.rerun()
                with col2:
                    if st.button("❌ Rechazar", key=f"rech_{mision['id']}", use_container_width=True):
                        supabase.table("misiones_diarias").delete().eq("id", mision['id']).execute()
                        st.rerun()
    else:
        st.info("El Sistema no detecta misiones rutinarias activas.")
        if st.button("🎲 Extraer Misiones Diarias", use_container_width=True):
            with st.spinner("Calculando fatiga y probabilidades..."):
                generar_misiones_del_dia(perfil['id'])
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
