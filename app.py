# ============================================================================
# app.py - Sistema Completo TikTok Live
# Pantalla pública + Login Admin + Login Agente + Vista Jugadores
# ============================================================================

import streamlit as st
import pandas as pd
from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import datetime
import calendar
import plotly.graph_objects as go
import plotly.express as px

# Cargar variables de entorno
load_dotenv()

# Configurar página
st.set_page_config(
    page_title="Sistema TikTok Live",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto"
)

# ============================================================================
# ESTILOS CSS
# ============================================================================

st.markdown("""
<style>
    :root {
        --tiktok-black: #000000;
        --tiktok-cyan: #00f2ea;
        --tiktok-pink: #fe2c55;
        --tiktok-white: #ffffff;
    }
    
    .stApp {
        background-color: var(--tiktok-black);
    }
    
    .stMetric {
        background: linear-gradient(135deg, var(--tiktok-cyan) 0%, var(--tiktok-pink) 100%);
        padding: 15px;
        border-radius: 10px;
        color: var(--tiktok-white);
    }
    
    .stMetric label {
        color: var(--tiktok-white) !important;
        font-weight: bold;
    }
    
    .stMetric [data-testid="stMetricValue"] {
        color: var(--tiktok-white);
        font-size: 28px;
        font-weight: bold;
    }
    
    h1, h2, h3 {
        color: var(--tiktok-cyan) !important;
        text-shadow: 2px 2px 4px rgba(254, 44, 85, 0.3);
    }
    
    div[data-testid="stDataFrame"] td,
    div[data-testid="stDataFrame"] th {
        text-align: center !important;
    }
    
    hr {
        background: linear-gradient(90deg, var(--tiktok-cyan) 0%, var(--tiktok-pink) 100%);
        height: 3px;
        border: none;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, var(--tiktok-cyan) 0%, var(--tiktok-pink) 100%);
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 8px;
        font-weight: bold;
        font-size: 16px;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, var(--tiktok-pink) 0%, var(--tiktok-cyan) 100%);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    
    .whatsapp-button {
        background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
        color: #000000 !important;
        padding: 12px 24px;
        border-radius: 25px;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        gap: 10px;
        font-weight: bold;
        font-size: 16px;
        box-shadow: 0 4px 6px rgba(37, 211, 102, 0.3);
    }
    
    .whatsapp-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(37, 211, 102, 0.4);
    }
    
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a1a 0%, #0a0a0a 100%);
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
# FUNCIONES DE AUTENTICACIÓN
# ============================================================================

def verificar_token_admin(token):
    """Verifica token de administrador"""
    supabase = get_supabase()
    resultado = supabase.table('contratos_tokens').select('*').eq('token', token).eq('activo', True).execute()
    
    if resultado.data:
        token_data = resultado.data[0]
        tipo = token_data.get('tipo', 'contrato')
        if tipo == 'admin':
            return token_data
    return None

def verificar_token_contrato(token):
    """Verifica token de contrato (jugadores)"""
    supabase = get_supabase()
    resultado = supabase.table('contratos_tokens').select('*').eq('token', token).eq('activo', True).execute()
    
    if resultado.data:
        token_data = resultado.data[0]
        tipo = token_data.get('tipo', 'contrato')
        if tipo == 'contrato':
            return token_data
    return None

def verificar_login_agente(usuario, password):
    """Verifica credenciales de agente"""
    supabase = get_supabase()
    resultado = supabase.table('agentes_login')\
        .select('*')\
        .eq('usuario', usuario)\
        .eq('password', password)\
        .eq('activo', True)\
        .execute()
    
    if resultado.data and len(resultado.data) > 0:
        return resultado.data[0]
    return None

def cambiar_password_agente(usuario, nueva_password):
    """Cambia la contraseña del agente"""
    supabase = get_supabase()
    try:
        supabase.table('agentes_login')\
            .update({'password': nueva_password, 'cambio_password': True})\
            .eq('usuario', usuario)\
            .execute()
        return True
    except:
        return False

# ============================================================================
# FUNCIONES COMPARTIDAS
# ============================================================================

def obtener_periodos_disponibles():
    """Obtiene periodos disponibles"""
    supabase = get_supabase()
    resultado = supabase.table('usuarios_tiktok').select('fecha_datos').execute()
    
    if resultado.data:
        fechas = sorted(list(set([r['fecha_datos'] for r in resultado.data])), reverse=True)
        return fechas
    return []

def obtener_mes_español(fecha_str):
    """Convierte fecha a Mes YYYY en español"""
    meses = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }
    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d')
        return f"{meses[fecha.month]} {fecha.year}"
    except:
        return fecha_str

def formatear_fecha_español(fecha_str):
    """Convierte fecha a DD de Mes, YYYY en español"""
    meses = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }
    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d')
        return f"{fecha.day} de {meses[fecha.month]}, {fecha.year}"
    except:
        return fecha_str

def obtener_incentivos():
    """Obtiene tabla de incentivos"""
    supabase = get_supabase()
    resultado = supabase.table('incentivos_horizontales').select('*').order('acumulado').execute()
    
    if resultado.data:
        return pd.DataFrame(resultado.data)
    return pd.DataFrame()

def determinar_nivel(dias, horas):
    """Determina nivel según días y horas"""
    try: 
        d = float(dias)
    except: 
        d = 0
    try: 
        h = float(horas)
    except: 
        h = 0
    
    if d >= 20 and h >= 40: return 3
    if d >= 14 and h >= 30: return 2
    if d >= 7  and h >= 15: return 1
    return 0

def calcular_incentivos(df_incentivos, diamantes, nivel):
    """Calcula incentivo"""
    if nivel == 0 or diamantes <= 0:
        return (0, 0)
    
    fila = df_incentivos[df_incentivos['acumulado'] <= diamantes].sort_values('acumulado', ascending=False)
    
    if fila.empty:
        return (0, 0)
    
    fila = fila.iloc[0]
    
    col_coins = f'nivel_{nivel}_monedas'
    col_paypal = f'nivel_{nivel}_paypal'
    
    incentivo_coins = fila.get(col_coins, 0) if col_coins in fila else 0
    incentivo_paypal = fila.get(col_paypal, 0) if col_paypal in fila else 0
    
    return (incentivo_coins, incentivo_paypal)

def obtener_datos_contrato(contrato, fecha_datos):
    """Obtiene datos del contrato"""
    supabase = get_supabase()
    
    config_resultado = supabase.table('contratos').select('*').eq('codigo', contrato).execute()
    
    nivel1_tabla3 = False
    if config_resultado.data and len(config_resultado.data) > 0:
        valor = config_resultado.data[0].get('nivel1_tabla3', False)
        if isinstance(valor, str):
            nivel1_tabla3 = valor.upper() in ['SI', 'YES', 'TRUE', '1', 'SÍ']
        else:
            nivel1_tabla3 = bool(valor)
    
    resultado = supabase.table('usuarios_tiktok')\
        .select('*')\
        .eq('contrato', contrato)\
        .eq('fecha_datos', fecha_datos)\
        .execute()
    
    if resultado.data:
        df = pd.DataFrame(resultado.data)
        
        mask_sin_nombre = df['usuario'].isna() | (df['usuario'] == '') | (df['usuario'].str.strip() == '')
        usuarios_sin_nombre = df[mask_sin_nombre]
        
        if not usuarios_sin_nombre.empty:
            ids_sin_nombre = usuarios_sin_nombre['id_tiktok'].astype(str).unique().tolist()
            
            try:
                historico = supabase.table('historico_usuarios')\
                    .select('id_tiktok, usuario_1, usuario_2, usuario_3')\
                    .in_('id_tiktok', ids_sin_nombre)\
                    .execute()
                
                if historico.data:
                    nombres_historico = {}
                    for registro in historico.data:
                        id_tiktok = str(registro['id_tiktok'])
                        nombre = None
                        for col in ['usuario_1', 'Usuario_1', 'usuario_2', 'Usuario_2', 'usuario_3', 'Usuario_3']:
                            valor = registro.get(col, '')
                            if valor and str(valor).strip() and str(valor).strip().lower() not in ['', 'nan', 'none', 'null']:
                                nombre = str(valor).strip()
                                break
                        
                        if nombre:
                            nombres_historico[id_tiktok] = nombre
                        else:
                            nombres_historico[id_tiktok] = f"Usuario_{id_tiktok[:8]}"
                    
                    def obtener_nombre(row):
                        if pd.isna(row['usuario']) or str(row['usuario']).strip() == '':
                            id_str = str(row['id_tiktok'])
                            return nombres_historico.get(id_str, f"Usuario_{id_str[:8]}")
                        return row['usuario']
                    
                    df['usuario'] = df.apply(obtener_nombre, axis=1)
            
            except Exception as e:
                pass
        
        if 'horas' not in df.columns:
            df['horas'] = 0
        
        df['nivel_original'] = df.apply(lambda r: determinar_nivel(r.get('dias', 0), r.get('horas', 0)), axis=1)
        df['cumple'] = df['nivel_original'].apply(lambda n: 'SI' if n > 0 else 'NO')
        
        df_incentivos = obtener_incentivos()
        
        if not df_incentivos.empty:
            def calcular_incentivo_row(row):
                nivel_original = row['nivel_original']
                if nivel1_tabla3 and nivel_original >= 1:
                    nivel_para_incentivo = 3
                else:
                    nivel_para_incentivo = nivel_original
                return calcular_incentivos(df_incentivos, row.get('diamantes', 0), nivel_para_incentivo)
            
            incentivos = df.apply(calcular_incentivo_row, axis=1, result_type='expand')
            df['incentivo_coins'] = incentivos[0]
            df['incentivo_paypal'] = incentivos[1]
            
            if nivel1_tabla3:
                df['nivel'] = df['nivel_original'].apply(lambda n: 3 if n >= 1 else 0)
            else:
                df['nivel'] = df['nivel_original']
        else:
            df['incentivo_coins'] = 0
            df['incentivo_paypal'] = 0
            df['nivel'] = df['nivel_original']
        
        df.loc[df['cumple'] == 'NO', ['incentivo_coins', 'incentivo_paypal']] = 0
        
        return df
    
    return pd.DataFrame()

def crear_grafico_pastel(nivel_counts):
    """Crea gráfico de pastel"""
    labels = []
    values = []
    colors = []
    
    if nivel_counts.get(3, 0) > 0:
        labels.append('🥇 Nivel 3')
        values.append(nivel_counts.get(3, 0))
        colors.append('#FFD700')
    
    if nivel_counts.get(2, 0) > 0:
        labels.append('🥈 Nivel 2')
        values.append(nivel_counts.get(2, 0))
        colors.append('#C0C0C0')
    
    if nivel_counts.get(1, 0) > 0:
        labels.append('🥉 Nivel 1')
        values.append(nivel_counts.get(1, 0))
        colors.append('#CD7F32')
    
    if nivel_counts.get(0, 0) > 0:
        labels.append('⚫ Nivel 0')
        values.append(nivel_counts.get(0, 0))
        colors.append('#6c757d')
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        marker=dict(colors=colors, line=dict(color='#000000', width=2)),
        textinfo='label+percent+value',
        textfont=dict(size=14, color='white'),
        hole=0.4
    )])
    
    fig.update_layout(
        showlegend=True,
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#00f2ea', size=12),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig

# ============================================================================
# MODO 1: PANTALLA PÚBLICA
# ============================================================================

def mostrar_pantalla_publica():
    """Pantalla inicial pública con 2 botones de login"""
    
    col_logo, col_titulo = st.columns([1, 4])
    
    with col_logo:
        st.image("https://img.icons8.com/color/96/000000/tiktok--v1.png", width=100)
    
    with col_titulo:
        st.title("🎵 Sistema de Gestión TikTok Live")
        st.markdown("### Bienvenido al sistema de consultas")
    
    st.divider()
    
    st.markdown("""
    ### 📊 Acerca del Sistema
    
    Este sistema permite consultar:
    - 📈 Métricas de rendimiento
    - 💎 Estadísticas de diamantes
    - 🎯 Niveles de cumplimiento
    - 💰 Incentivos calculados
    
    ---
    """)
    
    st.markdown("### 🔐 Opciones de Acceso")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 30px; border-radius: 15px; text-align: center;'>
            <h2 style='color: white; margin: 0;'>🔐 ADMINISTRACIÓN</h2>
            <p style='color: white; margin: 10px 0;'>Acceso completo al sistema</p>
            <ul style='color: white; text-align: left; padding-left: 20px;'>
                <li>Ver todos los contratos</li>
                <li>Buscar cualquier usuario</li>
                <li>Dashboard global</li>
                <li>Consultas personalizadas</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        token_admin = st.text_input(
            "Token de Administrador:",
            type="password",
            key="input_token_admin"
        )
        
        if st.button("🔓 Acceder como Administrador", key="btn_admin", use_container_width=True):
            if token_admin:
                # Verificar token inmediatamente
                token_data = verificar_token_admin(token_admin)
                
                if token_data:
                    st.session_state['modo'] = 'admin'
                    st.session_state['token_data'] = token_data
                    st.rerun()
                else:
                    st.error("❌ Token de administrador inválido")
            else:
                st.warning("⚠️ Por favor ingresa tu token")
    
    with col2:
        st.markdown("""
        <div style='background: linear-gradient(135deg, #00f2ea 0%, #fe2c55 100%); 
                    padding: 30px; border-radius: 15px; text-align: center;'>
            <h2 style='color: white; margin: 0;'>👔 AGENTE</h2>
            <p style='color: white; margin: 10px 0;'>Gestión de tu contrato</p>
            <ul style='color: white; text-align: left; padding-left: 20px;'>
                <li>Ver todos tus usuarios</li>
                <li>Consultar métricas completas</li>
                <li>Revisar incentivos</li>
                <li>Descargar reportes</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        usuario_agente = st.text_input(
            "Usuario:",
            key="input_usuario_agente"
        )
        
        password_agente = st.text_input(
            "Contraseña:",
            type="password",
            key="input_password_agente"
        )
        
        if st.button("📊 Acceder como Agente", key="btn_agente", use_container_width=True):
            if usuario_agente and password_agente:
                # Verificar login inmediatamente
                agente_data = verificar_login_agente(usuario_agente, password_agente)
                
                if agente_data:
                    st.session_state['modo'] = 'agente'
                    st.session_state['agente_data'] = agente_data
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos")
            else:
                st.warning("⚠️ Por favor ingresa usuario y contraseña")
    
    st.divider()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.caption("🔒 Acceso seguro")
    
    with col2:
        st.caption("📊 Datos en tiempo real")
    
    with col3:
        st.caption(f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}")

# ============================================================================
# MODO 2: PANEL ADMINISTRACIÓN
# ============================================================================

def mostrar_panel_admin(token_data):
    """Panel de administración"""
    
    supabase = get_supabase()
    
    st.title("🔐 Panel de Administración")
    st.markdown(f"**Administrador:** {token_data.get('nombre', 'Super Admin')}")
    
    if st.button("← Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()
    
    st.divider()
    
    with st.sidebar:
        st.header("🛠️ Herramientas")
        
        opcion = st.radio(
            "Selecciona:",
            [
                "🔍 Buscar Usuario",
                "📊 Dashboard Global",
                "📋 Ver Contratos"
            ]
        )
    
    if opcion == "🔍 Buscar Usuario":
        st.header("🔍 Buscar Usuario")
        
        tab1, tab2 = st.tabs(["Por Nombre", "Por ID"])
        
        with tab1:
            nombre = st.text_input("Nombre:", placeholder="user123")
            
            if st.button("🔍 Buscar"):
                if nombre:
                    resultado = supabase.table("usuarios_tiktok")\
                        .select("*")\
                        .ilike("usuario", f"%{nombre}%")\
                        .execute()
                    
                    if resultado.data:
                        st.success(f"✅ {len(resultado.data)} resultado(s)")
                        st.dataframe(pd.DataFrame(resultado.data))
                    else:
                        st.warning("❌ No encontrado")
        
        with tab2:
            user_id = st.text_input("ID TikTok:", placeholder="7123...")
            
            if st.button("🔍 Buscar ID"):
                if user_id:
                    resultado = supabase.table("usuarios_tiktok")\
                        .select("*")\
                        .eq("id_tiktok", user_id)\
                        .execute()
                    
                    if resultado.data:
                        st.success("✅ Encontrado")
                        st.dataframe(pd.DataFrame(resultado.data))
                    else:
                        st.warning("❌ No encontrado")
    
    elif opcion == "📊 Dashboard Global":
        st.header("📊 Dashboard Global")
        
        usuarios = supabase.table("usuarios_tiktok").select("*", count="exact").execute()
        total_usuarios = usuarios.count if usuarios.count else 0
        
        cumplen = supabase.table("usuarios_tiktok")\
            .select("*", count="exact")\
            .eq("cumple", "SI")\
            .execute()
        total_cumplen = cumplen.count if cumplen.count else 0
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("👥 Total Usuarios", f"{total_usuarios:,}")
        
        with col2:
            st.metric("✅ Cumplen", f"{total_cumplen:,}")
    
    elif opcion == "📋 Ver Contratos":
        st.header("📋 Contratos")
        
        resultado = supabase.table("contratos").select("*").order("codigo").execute()
        
        if resultado.data:
            st.dataframe(pd.DataFrame(resultado.data))

# ============================================================================
# MODO 3: VISTA AGENTE (con cambio de contraseña)
# ============================================================================

def mostrar_cambio_password(agente_data):
    """Pantalla de cambio de contraseña obligatorio"""
    
    st.title("🔒 Cambio de Contraseña Obligatorio")
    st.warning("⚠️ Es tu primera vez. Debes cambiar tu contraseña.")
    
    st.info(f"**Usuario:** {agente_data['usuario']}")
    
    nueva_pass = st.text_input("Nueva contraseña:", type="password", key="nueva_pass")
    confirma_pass = st.text_input("Confirmar contraseña:", type="password", key="confirma_pass")
    
    if st.button("💾 Guardar Nueva Contraseña"):
        if not nueva_pass or not confirma_pass:
            st.error("❌ Completa ambos campos")
        elif nueva_pass != confirma_pass:
            st.error("❌ Las contraseñas no coinciden")
        elif len(nueva_pass) < 4:
            st.error("❌ La contraseña debe tener al menos 4 caracteres")
        else:
            if cambiar_password_agente(agente_data['usuario'], nueva_pass):
                st.success("✅ Contraseña cambiada exitosamente")
                # Actualizar agente_data con la nueva info
                agente_data['password'] = nueva_pass
                agente_data['cambio_password'] = True
                st.session_state['agente_data'] = agente_data
                st.balloons()
                st.rerun()
            else:
                st.error("❌ Error al cambiar contraseña")

def mostrar_vista_agente(agente_data):
    """Vista completa para el agente"""
    
    contrato = agente_data['contrato']
    
    col_logo, col_titulo, col_cerrar = st.columns([1, 3, 1])
    
    with col_logo:
        st.image("https://img.icons8.com/color/96/000000/tiktok--v1.png", width=80)
    
    with col_titulo:
        st.title(f"👔 {contrato} - Panel de Agente")
        st.caption(f"Gestión Completa")
    
    with col_cerrar:
        if st.button("🚪 Cerrar Sesión"):
            st.session_state.clear()
            st.rerun()
    
    st.divider()
    
    periodos = obtener_periodos_disponibles()
    
    if not periodos:
        st.warning("⚠️ No hay datos")
        st.stop()
    
    col1, col2 = st.columns([2, 2])
    
    with col1:
        periodo_seleccionado = st.selectbox(
            "📅 Periodo:",
            periodos,
            format_func=formatear_fecha_español
        )
    
    with col2:
        st.metric("📆 Periodo", obtener_mes_español(periodo_seleccionado))
    
    with st.spinner('📄 Cargando...'):
        df = obtener_datos_contrato(contrato, periodo_seleccionado)
    
    if df.empty:
        st.info(f"ℹ️ Sin datos para {periodo_seleccionado}")
        st.stop()
    
    st.divider()
    
    tab1, tab2, tab3 = st.tabs(["👥 Todos", "✅ Cumplen", "📊 Resumen"])
    
    with tab1:
        st.caption(f"📊 {len(df)} usuarios")
        
        # MOSTRAR TODAS LAS COLUMNAS (sin ocultar)
        columnas_mostrar = ['usuario', 'dias', 'duracion', 'diamantes', 'nivel', 'cumple', 
                           'incentivo_coins', 'incentivo_paypal']
        
        df_show = df[[c for c in columnas_mostrar if c in df.columns]].copy()
        
        st.dataframe(df_show.sort_values('diamantes', ascending=False), 
                    use_container_width=True, hide_index=True, height=500)
    
    with tab2:
        df_cumplen = df[df['cumple'] == 'SI']
        st.caption(f"✅ {len(df_cumplen)} cumplen")
        
        if not df_cumplen.empty:
            df_show = df_cumplen[[c for c in columnas_mostrar if c in df_cumplen.columns]].copy()
            st.dataframe(df_show.sort_values('diamantes', ascending=False), 
                        use_container_width=True, hide_index=True, height=500)
    
    with tab3:
        st.markdown("### 📈 Métricas")
        
        total = len(df)
        cumplen = len(df[df['cumple'] == 'SI'])
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("👥 Total", total)
        
        with col2:
            st.metric("✅ Cumplen", cumplen)
        
        with col3:
            st.metric("💎 Diamantes", f"{df['diamantes'].sum():,.0f}")
        
        st.divider()
        
        nivel_counts = df['nivel'].value_counts().sort_index(ascending=False)
        fig = crear_grafico_pastel(nivel_counts)
        st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# MODO 4: VISTA JUGADORES (token grupal - columnas limitadas)
# ============================================================================

def obtener_columnas_ocultas(contrato):
    """Obtiene columnas ocultas"""
    supabase = get_supabase()
    resultado = supabase.table('config_columnas_ocultas').select('columna').eq('contrato', contrato).execute()
    
    if resultado.data:
        return [r['columna'] for r in resultado.data]
    return []

def mostrar_vista_jugadores(token_data):
    """Vista limitada para jugadores (con token grupal)"""
    
    contrato = token_data['contrato']
    nombre = token_data.get('nombre', contrato)
    
    columnas_ocultas_config = obtener_columnas_ocultas(contrato)
    
    col_logo, col_titulo, col_whatsapp = st.columns([1, 3, 2])
    
    with col_logo:
        st.image("https://img.icons8.com/color/96/000000/tiktok--v1.png", width=80)
    
    with col_titulo:
        st.title(f"{contrato} - {nombre}")
        st.caption("📊 Sistema de Consulta")
    
    with col_whatsapp:
        whatsapp_url = "https://wa.me/5215659842514"
        st.markdown(f"""
            <a href="{whatsapp_url}" target="_blank" class="whatsapp-button">
                <span>💬 Soporte</span>
            </a>
        """, unsafe_allow_html=True)
        st.markdown('<p style="color:#00f2ea;">📞 +52 1 56 5984 2514</p>', unsafe_allow_html=True)
    
    st.divider()
    
    st.info("""
    ### 🎁 Sobre tus Regalos del Mes (Incentivos)
    
    **📅 ¿Cuándo se entregan?**  
    Los regalos se procesan entre el **día 15 y 25** del mes siguiente.
    
    **✅ ¿Cómo califico?**  
    Cumpliendo el mínimo de días, horas y diamantes. Si alcanzaste **Nivel 1, 2 o 3**, ¡tu regalo está asegurado!
    
    **🔄 ¿No recibiste tu regalo?**  
    ¡Tranquilo! Se acumula automáticamente para el siguiente periodo.
    
    **💬 ¿Dudas?**  
    Contacta a tu agente o administración por WhatsApp.
    
    **✨ Ten paciencia y confianza** - Cada diamante cuenta. ¡Sigue adelante! 💪
    """)
    
    st.divider()
    
    periodos = obtener_periodos_disponibles()
    
    if not periodos:
        st.warning("⚠️ Sin datos")
        st.stop()
    
    col1, col2 = st.columns([2, 2])
    
    with col1:
        periodo_seleccionado = st.selectbox(
            "📅 Periodo:",
            periodos,
            format_func=formatear_fecha_español
        )
    
    with col2:
        st.metric("📆 Periodo", obtener_mes_español(periodo_seleccionado))
    
    with st.spinner('📄 Cargando...'):
        df = obtener_datos_contrato(contrato, periodo_seleccionado)
    
    if df.empty:
        st.info(f"ℹ️ Sin datos")
        st.stop()
    
    st.divider()
    
    tab1, tab2, tab3, tab4 = st.tabs(["👥 Todos", "✅ Cumplen", "❌ No Cumplen", "📊 Resumen"])
    
    def formatear_dataframe(df_input):
        """Formatea con columnas ocultas"""
        mapeo_ocultar = {
            'coins': 'incentivo_coins',
            'paypal': 'incentivo_paypal'
        }
        
        columnas_a_ocultar = set(['agencia'])
        
        for config in columnas_ocultas_config:
            if config in mapeo_ocultar:
                columnas_a_ocultar.add(mapeo_ocultar[config])
        
        columnas_orden = ['usuario', 'dias', 'duracion', 'diamantes', 'nivel', 'cumple', 
                         'incentivo_coins', 'incentivo_paypal']
        
        columnas_mostrar = [c for c in columnas_orden if c in df_input.columns and c not in columnas_a_ocultar]
        
        df_show = df_input[columnas_mostrar].copy()
        
        nombres = {
            'usuario': 'Usuario',
            'dias': 'Días',
            'duracion': 'Horas',
            'diamantes': 'Diamantes',
            'nivel': 'Nivel',
            'cumple': 'Cumple',
            'incentivo_coins': 'Coins',
            'incentivo_paypal': 'PayPal'
        }
        
        df_show = df_show.rename(columns={k: v for k, v in nombres.items() if k in df_show.columns})
        
        if 'Diamantes' in df_show.columns:
            df_show['Diamantes'] = df_show['Diamantes'].apply(lambda x: f"{int(x):,}" if pd.notnull(x) else "0")
        
        if 'Coins' in df_show.columns:
            df_show['Coins'] = df_show['Coins'].apply(lambda x: f"{int(x):,}" if pd.notnull(x) else "0")
        
        if 'PayPal' in df_show.columns:
            df_show['PayPal'] = df_show['PayPal'].apply(lambda x: f"${float(x):,.2f}" if pd.notnull(x) else "$0.00")
        
        return df_show
    
    with tab1:
        st.caption(f"📊 {len(df)} usuarios")
        st.dataframe(formatear_dataframe(df.sort_values('diamantes', ascending=False)), 
                    use_container_width=False, hide_index=True, height=500)
    
    with tab2:
        df_cumplen = df[df['cumple'] == 'SI']
        st.caption(f"✅ {len(df_cumplen)} cumplen")
        if not df_cumplen.empty:
            st.dataframe(formatear_dataframe(df_cumplen.sort_values('diamantes', ascending=False)), 
                        use_container_width=False, hide_index=True, height=500)
    
    with tab3:
        df_no = df[df['cumple'] == 'NO']
        st.caption(f"❌ {len(df_no)} no cumplen")
        if not df_no.empty:
            st.dataframe(formatear_dataframe(df_no.sort_values('diamantes', ascending=False)), 
                        use_container_width=False, hide_index=True, height=500)
    
    with tab4:
        st.markdown("### 📈 Métricas")
        
        total = len(df)
        cumplen = len(df[df['cumple'] == 'SI'])
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("👥 Total", total)
        
        with col2:
            st.metric("✅ Cumplen", cumplen)
        
        with col3:
            st.metric("💎 Diamantes", f"{df['diamantes'].sum():,.0f}")
        
        st.divider()
        
        nivel_counts = df['nivel'].value_counts().sort_index(ascending=False)
        fig = crear_grafico_pastel(nivel_counts)
        st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# MAIN - ROUTER
# ============================================================================

def main():
    """Router principal"""
    
    # Verificar si hay token en URL (jugadores con token grupal)
    query_params = st.query_params
    token_url = query_params.get("token", None)
    
    if token_url:
        # Verificar si es token de contrato (jugadores)
        token_data = verificar_token_contrato(token_url)
        if token_data:
            mostrar_vista_jugadores(token_data)
            return
        
        # Si no es válido
        st.error("❌ Token inválido")
        if st.button("← Volver"):
            st.query_params.clear()
            st.rerun()
        st.stop()
    
    # Sin token en URL - usar session_state
    if 'modo' not in st.session_state:
        mostrar_pantalla_publica()
        return
    
    modo = st.session_state.get('modo')
    
    if modo == 'admin':
        token_data = st.session_state.get('token_data')
        
        if token_data:
            mostrar_panel_admin(token_data)
        else:
            st.error("❌ Sesión expirada")
            st.session_state.clear()
            st.rerun()
    
    elif modo == 'agente':
        agente_data = st.session_state.get('agente_data')
        
        if agente_data:
            # Verificar si necesita cambiar contraseña
            if not agente_data.get('cambio_password', False):
                mostrar_cambio_password(agente_data)
            else:
                mostrar_vista_agente(agente_data)
        else:
            st.error("❌ Sesión expirada")
            st.session_state.clear()
            st.rerun()

if __name__ == "__main__":
    main()
