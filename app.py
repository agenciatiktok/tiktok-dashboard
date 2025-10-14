
# ============================================================================
# app.py - Sistema Completo TikTok Live (versión saneada)
# Pantalla pública + Login Admin + Login Agente + Vista Jugadores
# ----------------------------------------------------------------------------
# Nota: Esta versión corrige errores de indentación y strings sin cerrar,
# elimina secciones truncadas y conserva la lógica base (tokens + vistas).
# ============================================================================

import os
from datetime import datetime

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client
import plotly.graph_objects as go

# ------------------------- Carga de entorno y página ------------------------
load_dotenv()

st.set_page_config(page_title="Sistema TikTok Live", page_icon="📊", layout="wide")

# ------------------------------- Estilos -----------------------------------
st.markdown(
    """
    <style>
    :root { --tiktok-black:#000; --tiktok-cyan:#00f2ea; --tiktok-pink:#fe2c55; --tiktok-white:#fff; }
    .stApp { background:#000; }
    h1, h2, h3 { color: var(--tiktok-cyan) !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------- Conexión a Supabase ----------------------------
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

# ------------------------------ Utilidades ----------------------------------
def obtener_mes_espanol(fecha_str: str) -> str:
    meses = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
        7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }
    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
        return f"{meses[fecha.month]} {fecha.year}"
    except Exception:
        return fecha_str

def determinar_nivel(dias, horas) -> int:
    try: d = float(dias)
    except: d = 0
    try: h = float(horas)
    except: h = 0
    if d >= 20 and h >= 40: return 3
    if d >= 14 and h >= 30: return 2
    if d >= 7  and h >= 15: return 1
    return 0

def obtener_periodos_disponibles():
    sb = get_supabase()
    # retry simple
    for _ in range(3):
        try:
            res = sb.table("usuarios_tiktok").select("fecha_datos").execute()
            if res.data:
                fechas = sorted({r["fecha_datos"] for r in res.data}, reverse=True)
                return list(fechas)
            return []
        except Exception:
            pass
    st.error("❌ No fue posible consultar periodos en Supabase.")
    return []

def obtener_incentivos_df():
    sb = get_supabase()
    try:
        r = sb.table("incentivos_horizontales").select("*").order("acumulado").execute()
        return pd.DataFrame(r.data) if r.data else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def calcular_incentivos(df_inc: pd.DataFrame, diamantes: float, nivel: int):
    if df_inc.empty or nivel == 0 or (diamantes or 0) <= 0:
        return 0, 0
    fila = df_inc[df_inc["acumulado"] <= diamantes].sort_values("acumulado", ascending=False)
    if fila.empty: return 0, 0
    fila = fila.iloc[0]
    return (
        fila.get(f"nivel_{nivel}_monedas", 0) or 0,
        fila.get(f"nivel_{nivel}_paypal", 0) or 0,
    )

def obtener_datos_contrato(contrato: str, fecha_datos: str) -> pd.DataFrame:
    sb = get_supabase()

    # banderita nivel1_tabla3
    nivel1_tabla3 = False
    try:
        cfg = sb.table("contratos").select("*").eq("codigo", contrato).execute()
        if cfg.data:
            v = cfg.data[0].get("nivel1_tabla3", False)
            if isinstance(v, str):
                nivel1_tabla3 = v.strip().lower() in {"si","sí","true","1","yes"}
            else:
                nivel1_tabla3 = bool(v)
    except Exception:
        pass

    r = sb.table("usuarios_tiktok").select("*").eq("contrato", contrato).eq("fecha_datos", fecha_datos).execute()
    if not r.data:
        return pd.DataFrame()

    df = pd.DataFrame(r.data).copy()
    if "horas" not in df.columns:
        df["horas"] = 0

    df["nivel_original"] = df.apply(lambda r: determinar_nivel(r.get("dias",0), r.get("horas",0)), axis=1)
    df["cumple"] = df["nivel_original"].apply(lambda n: "SI" if n>0 else "NO")

    df_inc = obtener_incentivos_df()

    def _calc(row):
        n0 = row["nivel_original"]
        n = 3 if (nivel1_tabla3 and n0>=1) else n0
        coins, pp = calcular_incentivos(df_inc, row.get("diamantes",0) or 0, n)
        return n, coins, pp

    tmp = df.apply(_calc, axis=1, result_type="expand")
    df["nivel"] = tmp[0]
    df["incentivo_coins"] = tmp[1]
    df["incentivo_paypal"] = tmp[2]
    df.loc[df["cumple"]=="NO", ["incentivo_coins","incentivo_paypal"]] = 0

    # paypal_bruto desde reportes_contratos
    try:
        rep = sb.table("reportes_contratos").select("usuario_id, paypal_bruto").eq("contrato", contrato).eq("periodo", fecha_datos).execute()
        if rep.data:
            drep = pd.DataFrame(rep.data)
            df["id_tiktok_str"] = df["id_tiktok"].astype(str)
            drep["usuario_id_str"] = (drep["usuario_id"]).astype(str)
            mapa = dict(zip(drep["usuario_id_str"], drep["paypal_bruto"]))
            df["paypal_bruto"] = df["id_tiktok_str"].map(mapa).fillna(0)
            df.drop(columns=["id_tiktok_str"], inplace=True)
        else:
            df["paypal_bruto"] = 0
    except Exception:
        df["paypal_bruto"] = 0

    return df

# ------------------------------ Vistas --------------------------------------
def vista_publica():
    st.title("🎵 Sistema de Gestión TikTok Live")
    st.markdown("Sistema de consulta de métricas, diamantes, niveles e incentivos.")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔐 Administración")
        token_admin = st.text_input("Token de Administrador:", type="password", key="tok_admin")
        if st.button("Acceder como Administrador"):
            td = verificar_token_admin(token_admin) if token_admin else None
            if td:
                st.session_state["modo"] = "admin"
                st.session_state["token_data"] = td
                st.rerun()
            else:
                st.error("Token inválido")

    with col2:
        st.subheader("👔 Agente")
        usuario = st.text_input("Usuario:", key="usr_ag")
        password = st.text_input("Contraseña:", type="password", key="pwd_ag")
        if st.button("Acceder como Agente"):
            ag = verificar_login_agente(usuario, password) if usuario and password else None
            if ag:
                st.session_state["modo"] = "agente"
                st.session_state["agente"] = ag
                st.rerun()
            else:
                st.error("Usuario/contraseña inválidos")

def verificar_token_admin(token):
    if not token: return None
    sb = get_supabase()
    r = sb.table("contratos_tokens").select("*").eq("token", token).eq("activo", True).execute()
    if r.data and r.data[0].get("tipo","contrato")=="admin":
        return r.data[0]
    return None

def verificar_token_contrato(token):
    if not token: return None
    sb = get_supabase()
    r = sb.table("contratos_tokens").select("*").eq("token", token).eq("activo", True).execute()
    if r.data and r.data[0].get("tipo","contrato")=="contrato":
        return r.data[0]
    return None

def verificar_login_agente(usuario, password):
    sb = get_supabase()
    r = (sb.table("agentes_login").select("*").eq("usuario", usuario).eq("password", password).eq("activo", True).execute())
    if r.data: return r.data[0]
    return None

def vista_jugadores(token_data: dict):
    contrato = token_data.get("contrato") or token_data.get("codigo") or "A001"
    st.subheader(f"Contrato: {contrato}")
    periodos = obtener_periodos_disponibles()
    if not periodos:
        st.warning("Sin datos disponibles.")
        return
    periodo = st.selectbox("Periodo", periodos, format_func=obtener_mes_espanol)
    df = obtener_datos_contrato(contrato, periodo)
    if df.empty:
        st.warning("No hay registros para este contrato en el periodo seleccionado.")
        return

    # KPIs
    total = len(df)
    cumplen = int((df["cumple"]=="SI").sum())
    colA,colB,colC = st.columns(3)
    with colA: st.metric("Usuarios", total)
    with colB: st.metric("Cumplen (≥7d & ≥15h)", cumplen)
    with colC: st.metric("Diamantes totales", int(df["diamantes"].fillna(0).sum()))

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🔎 Tabla", "✅ Cumplen", "❌ No cumplen", "📈 Métricas"])

    with tab1:
        cols = [c for c in ["usuario","dias","horas","diamantes","nivel","cumple","incentivo_coins","incentivo_paypal","paypal_bruto"] if c in df.columns]
        st.dataframe(df[cols].sort_values("diamantes", ascending=False), use_container_width=True, hide_index=True)

    with tab2:
        d = df[df["cumple"]=="SI"]
        st.dataframe(d[cols].sort_values("diamantes", ascending=False), use_container_width=True, hide_index=True)

    with tab3:
        d = df[df["cumple"]=="NO"]
        st.dataframe(d[cols].sort_values("diamantes", ascending=False), use_container_width=True, hide_index=True)

    with tab4:
        # Pie por niveles
        counts = df["nivel"].value_counts().to_dict()
        labels, values, colors = [], [], []
        if counts.get(3,0): labels.append("Nivel 3"); values.append(counts[3]); colors.append("#FFD700")
        if counts.get(2,0): labels.append("Nivel 2"); values.append(counts[2]); colors.append("#C0C0C0")
        if counts.get(1,0): labels.append("Nivel 1"); values.append(counts[1]); colors.append("#CD7F32")
        if counts.get(0,0): labels.append("Nivel 0"); values.append(counts[0]); colors.append("#6c757d")
        fig = go.Figure(data=[go.Pie(labels=labels, values=values, marker=dict(colors=colors))])
        fig.update_layout(height=400, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

# ------------------------------- Main ---------------------------------------
def main():
    # Soporta token en URL tipo ?token=XYZ
    token_url = st.query_params.get("token")
    if token_url:
        td = verificar_token_admin(token_url)
        if td:
            st.session_state["modo"] = "admin"
            st.session_state["token_data"] = td
        else:
            tc = verificar_token_contrato(token_url)
            if tc:
                st.session_state["modo"] = "jugadores"
                st.session_state["token_data"] = tc
            else:
                st.error("Token inválido")

    modo = st.session_state.get("modo")
    if not modo:
        vista_publica()
        return

    if modo == "jugadores":
        vista_jugadores(st.session_state["token_data"])
        return

    if modo == "admin":
        st.subheader("Panel de Administración (en construcción)")
        st.info("Acceso confirmado. Usa un token de contrato en la URL para ver jugadores.")
        return

    if modo == "agente":
        st.subheader("Panel de Agente (en construcción)")
        st.info("Próximamente: listado de contratos del agente.")
        return

if __name__ == "__main__":
    main()
