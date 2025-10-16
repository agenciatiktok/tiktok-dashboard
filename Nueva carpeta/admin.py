# ============================================================================
# admin.py - Panel de Administración
# Sistema de consulta de contratos TikTok Live
# MODO ADMINISTRADOR: Acceso completo a todos los datos
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
    page_title="Panel de Administración - TikTok Live",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS - Tema Admin (oscuro)
st.markdown("""
<style>
    /* Tema oscuro admin */
    .stApp {
        background-color: #0a0a0a;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a1a 0%, #0a0a0a 100%);
    }
    
    /* Métricas con gradiente admin */
    .stMetric {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 15px;
        border-radius: 10px;
        color: white;
    }
    
    .stMetric label {
        color: white !important;
        font-weight: bold;
    }
    
    .stMetric [data-testid="stMetricValue"] {
        color: white;
        font-size: 28px;
        font-weight: bold;
    }
    
    /* Tablas */
    .dataframe {
        font-size: 12px;
    }
    
    /* Títulos */
    h1, h2, h3 {
        color: #667eea !important;
    }
    
    /* Botones */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 10px 24px;
        border-radius: 8px;
        font-weight: bold;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# FUNCIONES DE CONEXIÓN
# ============================================================================

@st.cache_resource
def init_supabase():
    """Inicializar cliente de Supabase"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        st.error("❌ Faltan credenciales de Supabase en .env")
        st.stop()
    return create_client(url, key)

# ============================================================================
# FUNCIONES DE AUTENTICACIÓN
# ============================================================================

def verificar_token_admin(supabase, token):
    """Verificar si el token es de tipo admin"""
    try:
        response = supabase.table("contratos_tokens")\
            .select("*")\
            .eq("token", token)\
            .eq("activo", True)\
            .execute()
        
        if response.data and len(response.data) > 0:
            token_data = response.data[0]
            # Verificar si tiene columna 'tipo' y es 'admin'
            if 'tipo' in token_data and token_data['tipo'] == 'admin':
                return True, token_data
        return False, None
    except Exception as e:
        st.error(f"❌ Error al verificar token: {str(e)}")
        return False, None

# ============================================================================
# FUNCIONES DE BÚSQUEDA
# ============================================================================

def buscar_usuario_por_nombre(supabase, nombre):
    """Buscar usuario por nombre (parcial o completo)"""
    try:
        # Buscar en usuarios_tiktok (activos)
        response = supabase.table("usuarios_tiktok")\
            .select("*")\
            .ilike("nombre", f"%{nombre}%")\
            .execute()
        
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error al buscar usuario: {str(e)}")
        return pd.DataFrame()

def buscar_usuario_por_id(supabase, user_id):
    """Buscar usuario por ID de TikTok"""
    try:
        response = supabase.table("usuarios_tiktok")\
            .select("*")\
            .eq("id_tiktok", user_id)\
            .execute()
        
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error al buscar usuario: {str(e)}")
        return pd.DataFrame()

def obtener_historial_usuario(supabase, user_id):
    """Obtener historial completo de un usuario"""
    try:
        response = supabase.table("historico_usuarios")\
            .select("*")\
            .eq("id_tiktok", user_id)\
            .order("periodo", desc=True)\
            .execute()
        
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error al obtener historial: {str(e)}")
        return pd.DataFrame()

# ============================================================================
# FUNCIONES DE DASHBOARD
# ============================================================================

def obtener_metricas_globales(supabase):
    """Obtener métricas globales del sistema"""
    try:
        # Total usuarios activos
        usuarios = supabase.table("usuarios_tiktok").select("*", count="exact").execute()
        total_usuarios = usuarios.count if usuarios.count else 0
        
        # Total que cumplen
        cumplen = supabase.table("usuarios_tiktok")\
            .select("*", count="exact")\
            .eq("cumple", True)\
            .execute()
        total_cumplen = cumplen.count if cumplen.count else 0
        
        # Total diamantes
        if usuarios.data:
            df = pd.DataFrame(usuarios.data)
            total_diamantes = df['diamantes'].sum() if 'diamantes' in df.columns else 0
        else:
            total_diamantes = 0
        
        # Total contratos activos
        contratos = supabase.table("contratos")\
            .select("*", count="exact")\
            .eq("activo", True)\
            .execute()
        total_contratos = contratos.count if contratos.count else 0
        
        return {
            'total_usuarios': total_usuarios,
            'total_cumplen': total_cumplen,
            'total_diamantes': total_diamantes,
            'total_contratos': total_contratos
        }
    except Exception as e:
        st.error(f"❌ Error al obtener métricas: {str(e)}")
        return None

def obtener_distribucion_contratos(supabase):
    """Obtener distribución de usuarios por contrato"""
    try:
        response = supabase.table("usuarios_tiktok")\
            .select("contrato")\
            .execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            distribucion = df['contrato'].value_counts().reset_index()
            distribucion.columns = ['Contrato', 'Usuarios']
            return distribucion
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error al obtener distribución: {str(e)}")
        return pd.DataFrame()

# ============================================================================
# FUNCIONES DE CONTRATOS
# ============================================================================

def obtener_todos_contratos(supabase):
    """Obtener listado de todos los contratos"""
    try:
        response = supabase.table("contratos")\
            .select("*")\
            .order("contrato")\
            .execute()
        
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error al obtener contratos: {str(e)}")
        return pd.DataFrame()

# ============================================================================
# INTERFAZ PRINCIPAL
# ============================================================================

def main():
    # Inicializar Supabase
    supabase = init_supabase()
    
    # ========================================================================
    # AUTENTICACIÓN
    # ========================================================================
    
    # Obtener token de la URL
    query_params = st.query_params
    token = query_params.get("token", None)
    
    if not token:
        st.error("🔒 **Acceso Denegado**")
        st.warning("Este panel requiere un token de administrador.")
        st.info("Formato: `?token=ADMIN-xxxxx`")
        st.stop()
    
    # Verificar token de admin
    es_admin, token_data = verificar_token_admin(supabase, token)
    
    if not es_admin:
        st.error("🔒 **Token Inválido o Sin Permisos de Administrador**")
        st.stop()
    
    # ========================================================================
    # HEADER
    # ========================================================================
    
    st.title("🔐 Panel de Administración")
    st.markdown(f"**Administrador:** {token_data.get('nombre', 'Super Admin')}")
    st.divider()
    
    # ========================================================================
    # SIDEBAR
    # ========================================================================
    
    with st.sidebar:
        st.header("🛠️ Herramientas")
        
        opcion = st.radio(
            "Selecciona una opción:",
            [
                "🔍 Buscar Usuario",
                "📊 Dashboard Global",
                "📋 Ver Todos los Contratos",
                "💾 Consulta SQL Personalizada"
            ]
        )
        
        st.divider()
        st.caption("Sistema de Administración TikTok Live")
        st.caption(f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    # ========================================================================
    # CONTENIDO SEGÚN OPCIÓN
    # ========================================================================
    
    if opcion == "🔍 Buscar Usuario":
        st.header("🔍 Buscar Usuario")
        
        tab1, tab2 = st.tabs(["Por Nombre", "Por ID de TikTok"])
        
        with tab1:
            st.subheader("Buscar por Nombre")
            nombre = st.text_input("Ingresa el nombre del usuario:", placeholder="Ej: user691276hk")
            
            if st.button("🔍 Buscar por Nombre", key="btn_nombre"):
                if nombre:
                    with st.spinner("Buscando..."):
                        df_resultado = buscar_usuario_por_nombre(supabase, nombre)
                        
                        if not df_resultado.empty:
                            st.success(f"✅ Se encontraron {len(df_resultado)} resultado(s)")
                            
                            # Mostrar resultados
                            st.dataframe(
                                df_resultado,
                                use_container_width=True,
                                hide_index=True
                            )
                            
                            # Mostrar historial del primero
                            if len(df_resultado) > 0:
                                user_id = df_resultado.iloc[0]['id_tiktok']
                                st.subheader(f"📜 Historial de {df_resultado.iloc[0]['nombre']}")
                                
                                df_historial = obtener_historial_usuario(supabase, user_id)
                                if not df_historial.empty:
                                    st.dataframe(
                                        df_historial,
                                        use_container_width=True,
                                        hide_index=True
                                    )
                                else:
                                    st.info("No hay historial disponible")
                        else:
                            st.warning("❌ No se encontraron usuarios con ese nombre")
                else:
                    st.warning("⚠️ Por favor ingresa un nombre")
        
        with tab2:
            st.subheader("Buscar por ID de TikTok")
            user_id = st.text_input("Ingresa el ID de TikTok:", placeholder="Ej: 7123456789012345678")
            
            if st.button("🔍 Buscar por ID", key="btn_id"):
                if user_id:
                    with st.spinner("Buscando..."):
                        df_resultado = buscar_usuario_por_id(supabase, user_id)
                        
                        if not df_resultado.empty:
                            st.success(f"✅ Usuario encontrado")
                            
                            # Mostrar datos
                            st.dataframe(
                                df_resultado,
                                use_container_width=True,
                                hide_index=True
                            )
                            
                            # Mostrar historial
                            st.subheader(f"📜 Historial de {df_resultado.iloc[0]['nombre']}")
                            
                            df_historial = obtener_historial_usuario(supabase, user_id)
                            if not df_historial.empty:
                                st.dataframe(
                                    df_historial,
                                    use_container_width=True,
                                    hide_index=True
                                )
                            else:
                                st.info("No hay historial disponible")
                        else:
                            st.warning("❌ No se encontró usuario con ese ID")
                else:
                    st.warning("⚠️ Por favor ingresa un ID")
    
    elif opcion == "📊 Dashboard Global":
        st.header("📊 Dashboard Global")
        
        with st.spinner("Cargando métricas..."):
            metricas = obtener_metricas_globales(supabase)
            
            if metricas:
                # Métricas principales
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("👥 Total Usuarios", f"{metricas['total_usuarios']:,}")
                
                with col2:
                    st.metric("✅ Usuarios que Cumplen", f"{metricas['total_cumplen']:,}")
                
                with col3:
                    st.metric("💎 Total Diamantes", f"{metricas['total_diamantes']:,.0f}")
                
                with col4:
                    st.metric("📋 Contratos Activos", f"{metricas['total_contratos']:,}")
                
                st.divider()
                
                # Porcentaje de cumplimiento
                if metricas['total_usuarios'] > 0:
                    porcentaje = (metricas['total_cumplen'] / metricas['total_usuarios']) * 100
                    st.subheader(f"📈 Tasa de Cumplimiento: {porcentaje:.1f}%")
                    st.progress(porcentaje / 100)
                
                st.divider()
                
                # Distribución por contratos
                st.subheader("📊 Distribución de Usuarios por Contrato")
                df_dist = obtener_distribucion_contratos(supabase)
                
                if not df_dist.empty:
                    col_tabla, col_grafico = st.columns([1, 1])
                    
                    with col_tabla:
                        st.dataframe(
                            df_dist,
                            use_container_width=True,
                            hide_index=True
                        )
                    
                    with col_grafico:
                        fig = px.pie(
                            df_dist,
                            values='Usuarios',
                            names='Contrato',
                            title='Distribución por Contrato'
                        )
                        st.plotly_chart(fig, use_container_width=True)
    
    elif opcion == "📋 Ver Todos los Contratos":
        st.header("📋 Todos los Contratos")
        
        with st.spinner("Cargando contratos..."):
            df_contratos = obtener_todos_contratos(supabase)
            
            if not df_contratos.empty:
                st.success(f"✅ Total de contratos: {len(df_contratos)}")
                
                # Filtros
                col1, col2 = st.columns(2)
                
                with col1:
                    filtro_activo = st.selectbox(
                        "Filtrar por estado:",
                        ["Todos", "Activos", "Inactivos"]
                    )
                
                # Aplicar filtros
                df_filtrado = df_contratos.copy()
                
                if filtro_activo == "Activos":
                    df_filtrado = df_filtrado[df_filtrado['activo'] == True]
                elif filtro_activo == "Inactivos":
                    df_filtrado = df_filtrado[df_filtrado['activo'] == False]
                
                st.dataframe(
                    df_filtrado,
                    use_container_width=True,
                    hide_index=True
                )
                
                # Opción de descargar
                csv = df_filtrado.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Descargar CSV",
                    data=csv,
                    file_name=f"contratos_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No hay contratos disponibles")
    
    elif opcion == "💾 Consulta SQL Personalizada":
        st.header("💾 Consulta SQL Personalizada")
        
        st.warning("⚠️ **Modo Avanzado** - Ten cuidado con las consultas que ejecutes")
        
        # Ejemplos de consultas
        with st.expander("📖 Ver ejemplos de consultas"):
            st.code("""
-- Total de usuarios por contrato
SELECT contrato, COUNT(*) as total
FROM usuarios_tiktok
GROUP BY contrato
ORDER BY total DESC;

-- Usuarios con más diamantes
SELECT nombre, diamantes, contrato
FROM usuarios_tiktok
ORDER BY diamantes DESC
LIMIT 10;

-- Usuarios que cumplen nivel 3
SELECT nombre, dias, horas, nivel, contrato
FROM usuarios_tiktok
WHERE nivel = 3
ORDER BY diamantes DESC;
            """, language="sql")
        
        # Input de consulta
        consulta = st.text_area(
            "Escribe tu consulta SQL:",
            height=200,
            placeholder="SELECT * FROM usuarios_tiktok LIMIT 10;"
        )
        
        if st.button("▶️ Ejecutar Consulta"):
            if consulta:
                try:
                    with st.spinner("Ejecutando consulta..."):
                        # Ejecutar consulta directa
                        response = supabase.rpc("execute_sql", {"query": consulta}).execute()
                        
                        if response.data:
                            df_resultado = pd.DataFrame(response.data)
                            
                            st.success(f"✅ Consulta ejecutada - {len(df_resultado)} resultados")
                            
                            st.dataframe(
                                df_resultado,
                                use_container_width=True,
                                hide_index=True
                            )
                            
                            # Descargar resultados
                            csv = df_resultado.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label="📥 Descargar Resultados",
                                data=csv,
                                file_name=f"consulta_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv"
                            )
                        else:
                            st.info("La consulta no devolvió resultados")
                            
                except Exception as e:
                    st.error(f"❌ Error al ejecutar consulta: {str(e)}")
                    st.info("💡 Verifica que la función RPC 'execute_sql' esté creada en Supabase")
            else:
                st.warning("⚠️ Por favor escribe una consulta SQL")

if __name__ == "__main__":
    main()
