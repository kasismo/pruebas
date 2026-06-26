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

if 'play_level_up' not in st.session_state: st.session_state['play_level_up'] = False
if 'mision_activa' not in st.session_state: st.session_state['mision_activa'] = None
if 'hora_inicio_mision' not in st.session_state: st.session_state['hora_inicio_mision'] = None

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
# MOTORES LÓGICOS: TÍTULOS Y PENALIDAD CON SANTUARIO
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

def procesar_sistema_penalidad(jugador_id, perfil):
    hoy = get_fecha_hoy()
    ultima_con_str = perfil.get('ultima_conexion')
    racha_actual = perfil.get('racha_dias', 0)
    
    # Miércoles = 2, Sábado = 5
    def es_dia_descanso(fecha):
        return fecha.weekday() in [2, 5]
        
    res_comp = supabase.table("misiones_diarias").select("fecha").eq("jugador_id", jugador_id).eq("estado", "completada").order("fecha", desc=True).limit(1).execute()
    
    if res_comp.data:
        ultima_fecha_completada = datetime.datetime.strptime(res_comp.data[0]['fecha'], '%Y-%m-%d').date()
    else:
        ultima_fecha_completada = hoy 
        
    if not ultima_con_str:
        supabase.table("perfil_jugador").update({"racha_dias": racha_actual, "ultima_conexion": hoy.isoformat()}).eq("id", jugador_id).execute()
        return racha_actual, 0, es_dia_descanso(hoy)
        
    ultima_conexion = datetime.datetime.strptime(ultima_con_str, '%Y-%m-%d').date()
    
    if hoy > ultima_conexion:
        dias_pasados = (hoy - ultima_conexion).days
        
        for i in range(1, dias_pasados + 1):
            fecha_evaluada = ultima_conexion + timedelta(days=i)
            if es_dia_descanso(fecha_evaluada):
                continue
                
            deuda_evaluada = 0
            curr = ultima_fecha_completada + timedelta(days=1)
            while curr <= fecha_evaluada:
                if not es_dia_descanso(curr):
                    deuda_evaluada += 1
                curr += timedelta(days=1)
                
            deuda_penalizable = deuda_evaluada - 1
            
            if deuda_penalizable == 3:
                racha_actual = max(0, racha_actual - 2)
            elif deuda_penalizable > 3:
                racha_actual = max(0, racha_actual - 1)
                
        supabase.table("perfil_jugador").update({
            "racha_dias": racha_actual,
            "ultima_conexion": hoy.isoformat()
        }).eq("id", jugador_id).execute()
        
    deuda_actual = 0
    curr = ultima_fecha_completada + timedelta(days=1)
    while curr <= hoy:
        if not es_dia_descanso(curr):
            deuda_actual += 1
        curr += timedelta(days=1)
        
    deuda_actual = max(0, deuda_actual - 1)
    
    return racha_actual, deuda_actual, es_dia_descanso(hoy)

# -----------------------------------------------------------------------------
# LÓGICA DE DATOS Y ORÁCULO IA DUAL (ÉPICO Y SIMPLE)
# -----------------------------------------------------------------------------
def obtener_perfil():
    respuesta = supabase.table("perfil_jugador").select("*").limit(1).execute()
    if respuesta.data: return respuesta.data[0]
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
    
    misiones_actuales = obtener_misiones_activas(jugador_id)
    res_recientes = supabase.table("misiones_diarias").select("*").eq("jugador_id", jugador_id).in_("fecha", [ayer, hoy_str]).execute()
    misiones_ya_generadas_hoy = [m['titulo'] for m in res_recientes.data if m.get('fecha') == hoy_str]
            
    misiones_asignadas = []
    
    # ENFOQUE EN CAMPAÑAS
    epicas_activas = [m for m in misiones_actuales if m.get('tipo_mision') == 'epica' and m.get('estado') == 'pendiente']
    
    for epica in epicas_activas:
        sub_tareas = epica.get('sub_tareas', [])
        tareas_pendientes = [t for t in sub_tareas if t.get('completadas', 0) < t.get('repeticiones_necesarias', 1)]
        
        if tareas_pendientes:
            es_lineal = any("Fase" in t.get('titulo', '') or "Nivel" in t.get('titulo', '') for t in sub_tareas)
            
            if es_lineal:
                tareas_hoy = [tareas_pendientes[0]]
            else:
                tareas_hoy = random.sample(tareas_pendientes, min(2, len(tareas_pendientes)))
                
            for t in tareas_hoy:
                titulo_campana = f"[Campaña] {t.get('titulo', 'Sub-misión')}"
                
                if titulo_campana not in misiones_ya_generadas_hoy:
                    misiones_asignadas.append({
                        'titulo': titulo_campana,
                        'descripcion': t.get('descripcion', ''),
                        'categoria': 'especial',
                        'rango': epica.get('rango', 'A'),
                        'zona_muscular': epica.get('zona_muscular', 'general'),
                        'parent_id': epica['id'], 
                        'xp_recompensa_dinamica': t.get('xp_por_vez', 20)
                    })

    for m in misiones_asignadas:
        supabase.table("misiones_diarias").insert({
            "jugador_id": jugador_id,
            "titulo": m['titulo'],
            "descripcion": m['descripcion'],
            "categoria": m.get('categoria', 'rutina'),
            "rango": m['rango'],
            "zona_muscular": m.get('zona_muscular', 'general'),
            "fecha": hoy_str,
            "estado": "pendiente",
            "tipo_mision": "diaria",
            "parent_id": m.get('parent_id', None),
            "xp_recompensa_dinamica": m.get('xp_recompensa_dinamica', 0)
        }).execute()
        
    return misiones_asignadas

def crear_mision_ia(jugador_id, contexto_usuario, tipo="epica"):
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    if tipo == "epica":
        prompt = f"""
        Actúa estrictamente como el Sistema de Solo Leveling. El jugador solicita una Misión Épica (Campaña Principal) basada en este objetivo: "{contexto_usuario}"
        Debes desglosar esta gran meta en un "Questline" (Sub-misiones rutinarias que deberán repetirse para llenar la meta final).
        
        [REGLA BIOMECÁNICA Y LÓGICA]: 
        Si es físico, NO aísles un solo músculo. Incluye ejercicios complementarios y sinergistas. Si es intelectual, abarca distintas ramas que converjan.
        
        Genera EXACTAMENTE este esquema JSON sin formato markdown:
        {{
          "titulo": "[MISIÓN ÉPICA] Nombre creativo",
          "descripcion": "Descripción del objetivo final.",
          "rango": "S",
          "zona_muscular": "intelecto",
          "xp_recompensa": 1500,
          "meta_total": 30, 
          "sub_tareas": [
            {{"titulo": "Tarea Principal / Foco", "descripcion": "Desc", "repeticiones_necesarias": 10, "completadas": 0, "xp_por_vez": 25}},
            {{"titulo": "Trabajo Secundario", "descripcion": "Desc", "repeticiones_necesarias": 10, "completadas": 0, "xp_por_vez": 25}}
          ]
        }}
        Asegúrate de que la suma de repeticiones de las sub_tareas sea igual a meta_total. Responde solo el JSON.
        """
    else: # Misión Simple Diaria
        prompt = f"""
        Actúa estrictamente como el Sistema de Solo Leveling. El jugador solicita una Misión Diaria Simple (una tarea rápida para completar HOY) basada en este contexto: "{contexto_usuario}"
        
        Esta misión NO tendrá sub-tareas ni será una campaña. Será una misión directa de un solo uso para autorregular la carga cognitiva o física del día.
        
        Genera EXACTAMENTE este esquema JSON plano sin formato markdown:
        {{
          "titulo": "[DIARIA] Nombre de la tarea",
          "descripcion": "Descripción concisa de la tarea a realizar hoy.",
          "rango": "C", 
          "zona_muscular": "intelecto",
          "xp_recompensa": 40
        }}
        El rango debe ser acorde al esfuerzo (C, B o A). La zona_muscular debe ser 'intelecto' o un músculo específico.
        Responde únicamente el objeto JSON.
        """
        
    response = model.generate_content(prompt)
    try:
        # EXTRACCIÓN BLINDADA (Regex busca únicamente el bloque JSON, ignora todo el texto extra)
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if not match:
            return False, f"La IA no devolvió un formato JSON válido. Respuesta: {response.text}"
            
        texto_limpio = match.group(0)
        datos_mision = json.loads(texto_limpio)
        
        if tipo == "epica":
            supabase.table("misiones_diarias").insert({
                "jugador_id": jugador_id,
                "titulo": datos_mision.get('titulo', '[MISIÓN ÉPICA]'),
                "descripcion": datos_mision.get('descripcion', ''),
                "categoria": "especial",
                "rango": datos_mision.get('rango', 'S'),
                "zona_muscular": datos_mision.get('zona_muscular', 'intelecto'),
                "fecha": get_fecha_hoy().isoformat(),
                "estado": "pendiente",
                "tipo_mision": "epica",
                "meta_total": int(datos_mision.get('meta_total', 1)),
                "sub_tareas": datos_mision.get('sub_tareas', []),
                "xp_recompensa_dinamica": int(datos_mision.get('xp_recompensa', 1000))
            }).execute()
        else: # Simple
            supabase.table("misiones_diarias").insert({
                "jugador_id": jugador_id,
                "titulo": datos_mision.get('titulo', '[DIARIA] Tarea'),
                "descripcion": datos_mision.get('descripcion', ''),
                "categoria": "especial", # Cambiado a 'especial' para evitar rechazos de base de datos
                "rango": datos_mision.get('rango', 'C'),
                "zona_muscular": datos_mision.get('zona_muscular', 'intelecto'),
                "fecha": get_fecha_hoy().isoformat(),
                "estado": "pendiente",
                "tipo_mision": "diaria", 
                "xp_recompensa_dinamica": int(datos_mision.get('xp_recompensa', 40))
            }).execute()
            
        return True, ""
    except Exception as e:
        # Si falla algo (tipo de dato, clave, BD), devolvemos el error exacto para verlo en pantalla
        return False, str(e)

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

def analizar_fisico(imagenes, peso_actual):
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    safety_settings = [
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    
    processed_images = []
    for img in imagenes:
        img.thumbnail((800, 800))
        processed_images.append(img)
        
    if len(processed_images) == 1:
        prompt = f"""
        Actúa estrictamente como un Sistema RPG de entrenamiento físico. Analiza esta imagen.
        El usuario pesa {peso_actual} kg y entrena calistenia. 
        Reporte: 1. Musculatura visible. 2. Consejo técnico. 3. Frase épica.
        """
    else:
        prompt = f"""
        Actúa estrictamente como un Sistema RPG de entrenamiento físico. Analiza estas {len(processed_images)} imágenes subidas por el usuario tomadas en diferentes momentos.
        El usuario pesa {peso_actual} kg y entrena calistenia. 
        Compara las imágenes y genera un reporte de progreso que incluya:
        1. Diferencias o mejoras notables en la composición corporal.
        2. Puntos fuertes a mantener y áreas de oportunidad.
        3. Frase épica del Sistema.
        """
        
    contents = [prompt] + processed_images
    
    try:
        response = model.generate_content(contents, safety_settings=safety_settings)
        texto = response.text 
        return texto
    except ValueError:
        return "⚠️ ALERTA DEL SISTEMA: El escáner visual fue bloqueado por los protocolos de seguridad de la IA de Google (posible exceso de piel descubierta). Intenta con otra foto que muestre mejor el contexto deportivo."
    except Exception as e:
        return f"⚠️ Error de conexión con el satélite escáner: {e}"

# -----------------------------------------------------------------------------
# INTERFAZ DE USUARIO (UI)
# -----------------------------------------------------------------------------
perfil = obtener_perfil()

# --- VALIDACIÓN DEL PENALTY ZONE Y DESCANSOS ---
racha_dias, deuda_dias, es_descanso_hoy = procesar_sistema_penalidad(perfil['id'], perfil)

rango_it = calcular_rango_it(perfil.get('exp_intelecto', 0))
xp_total_fisica = perfil.get('exp_pecho',0) + perfil.get('exp_espalda',0) + perfil.get('exp_piernas',0) + perfil.get('exp_core',0)
rango_fisico = calcular_rango_fisico(xp_total_fisica)

col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.title("STATUS PANEL")
with col_head2:
    st.markdown(f"<h3 style='text-align: right; color: #E50914;'>🔥 Racha: {racha_dias} Días</h3>", unsafe_allow_html=True)
    if es_descanso_hoy:
        st.markdown("<p style='text-align: right; color: #00ffcc; font-weight: bold;'>🛌 DÍA DE RECUPERACIÓN (Santuario Activo)</p>", unsafe_allow_html=True)
    elif deuda_dias == 1:
        st.markdown("<p style='text-align: right; color: #FFA500; font-weight: bold;'>⚠️ Deuda: 1 Día (Pausada)</p>", unsafe_allow_html=True)
    elif deuda_dias == 2:
        st.markdown("<p style='text-align: right; color: #FF4500; font-weight: bold;'>⚠️ Deuda: 2 Días (Última Oportunidad)</p>", unsafe_allow_html=True)
    elif deuda_dias >= 3:
        st.markdown(f"<p style='text-align: right; color: #8B0000; font-weight: bold;'>🩸 PENALTY ZONE (-{deuda_dias - 2} Días Historial)</p>", unsafe_allow_html=True)

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

with st.expander("🔮 ORÁCULO DEL SISTEMA (Forjar Misiones y Campañas)"):
    st.write("Configura tus objetivos. Usa Campañas para metas a largo plazo (se desglosarán en días) o Misiones Simples para tareas únicas de autorregulación (sólo por hoy).")
    
    tipo_mision = st.radio("Tipo de Forja:", ["Misión Diaria Simple (Para hoy)", "Campaña Épica (Largo Plazo)"])
    prompt_mision = st.text_area("Contexto:", placeholder="Ej: Mirar 3 videos de inecuaciones en Youtube y tomar apuntes...")
    
    if st.button("⚡ Forjar con IA"):
        if prompt_mision:
            with st.spinner("El Sistema está forjando tu destino..."):
                tipo_param = "simple" if "Simple" in tipo_mision else "epica"
                exito, msg_error = crear_mision_ia(perfil['id'], prompt_mision, tipo=tipo_param)
                if exito:
                    if tipo_param == "simple":
                        st.success("Misión Diaria inyectada. Ya puedes verla en tu Quest Board de hoy.")
                    else:
                        st.success("Misión Épica registrada. Extrae tus misiones diarias para obtener tus primeras sub-tareas.")
                    st.rerun()
                else:
                    st.error(f"Error devuelto por el Oráculo: {msg_error}")

st.markdown("---")

st.subheader("ANÁLISIS ESTRUCTURAL AVANZADO")
tab_svg, tab_ia, tab_arbol = st.tabs(["Holograma", "Escáner de Progreso (IA)", "Árbol de Habilidades"])

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
    st.write("Sube una foto actual para evaluación, o selecciona **múltiples fotos** tomadas a lo largo del tiempo para que el Sistema compare tu progreso.")
    fotos_subidas = st.file_uploader("Subir fotos del torso", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)
    peso_input = st.number_input("Peso actual (kg):", min_value=50.0, max_value=150.0, value=102.0)
    
    if fotos_subidas and st.button("👁️ Iniciar Escaneo de Progreso"):
        with st.spinner("Analizando composición y cruzando datos temporales..."):
            imagenes_abiertas = [Image.open(f) for f in fotos_subidas]
            resultado_ia = analizar_fisico(imagenes_abiertas, peso_input)
            st.markdown(f"> *{resultado_ia}*")

with tab_arbol:
    st.markdown("### EL CAMINO DE LA CALISTENIA (Path of the Monarch)")
    st.write("Tu progreso estático. El color dorado marca las habilidades que tu Nivel actual te permite dominar.")
    
    nivel_actual = perfil['nivel']
    
    fases = [
        {"fase": "🟢 FASE 1: Novato Absoluto (Nv. 1-20)", "desc": "Acondicionamiento base.", "hitos": [(1, "Plancha abdominal 30s"), (5, "Push-ups de rodillas x10"), (10, "Remo invertido"), (12, "Dead hang 1 min"), (15, "1 Push-up estricta"), (20, "Dominada negativa")]},
        {"fase": "🔵 FASE 2: Principiante (Nv. 21-40)", "desc": "Dominio del 100% de tu peso.", "hitos": [(25, "1 Pull-up estricta"), (30, "Fondos en paralelas x5"), (35, "Pike Push-ups"), (40, "L-Sit 10s")]},
        {"fase": "🟡 FASE 3: Intermedio (Nv. 41-60)", "desc": "Fuerza atlética superior.", "hitos": [(45, "Pistol Squat"), (50, "Muscle-Up (con impulso)"), (55, "One-arm Push-up"), (60, "Dragon Flag")]},
        {"fase": "🟠 FASE 4: Avanzado (Nv. 61-80)", "desc": "Isometría severa.", "hitos": [(65, "Muscle-Up estricto"), (70, "Back Lever"), (75, "Wall Handstand Push-ups"), (80, "Front Lever")]},
        {"fase": "🔴 FASE 5: Élite (Nv. 81-95)", "desc": "Nivel competitivo.", "hitos": [(85, "Freestanding Handstand Push-up"), (90, "One Arm Pull-up (OAP)"), (93, "Straddle Planche"), (95, "Full Planche")]},
        {"fase": "👑 FASE 6: Profesional / Nivel Dios (Nv. 96-100)", "desc": "Desafío a la física.", "hitos": [(97, "Zanetti (Plancha en anillas)"), (98, "Hefesto"), (99, "Maltese"), (100, "Victorian Cross")]}
    ]
    
    for f in fases:
        with st.expander(f["fase"], expanded=(nivel_actual >= f["hitos"][0][0] and nivel_actual <= f["hitos"][-1][0])):
            st.caption(f["desc"])
            for hito in f["hitos"]:
                lvl, nombre = hito
                color = "#FFD700" if nivel_actual >= lvl else "#555"
                check = "✅" if nivel_actual >= lvl else "🔒"
                st.markdown(f"<p style='color: {color}; margin: 0;'>{check} <b>Nivel {lvl}:</b> {nombre}</p>", unsafe_allow_html=True)

st.markdown("---")

# -----------------------------------------------------------------------------
# Sección 4: Misiones Diarias & Modo Combate
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
            
            hoy_str = get_fecha_hoy().isoformat()
            res_hoy = supabase.table("misiones_diarias").select("id").eq("jugador_id", perfil['id']).eq("estado", "completada").eq("fecha", hoy_str).execute()
            es_primera_del_dia = len(res_hoy.data) == 0
            
            if es_primera_del_dia:
                nueva_racha = racha_dias + 1
                supabase.table("perfil_jugador").update({"racha_dias": nueva_racha}).eq("id", perfil['id']).execute()
                st.toast(f"🔥 Sistema: ¡Racha aumentada a {nueva_racha} días!", icon="🔥")

            if mision_activa.get('parent_id'):
                base_xp = mision_activa.get('xp_recompensa_dinamica', 20)
            elif mision_activa.get('xp_recompensa_dinamica'):
                base_xp = mision_activa.get('xp_recompensa_dinamica', 40)
            else:
                base_xp = 40
                
            mult_xp = {'Muy Fácil': 0.7, 'Un poco fácil': 0.85, 'Adecuada': 1.0, 'Un poco compleja': 1.15, 'Compleja': 1.3}
            xp_final = int(base_xp * mult_xp[esfuerzo_seleccionado])
            
            zona_trabajada = mision_activa.get('zona_muscular', None)
            if zona_trabajada == 'caminata': zona_trabajada = 'piernas'
            
            level_up, nuevo_nivel = otorgar_xp(perfil['id'], xp_final, zona_trabajada)
            
            if mision_activa.get('parent_id'):
                res_parent = supabase.table("misiones_diarias").select("*").eq("id", mision_activa['parent_id']).execute()
                if res_parent.data:
                    parent = res_parent.data[0]
                    sub_tareas = parent.get('sub_tareas', [])
                    nombre_subtarea = mision_activa['titulo'].replace("[Campaña] ", "")
                    
                    for st_task in sub_tareas:
                        if st_task.get('titulo') == nombre_subtarea:
                            st_task['completadas'] = st_task.get('completadas', 0) + 1
                            break
                    
                    nuevo_progreso = parent.get('progreso_actual', 0) + 1
                    meta = parent.get('meta_total', 1)
                    estado_parent = "completada" if nuevo_progreso >= meta else "pendiente"
                    
                    supabase.table("misiones_diarias").update({
                        "progreso_actual": nuevo_progreso, 
                        "sub_tareas": sub_tareas, 
                        "estado": estado_parent
                    }).eq("id", parent['id']).execute()
                    
                    if estado_parent == "completada":
                        xp_masiva = parent.get('xp_recompensa_dinamica', 1000)
                        otorgar_xp(perfil['id'], xp_masiva, parent.get('zona_muscular'))
                        st.session_state['play_level_up'] = True
                        st.toast(f"👑 ¡CAMPAÑA ÉPICA COMPLETADA! +{xp_masiva} XP Masiva.")
                        
            elif mision_activa.get('tipo_mision') == 'epica':
                supabase.table("misiones_diarias").update({
                    "estado": "completada",
                    "tiempo_segundos": segundos_tardados,
                    "nivel_esfuerzo": esfuerzo_seleccionado
                }).eq("id", mision_activa['id']).execute()

            # Completar la Tarea actual en BD
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

    hoy_str = get_fecha_hoy().isoformat()
    diarias_generadas_hoy = [m for m in misiones_activas if m.get('tipo_mision') == 'diaria' and m.get('fecha') == hoy_str and m.get('parent_id') is not None]

    if epicas:
        st.write("### 👑 CAMPAÑAS ACTIVAS (LARGO PLAZO)")
        for mision in epicas:
            with st.container(border=True):
                st.markdown(f"<h4 style='color: #FFD700;'>[{mision['rango']}] {mision['titulo']}</h4>", unsafe_allow_html=True)
                st.caption(f"ZONA DE IMPACTO: **{mision.get('zona_muscular', 'N/A').upper()}**")
                st.write(mision['descripcion'])
                
                prog = mision.get('progreso_actual', 0)
                meta = mision.get('meta_total', 1)
                st.progress(prog / meta if meta > 0 else 0, text=f"Progreso de Campaña: {prog} / {meta} Sub-misiones")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("▶️ DETALLES DE CAMPAÑA", key=f"det_{mision['id']}", use_container_width=True):
                        st.info("Para avanzar en esta Campaña, Extrae los Objetivos del Sistema. Se añadirán sub-tareas a tu Quest Board.")
                with col2:
                    if st.button("❌ Abandonar Campaña", key=f"rech_epica_{mision['id']}", use_container_width=True):
                        supabase.table("misiones_diarias").delete().eq("parent_id", mision['id']).execute()
                        supabase.table("misiones_diarias").delete().eq("id", mision['id']).execute()
                        st.rerun()
                        
    st.write("### ⚠️ MISIONES DIARIAS (OBJETIVOS Y TAREAS SIMPLES)")
    
    if not diarias_generadas_hoy and not diarias:
        st.info("El Sistema no detecta objetivos de campaña activos para hoy.")
        if st.button("🎲 Extraer Objetivos de Campaña", use_container_width=True):
            with st.spinner("Desglosando árbol de habilidades y fatiga..."):
                generar_misiones_del_dia(perfil['id'])
                st.rerun()
                
    if diarias:
        for mision in diarias:
            with st.container(border=True):
                if mision.get('parent_id'):
                    st.markdown(f"<h4 style='color: #00ffcc;'>{mision['titulo']}</h4>", unsafe_allow_html=True)
                elif "[DIARIA]" in mision.get('titulo', ''):
                    st.markdown(f"<h4 style='color: #FF8C00;'>{mision['titulo']}</h4>", unsafe_allow_html=True)
                else:
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
                        
    if completadas:
        st.write("### 🏆 REGISTRO DE VICTORIAS HOY")
        for mision in completadas:
            with st.container(border=True):
                st.markdown(f"~~[{mision.get('rango', 'C')}] {mision['titulo']}~~")
                tiempo_texto = ""
                if mision.get('tiempo_segundos'):
                    m, s = divmod(mision['tiempo_segundos'], 60)
                    tiempo_texto = f" | ⏱️ {m}m {s}s | 🔥 {mision.get('nivel_esfuerzo', '')}"
                st.success(f"Misión Completada {tiempo_texto}")