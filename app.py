# ============================================================================
# app.py - Sistema Completo TikTok Live
# Ruta pública por token de contrato + Login Admin/Agente
# ============================================================================

import os
from datetime import datetime

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client
import plotly.graph_objects as go

# ----------------------------------------------------------------------------
# Carga de .env y configuración de página
# ----------------------------------------------------------------------------
load_dotenv()

st.set_page_config(
    page_title="Sistema TikTok Live",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto",
)

# ----------------------------------------------------------------------------
# Estilos (igual a tu base, sin tocar lógica de negocio)
# ----------------------------------------------------------------------------
st.markdown(
    """
<style>
:root {
    --tiktok-black: #000000;
    --tiktok-cyan: #00f2ea;
    --tiktok-pink: #fe2c55;
    --tiktok-white: #ffffff;
}
.stApp { background-color: var(--tiktok-black); }
.stMetric {
    background: linear-gradient(135deg, var(--tiktok-cyan) 0%, var(--tiktok-pink) 100%);
    padding: 15px; border-radius: 10px; color: var(--tiktok-white);
}
.stMetric label { color: var(--tiktok-white) !important; font-weight: bold; }
.stMetric [data-testid="stMetricValue"] {
    color: var(--tiktok-white); font-size: 28px; font-weight: bold;
}
h1, h2, h3 { color: var(--tiktok-cyan) !important; text-shadow: 2px 2px 4px rgba(254, 44, 85, 0.3); }
div[data-testid="stDataFrame"] td, div[data-testid="stDataFrame"] th { text-align: center !important; }
hr { background: linear-gradient(90deg, var(--tiktok-cyan) 0%, var(--tiktok-pink) 100%); height: 3px; border: none; }
.stButton > button {
    background: linear-gradient(135deg, var(--tiktok-cyan) 0%, var(--tiktok-pink) 100%);
    color: white; border: none; padding: 12px 24px; border-radius: 8px; font-weight: bold; font-size: 16px;
}
.stButton > button:hover {
    background: linear-gradient(135deg, var(--tiktok-pink) 0%, var(--tiktok-cyan) 100%);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}
.whatsapp-button {
    background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
    color: #000000 !important; padding: 12px 24px; border-radius: 25px; text-decoration: none;
    display: inline-flex; align-items: center; gap: 10px; font-weight: bold; font-size: 16px;
    box-shadow: 0 4px 6px rgba(37, 211, 102, 0.3);
}
.whatsapp-button:hover { transform: translateY(-2px); box-shadow: 0 6px 12px rgba(37, 211, 102, 0.4); }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #1a1a1a 0%, #0a0a0a 100%); }
</style>
""",
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# Conexión Supabase (misma lógica)
# ----------------------------------------------------------------------------
@st.cache_resource
def get_supabase():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_SERVICE_KEY"]
    except Exception:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        st.error("❌ Error: Credenciales de Supabase no configuradas")
        st.stop()
    return create_client(url, key)

# ----------------------------------------------------------------------------
# Autenticaciones (misma lógica)
# ----------------------------------------------------------------------------
def verificar_token_admin(token: str):
    supabase = get_supabase()
    r = supabase.table("contratos_tokens").select("*").eq("token", token).eq("activo", True).execute()
    if r.data:
        d = r.data[0]
        if d.get("tipo", "contrato") == "admin":
            return d
    return None

def verificar_token_contrato(token: str):
    supabase = get_supabase()
    r = supabase.table("contratos_tokens").select("*").eq("token", token).eq("activo", True).execute()
    if r.data:
        d = r.data[0]
        if d.get("tipo", "contrato") == "contrato":
            return d
    return None

def verificar_login_agente(usuario: str, password: str):
    supabase = get_supabase()
    r = (
        supabase.table("agentes_login")
        .select("*")
        .eq("usuario", usuario)
        .eq("password", password)
        .eq("activo", True)
        .execute()
    )
    if r.data:
        return r.data[0]
    return None

# ----------------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------------
def obtener_periodos_disponibles():
    supabase = get_supabase()
    r = supabase.table("usuarios_tiktok").select("fecha_datos").execute()
    if r.data:
        fechas = sorted(list(set([row["fecha_datos"] for row in r.data])), reverse=True)
        return fechas
    return []

def determinar_nivel(dias, horas):
    try:
        d = float(dias)
    except Exception:
        d = 0
    try:
        h = float(horas)
    except Exception:
        h = 0
    if d >= 20 and h >= 40:
        return 3
    if d >= 14 and h >= 30:
        return 2
    if d >= 7 and h >= 15:
        return 1
    return 0

def obtener_incentivos_df():
    supabase = get_supabase()
    r = supabase.table("incentivos_horizontales").select("*").order("acumulado").execute()
    if r.data:
        return pd.DataFrame(r.data)
    return pd.DataFrame()

def calcular_incentivos(df_inc, diamantes, nivel):
    if nivel == 0 or (diamantes or 0) <= 0:
        return (0, 0)
    fila = df_inc[df_inc["acumulado"] <= diamantes].sort_values("acumulado", ascending=False)
    if fila.empty:
        return (0, 0)
    f = fila.iloc[0]
    coins = f.get(f"nivel_{nivel}_monedas", 0)
    paypal = f.get(f"nivel_{nivel}_paypal", 0)
    return (coins or 0, paypal or 0)

def crear_grafico_pastel(nivel_counts):
    labels, values, colors = [], [], []
    if nivel_counts.get(3, 0) > 0:
        labels.append("🥇 Nivel 3"); values.append(nivel_counts.get(3, 0)); colors.append("#FFD700")
    if nivel_counts.get(2, 0) > 0:
        labels.append("🥈 Nivel 2"); values.append(nivel_counts.get(2, 0)); colors.append("#C0C0C0")
    if nivel_counts.get(1, 0) > 0:
        labels.append("🥉 Nivel 1"); values.append(nivel_counts.get(1, 0)); colors.append("#CD7F32")
    if nivel_counts.get(0, 0) > 0:
        labels.append("⚫ Nivel 0"); values.append(nivel_counts.get(0, 0)); colors.append("#6c757d")
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.4)])
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=20, b=10), paper_bgcolor="rgba(0,0,0,0)")
    return fig

# ----------------------------------------------------------------------------
# Carga de datos del contrato (igual a tu base)
# ----------------------------------------------------------------------------
def obtener_datos_contrato(contrato: str, fecha_datos: str) -> pd.DataFrame:
    supabase = get_supabase()

    # Config del contrato (nivel1_tabla3)
    nivel1_tabla3 = False
    conf = supabase.table("contratos").select("*").eq("codigo", contrato).execute()
    if conf.data:
        valor = conf.data[0].get("nivel1_tabla3", False)
        if isinstance(valor, str):
            nivel1_tabla3 = valor.upper() in ["SI", "YES", "TRUE", "1", "SÍ"]
        else:
            nivel1_tabla3 = bool(valor)

    # Datos base
    r = (
        supabase.table("usuarios_tiktok")
        .select("*")
        .eq("contrato", contrato)
        .eq("fecha_datos", fecha_datos)
        .execute()
    )
    if not r.data:
        return pd.DataFrame()

    df = pd.DataFrame(r.data)

    # Relleno de nombre desde histórico cuando falte
    mask = df["usuario"].isna() | (df["usuario"].astype(str).str.strip() == "")
    if mask.any():
        ids = df.loc[mask, "id_tiktok"].astype(str).unique().tolist()
        try:
            h = (
                supabase.table("historico_usuarios")
                .select("id_tiktok, usuario_1, usuario_2, usuario_3")
                .in_("id_tiktok", ids)
                .execute()
            )
            if h.data:
                name_map = {}
                for row in h.data:
                    tid = str(row["id_tiktok"])
                    cand = None
                    for col in ["usuario_1", "Usuario_1", "usuario_2", "Usuario_2", "usuario_3", "Usuario_3"]:
                        v = row.get(col, "")
                        if v and str(v).strip().lower() not in ["", "nan", "none", "null"]:
                            cand = str(v).strip(); break
                    name_map[tid] = cand or f"Usuario_{tid[:8]}"
                def _fill(row):
                    if pd.isna(row["usuario"]) or str(row["usuario"]).strip() == "":
                        return name_map.get(str(row["id_tiktok"]), f"Usuario_{str(row['id_tiktok'])[:8]}")
                    return row["usuario"]
                df["usuario"] = df.apply(_fill, axis=1)
        except Exception:
            pass

    if "horas" not in df.columns:
        df["horas"] = 0

    df["nivel_original"] = df.apply(lambda r: determinar_nivel(r.get("dias", 0), r.get("horas", 0)), axis=1)
    df["cumple"] = df["nivel_original"].apply(lambda n: "SI" if n > 0 else "NO")

    inc = obtener_incentivos_df()
    if not inc.empty:
        def _calc(row):
            base = row["nivel_original"]
            nivel = 3 if (nivel1_tabla3 and base >= 1) else base
            return calcular_incentivos(inc, row.get("diamantes", 0), nivel)
        par = df.apply(_calc, axis=1, result_type="expand")
        df["incentivo_coins"] = par[0]; df["incentivo_paypal"] = par[1]
        df["nivel"] = df["nivel_original"].where(~(nivel1_tabla3 & (df["nivel_original"] >= 1)), 3)
    else:
        df["incentivo_coins"] = 0; df["incentivo_paypal"] = 0; df["nivel"] = df["nivel_original"]

    df.loc[df["cumple"] == "NO", ["incentivo_coins", "incentivo_paypal"]] = 0

    # paypal_bruto desde reportes_contratos (usa 'periodo')
    try:
        rep = (
            supabase.table("reportes_contratos")
            .select("usuario_id, paypal_bruto")
            .eq("contrato", contrato)
            .eq("periodo", fecha_datos)
            .execute()
        )
        if rep.data:
            m = pd.DataFrame(rep.data)
            df["id_tiktok_str"] = df["id_tiktok"].astype(str)
            m["usuario_id_str"] = m["usuario_id"].astype(str)
            pmap = dict(zip(m["usuario_id_str"], m["paypal_bruto"]))
            df["paypal_bruto"] = df["id_tiktok_str"].map(pmap).fillna(0)
            df.drop(columns=["id_tiktok_str"], inplace=True, errors="ignore")
        else:
            df["paypal_bruto"] = 0
    except Exception:
        df["paypal_bruto"] = 0

    return df

# ----------------------------------------------------------------------------
# UI: Pantalla pública (dos logins)
# ----------------------------------------------------------------------------
def mostrar_pantalla_publica():
    col_logo, col_titulo = st.columns([1, 4])
    with col_logo:
        st.image("https://img.icons8.com/color/96/000000/tiktok--v1.png", width=100)
    with col_titulo:
        st.title("🎵 Sistema de Gestión TikTok Live")
        st.markdown("### Bienvenido al sistema de consultas")

    st.divider()

    st.markdown("### 🔐 Opciones de Acceso")

    col1, col2 = st.columns(2)

    with col1:
        html_admin = """
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
        """
        st.markdown(html_admin, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        token_admin = st.text_input("Token de Administrador:", type="password", key="input_token_admin")
        if st.button("🔓 Acceder como Administrador", key="btn_admin", kwargs=None):
            if token_admin:
                td = verificar_token_admin(token_admin)
                if td:
                    st.session_state["modo"] = "admin"
                    st.session_state["token_data"] = td
                    st.rerun()
                else:
                    st.error("❌ Token de administrador inválido")
            else:
                st.warning("⚠️ Ingresa tu token")

    with col2:
        html_agente = """
        <div style='background: linear-gradient(135deg, #00f2ea 0%, #fe2c55 100%);
                    padding: 30px; border-radius: 15px; text-align: center;'>
            <h2 style='color: white; margin: 0;'>👔 AGENTE</h2>
            <p style='color: white; margin: 10px 0;'>Gestión de tu contrato</p>
            <ul style='color: white; text-align: left; padding-left: 20px;'>
                <li>Ver todos tus usuarios</li>
                <li>Consultar métricas</li>
                <li>Revisar incentivos</li>
                <li>Descargar reportes</li>
            </ul>
        </div>
        """
        st.markdown(html_agente, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        usuario_agente = st.text_input("Usuario de Agente:", key="input_usuario_agente")
        password_agente = st.text_input("Contraseña:", type="password", key="input_password_agente")

        if st.button("👔 Acceder como Agente", key="btn_agente", kwargs=None):
            if usuario_agente and password_agente:
                agente = verificar_login_agente(usuario_agente, password_agente)
                if agente:
                    st.session_state["modo"] = "agente"
                    st.session_state["agente"] = agente
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña inválidos")
            else:
                st.warning("⚠️ Completa usuario y contraseña")

# ----------------------------------------------------------------------------
# UI: Vista pública de jugadores (por token de contrato en URL)
# ----------------------------------------------------------------------------
def mostrar_vista_jugadores(token_data: dict):
    contrato = token_data.get("contrato") or token_data.get("codigo") or token_data.get("contrato_codigo")
    st.title(f"📄 Contrato {contrato} – Vista pública")

    periodos = obtener_periodos_disponibles()
    if not periodos:
        st.warning("⚠️ Sin datos")
        return

    periodo = st.selectbox("Periodo", periodos, index=0)
    df = obtener_datos_contrato(contrato, periodo)
    if df.empty:
        st.info("Sin registros para el periodo seleccionado.")
        return

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Todos", "✅ Cumplen", "❌ No cumplen", "📊 Resumen"])

    with tab1:
        st.caption(f"📊 {len(df)} usuarios")
        st.dataframe(df.sort_values("diamantes", ascending=False), use_container_width=True)

    with tab2:
        df_ok = df[df["cumple"] == "SI"].copy()
        st.caption(f"✅ Cumplen: {len(df_ok)}")
        st.dataframe(df_ok.sort_values("diamantes", ascending=False), use_container_width=True)

    with tab3:
        df_no = df[df["cumple"] == "NO"].copy()
        st.caption(f"❌ No cumplen: {len(df_no)}")
        st.dataframe(df_no.sort_values("diamantes", ascending=False), use_container_width=True)

    with tab4:
        counts = df["nivel"].value_counts().to_dict()
        st.plotly_chart(crear_grafico_pastel(counts), use_container_width=True)

# ----------------------------------------------------------------------------
# UI: Panel de agente (una sola versión de tabs, sin duplicados)
# ----------------------------------------------------------------------------
def mostrar_vista_agente(agente_data: dict):
    st.title("👔 Panel del Agente")
    contrato = agente_data.get("contrato") or agente_data.get("codigo") or agente_data.get("contrato_codigo")

    if not contrato:
        st.info("Este agente no tiene contrato asociado en el registro.")
        return

    periodos = obtener_periodos_disponibles()
    if not periodos:
        st.warning("⚠️ Sin datos disponibles")
        return

    periodo = st.selectbox("Periodo", periodos, index=0, key="periodo_agente")
    df = obtener_datos_contrato(contrato, periodo)

    tab1, tab2, tab3, tab4 = st.tabs(["📋 Todos", "✅ Cumplen", "📝 Notas del periodo", "📊 Resumen"])

    with tab1:
        st.caption(f"📊 {len(df)} usuarios")
        if not df.empty:
            st.dataframe(df.sort_values("diamantes", ascending=False), use_container_width=True)
        else:
            st.info("Sin datos para este periodo.")

    with tab2:
        if not df.empty:
            df_ok = df[df["cumple"] == "SI"].copy()
            st.caption(f"✅ Cumplen: {len(df_ok)}")
            st.dataframe(df_ok.sort_values("diamantes", ascending=False), use_container_width=True)
        else:
            st.info("Sin datos para este periodo.")

    with tab3:
        supabase = get_supabase()
        try:
            rep = (
                supabase.table("reportes_contratos")
                .select("usuario_id, paypal_bruto, notas, periodo")
                .eq("contrato", contrato)
                .eq("periodo", periodo)  # unificado a 'periodo'
                .execute()
            )
            if rep.data:
                st.dataframe(pd.DataFrame(rep.data), use_container_width=True)
            else:
                st.info("Sin notas para el periodo.")
        except Exception as e:
            st.error(f"Error al cargar notas: {e}")

    with tab4:
        if not df.empty:
            counts = df["nivel"].value_counts().to_dict()
            st.plotly_chart(crear_grafico_pastel(counts), use_container_width=True)
        else:
            st.info("Sin datos para este periodo.")

# ----------------------------------------------------------------------------
# UI: Panel admin (mínimo y estable; no se altera tu lógica)
# ----------------------------------------------------------------------------
def mostrar_panel_admin(token_data: dict):
    st.title("🔐 Panel de Administración")
    st.info("Panel de administración activo. (Contenido operativo según tus consultas.)")

# ----------------------------------------------------------------------------
# MAIN ROUTER: respeta tu flujo exacto
# ----------------------------------------------------------------------------
def main():
    # 1) Si hay token en URL y es de contrato, mostrar vista pública del contrato
    params = st.query_params
    token_url = params.get("token", [None])
    token_url = token_url[0] if isinstance(token_url, list) else token_url

    if token_url:
        td = verificar_token_contrato(token_url)
        if td:
            mostrar_vista_jugadores(td)
            return
        else:
            st.error("❌ Token inválido o inactivo.")
            st.stop()

    # 2) Sesión persistente (admin/agente)
    modo = st.session_state.get("modo")
    if modo == "admin":
        mostrar_panel_admin(st.session_state.get("token_data", {}))
        return
    if modo == "agente":
        mostrar_vista_agente(st.session_state.get("agente", {}))
        return

    # 3) Sin token y sin sesión -> pantalla pública con logins
    mostrar_pantalla_publica()


if __name__ == "__main__":
    main()
