# ============================================================================
# app.py - Sistema Completo TikTok Live
# Pantalla pública + Login Admin + Login Agente + Vista Jugadores
# Build: 2025-11-19a - Mejora legibilidad métricas + Mensaje días actualización
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

# Build tracking
st.sidebar.caption("🔧 Build: 2025-11-19a")

# DEBUG: Descomentar si necesitas forzar recarga
# if st.sidebar.button("🔄 Forzar Recarga de Periodos"):
#     st.cache_data.clear()
#     st.rerun()

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
        --metric-bg: #1a1a1a;
    }
    
    .stApp {
        background-color: var(--tiktok-black);
    }
    
    /* Métricas mejoradas - Fondo sólido con borde brillante */
    .stMetric {
        background: var(--metric-bg);
        border: 2px solid;
        border-image: linear-gradient(135deg, var(--tiktok-cyan) 0%, var(--tiktok-pink) 100%) 1;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 242, 234, 0.2);
    }
    
    .stMetric label {
        color: var(--tiktok-cyan) !important;
        font-weight: bold;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .stMetric [data-testid="stMetricValue"] {
        color: var(--tiktok-white);
        font-size: 32px;
        font-weight: bold;
        text-shadow: 0 2px 4px rgba(0, 242, 234, 0.3);
    }
    
    h1, h2, h3 {
        color: var(--tiktok-cyan) !important;
        text-shadow: 2px 2px 4px rgba(254, 44, 85, 0.3);
    }
    
    div[data-testid="stDataFrame"] td,
    div[data-testid="stDataFrame"] th {
        text-align: center !important;
    }
    
    /* Centrado forzado AG Grid */
    .ag-cell, .ag-header-cell {
        text-align: center !important;
        justify-content: center !important;
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
    
    /* Tablas centradas y compactas */
    div[data-testid="stDataFrame"] table { font-size: 13px; }
    div[data-testid="stDataFrame"] td, div[data-testid="stDataFrame"] th{
        padding: 6px 8px !important; 
        text-align:center !important;
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
    """
    Obtiene periodos disponibles con lógica inteligente:
    - Siempre muestra cierres de mes (último día del mes)
    - Para cada mes, solo muestra la fecha MÁS RECIENTE
    """
    supabase = get_supabase()
    
    try:
        # OPCIÓN A: Intentar usar función RPC (si existe)
        try:
            resultado_rpc = supabase.rpc('obtener_fechas_disponibles').execute()
            if resultado_rpc.data:
                fechas = [r['fecha_datos'] for r in resultado_rpc.data]
                fechas_filtradas = filtrar_fechas_inteligente(fechas)
                # DEBUG: Descomentar para ver info de fechas
                # st.sidebar.success(f"✅ Usando RPC: {len(fechas_filtradas)} fechas visibles")
                # st.sidebar.write("📋 Fechas mostradas:", fechas_filtradas)
                return fechas_filtradas
        except Exception as e_rpc:
            # DEBUG: Descomentar para ver errores de RPC
            # st.sidebar.warning(f"⚠️ RPC no disponible: {str(e_rpc)}")
            pass
        
        # OPCIÓN B: Paginación manual (fallback)
        todas_fechas = set()
        offset = 0
        batch_size = 1000
        batch_count = 0
        
        while batch_count < 10:  # Máximo 10 batches = 10,000 registros
            resultado = supabase.table('usuarios_tiktok')\
                .select('fecha_datos')\
                .range(offset, offset + batch_size - 1)\
                .execute()
            
            if not resultado.data or len(resultado.data) == 0:
                break
            
            # Extraer fechas del batch
            fechas_batch = [r['fecha_datos'] for r in resultado.data if r.get('fecha_datos')]
            todas_fechas.update(fechas_batch)
            batch_count += 1
            
            # Si obtuvimos menos que batch_size, ya terminamos
            if len(resultado.data) < batch_size:
                break
            
            offset += batch_size
        
        fechas_unicas = list(todas_fechas)
        fechas_filtradas = filtrar_fechas_inteligente(fechas_unicas)
        
        # DEBUG: Descomentar para ver info de paginación
        # st.sidebar.success(f"✅ Paginación: {len(fechas_filtradas)} fechas visibles")
        # st.sidebar.write(f"📦 Procesados {batch_count} batches")
        # st.sidebar.write("📋 Fechas mostradas:", fechas_filtradas)
        
        return fechas_filtradas
        
    except Exception as e:
        st.sidebar.error(f"❌ Error: {str(e)}")
        return []

def filtrar_fechas_inteligente(fechas_str):
    """
    Filtra fechas con lógica inteligente:
    - Cierres de mes (último día): SIEMPRE
    - Fechas intermedias: Solo la MÁS RECIENTE por mes
    """
    from datetime import datetime
    from collections import defaultdict
    
    if not fechas_str:
        return []
    
    # Convertir strings a datetime y agrupar por mes
    fechas_obj = []
    for f_str in fechas_str:
        try:
            f_obj = datetime.strptime(str(f_str).strip(), '%Y-%m-%d')
            fechas_obj.append(f_obj)
        except:
            continue
    
    # Agrupar por año-mes
    por_mes = defaultdict(list)
    for f in fechas_obj:
        clave_mes = f.strftime('%Y-%m')
        por_mes[clave_mes].append(f)
    
    # Filtrar: cierres de mes + fecha más reciente por mes
    fechas_finales = []
    
    for mes, fechas_del_mes in por_mes.items():
        fechas_del_mes_sorted = sorted(fechas_del_mes, reverse=True)  # Más reciente primero
        
        # Obtener último día del mes
        primera_fecha = fechas_del_mes_sorted[0]
        año = primera_fecha.year
        mes_num = primera_fecha.month
        
        # Último día del mes
        if mes_num == 12:
            ultimo_dia = 31
        else:
            from calendar import monthrange
            ultimo_dia = monthrange(año, mes_num)[1]
        
        # Buscar si hay cierre de mes
        cierre_existe = False
        for f in fechas_del_mes:
            if f.day == ultimo_dia:
                fechas_finales.append(f)
                cierre_existe = True
                break
        
        # Si NO hay cierre, agregar la más reciente
        if not cierre_existe:
            fechas_finales.append(fechas_del_mes_sorted[0])
    
    # Ordenar descendente y convertir a strings
    fechas_finales_sorted = sorted(fechas_finales, reverse=True)
    return [f.strftime('%Y-%m-%d') for f in fechas_finales_sorted]

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
    """Calcula incentivos según tabla horizontal"""
    if nivel == 0:
        return (0, 0)
    
    try:
        fila_valida = None
        for idx, row in df_incentivos.iterrows():
            if diamantes >= row.get('acumulado', 0):
                fila_valida = idx
            else:
                break
        
        if fila_valida is None:
            return (0, 0)
        
        fila = df_incentivos.iloc[fila_valida]
        coins = fila.get(f'nivel_{nivel}_monedas', 0)
        paypal = fila.get(f'nivel_{nivel}_paypal', 0)
        
        return (coins, paypal)
    except Exception:
        return (0, 0)

# ============================================================================
# NUEVAS FUNCIONES INTEGRADAS DE CHATGPT
# ============================================================================

def _col(df, *cands):
    """Helper para encontrar columna con diferentes nombres posibles"""
    for c in cands:
        if c in df.columns: 
            return c
    return None

def enriquecer_nombres_desde_historial(df: pd.DataFrame, sb) -> pd.DataFrame:
    """
    INTEGRADO DE CHATGPT - MEJORADO
    Rellena 'usuario' cuando viene vacío usando historico_usuarios.
    Busca por id_tiktok (o usuario_id) y usa el último username conocido.
    Procesa en lotes de 400 para no sobrecargar Supabase.
    """
    if df.empty or sb is None: 
        return df

    col_user = _col(df, "usuario", "username", "user", "nick")
    col_id   = _col(df, "id_tiktok", "usuario_id", "user_id", "id_usuario")
    if not col_user or not col_id:
        return df

    # Identificar usuarios sin nombre
    mask = df[col_user].isna() | (df[col_user].astype(str).str.strip() == "")
    ids = df.loc[mask, col_id].dropna().astype(str).unique().tolist()
    if not ids:
        return df

    mapping = {}
    CHUNK = 400  # Procesar en lotes de 400
    
    for i in range(0, len(ids), CHUNK):
        lote = ids[i:i+CHUNK]
        rows = []
        
        # Intento 1: Por id_tiktok
        try:
            r = (sb.table("historico_usuarios")
                    .select("*")
                    .in_("id_tiktok", lote)
                    .order("visto_ultima_vez", desc=True)
                    .execute())
            rows = r.data or []
        except Exception:
            rows = []
        
        # Intento 2: Por usuario_id si no funcionó
        if not rows:
            try:
                r = (sb.table("historico_usuarios")
                        .select("*")
                        .in_("usuario_id", lote)
                        .order("visto_ultima_vez", desc=True)
                        .execute())
                rows = r.data or []
            except Exception:
                rows = []

        if not rows: 
            continue

        # Mapear IDs a nombres
        h = pd.DataFrame(rows)
        hid = _col(h, "id_tiktok", "usuario_id", "user_id")
        hun = _col(h, "usuario_1", "usuario_2", "usuario_3", "usuario", "username", "user", "nick")
        
        if not hid or not hun:
            continue

        h["id_str"] = h[hid].astype(str)
        h = h.dropna(subset=[hun]).drop_duplicates(subset=["id_str"], keep="first")
        mapping.update(dict(zip(h["id_str"], h[hun])))

    # Aplicar mapeo
    if mapping:
        df[col_id] = df[col_id].astype(str)
        df.loc[mask, col_user] = df.loc[mask, col_id].map(mapping).fillna(df.loc[mask, col_user])

    return df

def _alias_oculto(col_raw: str) -> str:
    """
    INTEGRADO DE CHATGPT
    Normaliza nombres de columnas para sistema de ocultamiento.
    Acepta múltiples variaciones.
    """
    alias = {
        # Base visibles
        "usuario":"usuario","username":"usuario","user":"usuario","nick":"usuario",
        "agencia":"agencia","agency":"agencia","Agencia":"agencia","AGENCIA":"agencia",
        "dias":"dias","días":"dias","Dias":"dias","Días":"dias",
        "duracion":"duracion","horas":"duracion","tiempo":"duracion",
        "diamantes":"diamantes",
        "nivel":"nivel","cumple":"cumple",
        # Incentivos/pagos
        "coins":"incentivo_coins","incentivo coin":"incentivo_coins","incentivo_coins":"incentivo_coins",
        "paypal":"incentivo_paypal","incentivo paypal":"incentivo_paypal","incentivo_paypal":"incentivo_paypal",
        "sueldo":"paypal_bruto","paypal_bruto":"paypal_bruto","coins_bruto":"coins_bruto",
    }
    return alias.get(col_raw.lower(), col_raw.lower())

@st.cache_data(ttl=300)
def _leer_reglas_ocultas():
    """Lee reglas de columnas ocultas desde Supabase"""
    sb = get_supabase()
    if not sb: 
        return []
    try:
        r = sb.table("config_columnas_ocultas").select("*").execute()
        return r.data or []
    except Exception:
        return []

def obtener_columnas_ocultas(contrato: str):
    """
    MEJORADO CON ALIAS
    Obtiene columnas ocultas con normalización de nombres
    """
    reglas = _leer_reglas_ocultas()
    ocultas = []
    
    for row in reglas:
        c = row.get("contrato")
        col_raw = str(row.get("columna", "")).strip()
        
        if not col_raw:
            continue
        
        col = _alias_oculto(col_raw)
        
        # Aplica si es global (contrato=None) o específico
        if (c is None) or (str(c).strip() == "") or (str(c).strip() == str(contrato).strip()):
            ocultas.append(col)
    
    return ocultas

# ============================================================================
# FUNCIONES DE DATOS
# ============================================================================

def obtener_contrato_equivalente(supabase, contrato):
    """Busca si el contrato tiene un equivalente en contratos_equivalencias (A↔B)."""
    try:
        # Buscar como nexus_codigo
        r = supabase.table('contratos_equivalencias')\
            .select('nexus_codigo,vertex_codigo')\
            .or_(f'nexus_codigo.eq.{contrato},vertex_codigo.eq.{contrato}')\
            .execute()
        if r.data:
            row = r.data[0]
            # Devolver el otro lado
            if row['nexus_codigo'] == contrato:
                return row['vertex_codigo']
            else:
                return row['nexus_codigo']
    except Exception:
        pass
    return None


def obtener_datos_contrato(contrato, fecha_datos):
    """
    MEJORADO CON ENRIQUECIMIENTO + INTEGRACIÓN VERTEX
    Obtiene datos del contrato desde usuarios_tiktok,
    enriquece nombres desde histórico,
    mapea paypal_bruto desde reportes_contratos,
    y une datos del contrato equivalente (A↔B) si existe.
    """
    supabase = get_supabase()
    
    # Verificar nivel1_tabla3
    config_resultado = supabase.table('contratos').select('*').eq('codigo', contrato).execute()
    
    nivel1_tabla3 = False
    if config_resultado.data and len(config_resultado.data) > 0:
        valor = config_resultado.data[0].get('nivel1_tabla3', False)
        if isinstance(valor, str):
            nivel1_tabla3 = valor.upper() in ['SI', 'YES', 'TRUE', '1', 'SÍ']
        else:
            nivel1_tabla3 = bool(valor)

    # Buscar contrato equivalente (Nexus ↔ Vertex)
    contrato_equivalente = obtener_contrato_equivalente(supabase, contrato)

    # Obtener datos base de usuarios_tiktok
    # Si hay equivalente, traer ambos contratos en una sola query
    if contrato_equivalente:
        resultado = supabase.table('usuarios_tiktok')\
            .select('*')\
            .in_('contrato', [contrato, contrato_equivalente])\
            .eq('fecha_datos', fecha_datos)\
            .execute()
    else:
        resultado = supabase.table('usuarios_tiktok')\
            .select('*')\
            .eq('contrato', contrato)\
            .eq('fecha_datos', fecha_datos)\
            .execute()
    
    if resultado.data:
        df = pd.DataFrame(resultado.data)
        
        # ✨ NUEVO: Enriquecer nombres desde histórico (INTEGRADO DE CHATGPT)
        df = enriquecer_nombres_desde_historial(df, supabase)
        
        # Normalizar horas
        if 'horas' not in df.columns:
            df['horas'] = 0
        
        # Calcular nivel y cumplimiento
        df['nivel_original'] = df.apply(lambda r: determinar_nivel(r.get('dias', 0), r.get('horas', 0)), axis=1)
        df['cumple'] = df['nivel_original'].apply(lambda n: 'SI' if n > 0 else 'NO')
        
        # Calcular incentivos
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
        
        # Limpiar valores para no cumplen
        df.loc[df['cumple'] == 'NO', ['incentivo_coins', 'incentivo_paypal']] = 0
        
        # ✨ OBTENER paypal_bruto desde reportes_contratos (ambos contratos si hay equivalente)
        try:
            contratos_buscar = [contrato]
            if contrato_equivalente:
                contratos_buscar.append(contrato_equivalente)

            reportes = supabase.table('reportes_contratos')\
                .select('usuario_id, paypal_bruto')\
                .in_('contrato', contratos_buscar)\
                .eq('periodo', fecha_datos)\
                .execute()

            if reportes.data:
                df_reportes = pd.DataFrame(reportes.data)
                df['id_tiktok_str'] = df['id_tiktok'].astype(str)
                df_reportes['usuario_id_str'] = df_reportes['usuario_id'].astype(str)

                paypal_map = dict(zip(df_reportes['usuario_id_str'], df_reportes['paypal_bruto']))

                df['paypal_bruto'] = df['id_tiktok_str'].map(paypal_map).fillna(
                    df.get('paypal_bruto', pd.Series(0, index=df.index))
                )
                df = df.drop('id_tiktok_str', axis=1)
            else:
                # Para jugadores de Vertex usar sueldo ya calculado si existe
                if 'paypal_bruto' not in df.columns:
                    df['paypal_bruto'] = 0
        except Exception:
            df['paypal_bruto'] = 0
        
        return df
    
    return pd.DataFrame()

# ============================================================================
# GRÁFICOS
# ============================================================================

def crear_grafico_pastel(nivel_counts):
    """Crea gráfico de pastel para niveles"""
    labels = []
    values = []
    colors = []
    
    nivel_map = {
        3: ('🥇 Nivel 3', '#FFD700'),
        2: ('🥈 Nivel 2', '#C0C0C0'),
        1: ('🥉 Nivel 1', '#CD7F32'),
        0: ('⚫ Nivel 0', '#404040')
    }
    
    for nivel in sorted(nivel_counts.index, reverse=True):
        if nivel in nivel_map:
            labels.append(nivel_map[nivel][0])
            values.append(nivel_counts[nivel])
            colors.append(nivel_map[nivel][1])
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=.4,
        marker=dict(colors=colors)
    )])
    
    fig.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white', size=14)
    )
    
    return fig

# ============================================================================
# MODO 1: PANTALLA PÚBLICA (sin login)
# ============================================================================

def mostrar_pantalla_publica():
    """Pantalla pública con información general"""
    
    col_logo, col_titulo, col_whatsapp = st.columns([1, 3, 2])
    
    with col_logo:
        st.image("https://img.icons8.com/color/96/000000/tiktok--v1.png", width=100)
    
    with col_titulo:
        st.title("🎵 Sistema TikTok Live")
        st.caption("📊 Plataforma de Gestión de Streamers")
    
    with col_whatsapp:
        whatsapp_url = "https://wa.me/5215659842514"
        st.markdown(f"""
            <a href="{whatsapp_url}" target="_blank" class="whatsapp-button">
                <span>💬 Contacto</span>
            </a>
        """, unsafe_allow_html=True)
        st.markdown('<p style="color:#00f2ea;">📞 +52 1 56 5984 2514</p>', unsafe_allow_html=True)
    
    st.divider()
    
    st.info("""
    ### 👋 Bienvenido al Sistema TikTok Live
    
    **¿Qué puedo hacer aquí?**
    - 🔐 Administradores: Acceso completo al sistema
    - 👔 Agentes: Gestión de usuarios y reportes
    - 🎮 Jugadores: Consulta tu desempeño (requiere token)
    
    **¿Cómo accedo?**
    - Si eres **jugador**, tu agente te proporcionará un enlace directo
    - Si eres **agente**, usa el login de agente
    - Si eres **administrador**, usa el token de acceso
    
    **💬 ¿Necesitas ayuda?**
    Contacta por WhatsApp usando el botón de arriba
    """)
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔐 Acceso Administración")
        token_admin = st.text_input("Token de Administrador", type="password", key="token_admin_input")
        if st.button("Acceder como Admin", key="btn_admin"):
            if token_admin:
                token_data = verificar_token_admin(token_admin)
                if token_data:
                    st.session_state['modo'] = 'admin'
                    st.session_state['token_data'] = token_data
                    st.success("✅ Acceso concedido")
                    st.rerun()
                else:
                    st.error("❌ Token inválido")
            else:
                st.warning("⚠️ Ingresa un token")
    
    with col2:
        st.subheader("👔 Acceso Agentes")
        usuario = st.text_input("Usuario", key="usuario_agente_input")
        password = st.text_input("Contraseña", type="password", key="password_agente_input")
        if st.button("Acceder como Agente", key="btn_agente"):
            if usuario and password:
                agente_data = verificar_login_agente(usuario, password)
                if agente_data:
                    st.session_state['modo'] = 'agente'
                    st.session_state['agente_data'] = agente_data
                    st.success("✅ Acceso concedido")
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos")
            else:
                st.warning("⚠️ Completa todos los campos")

# ============================================================================
# MODO 2: PANEL ADMIN
# ============================================================================

def mostrar_panel_admin(token_data):
    """Panel de administración completo"""
    
    st.sidebar.title("🔐 Panel Admin")
    st.sidebar.success(f"✅ Sesión: {token_data.get('nombre', 'Admin')}")
    
    if st.sidebar.button("🚪 Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()
    
    st.title("🔐 Panel de Administración")
    
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "👥 Usuarios", "⚙️ Configuración"])
    
    with tab1:
        st.subheader("📈 Métricas Generales")
        
        periodos = obtener_periodos_disponibles()
        if periodos:
            periodo_actual = periodos[0]
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("📅 Periodo Actual", obtener_mes_español(periodo_actual))
            
            with col2:
                st.metric("📊 Periodos Disponibles", len(periodos))
            
            with col3:
                st.metric("✅ Sistema", "Operativo")
        
        st.divider()
        st.info("💡 Dashboard completo - En desarrollo")
    
    with tab2:
        st.subheader("👥 Gestión de Usuarios")
        st.info("💡 Gestión de usuarios - En desarrollo")
    
    with tab3:
        st.subheader("⚙️ Configuración del Sistema")
        st.info("💡 Configuración - En desarrollo")

# ============================================================================
# MODO 3: PANEL AGENTE
# ============================================================================

def mostrar_cambio_password(agente_data):
    """Forzar cambio de contraseña en primer login"""
    st.title("🔐 Cambio de Contraseña Obligatorio")
    
    st.warning("""
    ⚠️ **Acción requerida**
    
    Por seguridad, debes cambiar tu contraseña antes de continuar.
    """)
    
    st.divider()
    
    usuario = agente_data['usuario']
    
    col1, col2 = st.columns(2)
    
    with col1:
        nueva_password = st.text_input("Nueva Contraseña", type="password", key="nueva_pwd")
    
    with col2:
        confirmar_password = st.text_input("Confirmar Contraseña", type="password", key="conf_pwd")
    
    if st.button("💾 Cambiar Contraseña"):
        if not nueva_password or not confirmar_password:
            st.error("❌ Completa todos los campos")
        elif nueva_password != confirmar_password:
            st.error("❌ Las contraseñas no coinciden")
        elif len(nueva_password) < 6:
            st.error("❌ La contraseña debe tener al menos 6 caracteres")
        else:
            if cambiar_password_agente(usuario, nueva_password):
                st.success("✅ Contraseña actualizada correctamente")
                # Actualizar datos en sesión
                agente_data['cambio_password'] = True
                agente_data['password'] = nueva_password
                st.session_state['agente_data'] = agente_data
                st.rerun()
            else:
                st.error("❌ Error al cambiar contraseña")

def mostrar_vista_agente(agente_data):
    """Vista completa del agente con TODOS los datos"""
    
    st.sidebar.title("👔 Panel Agente")
    st.sidebar.success(f"✅ {agente_data['usuario']}")
    st.sidebar.caption(f"📧 {agente_data.get('email', 'N/A')}")
    
    if st.sidebar.button("🚪 Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()
    
    contrato = agente_data.get('contrato', 'N/A')
    
    col_logo, col_titulo = st.columns([1, 4])
    
    with col_logo:
        st.image("https://img.icons8.com/color/96/000000/tiktok--v1.png", width=80)
    
    with col_titulo:
        st.title(f"👔 Panel del Agente")
        st.caption(f"{contrato}")
    
    st.divider()
    
    periodos = obtener_periodos_disponibles()
    
    if not periodos:
        st.warning("⚠️ No hay datos disponibles")
        st.stop()
    
    col1, col2 = st.columns([2, 2])
    
    with col1:
        periodo_seleccionado = st.selectbox(
            "📅 Periodo:",
            periodos,
            format_func=formatear_fecha_español,
            key="periodo_agente"
        )
    
    with col2:
        st.metric("📆 Periodo", obtener_mes_español(periodo_seleccionado))
    
    with st.spinner('📄 Cargando datos...'):
        df = obtener_datos_contrato(contrato, periodo_seleccionado)
    
    if df.empty:
        st.info(f"ℹ️ Sin datos para el periodo {obtener_mes_español(periodo_seleccionado)}")
        st.stop()
    
    st.divider()
    
    tab1, tab2, tab3, tab4 = st.tabs(["👥 Todos", "✅ Cumplen", "📄 Notas del Periodo", "📊 Resumen"])
    
    with tab1:
        st.caption(f"📊 {len(df)} usuarios")
        
        # MOSTRAR COLUMNAS COMPLETAS (vista agente)
        columnas_mostrar = ['usuario', 'agencia', 'dias', 'duracion', 'diamantes', 
                           'nivel', 'cumple', 'incentivo_coins', 'incentivo_paypal',
                           'paypal_bruto']
        
        df_show = df[[c for c in columnas_mostrar if c in df.columns]].copy()
        
        # Renombrar columnas
        nombres_columnas = {
            'usuario': 'Usuario',
            'agencia': 'Agencia',
            'dias': 'Días',
            'duracion': 'Horas',
            'diamantes': 'Diamantes',
            'nivel': 'Nivel',
            'cumple': 'Cumple',
            'incentivo_coins': 'Incentivo Coin',
            'incentivo_paypal': 'Incentivo PayPal',
            'paypal_bruto': 'Sueldo'
        }
        
        df_show = df_show.rename(columns={k: v for k, v in nombres_columnas.items() if k in df_show.columns})
        
        # Formatear números
        if 'Diamantes' in df_show.columns:
            df_show['Diamantes'] = df_show['Diamantes'].apply(lambda x: f"{int(x):,}" if pd.notnull(x) else "0")
        
        if 'Incentivo Coin' in df_show.columns:
            df_show['Incentivo Coin'] = df_show['Incentivo Coin'].apply(lambda x: f"{int(x):,}" if pd.notnull(x) else "0")
        
        if 'Incentivo PayPal' in df_show.columns:
            df_show['Incentivo PayPal'] = df_show['Incentivo PayPal'].apply(lambda x: f"${float(x):,.2f}" if pd.notnull(x) else "$0.00")
        
        if 'Sueldo' in df_show.columns:
            df_show['Sueldo'] = df_show['Sueldo'].apply(lambda x: f"${float(x):,.2f}" if pd.notnull(x) else "$0.00")
        
        # Configuración de columnas compactas
        column_config = {
            'Usuario': st.column_config.TextColumn('Usuario', width='medium'),
            'Agencia': st.column_config.TextColumn('Agencia', width='small'),
            'Días': st.column_config.NumberColumn('Días', width='small'),
            'Horas': st.column_config.TextColumn('Horas', width='small'),
            'Diamantes': st.column_config.TextColumn('Diamantes', width='medium'),
            'Nivel': st.column_config.NumberColumn('Nivel', width='small'),
            'Cumple': st.column_config.TextColumn('Cumple', width='small'),
            'Incentivo Coin': st.column_config.TextColumn('Incentivo Coin', width='medium'),
            'Incentivo PayPal': st.column_config.TextColumn('Incentivo PayPal', width='medium'),
            'Sueldo': st.column_config.TextColumn('Sueldo', width='medium')
        }
        
        st.dataframe(
            df_show.sort_values('Diamantes', ascending=False) if 'Diamantes' in df_show.columns else df_show, 
            use_container_width=True, 
            hide_index=True, 
            height=500,
            column_config=column_config
        )
    
    with tab2:
        df_cumplen = df[df['cumple'] == 'SI']
        st.caption(f"✅ {len(df_cumplen)} cumplen")
        
        if not df_cumplen.empty:
            df_show = df_cumplen[[c for c in columnas_mostrar if c in df_cumplen.columns]].copy()
            df_show = df_show.rename(columns={k: v for k, v in nombres_columnas.items() if k in df_show.columns})
            
            # Formatear igual
            if 'Diamantes' in df_show.columns:
                df_show['Diamantes'] = df_show['Diamantes'].apply(lambda x: f"{int(x):,}" if pd.notnull(x) else "0")
            if 'Incentivo Coin' in df_show.columns:
                df_show['Incentivo Coin'] = df_show['Incentivo Coin'].apply(lambda x: f"{int(x):,}" if pd.notnull(x) else "0")
            if 'Incentivo PayPal' in df_show.columns:
                df_show['Incentivo PayPal'] = df_show['Incentivo PayPal'].apply(lambda x: f"${float(x):,.2f}" if pd.notnull(x) else "$0.00")
            if 'Sueldo' in df_show.columns:
                df_show['Sueldo'] = df_show['Sueldo'].apply(lambda x: f"${float(x):,.2f}" if pd.notnull(x) else "$0.00")
            
            st.dataframe(
                df_show.sort_values('Diamantes', ascending=False) if 'Diamantes' in df_show.columns else df_show, 
                use_container_width=True, 
                hide_index=True, 
                height=500,
                column_config=column_config
            )
    
    with tab3:
        st.subheader("📄 Notas del Periodo")
        st.caption(f"{contrato} | Periodo: {obtener_mes_español(periodo_seleccionado)}")
        
        st.info("""
        📝 **Sobre las Notas**
        
        Las notas muestran el **total consolidado** a pagar por el periodo.
        Se generan automáticamente mediante los scripts Python 09-20.
        """)
        
        supabase = get_supabase()
        
        try:
            # ✅ CORREGIDO: Leer de resumen_contratos (totales ya calculados)
            resumen_resultado = supabase.table('resumen_contratos')\
                .select('*')\
                .eq('contrato', contrato)\
                .eq('periodo', periodo_seleccionado)\
                .execute()
            
            if resumen_resultado.data and len(resumen_resultado.data) > 0:
                resumen = resumen_resultado.data[0]
                
                # Obtener valores del resumen (ya calculados por Python)
                total_coins = int(resumen.get('total_coins', 0))
                total_paypal = float(resumen.get('total_paypal', 0))
                total_final = float(resumen.get('total_final', 0))
                usuarios_validos = int(resumen.get('usuarios_validos', 0))
                
                st.success(f"✅ Nota generada para {usuarios_validos} usuarios que cumplen")
                
                st.divider()
                
                # MOSTRAR SOLO TOTALES (sin duplicar valores)
                st.markdown("### 💰 Resumen de Pagos del Periodo")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("🎁 Total Incentivo Coins", f"{total_coins:,}")
                
                with col2:
                    st.metric("✅ TOTAL A PAGAR", f"${total_final:,.2f}", 
                             delta=None, delta_color="normal")
                
                st.divider()
                
                # Info adicional
                st.info(f"""
                📊 **Desglose:**
                - {usuarios_validos} usuarios que cumplen
                - Periodo: {obtener_mes_español(periodo_seleccionado)}
                - Código: {contrato}
                - Total Coins: {total_coins:,}
                - Total PayPal: ${total_paypal:,.2f}
                """)
                
                # Botón para ver detalle en reportes_contratos
                if st.button("🔍 Ver Detalle por Usuario"):
                    detalle = supabase.table('reportes_contratos')\
                        .select('*')\
                        .eq('contrato', contrato)\
                        .eq('periodo', periodo_seleccionado)\
                        .execute()
                    
                    if detalle.data:
                        df_detalle = pd.DataFrame(detalle.data)
                        st.dataframe(df_detalle, use_container_width=True, hide_index=True)
                        
                        # Botón descarga
                        csv = df_detalle.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Descargar Detalle CSV",
                            data=csv,
                            file_name=f"detalle_{contrato}_{periodo_seleccionado}.csv",
                            mime="text/csv"
                        )
            else:
                st.warning("⚠️ No hay notas generadas para este periodo")
                st.markdown("""
                **Las notas se generarán cuando se ejecuten los scripts 09-20.**
                
                Una vez procesadas, verás aquí el total a pagar del periodo.
                """)
        
        except Exception as e:
            st.error(f"❌ Error al cargar notas: {str(e)}")
            st.info("💡 Verifica que la tabla 'resumen_contratos' tenga datos para este periodo")
    
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
# MODO 4: VISTA JUGADORES (token grupal - columnas limitadas)
# ============================================================================

def mostrar_vista_jugadores(token_data):
    """Vista limitada para jugadores (con token grupal)"""
    
    contrato = token_data['contrato']
    nombre = token_data.get('nombre', contrato)
    
    # ✨ MEJORADO: Obtener columnas ocultas con alias
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
        st.markdown('<p style="color:#00f2ea; font-size:14px; margin-top:5px;">📞 +52 1 56 5984 2514</p>', unsafe_allow_html=True)
        st.markdown('<p style="color:#fe2c55; font-size:12px; font-weight:600; margin-top:8px;">DUDAS, COMENTARIOS, QUEJAS<br>Chatea con la administración general</p>', unsafe_allow_html=True)
    
    st.divider()
    
    # Mensaje de días de actualización
    st.warning("""
    ### 📅 Días de Actualización de Datos
    
    **Los datos se actualizan los días: 8, 15, 22, 25 y al cierre del mes en curso.**
    
    ⚠️ **IMPORTANTE:** Debes visitar esta página regularmente para verificar tu información actualizada.  
    Los datos se refrescan en estas fechas específicas, así que revisa tu progreso constantemente.
    """)
    
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
    
    def formatear_dataframe_jugadores(df_input):
        """Formatea con columnas ocultas usando aliases"""
        # Mapeo de configuración a columnas reales
        mapeo_ocultar = {
            # Incentivos
            'coins': 'incentivo_coins',
            'incentivo_coins': 'incentivo_coins',
            'paypal': 'incentivo_paypal',
            'incentivo_paypal': 'incentivo_paypal',
            'sueldo': 'paypal_bruto',
            'paypal_bruto': 'paypal_bruto',
            'coins_bruto': 'coins_bruto',
            # Métricas básicas
            'diamantes': 'diamantes',
            'dias': 'dias',
            'duracion': 'duracion',
            'horas': 'duracion',
            'nivel': 'nivel',
            'cumple': 'cumple',
            # Usuario
            'usuario': 'usuario'
        }
        
        columnas_a_ocultar = set(['agencia'])  # Siempre ocultar agencia en vista jugadores
        
        for config in columnas_ocultas_config:
            if config in mapeo_ocultar:
                columnas_a_ocultar.add(mapeo_ocultar[config])
        
        columnas_orden = ['usuario', 'dias', 'duracion', 'diamantes', 'nivel', 'cumple', 
                         'incentivo_coins', 'incentivo_paypal', 'paypal_bruto']
        
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
            'incentivo_paypal': 'PayPal',
            'paypal_bruto': 'Sueldo'
        }
        
        df_show = df_show.rename(columns={k: v for k, v in nombres.items() if k in df_show.columns})
        
        if 'Diamantes' in df_show.columns:
            df_show['Diamantes'] = df_show['Diamantes'].apply(lambda x: f"{int(x):,}" if pd.notnull(x) else "0")
        
        if 'Coins' in df_show.columns:
            df_show['Coins'] = df_show['Coins'].apply(lambda x: f"{int(x):,}" if pd.notnull(x) else "0")
        
        if 'PayPal' in df_show.columns:
            df_show['PayPal'] = df_show['PayPal'].apply(lambda x: f"${float(x):,.2f}" if pd.notnull(x) else "$0.00")
        
        if 'Sueldo' in df_show.columns:
            df_show['Sueldo'] = df_show['Sueldo'].apply(lambda x: f"${float(x):,.2f}" if pd.notnull(x) else "$0.00")
        
        return df_show
    
    with tab1:
        st.caption(f"📊 {len(df)} usuarios")
        st.dataframe(formatear_dataframe_jugadores(df.sort_values('dias', ascending=False)), 
                    use_container_width=True, hide_index=True, height=500)
    
    with tab2:
        df_cumplen = df[df['cumple'] == 'SI']
        st.caption(f"✅ {len(df_cumplen)} cumplen")
        if not df_cumplen.empty:
            st.dataframe(formatear_dataframe_jugadores(df_cumplen.sort_values('dias', ascending=False)), 
                        use_container_width=True, hide_index=True, height=500)
    
    with tab3:
        df_no = df[df['cumple'] == 'NO']
        st.caption(f"❌ {len(df_no)} no cumplen")
        if not df_no.empty:
            st.dataframe(formatear_dataframe_jugadores(df_no.sort_values('dias', ascending=False)), 
                        use_container_width=True, hide_index=True, height=500)
    
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
