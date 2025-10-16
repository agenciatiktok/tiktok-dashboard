# ============================================================================
# pages/1_📅_Registro_Eventos.py
# Formulario de registro de batallas, eventos y subastas
# ============================================================================

import streamlit as st
import pandas as pd
from supabase import create_client
import os
from datetime import datetime
import random
import urllib.parse

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

st.set_page_config(
    page_title="Registro de Eventos",
    page_icon="📅",
    layout="wide"
)

# Estilos CSS con colores suaves
st.markdown("""
<style>
    :root {
        --bg-black: #0a0a0a;
        --primary-blue: #4A90E2;
        --secondary-purple: #7B68EE;
        --success-green: #5CB85C;
        --warning-orange: #F5A623;
        --neutral-gray: #E0E0E0;
        --text-light: #F5F5F5;
    }
    
    .stApp {
        background-color: var(--bg-black);
        color: var(--text-light);
    }
    
    .stButton > button {
        background: linear-gradient(135deg, var(--primary-blue) 0%, var(--secondary-purple) 100%);
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 8px;
        font-weight: bold;
        font-size: 16px;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, var(--secondary-purple) 0%, var(--primary-blue) 100%);
        box-shadow: 0 4px 12px rgba(74, 144, 226, 0.4);
    }
    
    .success-box {
        background: linear-gradient(135deg, var(--success-green) 0%, #4CAF50 100%);
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        color: white;
        margin: 20px 0;
    }
    
    .whatsapp-button {
        background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
        color: white !important;
        padding: 15px 30px;
        border-radius: 25px;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        gap: 10px;
        font-weight: bold;
        font-size: 18px;
        box-shadow: 0 4px 6px rgba(37, 211, 102, 0.3);
        margin: 10px 0;
    }
    
    .whatsapp-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(37, 211, 102, 0.5);
    }
    
    .info-card {
        background: linear-gradient(135deg, #2C3E50 0%, #34495E 100%);
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 4px solid var(--primary-blue);
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# CONEXIÓN SUPABASE
# ============================================================================

@st.cache_resource
def get_supabase():
    """Obtiene cliente de Supabase"""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_SERVICE_KEY"]
    except:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not url or not key:
        st.error("❌ Error: Credenciales de Supabase no configuradas")
        st.stop()
    
    return create_client(url, key)

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def generar_codigo_evento():
    """Genera código aleatorio de 5 dígitos (10000-99999)"""
    return random.randint(10000, 99999)

def validar_usuario_existe(usuario_tiktok, contrato):
    """
    Valida que el usuario exista en usuarios_tiktok o historico_usuarios
    y que pertenezca al contrato correcto
    """
    supabase = get_supabase()
    usuario_tiktok = usuario_tiktok.strip().replace('@', '').lower()
    
    # Buscar en usuarios_tiktok
    resultado = supabase.table('usuarios_tiktok')\
        .select('*')\
        .ilike('usuario', f'%{usuario_tiktok}%')\
        .eq('contrato', contrato)\
        .execute()
    
    if resultado.data and len(resultado.data) > 0:
        return resultado.data[0]
    
    # Buscar en historico_usuarios
    resultado_hist = supabase.table('historico_usuarios')\
        .select('*')\
        .or_(f'usuario_1.ilike.%{usuario_tiktok}%,usuario_2.ilike.%{usuario_tiktok}%,usuario_3.ilike.%{usuario_tiktok}%')\
        .execute()
    
    if resultado_hist.data and len(resultado_hist.data) > 0:
        # Buscar qué contrato tiene este usuario
        hist_usuario = resultado_hist.data[0]
        id_tiktok = hist_usuario.get('id_tiktok')
        
        # Verificar en usuarios_tiktok con ese id_tiktok
        usuario_final = supabase.table('usuarios_tiktok')\
            .select('*')\
            .eq('id_tiktok', id_tiktok)\
            .eq('contrato', contrato)\
            .execute()
        
        if usuario_final.data and len(usuario_final.data) > 0:
            return usuario_final.data[0]
    
    return None

def obtener_info_usuario(usuario_data):
    """Extrae información del usuario desde la BD"""
    return {
        'usuario': usuario_data.get('usuario', ''),
        'id_tiktok': usuario_data.get('id_tiktok', ''),
        'agencia': usuario_data.get('agencia', ''),
        'agente': usuario_data.get('agente', ''),
        'nivel': usuario_data.get('nivel', 0)
    }

# ============================================================================
# INTERFAZ PRINCIPAL
# ============================================================================

def main():
    # Verificar autenticación por token
    query_params = st.query_params
    token_url = query_params.get("token", None)
    
    if not token_url:
        st.error("❌ Acceso denegado. Necesitas un token válido.")
        st.info("💡 Este formulario solo es accesible mediante el enlace de tu contrato.")
        st.stop()
    
    # Verificar token
    supabase = get_supabase()
    resultado = supabase.table('contratos_tokens')\
        .select('*')\
        .eq('token', token_url)\
        .eq('activo', True)\
        .execute()
    
    if not resultado.data:
        st.error("❌ Token inválido o expirado.")
        st.stop()
    
    token_data = resultado.data[0]
    contrato = token_data['contrato']
    nombre_contrato = token_data.get('nombre', contrato)
    
    # Header
    col1, col2 = st.columns([1, 4])
    
    with col1:
        st.image("https://img.icons8.com/color/96/000000/tiktok--v1.png", width=80)
    
    with col2:
        st.title("📅 Registro de Eventos y Batallas")
        st.caption(f"{contrato} - {nombre_contrato}")
    
    st.divider()
    
    # Información importante
    st.markdown("""
    <div class="info-card">
    <h3>📋 Instrucciones Importantes</h3>
    <ul>
        <li>✅ <b>Solo puedes registrar usuarios de tu contrato</b></li>
        <li>⚠️ <b>Verifica tu usuario antes de continuar</b></li>
        <li>📸 <b>El último paso es enviar el flyer por WhatsApp</b></li>
        <li>🔒 <b>Sin flyer, el evento no será confirmado</b></li>
    </ul>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # ========================================================================
    # PASO 1: VALIDAR USUARIO
    # ========================================================================
    
    if 'usuario_validado' not in st.session_state:
        st.session_state['usuario_validado'] = False
        st.session_state['usuario_data'] = None
    
    if not st.session_state['usuario_validado']:
        st.markdown("### 🔍 PASO 1: Validar tu Usuario")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            usuario_input = st.text_input(
                "🆔 Tu Usuario de TikTok",
                placeholder="Ejemplo: miusuario (sin @)",
                help="Escribe tu usuario SIN el @"
            )
        
        with col2:
            st.write("")
            st.write("")
            if st.button("🔍 Validar Usuario", use_container_width=True):
                if not usuario_input or not usuario_input.strip():
                    st.error("❌ Debes escribir tu usuario")
                else:
                    with st.spinner("Validando usuario..."):
                        usuario_data = validar_usuario_existe(usuario_input, contrato)
                        
                        if usuario_data:
                            st.session_state['usuario_validado'] = True
                            st.session_state['usuario_data'] = usuario_data
                            st.success(f"✅ Usuario encontrado: @{usuario_data.get('usuario')}")
                            st.rerun()
                        else:
                            st.error(f"""
                            ❌ **Usuario no encontrado en el contrato {contrato}**
                            
                            Posibles razones:
                            - El usuario no existe en nuestro sistema
                            - Perteneces a otro contrato
                            - Escribiste mal tu usuario
                            
                            📞 Contacta a tu agente para verificar:
                            """)
                            
                            st.markdown("""
                            <a href="https://wa.me/5215659842514" target="_blank" class="whatsapp-button">
                                📲 Contactar Agencia
                            </a>
                            """, unsafe_allow_html=True)
        
        st.stop()
    
    # ========================================================================
    # PASO 2: FORMULARIO DE EVENTO
    # ========================================================================
    
    usuario_info = obtener_info_usuario(st.session_state['usuario_data'])
    
    st.markdown("### ✅ Usuario Validado")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("👤 Usuario", f"@{usuario_info['usuario']}")
    with col2:
        st.metric("🏢 Agencia", usuario_info['agencia'])
    with col3:
        st.metric("⭐ Nivel", usuario_info['nivel'])
    
    if st.button("🔄 Cambiar Usuario"):
        st.session_state['usuario_validado'] = False
        st.session_state['usuario_data'] = None
        st.rerun()
    
    st.divider()
    
    st.markdown("### 📝 PASO 2: Datos del Evento")
    
    with st.form("form_evento", clear_on_submit=False):
        # Tipo y fecha
        col1, col2 = st.columns(2)
        
        with col1:
            tipo_evento = st.selectbox(
                "🎯 Tipo de Evento *",
                ["Batalla", "Evento", "Subasta", "Otro"]
            )
            
            fecha_evento = st.date_input(
                "📅 Fecha del Evento *",
                help="Fecha según tu país"
            )
        
        with col2:
            hora_evento = st.time_input(
                "🕐 Hora del Evento *",
                help="Hora según tu país"
            )
            
            pais = st.text_input(
                "🌎 País *",
                placeholder="Ejemplo: México, Colombia, USA"
            )
        
        # Ciudad USA (solo si aplica)
        ciudad_usa = st.text_input(
            "🏙️ Ciudad (solo si estás en USA)",
            placeholder="Ejemplo: Miami, Los Angeles, Houston"
        )
        
        st.divider()
        
        # Rival
        st.markdown("#### ⚔️ Información del Rival")
        
        col1, col2 = st.columns(2)
        
        with col1:
            necesita_rival = st.radio(
                "¿Necesitas rival? *",
                ["No", "Sí"],
                horizontal=True
            )
        
        with col2:
            usuario_rival = st.text_input(
                "Usuario Rival (si ya tienes)",
                placeholder="@usuario_rival"
            )
        
        nivel_rival = st.number_input(
            "Nivel del Rival (si lo conoces)",
            min_value=0,
            max_value=50,
            value=0,
            help="Deja en 0 si no conoces el nivel"
        )
        
        st.divider()
        
        # Extra
        st.markdown("#### 📋 Información Adicional")
        
        enlace_live = st.text_input(
            "🔗 Enlace del LIVE (opcional)",
            placeholder="https://..."
        )
        
        notas = st.text_area(
            "📝 Notas o Comentarios (opcional)",
            placeholder="Cualquier información adicional...",
            height=100
        )
        
        st.divider()
        
        # Botón enviar
        submitted = st.form_submit_button("🎮 GENERAR CÓDIGO DE EVENTO", use_container_width=True)
        
        if submitted:
            # Validaciones
            errores = []
            
            if not pais or not pais.strip():
                errores.append("❌ El país es obligatorio")
            
            if errores:
                for error in errores:
                    st.error(error)
            else:
                try:
                    # Generar código único
                    codigo_evento = generar_codigo_evento()
                    
                    # Verificar que no exista (por si acaso)
                    while True:
                        existe = supabase.table('agenda_eventos')\
                            .select('id')\
                            .eq('codigo_evento', codigo_evento)\
                            .execute()
                        
                        if not existe.data:
                            break
                        
                        codigo_evento = generar_codigo_evento()
                    
                    # Insertar en BD
                    resultado = supabase.table('agenda_eventos').insert({
                        'codigo_evento': codigo_evento,
                        'usuario': usuario_info['usuario'],
                        'id_tiktok': usuario_info['id_tiktok'],
                        'agencia': usuario_info['agencia'],
                        'agente': usuario_info['agente'],
                        'contrato': contrato,
                        'nivel_usuario': usuario_info['nivel'],
                        'tipo_evento': tipo_evento,
                        'fecha_evento': str(fecha_evento),
                        'hora_evento': str(hora_evento),
                        'pais': pais.strip(),
                        'ciudad_usa': ciudad_usa.strip() if ciudad_usa else None,
                        'usuario_rival': usuario_rival.strip() if usuario_rival else None,
                        'nivel_rival': nivel_rival if nivel_rival > 0 else None,
                        'necesita_rival': necesita_rival == "Sí",
                        'enlace_live': enlace_live.strip() if enlace_live else None,
                        'notas': notas.strip() if notas else None,
                        'estado': 'PENDIENTE_FLYER'
                    }).execute()
                    
                    if resultado.data:
                        st.session_state['evento_creado'] = True
                        st.session_state['codigo_evento'] = codigo_evento
                        st.session_state['datos_evento'] = {
                            'usuario': usuario_info['usuario'],
                            'agencia': usuario_info['agencia'],
                            'tipo_evento': tipo_evento,
                            'fecha_evento': str(fecha_evento),
                            'hora_evento': str(hora_evento),
                            'pais': pais,
                            'rival': usuario_rival if usuario_rival else "Sin rival",
                            'necesita_rival': "Sí" if necesita_rival == "Sí" else "No"
                        }
                        st.rerun()
                    else:
                        st.error("❌ Error al crear el evento")
                
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    # ========================================================================
    # PASO 3: EVENTO CREADO - ENVIAR POR WHATSAPP
    # ========================================================================
    
    if st.session_state.get('evento_creado', False):
        st.balloons()
        
        codigo = st.session_state['codigo_evento']
        datos = st.session_state['datos_evento']
        
        st.markdown(f"""
        <div class="success-box">
            <h2>🎉 ¡EVENTO REGISTRADO!</h2>
            <h1>#{codigo}</h1>
            <p>Tu código de evento ha sido generado exitosamente</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        st.markdown("### 📲 PASO FINAL: Enviar Flyer por WhatsApp")
        
        st.warning("""
        ⚠️ **MUY IMPORTANTE:**
        
        Tu evento está registrado pero **NO CONFIRMADO**.
        
        Para confirmar el evento, debes:
        1. Hacer clic en el botón de abajo
        2. Se abrirá WhatsApp con tus datos
        3. **Adjunta la foto/flyer del evento**
        4. Envía el mensaje
        
        🔒 **Sin flyer, el evento NO será visible en la agenda**
        """)
        
        # Preparar mensaje para WhatsApp
        mensaje = f"""🎮 EVENTO #{codigo}

📋 DATOS DEL EVENTO:
👤 Usuario: @{datos['usuario']}
🏢 Agencia: {datos['agencia']}
📍 Contrato: {contrato}

🎯 Tipo: {datos['tipo_evento']}
📅 Fecha: {datos['fecha_evento']}
🕐 Hora: {datos['hora_evento']}
🌎 País: {datos['pais']}

⚔️ Rival: {datos['rival']}
❓ Necesita rival: {datos['necesita_rival']}

📸 ADJUNTO: Flyer del evento"""
        
        mensaje_encoded = urllib.parse.quote(mensaje)
        whatsapp_url = f"https://wa.me/5215659842514?text={mensaje_encoded}"
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown(f"""
            <center>
            <a href="{whatsapp_url}" target="_blank" class="whatsapp-button">
                📲 ENVIAR FLYER POR WHATSAPP
            </a>
            </center>
            """, unsafe_allow_html=True)
        
        st.divider()
        
        st.info("""
        ℹ️ **Después de enviar el flyer:**
        
        - Tu evento será revisado por la administración
        - Una vez confirmado, aparecerá en la agenda oficial
        - Recibirás confirmación por el mismo WhatsApp
        
        ¿Necesitas ayuda? Escribe al mismo número de WhatsApp
        """)
        
        if st.button("✅ Ya envié mi flyer - Registrar otro evento"):
            st.session_state['evento_creado'] = False
            st.session_state['usuario_validado'] = False
            st.session_state['usuario_data'] = None
            st.rerun()

if __name__ == "__main__":
    main()
