# ====
# streamlit_app/app.py
# Sistema de consulta de contratos TikTok Live
# MODO PÚBLICO: Columnas ocultas según configuración
# Acceso por token único
# ====

import streamlit as st
import pandas as pd
from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import datetime
import calendar
import plotly.graph_objects as go

# Cargar variables de entorno
load_dotenv()

# Configurar página
st.set_page_config(
    page_title="Sistema de Consulta - TikTok Live",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilos CSS personalizados con colores TikTok
st.markdown("""
<style>
    /* Colores TikTok */
    :root {
        --tiktok-black: #000000;
        --tiktok-cyan: #00f2ea;
        --tiktok-pink: #fe2c55;
        --tiktok-white: #ffffff;
    }
    
    /* Fondo general */
    .stApp {
        background-color: var(--tiktok-black);
    }
    
    /* Métricas */
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
    
    /* Títulos */
    h1, h2, h3 {
        color: var(--tiktok-cyan) !important;
        text-shadow: 2px 2px 4px rgba(254, 44, 85, 0.3);
    }
    
    /* FORZAR CENTRADO EN TABLAS */
    div[data-testid="stDataFrame"] td {
        text-align: center !important;
    }
    
    div[data-testid="stDataFrame"] th {
        text-align: center !important;
    }
    
    /* Ajustar padding de celdas */
    div[data-testid="stDataFrame"] td,
    div[data-testid="stDataFrame"] th {
        padding: 8px 4px !important;
    }
    
    /* Divider con gradiente TikTok */
    hr {
        background: linear-gradient(90deg, var(--tiktok-cyan) 0%, var(--tiktok-pink) 100%);
        height: 3px;
        border: none;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: rgba(0, 242, 234, 0.1);
        border-radius: 10px;
        padding: 5px;
    }
    
    .stTabs [data-baseweb="tab"] {
        color: var(--tiktok-cyan);
        font-weight: bold;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--tiktok-cyan) 0%, var(--tiktok-pink) 100%);
        color: var(--tiktok-white) !important;
        border-radius: 8px;
    }
    
    /* Captions y texto */
    .stCaption {
        color: var(--tiktok-cyan) !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: rgba(0, 242, 234, 0.1);
        border: 1px solid var(--tiktok-cyan);
        border-radius: 8px;
        color: var(--tiktok-cyan) !important;
    }
    
    /* Alert boxes personalizados */
    .stAlert {
        background: linear-gradient(135deg, rgba(0, 242, 234, 0.1) 0%, rgba(254, 44, 85, 0.1) 100%);
        border: 2px solid var(--tiktok-cyan);
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ==== CONEXIÓN SUPABASE ====

@st.cache_resource
def get_supabase():
    """Obtiene cliente de Supabase - Compatible con local y Streamlit Cloud"""
    try:
        # Intentar desde st.secrets primero (Streamlit Cloud)
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_SERVICE_KEY"]
    except:
        # Fallback a variables de entorno (local con .env)
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not url or not key:
        st.error("Error: Credenciales de Supabase no configuradas")
        st.stop()
    
    return create_client(url, key)

# ==== FUNCIONES ====

def verificar_token(token):
    """Verifica si el token es válido y retorna info del contrato"""
    supabase = get_supabase()
    resultado = supabase.table('contratos_tokens').select('*').eq('token', token).eq('activo', True).execute()
    
    if resultado.data:
        return resultado.data[0]
    return None

def obtener_columnas_ocultas(contrato):
    """Obtiene columnas ocultas para el contrato desde Supabase"""
    supabase = get_supabase()
    resultado = supabase.table('config_columnas_ocultas').select('columna').eq('contrato', contrato).execute()
    
    if resultado.data:
        return [r['columna'] for r in resultado.data]
    return []

def obtener_periodos_disponibles():
    """Obtiene todos los periodos disponibles"""
    supabase = get_supabase()
    resultado = supabase.table('usuarios_tiktok').select('fecha_datos').execute()
    
    if resultado.data:
        fechas = sorted(list(set([r['fecha_datos'] for r in resultado.data])), reverse=True)
        return fechas
    return []

def obtener_incentivos():
    """Obtiene la tabla de incentivos horizontales"""
    supabase = get_supabase()
    resultado = supabase.table('incentivos_horizontales').select('*').order('acumulado').execute()
    
    if resultado.data:
        return pd.DataFrame(resultado.data)
    return pd.DataFrame()

def determinar_nivel(dias, horas):
    """Determina nivel según días y horas trabajadas"""
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
    """
    Calcula el incentivo según diamantes acumulados y nivel de cumplimiento
    """
    if nivel == 0 or diamantes <= 0:
        return (0, 0)
    
    # Buscar la fila correspondiente según diamantes
    fila = df_incentivos[df_incentivos['acumulado'] <= diamantes].sort_values('acumulado', ascending=False)
    
    if fila.empty:
        return (0, 0)
    
    fila = fila.iloc[0]
    
    # Usar nombres exactos con "s" al final
    col_coins = f'nivel_{nivel}_monedas'
    col_paypal = f'nivel_{nivel}_paypal'
    
    incentivo_coins = fila.get(col_coins, 0) if col_coins in fila else 0
    incentivo_paypal = fila.get(col_paypal, 0) if col_paypal in fila else 0
    
    return (incentivo_coins, incentivo_paypal)

def obtener_datos_contrato(contrato, fecha_datos):
    """Obtiene TODOS los datos del contrato para un periodo específico"""
    supabase = get_supabase()
    
    # 1. Obtener configuración del contrato
    config_resultado = supabase.table('contratos').select('*').eq('codigo', contrato).execute()
    
    nivel1_tabla3 = False
    if config_resultado.data and len(config_resultado.data) > 0:
        valor = config_resultado.data[0].get('nivel1_tabla3', False)
        # CORRECCIÓN: Manejar tanto boolean como string
        if isinstance(valor, str):
            nivel1_tabla3 = valor.upper() in ['SI', 'YES', 'TRUE', '1', 'SÍ']
        else:
            nivel1_tabla3 = bool(valor)
    
    # 2. Obtener usuarios
    resultado = supabase.table('usuarios_tiktok')\
        .select('*')\
        .eq('contrato', contrato)\
        .eq('fecha_datos', fecha_datos)\
        .execute()
    
    if resultado.data:
        df = pd.DataFrame(resultado.data)
        
        # CORRECCIÓN MEJORADA: Consultar histórico para usuarios sin nombre
        # Identificar usuarios sin nombre (NULL o vacío)
        mask_sin_nombre = df['usuario'].isna() | (df['usuario'] == '') | (df['usuario'].str.strip() == '')
        usuarios_sin_nombre = df[mask_sin_nombre]
        
        if not usuarios_sin_nombre.empty:
            print(f"DEBUG: Encontrados {len(usuarios_sin_nombre)} usuarios sin nombre")
            
            # Obtener IDs únicos de usuarios sin nombre
            ids_sin_nombre = usuarios_sin_nombre['id_tiktok'].astype(str).unique().tolist()
            print(f"DEBUG: IDs a buscar en histórico: {ids_sin_nombre[:3]}...")
            
            # Consultar histórico - PROBAR AMBOS FORMATOS DE COLUMNAS
            try:
                historico = supabase.table('historico_usuarios')\
                    .select('id_tiktok, usuario_1, usuario_2, usuario_3')\
                    .in_('id_tiktok', ids_sin_nombre)\
                    .execute()
                
                print(f"DEBUG: Registros encontrados en histórico: {len(historico.data) if historico.data else 0}")
                
                if historico.data:
                    # Crear diccionario de id_tiktok -> nombre
                    nombres_historico = {}
                    for registro in historico.data:
                        id_tiktok = str(registro['id_tiktok'])
                        # Buscar primer nombre no vacío (intentar con minúsculas y mayúsculas)
                        nombre = None
                        for col in ['usuario_1', 'Usuario_1', 'usuario_2', 'Usuario_2', 'usuario_3', 'Usuario_3']:
                            valor = registro.get(col, '')
                            if valor and str(valor).strip() and str(valor).strip().lower() not in ['', 'nan', 'none', 'null']:
                                nombre = str(valor).strip()
                                break
                        
                        if nombre:
                            nombres_historico[id_tiktok] = nombre
                            print(f"DEBUG: ID {id_tiktok[:10]}... -> {nombre}")
                        else:
                            # Si no hay nombre en el histórico, usar ID truncado
                            nombres_historico[id_tiktok] = f"Usuario_{id_tiktok[:8]}"
                    
                    print(f"DEBUG: Nombres encontrados en histórico: {len(nombres_historico)}")
                    
                    # Actualizar nombres en el dataframe
                    def obtener_nombre(row):
                        if pd.isna(row['usuario']) or str(row['usuario']).strip() == '':
                            id_str = str(row['id_tiktok'])
                            return nombres_historico.get(id_str, f"Usuario_{id_str[:8]}")
                        return row['usuario']
                    
                    df['usuario'] = df.apply(obtener_nombre, axis=1)
                    print(f"DEBUG: Usuarios actualizados con nombres del histórico")
            
            except Exception as e:
                print(f"ERROR consultando histórico: {e}")
        
        # Horas ya viene como numeric
        if 'horas' not in df.columns:
            df['horas'] = 0
        
        # Calcular nivel ORIGINAL
        df['nivel_original'] = df.apply(lambda r: determinar_nivel(r.get('dias', 0), r.get('horas', 0)), axis=1)
        
        # Determinar cumplimiento
        df['cumple'] = df['nivel_original'].apply(lambda n: 'SI' if n > 0 else 'NO')
        
        # Obtener tabla de incentivos
        df_incentivos = obtener_incentivos()
        
        if not df_incentivos.empty:
            # Calcular incentivos
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
            
            # Asignar nivel FINAL
            if nivel1_tabla3:
                df['nivel'] = df['nivel_original'].apply(lambda n: 3 if n >= 1 else 0)
            else:
                df['nivel'] = df['nivel_original']
        else:
            df['incentivo_coins'] = 0
            df['incentivo_paypal'] = 0
            df['nivel'] = df['nivel_original']
        
        # Limpiar incentivos para usuarios que no cumplen
        df.loc[df['cumple'] == 'NO', ['incentivo_coins', 'incentivo_paypal']] = 0
        
        return df
    
    return pd.DataFrame()

def formatear_numero(num):
    """Formatea número con separadores de miles"""
    try:
        return f"{int(num):,}"
    except:
        return "0"

def formatear_moneda(num):
    """Formatea número como moneda USD"""
    try:
        return f"${float(num):,.2f}"
    except:
        return "$0.00"

def es_ultimo_dia_mes(fecha_str):
    """Verifica si la fecha es el último día del mes"""
    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d')
        ultimo_dia = calendar.monthrange(fecha.year, fecha.month)[1]
        return fecha.day == ultimo_dia
    except:
        return False

def obtener_mensaje_periodo(fecha_str, usuarios_cumplen, total_usuarios):
    """Genera mensaje motivacional según la fecha del periodo"""
    es_cierre = es_ultimo_dia_mes(fecha_str)
    porcentaje_cumple = (usuarios_cumplen / total_usuarios * 100) if total_usuarios > 0 else 0
    
    if es_cierre:
        # Mensajes de cierre
        if porcentaje_cumple >= 80:
            return "🎉 **¡CIERRE DEL MES!** Excelente desempeño del equipo. ¡Felicidades! 🏆"
        elif porcentaje_cumple >= 50:
            return "📊 **CIERRE DEL MES** - Resultados finales del periodo."
        else:
            return "📊 **CIERRE DEL MES** - Periodo finalizado. Revisa los resultados."
    else:
        # Mensajes motivacionales durante el mes
        if porcentaje_cumple >= 80:
            return "🚀 **¡Excelente avance!** El equipo va muy bien. ¡Sigan así!"
        elif porcentaje_cumple >= 50:
            return "💪 **¡Buen ritmo!** Aún hay tiempo para mejorar. ¡Vamos por más!"
        else:
            return "⏰ **¡Aún están a tiempo!** Motiva a tu equipo para alcanzar las metas. 🎯"

def crear_grafico_pastel(nivel_counts):
    """Crea un gráfico de pastel con los niveles de cumplimiento"""
    
    labels = []
    values = []
    colors = []
    
    # Nivel 3
    if nivel_counts.get(3, 0) > 0:
        labels.append('🥇 Nivel 3')
        values.append(nivel_counts.get(3, 0))
        colors.append('#FFD700')  # Oro
    
    # Nivel 2
    if nivel_counts.get(2, 0) > 0:
        labels.append('🥈 Nivel 2')
        values.append(nivel_counts.get(2, 0))
        colors.append('#C0C0C0')  # Plata
    
    # Nivel 1
    if nivel_counts.get(1, 0) > 0:
        labels.append('🥉 Nivel 1')
        values.append(nivel_counts.get(1, 0))
        colors.append('#CD7F32')  # Bronce
    
    # Nivel 0
    if nivel_counts.get(0, 0) > 0:
        labels.append('⚫ Nivel 0')
        values.append(nivel_counts.get(0, 0))
        colors.append('#6c757d')  # Gris
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        marker=dict(colors=colors, line=dict(color='#000000', width=2)),
        textinfo='label+percent+value',
        textfont=dict(size=14, color='white'),
        hole=0.4  # Donut chart
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

# ==== INTERFAZ PRINCIPAL ====

def main():
    # Obtener token de la URL
    query_params = st.query_params
    token = query_params.get('token', None)
    
    if not token:
        st.error("❌ **Acceso denegado**: Token no proporcionado")
        st.info("💡 Solicita tu enlace de acceso personalizado al administrador")
        st.stop()
    
    # Verificar token
    info_contrato = verificar_token(token)
    
    if not info_contrato:
        st.error("❌ **Acceso denegado**: Token inválido o inactivo")
        st.info("💡 Verifica tu enlace o contacta al administrador")
        st.stop()
    
    # Token válido - Información del contrato
    contrato = info_contrato['contrato']
    nombre = info_contrato.get('nombre', contrato)
    
    # OBTENER COLUMNAS OCULTAS PARA ESTE CONTRATO
    columnas_ocultas_config = obtener_columnas_ocultas(contrato)
    
    # ==== HEADER ====
    
    col_logo, col_titulo = st.columns([1, 4])
    
    with col_logo:
        st.image("https://img.icons8.com/color/96/0000/tiktok--v1.png", width=80)
    
    with col_titulo:
        st.title(f"📊 Sistema de Consulta - Contrato {contrato}")
        st.subheader(f"👤 {nombre}")
    
    st.divider()
    
    # ==== SELECTOR DE PERIODO ====
    
    periodos = obtener_periodos_disponibles()
    
    if not periodos:
        st.warning("⚠️ No hay datos disponibles en el sistema")
        st.stop()
    
    col1, col2, col3 = st.columns([2, 2, 4])
    
    with col1:
        periodo_seleccionado = st.selectbox(
            "📅 **Seleccionar periodo:**",
            periodos,
            format_func=lambda x: datetime.strptime(x, '%Y-%m-%d').strftime('%d de %B, %Y')
        )
    
    with col2:
        st.metric("📆 Periodo activo", datetime.strptime(periodo_seleccionado, '%Y-%m-%d').strftime('%B %Y'))
    
    # ==== CARGAR DATOS ====
    
    with st.spinner('🔄 Cargando datos...'):
        df = obtener_datos_contrato(contrato, periodo_seleccionado)
    
    if df.empty:
        st.info(f"ℹ️ No hay usuarios registrados para el contrato **{contrato}** en el periodo **{periodo_seleccionado}**")
        st.stop()
    
    # ==== MENSAJE MOTIVACIONAL ====
    
    total_usuarios = len(df)
    usuarios_cumplen = len(df[df['cumple'] == 'SI'])
    
    mensaje = obtener_mensaje_periodo(periodo_seleccionado, usuarios_cumplen, total_usuarios)
    
    if es_ultimo_dia_mes(periodo_seleccionado):
        st.success(mensaje)
    else:
        st.info(mensaje)
    
    st.divider()
    
    # ==== TABLA DE USUARIOS (PRINCIPAL) ====
    
    st.subheader("📋 Listado de Usuarios")
    
    # Tabs para separar usuarios
    tab1, tab2, tab3, tab4 = st.tabs([
        "👥 Todos los Usuarios", 
        "✅ Usuarios que Cumplen", 
        "❌ Usuarios que NO Cumplen",
        "📊 Resumen del Periodo"
    ])
    
    # Preparar dataframe para mostrar CON COLUMNAS OCULTAS
    def formatear_dataframe(df_input):
        """Formatea el dataframe para visualización APLICANDO OCULTAR COLUMNAS"""
        
        # Mapeo de columnas config -> columnas reales
        mapeo_ocultar = {
            'coins': 'incentivo_coins',
            'paypal': 'incentivo_paypal',
            'sueldo': ['coins_bruto', 'paypal_bruto']  # Sueldo oculta ambas
        }
        
        # Determinar qué columnas reales hay que ocultar
        columnas_a_ocultar = set()
        
        # SIEMPRE ocultar Agencia
        columnas_a_ocultar.add('agencia')
        
        # Ocultar según configuración
        for config in columnas_ocultas_config:
            if config in mapeo_ocultar:
                valor = mapeo_ocultar[config]
                if isinstance(valor, list):
                    columnas_a_ocultar.update(valor)
                else:
                    columnas_a_ocultar.add(valor)
        
        # Orden de columnas base (incluye todas las posibles)
        columnas_orden_completo = [
            'usuario', 'agencia', 'dias', 'duracion', 'diamantes', 
            'nivel', 'cumple', 'incentivo_coins', 'incentivo_paypal'
        ]
        
        # Filtrar: solo mostrar las que NO están ocultas y existen
        columnas_mostrar = [
            col for col in columnas_orden_completo 
            if col in df_input.columns and col not in columnas_a_ocultar
        ]
        
        df_show = df_input[columnas_mostrar].copy()
        
        # Renombrar columnas
        nombres_columnas = {
            'usuario': 'Usuario',
            'agencia': 'Agencia',  # Esta no se mostrará porque siempre está oculta
            'dias': 'Días',
            'duracion': 'Horas',
            'diamantes': 'Diamantes',
            'nivel': 'Nivel',
            'cumple': 'Cumple',
            'incentivo_coins': 'Incentivo Coin',
            'incentivo_paypal': 'Incentivo PayPal'
        }
        
        df_show = df_show.rename(columns={k: v for k, v in nombres_columnas.items() if k in df_show.columns})
        
        # Formatear números
        if 'Diamantes' in df_show.columns:
            df_show['Diamantes'] = df_show['Diamantes'].apply(lambda x: f"{int(x):,}" if pd.notnull(x) else "0")
        
        if 'Días' in df_show.columns:
            df_show['Días'] = df_show['Días'].apply(lambda x: int(x) if pd.notnull(x) else 0)
        
        # Formatear Incentivo Coin
        if 'Incentivo Coin' in df_show.columns:
            df_show['Incentivo Coin'] = df_show['Incentivo Coin'].apply(
                lambda x: f"{int(x):,}" if pd.notnull(x) and x > 0 else "0"
            )
        
        # Formatear Incentivo PayPal
        if 'Incentivo PayPal' in df_show.columns:
            df_show['Incentivo PayPal'] = df_show['Incentivo PayPal'].apply(
                lambda x: f"${float(x):,.2f}" if pd.notnull(x) and x > 0 else "$0.00"
            )
        
        return df_show
    
    with tab1:
        st.caption(f"📊 Mostrando {len(df)} usuarios totales")
        df_todos = formatear_dataframe(df.sort_values('diamantes', ascending=False))
        
        st.dataframe(
            df_todos,
            use_container_width=False,
            hide_index=True,
            height=500
        )
    
    with tab2:
        df_cumplen = df[df['cumple'] == 'SI']
        st.caption(f"✅ Mostrando {len(df_cumplen)} usuarios que CUMPLEN requisitos")
        
        if not df_cumplen.empty:
            df_cumplen_show = formatear_dataframe(df_cumplen.sort_values('diamantes', ascending=False))
            st.dataframe(
                df_cumplen_show,
                use_container_width=False,
                hide_index=True,
                height=500
            )
        else:
            st.info("No hay usuarios que cumplan los requisitos en este periodo")
    
    with tab3:
        df_no_cumplen = df[df['cumple'] == 'NO']
        st.caption(f"❌ Mostrando {len(df_no_cumplen)} usuarios que NO CUMPLEN requisitos")
        
        if not df_no_cumplen.empty:
            df_no_cumplen_show = formatear_dataframe(df_no_cumplen.sort_values('diamantes', ascending=False))
            st.dataframe(
                df_no_cumplen_show,
                use_container_width=False,
                hide_index=True,
                height=500
            )
        else:
            st.success("¡Todos los usuarios cumplen requisitos!")
    
    with tab4:
        # ==== RESUMEN DEL PERIODO ====
        
        st.markdown("### 📈 Métricas Generales")
        
        usuarios_no_cumplen = len(df[df['cumple'] == 'NO'])
        total_diamantes = df['diamantes'].sum() if 'diamantes' in df.columns else 0
        total_diamantes_validos = df[df['cumple'] == 'SI']['diamantes'].sum() if 'diamantes' in df.columns else 0
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("👥 Total Usuarios", total_usuarios)
        
        with col2:
            st.metric("✅ Cumplen", usuarios_cumplen, 
                      delta=f"{(usuarios_cumplen/total_usuarios*100):.1f}%" if total_usuarios > 0 else "0%")
        
        with col3:
            st.metric("❌ No Cumplen", usuarios_no_cumplen,
                      delta=f"{(usuarios_no_cumplen/total_usuarios*100):.1f}%" if total_usuarios > 0 else "0%",
                      delta_color="inverse")
        
        st.divider()
        
        col4, col5 = st.columns(2)
        
        with col4:
            st.metric("💎 Diamantes Totales", formatear_numero(total_diamantes))
        
        with col5:
            st.metric("💰 Diamantes Válidos", formatear_numero(total_diamantes_validos))
        
        st.divider()
        
        # Distribución por nivel con gráfico de pastel
        st.markdown("### 🎯 Distribución por Nivel")
        
        nivel_counts = df['nivel'].value_counts().sort_index(ascending=False)
        
        col_metricas, col_grafico = st.columns([1, 1])
        
        with col_metricas:
            col1, col2 = st.columns(2)
            
            with col1:
                nivel_3 = nivel_counts.get(3, 0)
                st.metric("🥇 Nivel 3", nivel_3, help="≥20 días Y ≥40 horas")
                
                nivel_1 = nivel_counts.get(1, 0)
                st.metric("🥉 Nivel 1", nivel_1, help="≥7 días Y ≥15 horas")
            
            with col2:
                nivel_2 = nivel_counts.get(2, 0)
                st.metric("🥈 Nivel 2", nivel_2, help="≥14 días Y ≥30 horas")
                
                nivel_0 = nivel_counts.get(0, 0)
                st.metric("⚫ Nivel 0", nivel_0, help="No cumple requisitos")
        
        with col_grafico:
            fig = crear_grafico_pastel(nivel_counts)
            st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # ==== FOOTER ====
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.caption(f"🔒 Vista privada para **{contrato}**")
    
    with col2:
        st.caption(f"📅 Periodo: **{periodo_seleccionado}**")
    
    with col3:
        st.caption(f"🕐 Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    # ==== EXPANDER CON INFO ADICIONAL ====
    
    with st.expander("ℹ️ Información sobre niveles de cumplimiento"):
        st.markdown("""
        ### 🎯 Niveles de Cumplimiento:
        
        - **Nivel 3** 🥇: ≥20 días Y ≥40 horas
        - **Nivel 2** 🥈: ≥14 días Y ≥30 horas
        - **Nivel 1** 🥉: ≥7 días Y ≥15 horas
        - **Nivel 0** ⚫: No cumple requisitos
        
        ### ✅ Criterio de Cumplimiento:
        Un usuario **CUMPLE** cuando alcanza al menos **Nivel 1** (≥7 días Y ≥15 horas)
        
        ### 💰 Incentivos:
        Los incentivos se calculan según la tabla de incentivos horizontales y el nivel alcanzado.
        Solo los usuarios que **CUMPLEN** reciben incentivos.
        
        Se muestran las columnas según la configuración de tu contrato.
        
        ### 🎁 Beneficio Especial:
        Algunos contratos tienen el beneficio **"Nivel 1 = Tabla 3"**, lo que significa que cualquier usuario que cumpla el nivel mínimo (Nivel 1) recibe incentivos de Nivel 3.
        """)

if __name__ == "__main__":
    main()