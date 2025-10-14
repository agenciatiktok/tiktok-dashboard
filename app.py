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
    """Obtiene datos del contrato desde usuarios_tiktok y paypal_bruto desde reportes_contratos"""
    supabase = get_supabase()
    
    config_resultado = supabase.table('contratos').select('*').eq('codigo', contrato).execute()
    
    nivel1_tabla3 = False
    if config_resultado.data and len(config_resultado.data) > 0:
        valor = config_resultado.data[0].get('nivel1_tabla3', False)
        if isinstance(valor, str):
            nivel1_tabla3 = valor.upper() in ['SI', 'YES', 'TRUE', '1', 'SÍ']
        else:
            nivel1_tabla3 = bool(valor)
    
    # Obtener datos base de usuarios_tiktok
    resultado = supabase.table('usuarios_tiktok')\
        .select('*')\
        .eq('contrato', contrato)\
        .eq('fecha_datos', fecha_datos)\
        .execute()
    
    if resultado.data:
        df = pd.DataFrame(resultado.data)
        
        # Resolver usuarios sin nombre desde histórico
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
        
        # OBTENER paypal_bruto desde reportes_contratos
        try:
            reportes = supabase.table('reportes_contratos')\
                .select('usuario_id, paypal_bruto')\
                .eq('contrato', contrato)\
                .eq('periodo', fecha_datos)\
                .execute()
            
            if reportes.data:
                df_reportes = pd.DataFrame(reportes.data)
                # Crear mapeo de id_tiktok -> paypal_bruto
                df['id_tiktok_str'] = df['id_tiktok'].astype(str)
                df_reportes['usuario_id_str'] = df_reportes['usuario_id'].astype(str)
                
                paypal_map = dict(zip(df_reportes['usuario_id_str'], df_reportes['paypal_bruto']))
                
                # Aplicar valores de reportes
                df['paypal_bruto'] = df['id_tiktok_str'].map(paypal_map).fillna(0)
                df = df.drop('id_tiktok_str', axis=1)
            else:
                df['paypal_bruto'] = 0
        except Exception as e:
            df['paypal_bruto'] = 0
        
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
                <li
# (… el resto del archivo continúa sin cambios de lógica; solo se eliminó el `with tab4:` vacío que provocaba el IndentationError)
