# ============================================================================
# app.py - Sistema Completo TikTok Live
# MODO 1: Pantalla Pública (sin token)
# MODO 2: Panel de Administración (token tipo 'admin')
# MODO 3: Vista por Contrato (token tipo 'contrato')
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
# ESTILOS CSS GLOBALES
# ============================================================================

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
    
    /* Centrado en tablas */
    div[data-testid="stDataFrame"] td {
        text-align: center !important;
    }
    
    div[data-testid="stDataFrame"] th {
        text-align: center !important;
    }
    
    /* Divider con gradiente TikTok */
    hr {
        background: linear-gradient(90deg, var(--tiktok-cyan) 0%, var(--tiktok-pink) 100%);
        height: 3px;
        border: none;
    }
    
    /* Botones personalizados */
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
    
    /* Botón WhatsApp */
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
        transition: all 0.3s ease;
    }
    
    .whatsapp-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(37, 211, 102, 0.4);
    }
    
    /* Sidebar admin */
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
    """Obtiene cliente de Supabase - Compatible con local y Streamlit Cloud"""
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

def verificar_token(token):
    """Verifica token y retorna info con tipo (admin o contrato)"""
    supabase = get_supabase()
    resultado = supabase.table('contratos_tokens').select('*').eq('token', token).eq('activo', True).execute()
    
    if resultado.data:
        token_data = resultado.data[0]
        # Determinar tipo (si no existe la columna, asumir 'contrato')
        tipo = token_data.get('tipo', 'contrato')
        return token_data, tipo
    return None, None

# ============================================================================
# FUNCIONES COMPARTIDAS
# ============================================================================

def obtener_periodos_disponibles():
    """Obtiene todos los periodos disponibles"""
    supabase = get_supabase()
    resultado = supabase.table('usuarios_tiktok').select('fecha_datos').execute()
    
    if resultado.data:
        fechas = sorted(list(set([r['fecha_datos'] for r in resultado.data])), reverse=True)
        return fechas
    return []

def obtener_mes_español(fecha_str):
    """Convierte fecha a formato 'Mes YYYY' en español"""
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
    """Convierte fecha a formato 'DD de Mes, YYYY' en español"""
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

# ============================================================================
# MODO 1: PANTALLA PÚBLICA (SIN TOKEN)
# ============================================================================

def mostrar_pantalla_publica():
    """Pantalla inicial pública con opciones de login"""
    
    # Header
    col_logo, col_titulo = st.columns([1, 4])
    
    with col_logo:
        st.image("https://img.icons8.com/color/96/000000/tiktok--v1.png", width=100)
    
    with col_titulo:
        st.title("🎵 Sistema de Gestión TikTok Live")
        st.markdown("### Bienvenido al sistema de consultas")
    
    st.divider()
    
    # Información pública
    st.markdown("""
    ### 📊 Acerca del Sistema
    
    Este sistema permite a las agencias y administradores consultar:
    - 📈 Métricas de rendimiento de usuarios
    - 💎 Estadísticas de diamantes
    - 🎯 Niveles de cumplimiento
    - 💰 Incentivos calculados
    
    ---
    """)
    
    # Opciones de acceso
    st.markdown("### 🔐 Opciones de Acceso")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 30px; border-radius: 15px; text-align: center;'>
            <h2 style='color: white; margin: 0;'>🔐 Administrador</h2>
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
            placeholder="ADMIN-xxxxx-xxxxx",
            key="token_admin"
        )
        
        if st.button("🔓 Acceder como Administrador", key="btn_admin", use_container_width=True):
            if token_admin:
                st.query_params["token"] = token_admin
                st.rerun()
            else:
                st.warning("⚠️ Por favor ingresa tu token de administrador")
    
    with col2:
        st.markdown("""
        <div style='background: linear-gradient(135deg, #00f2ea 0%, #fe2c55 100%); 
                    padding: 30px; border-radius: 15px; text-align: center;'>
            <h2 style='color: white; margin: 0;'>📊 Contrato</h2>
            <p style='color: white; margin: 10px 0;'>Vista de tu agencia</p>
            <ul style='color: white; text-align: left; padding-left: 20px;'>
                <li>Ver tus usuarios</li>
                <li>Consultar métricas</li>
                <li>Revisar incentivos</li>
                <li>Descargar reportes</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        token_contrato = st.text_input(
            "Token de Contrato:",
            type="password",
            placeholder="xxxxx-xxxxx-xxxxx",
            key="token_contrato"
        )
        
        if st.button("📈 Acceder a mi Contrato", key="btn_contrato", use_container_width=True):
            if token_contrato:
                st.query_params["token"] = token_contrato
                st.rerun()
            else:
                st.warning("⚠️ Por favor ingresa tu token de contrato")
    
    st.divider()
    
    # Footer
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.caption("🔒 Acceso seguro con tokens únicos")
    
    with col2:
        st.caption("📊 Datos actualizados en tiempo real")
    
    with col3:
        st.caption(f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}")

# ============================================================================
# MODO 2: PANEL DE ADMINISTRACIÓN
# ============================================================================

def mostrar_panel_admin(token_data):
    """Panel de administración completo"""
    
    supabase = get_supabase()
    
    # Header
    st.title("🔐 Panel de Administración")
    st.markdown(f"**Administrador:** {token_data.get('nombre', 'Super Admin')}")
    st.divider()
    
    # Sidebar
    with st.sidebar:
        st.header("🛠️ Herramientas")
        
        opcion = st.radio(
            "Selecciona una opción:",
            [
                "🔍 Buscar Usuario",
                "📊 Dashboard Global",
                "📋 Ver Todos los Contratos",
                "💾 Consulta SQL"
            ]
        )
        
        st.divider()
        st.caption("Sistema de Administración TikTok Live")
        st.caption(f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    # Contenido según opción
    if opcion == "🔍 Buscar Usuario":
        st.header("🔍 Buscar Usuario")
        
        tab1, tab2 = st.tabs(["Por Nombre", "Por ID de TikTok"])
        
        with tab1:
            nombre = st.text_input("Nombre del usuario:", placeholder="Ej: user691276hk")
            
            if st.button("🔍 Buscar", key="btn_nombre"):
                if nombre:
                    with st.spinner("Buscando..."):
                        resultado = supabase.table("usuarios_tiktok")\
                            .select("*")\
                            .ilike("usuario", f"%{nombre}%")\
                            .execute()
                        
                        if resultado.data:
                            st.success(f"✅ {len(resultado.data)} resultado(s)")
                            st.dataframe(pd.DataFrame(resultado.data), use_container_width=True)
                        else:
                            st.warning("❌ No se encontraron usuarios")
        
        with tab2:
            user_id = st.text_input("ID de TikTok:", placeholder="7123456789012345678")
            
            if st.button("🔍 Buscar", key="btn_id"):
                if user_id:
                    with st.spinner("Buscando..."):
                        resultado = supabase.table("usuarios_tiktok")\
                            .select("*")\
                            .eq("id_tiktok", user_id)\
                            .execute()
                        
                        if resultado.data:
                            st.success("✅ Usuario encontrado")
                            st.dataframe(pd.DataFrame(resultado.data), use_container_width=True)
                        else:
                            st.warning("❌ No se encontró usuario")
    
    elif opcion == "📊 Dashboard Global":
        st.header("📊 Dashboard Global")
        
        with st.spinner("Cargando métricas..."):
            # Total usuarios
            usuarios = supabase.table("usuarios_tiktok").select("*", count="exact").execute()
            total_usuarios = usuarios.count if usuarios.count else 0
            
            # Usuarios que cumplen
            cumplen = supabase.table("usuarios_tiktok")\
                .select("*", count="exact")\
                .eq("cumple", "SI")\
                .execute()
            total_cumplen = cumplen.count if cumplen.count else 0
            
            # Total diamantes
            if usuarios.data:
                df = pd.DataFrame(usuarios.data)
                total_diamantes = df['diamantes'].sum() if 'diamantes' in df.columns else 0
            else:
                total_diamantes = 0
            
            # Contratos activos
            contratos = supabase.table("contratos")\
                .select("*", count="exact")\
                .eq("activo", True)\
                .execute()
            total_contratos = contratos.count if contratos.count else 0
            
            # Métricas
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("👥 Total Usuarios", f"{total_usuarios:,}")
            
            with col2:
                st.metric("✅ Cumplen", f"{total_cumplen:,}")
            
            with col3:
                st.metric("💎 Diamantes", f"{total_diamantes:,.0f}")
            
            with col4:
                st.metric("📋 Contratos", f"{total_contratos:,}")
            
            # Tasa de cumplimiento
            if total_usuarios > 0:
                porcentaje = (total_cumplen / total_usuarios) * 100
                st.subheader(f"📈 Tasa de Cumplimiento: {porcentaje:.1f}%")
                st.progress(porcentaje / 100)
    
    elif opcion == "📋 Ver Todos los Contratos":
        st.header("📋 Todos los Contratos")
        
        with st.spinner("Cargando..."):
            resultado = supabase.table("contratos")\
                .select("*")\
                .order("codigo")\
                .execute()
            
            if resultado.data:
                df = pd.DataFrame(resultado.data)
                st.success(f"✅ Total: {len(df)} contratos")
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.warning("No hay contratos")
    
    elif opcion == "💾 Consulta SQL":
        st.header("💾 Consulta SQL Personalizada")
        st.warning("⚠️ Modo avanzado - Ten cuidado")
        
        consulta = st.text_area(
            "Escribe tu consulta:",
            height=200,
            placeholder="SELECT * FROM usuarios_tiktok LIMIT 10;"
        )
        
        if st.button("▶️ Ejecutar"):
            if consulta:
                st.info("💡 Función SQL directa no disponible. Usa las otras herramientas.")

# ============================================================================
# MODO 3: VISTA POR CONTRATO (TU CÓDIGO ORIGINAL)
# ============================================================================

def obtener_columnas_ocultas(contrato):
    """Obtiene columnas ocultas para el contrato"""
    supabase = get_supabase()
    resultado = supabase.table('config_columnas_ocultas').select('columna').eq('contrato', contrato).execute()
    
    if resultado.data:
        return [r['columna'] for r in resultado.data]
    return []

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
    """Calcula incentivo según diamantes y nivel"""
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
    """Obtiene datos del contrato (tu función original completa)"""
    supabase = get_supabase()
    
    # Configuración del contrato
    config_resultado = supabase.table('contratos').select('*').eq('codigo', contrato).execute()
    
    nivel1_tabla3 = False
    if config_resultado.data and len(config_resultado.data) > 0:
        valor = config_resultado.data[0].get('nivel1_tabla3', False)
        if isinstance(valor, str):
            nivel1_tabla3 = valor.upper() in ['SI', 'YES', 'TRUE', '1', 'SÍ']
        else:
            nivel1_tabla3 = bool(valor)
    
    # Obtener usuarios
    resultado = supabase.table('usuarios_tiktok')\
        .select('*')\
        .eq('contrato', contrato)\
        .eq('fecha_datos', fecha_datos)\
        .execute()
    
    if resultado.data:
        df = pd.DataFrame(resultado.data)
        
        # Buscar nombres en histórico
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
                print(f"Error consultando histórico: {e}")
        
        if 'horas' not in df.columns:
            df['horas'] = 0
        
        # Calcular nivel original
        df['nivel_original'] = df.apply(lambda r: determinar_nivel(r.get('dias', 0), r.get('horas', 0)), axis=1)
        df['cumple'] = df['nivel_original'].apply(lambda n: 'SI' if n > 0 else 'NO')
        
        # Obtener incentivos
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

def mostrar_vista_contrato(token_data):
    """Vista por contrato (tu interfaz original)"""
    
    contrato = token_data['contrato']
    nombre = token_data.get('nombre', contrato)
    
    columnas_ocultas_config = obtener_columnas_ocultas(contrato)
    
    # Header
    col_logo, col_titulo, col_whatsapp = st.columns([1, 3, 2])
    
    with col_logo:
        st.image("https://img.icons8.com/color/96/000000/tiktok--v1.png", width=80)
    
    with col_titulo:
        st.title(f"{contrato} - {nombre}")
        st.caption("📊 Sistema de Consulta TikTok Live")
    
    with col_whatsapp:
        whatsapp_url = "https://wa.me/5215659842514?text=Hola,%20tengo%20una%20consulta"
        st.markdown(f"""
            <a href="{whatsapp_url}" target="_blank" class="whatsapp-button">
                <img src="https://img.icons8.com/color/48/000000/whatsapp--v1.png" style="width:24px;height:24px"/>
                <span>Contactar Soporte</span>
            </a>
        """, unsafe_allow_html=True)
        st.markdown('<p style="color:#00f2ea;font-size:18px;font-weight:bold;">📞 +52 1 56 5984 2514</p>', unsafe_allow_html=True)
    
    st.divider()
    
    # ==== MENSAJE SOBRE INCENTIVOS ====
    st.info("""
    ### 🎁 Sobre tus Regalos del Mes (Incentivos)
    
    **📅 ¿Cuándo se entregan?**  
    Los regalos se procesan entre el **día 15 y 25** del mes siguiente al periodo trabajado. Por ejemplo, si trabajaste en octubre, tu regalo llegará entre el 15 y 25 de noviembre.
    
    **✅ ¿Cómo sé si califico para mi regalo?**  
    Solo necesitas cumplir con el mínimo de días, horas y diamantes según la tabla de incentivos. Si alcanzaste **Nivel 1, 2 o 3**, ¡felicidades! Tu regalo está asegurado.
    
    **🔄 ¿No recibiste tu regalo este mes?**  
    ¡Tranquilo! No se pierde nada. Si cumpliste con los requisitos pero por alguna razón no recibiste tu incentivo en el mes correspondiente, **se acumula automáticamente** para el siguiente periodo. Tu esfuerzo no se pierde, está seguro y llegará.
    
    **💬 ¿Tienes dudas o inquietudes?**  
    Contacta a tu agente o a la administración por WhatsApp. Estamos aquí para ayudarte y resolver cualquier pregunta. La comunicación es clave para que todo fluya bien.
    
    **✨ Ten paciencia y confianza** - Valoramos tu esfuerzo y dedicación. Cada diamante cuenta, cada hora transmitida importa. ¡Sigue adelante! 💪
    """)
    
    st.divider()
    
    # Selector de periodo
    periodos = obtener_periodos_disponibles()
    
    if not periodos:
        st.warning("⚠️ No hay datos disponibles")
        st.stop()
    
    col1, col2 = st.columns([2, 2])
    
    with col1:
        periodo_seleccionado = st.selectbox(
            "📅 Seleccionar periodo:",
            periodos,
            format_func=formatear_fecha_español
        )
    
    with col2:
        st.metric("📆 Periodo activo", obtener_mes_español(periodo_seleccionado))
    
    # Cargar datos
    with st.spinner('📄 Cargando...'):
        df = obtener_datos_contrato(contrato, periodo_seleccionado)
    
    if df.empty:
        st.info(f"ℹ️ No hay usuarios para {contrato} en {periodo_seleccionado}")
        st.stop()
    
    st.divider()
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "👥 Todos", 
        "✅ Cumplen", 
        "❌ No Cumplen",
        "📊 Resumen"
    ])
    
    def formatear_dataframe(df_input):
        """Formatea dataframe aplicando columnas ocultas"""
        mapeo_ocultar = {
            'coins': 'incentivo_coins',
            'paypal': 'incentivo_paypal',
            'sueldo': ['coins_bruto', 'paypal_bruto']
        }
        
        columnas_a_ocultar = set(['agencia'])
        
        for config in columnas_ocultas_config:
            if config in mapeo_ocultar:
                valor = mapeo_ocultar[config]
                if isinstance(valor, list):
                    columnas_a_ocultar.update(valor)
                else:
                    columnas_a_ocultar.add(valor)
        
        columnas_orden = [
            'usuario', 'agencia', 'dias', 'duracion', 'diamantes', 
            'nivel', 'cumple', 'incentivo_coins', 'incentivo_paypal'
        ]
        
        columnas_mostrar = [
            col for col in columnas_orden 
            if col in df_input.columns and col not in columnas_a_ocultar
        ]
        
        df_show = df_input[columnas_mostrar].copy()
        
        nombres_columnas = {
            'usuario': 'Usuario',
            'dias': 'Días',
            'duracion': 'Horas',
            'diamantes': 'Diamantes',
            'nivel': 'Nivel',
            'cumple': 'Cumple',
            'incentivo_coins': 'Incentivo Coin',
            'incentivo_paypal': 'Incentivo PayPal'
        }
        
        df_show = df_show.rename(columns={k: v for k, v in nombres_columnas.items() if k in df_show.columns})
        
        if 'Diamantes' in df_show.columns:
            df_show['Diamantes'] = df_show['Diamantes'].apply(lambda x: f"{int(x):,}" if pd.notnull(x) else "0")
        
        if 'Días' in df_show.columns:
            df_show['Días'] = df_show['Días'].apply(lambda x: int(x) if pd.notnull(x) else 0)
        
        if 'Incentivo Coin' in df_show.columns:
            df_show['Incentivo Coin'] = df_show['Incentivo Coin'].apply(
                lambda x: f"{int(x):,}" if pd.notnull(x) and x > 0 else "0"
            )
        
        if 'Incentivo PayPal' in df_show.columns:
            df_show['Incentivo PayPal'] = df_show['Incentivo PayPal'].apply(
                lambda x: f"${float(x):,.2f}" if pd.notnull(x) and x > 0 else "$0.00"
            )
        
        return df_show
    
    with tab1:
        st.caption(f"📊 {len(df)} usuarios totales")
        st.dataframe(formatear_dataframe(df.sort_values('diamantes', ascending=False)), 
                    use_container_width=False, hide_index=True, height=500)
    
    with tab2:
        df_cumplen = df[df['cumple'] == 'SI']
        st.caption(f"✅ {len(df_cumplen)} usuarios cumplen")
        if not df_cumplen.empty:
            st.dataframe(formatear_dataframe(df_cumplen.sort_values('diamantes', ascending=False)), 
                        use_container_width=False, hide_index=True, height=500)
    
    with tab3:
        df_no_cumplen = df[df['cumple'] == 'NO']
        st.caption(f"❌ {len(df_no_cumplen)} usuarios no cumplen")
        if not df_no_cumplen.empty:
            st.dataframe(formatear_dataframe(df_no_cumplen.sort_values('diamantes', ascending=False)), 
                        use_container_width=False, hide_index=True, height=500)
    
    with tab4:
        st.markdown("### 📈 Métricas")
        
        usuarios_cumplen = len(df[df['cumple'] == 'SI'])
        total_usuarios = len(df)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("👥 Total", total_usuarios)
        
        with col2:
            st.metric("✅ Cumplen", usuarios_cumplen, 
                     delta=f"{(usuarios_cumplen/total_usuarios*100):.1f}%" if total_usuarios > 0 else "0%")
        
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
    """Router principal - decide qué interfaz mostrar"""
    
    # Obtener token de URL
    query_params = st.query_params
    token = query_params.get("token", None)
    
    if not token:
        # MODO 1: Sin token → Pantalla pública
        mostrar_pantalla_publica()
    else:
        # Verificar token
        token_data, tipo = verificar_token(token)
        
        if not token_data:
            st.error("❌ Token inválido o inactivo")
            if st.button("← Volver al inicio"):
                st.query_params.clear()
                st.rerun()
            st.stop()
        
        # MODO 2 o 3 según tipo de token
        if tipo == 'admin':
            # MODO 2: Panel de Administración
            mostrar_panel_admin(token_data)
        else:
            # MODO 3: Vista por Contrato
            mostrar_vista_contrato(token_data)

if __name__ == "__main__":
    main()
