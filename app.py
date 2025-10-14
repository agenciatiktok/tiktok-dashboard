# ============================================================================
# app.py - TikTok Live: Vista pública por token + login Admin/Agente
# Basado en la lógica de tu app5, con ocultamiento de columnas desde BD.
# ============================================================================

import os
import pandas as pd
import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
import plotly.graph_objects as go

# ----------------------------------------------------------------------------
# Setup
# ----------------------------------------------------------------------------
load_dotenv()

st.set_page_config(
    page_title="Sistema TikTok Live",
    page_icon="📊",
    layout="wide",
)

# ----------------------------------------------------------------------------
# Estilos (sin tocar tu lógica de negocio)
# ----------------------------------------------------------------------------
st.markdown("""
<style>
:root { --tiktok-black:#000; --tiktok-cyan:#00f2ea; --tiktok-pink:#fe2c55; --tiktok-white:#fff; }
.stApp{background:#000;}
h1,h2,h3{color:var(--tiktok-cyan)!important;text-shadow:2px 2px 4px rgba(254,44,85,.3);}
div[data-testid="stDataFrame"] td,div[data-testid="stDataFrame"] th{ text-align:center!important;}
.stButton>button{background:linear-gradient(135deg,#00f2ea 0%,#fe2c55 100%);color:#fff;border:none;padding:10px 18px;border-radius:10px;font-weight:600;}
.stButton>button:hover{filter:brightness(1.1);}
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# Conexión Supabase
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
        st.error("❌ Falta SUPABASE_URL / SUPABASE_SERVICE_KEY")
        st.stop()
    return create_client(url, key)

# ----------------------------------------------------------------------------
# Auth (igual espíritu que app5)
# ----------------------------------------------------------------------------
def verificar_token_contrato(token: str):
    sb = get_supabase()
    r = sb.table("contratos_tokens").select("*").eq("token", token).eq("activo", True).execute()
    if r.data:
        d = r.data[0]
        return d if d.get("tipo", "contrato") == "contrato" else None
    return None

def verificar_token_admin(token: str):
    sb = get_supabase()
    r = sb.table("contratos_tokens").select("*").eq("token", token).eq("activo", True).execute()
    if r.data:
        d = r.data[0]
        return d if d.get("tipo", "") == "admin" else None
    return None

def verificar_login_agente(usuario: str, password: str):
    sb = get_supabase()
    r = (sb.table("agentes_login").select("*")
         .eq("usuario", usuario).eq("password", password).eq("activo", True).execute())
    if r.data: return r.data[0]
    return None

# ----------------------------------------------------------------------------
# Utilidades de datos
# ----------------------------------------------------------------------------
def obtener_periodos_disponibles():
    sb = get_supabase()
    r = sb.table("usuarios_tiktok").select("fecha_datos").execute()
    if not r.data: return []
    return sorted({row["fecha_datos"] for row in r.data}, reverse=True)

def determinar_nivel(dias, horas):
    try: d = float(dias)
    except: d = 0
    try: h = float(horas)
    except: h = 0
    if d >= 20 and h >= 40: return 3
    if d >= 14 and h >= 30: return 2
    if d >= 7  and h >= 15: return 1
    return 0

def obtener_incentivos_df():
    sb = get_supabase()
    r = sb.table("incentivos_horizontales").select("*").order("acumulado").execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()

def calcular_incentivos(df_inc, diamantes, nivel):
    if nivel == 0 or (diamantes or 0) <= 0: return (0, 0)
    fila = df_inc[df_inc["acumulado"] <= diamantes].sort_values("acumulado", ascending=False)
    if fila.empty: return (0, 0)
    f = fila.iloc[0]
    return (f.get(f"nivel_{nivel}_monedas", 0) or 0, f.get(f"nivel_{nivel}_paypal", 0) or 0)

# ----------------------------------------------------------------------------
# Ocultar columnas (como en app5: obtiene reglas de una tabla)
# ----------------------------------------------------------------------------
@st.cache_data(ttl=300)
def _leer_reglas_ocultas():
    """
    Lee config_columnas_ocultas:
      - contrato (nullable) → reglas globales si es NULL
      - columna (texto) → token ('coins','paypal','sueldo') o nombre real ('id', 'id_tiktok', etc.)
    """
    sb = get_supabase()
    try:
        r = sb.table("config_columnas_ocultas").select("*").execute()
        return r.data or []
    except Exception:
        return []

def obtener_columnas_ocultas(contrato: str):
    """
    Devuelve lista de columnas a ocultar (tokens o nombres reales),
    combinando reglas globales (contrato NULL) + específicas del contrato.
    """
    reglas = _leer_reglas_ocultas()
    ocultas = []
    for row in reglas:
        c = row.get("contrato")
        col = str(row.get("columna", "")).strip()
        if not col: continue
        if c is None or str(c).strip() == "":
            ocultas.append(col)          # global
        elif str(c).strip() == str(contrato).strip():
            ocultas.append(col)          # específica
    return ocultas

def formatear_dataframe(df_input: pd.DataFrame, contrato: str) -> pd.DataFrame:
    """
    Selecciona columnas visibles y aplica reglas de ocultamiento.
    Tokens reconocidos: 'coins' → incentivo_coins,
                        'paypal' → incentivo_paypal,
                        'sueldo' → ['coins_bruto','paypal_bruto']
    Además: si hay nombres reales en la config, también se ocultan.
    """
    # columnas visibles por defecto (como tu app5)
    columnas_orden = [
        'usuario', 'agencia', 'dias', 'duracion', 'diamantes',
        'nivel', 'cumple', 'incentivo_coins', 'incentivo_paypal'
    ]

    # reglas de ocultamiento
    mapeo_tokens = {
        'coins': 'incentivo_coins',
        'paypal': 'incentivo_paypal',
        'sueldo': ['coins_bruto', 'paypal_bruto']
    }
    ocultas_cfg = set()
    for item in obtener_columnas_ocultas(contrato):
        key = item.lower()
        if key in mapeo_tokens:
            val = mapeo_tokens[key]
            ocultas_cfg.update(val if isinstance(val, list) else [val])
        else:
            # nombre real
            ocultas_cfg.add(item)

    # si la tabla de config no existe / está vacía → defaults para vista pública
    if not _leer_reglas_ocultas():
        ocultas_cfg.update(['agencia'])  # suele ocultarse en pública

    # columnas finales a mostrar, respetando orden
    columnas_mostrar = [c for c in columnas_orden if c in df_input.columns and c not in ocultas_cfg]
    df_show = df_input[columnas_mostrar].copy()

    # renombres y formatos
    ren = {
        'usuario':'Usuario','agencia':'Agencia','dias':'Días','duracion':'Horas',
        'diamantes':'Diamantes','nivel':'Nivel','cumple':'Cumple',
        'incentivo_coins':'Incentivo Coin','incentivo_paypal':'Incentivo PayPal'
    }
    df_show.rename(columns={k:v for k,v in ren.items() if k in df_show.columns}, inplace=True)

    if 'Diamantes' in df_show.columns:
        df_show['Diamantes'] = df_show['Diamantes'].apply(lambda x: f"{int(x):,}" if pd.notnull(x) else "0")
    if 'Días' in df_show.columns:
        df_show['Días'] = df_show['Días'].apply(lambda x: int(x) if pd.notnull(x) else 0)
    if 'Incentivo Coin' in df_show.columns:
        df_show['Incentivo Coin'] = df_show['Incentivo Coin'].apply(lambda x: f"{int(x):,}" if pd.notnull(x) and x>0 else "0")
    if 'Incentivo PayPal' in df_show.columns:
        df_show['Incentivo PayPal'] = df_show['Incentivo PayPal'].apply(lambda x: f"${float(x):,.2f}" if pd.notnull(x) and x>0 else "$0.00")

    return df_show

# ----------------------------------------------------------------------------
# Carga de datos del contrato (como en tu app original)
# ----------------------------------------------------------------------------
def obtener_datos_contrato(contrato: str, fecha_datos: str) -> pd.DataFrame:
    sb = get_supabase()

    # banderita nivel1_tabla3 en contratos
    nivel1_tabla3 = False
    conf = sb.table("contratos").select("*").eq("codigo", contrato).execute()
    if conf.data:
        v = conf.data[0].get("nivel1_tabla3", False)
        if isinstance(v, str):
            nivel1_tabla3 = v.upper() in ["SI","SÍ","TRUE","YES","1"]
        else:
            nivel1_tabla3 = bool(v)

    # usuarios del periodo
    r = (sb.table("usuarios_tiktok").select("*")
         .eq("contrato", contrato).eq("fecha_datos", fecha_datos).execute())
    if not r.data: return pd.DataFrame()
    df = pd.DataFrame(r.data)

    # asegurar horas
    if "horas" not in df.columns: df["horas"] = 0

    # nivel y cumple
    df["nivel_original"] = df.apply(lambda row: determinar_nivel(row.get("dias",0), row.get("horas",0)), axis=1)
    df["cumple"] = df["nivel_original"].apply(lambda n: "SI" if n>0 else "NO")

    # incentivos
    inc = obtener_incentivos_df()
    if not inc.empty:
        def _calc(row):
            base = row["nivel_original"]
            nivel = 3 if (nivel1_tabla3 and base>=1) else base
            return calcular_incentivos(inc, row.get("diamantes",0), nivel)
        par = df.apply(_calc, axis=1, result_type="expand")
        df["incentivo_coins"], df["incentivo_paypal"] = par[0], par[1]
        df["nivel"] = df["nivel_original"] if not nivel1_tabla3 else df["nivel_original"].apply(lambda n: 3 if n>=1 else 0)
    else:
        df["incentivo_coins"] = 0; df["incentivo_paypal"] = 0; df["nivel"] = df["nivel_original"]

    # si no cumple → cero incentivos
    df.loc[df["cumple"]=="NO", ["incentivo_coins","incentivo_paypal"]] = 0

    # sueldo (paypal_bruto) desde reportes_contratos (periodo)
    try:
        rep = (sb.table("reportes_contratos").select("usuario_id, paypal_bruto")
               .eq("contrato", contrato).eq("periodo", fecha_datos).execute())
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
# Gráfico
# ----------------------------------------------------------------------------
def grafico_niveles(df: pd.DataFrame):
    counts = df["nivel"].value_counts().to_dict() if "nivel" in df.columns else {}
    labels, values = [], []
    if counts.get(3,0): labels.append("🥇 Nivel 3"); values.append(counts[3])
    if counts.get(2,0): labels.append("🥈 Nivel 2"); values.append(counts[2])
    if counts.get(1,0): labels.append("🥉 Nivel 1"); values.append(counts[1])
    if counts.get(0,0): labels.append("⚫ Nivel 0"); values.append(counts[0])
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4)])
    fig.update_layout(height=360, margin=dict(l=10,r=10,t=20,b=10), paper_bgcolor="rgba(0,0,0,0)")
    return fig

# ----------------------------------------------------------------------------
# Pantallas
# ----------------------------------------------------------------------------
def vista_publica_contrato(token_data: dict):
    contrato = token_data.get("contrato") or token_data.get("codigo") or token_data.get("contrato_codigo")
    st.session_state["contrato_actual"] = contrato

    st.title(f"📄 Contrato {contrato} – Vista pública")

    periodos = obtener_periodos_disponibles()
    if not periodos:
        st.warning("Sin datos disponibles.")
        return

    periodo = st.selectbox("Periodo", periodos, index=0, key="periodo_publico")
    df = obtener_datos_contrato(contrato, periodo)
    if df.empty:
        st.info("Sin registros para el periodo seleccionado.")
        return

    tab1, tab2, tab3, tab4 = st.tabs(["📋 Todos", "✅ Cumplen", "❌ No cumplen", "📊 Resumen"])

    with tab1:
        st.caption(f"📊 {len(df)} usuarios")
        st.dataframe(formatear_dataframe(df.sort_values("diamantes", ascending=False), contrato),
                     use_container_width=True)

    with tab2:
        df_ok = df[df["cumple"]=="SI"].copy()
        st.caption(f"✅ Cumplen: {len(df_ok)}")
        st.dataframe(formatear_dataframe(df_ok.sort_values("diamantes", ascending=False), contrato),
                     use_container_width=True)

    with tab3:
        df_no = df[df["cumple"]=="NO"].copy()
        st.caption(f"❌ No cumplen: {len(df_no)}")
        st.dataframe(formatear_dataframe(df_no.sort_values("diamantes", ascending=False), contrato),
                     use_container_width=True)

    with tab4:
        st.plotly_chart(grafico_niveles(df), use_container_width=True)

def pantalla_login():
    st.title("🎵 Sistema de Gestión TikTok Live")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🔐 Administración")
        token_admin = st.text_input("Token de Administrador", type="password", key="token_admin")
        if st.button("Acceder como Admin"):
            td = verificar_token_admin(token_admin) if token_admin else None
            if td:
                st.session_state["modo"] = "admin"
                st.session_state["token_data"] = td
                st.rerun()
            else:
                st.error("Token inválido")

    with col2:
        st.subheader("👔 Agente")
        user = st.text_input("Usuario", key="u_agente")
        pwd = st.text_input("Contraseña", type="password", key="p_agente")
        if st.button("Acceder como Agente"):
            ag = verificar_login_agente(user, pwd) if (user and pwd) else None
            if ag:
                st.session_state["modo"] = "agente"
                st.session_state["agente"] = ag
                st.rerun()
            else:
                st.error("Usuario o contraseña inválidos")

def panel_admin():
    st.title("🔐 Panel de Administración")
    st.info("Placeholder de administración (sin romper el flujo).")

def panel_agente():
    st.title("👔 Panel del Agente")
    st.info("Placeholder del agente (puedes reusar las tablas formateadas si quieres).")

# ----------------------------------------------------------------------------
# Router principal (como en app5)
# ----------------------------------------------------------------------------
def main():
    # 1) Token en URL → vista pública del contrato
    params = st.query_params
    token_url = params.get("token", [None])
    token_url = token_url[0] if isinstance(token_url, list) else token_url
    if token_url:
        td = verificar_token_contrato(token_url)
        if td:
            vista_publica_contrato(td)
            return
        else:
            st.error("❌ Token inválido o inactivo.")
            st.stop()

    # 2) Si ya hay sesión (admin/agente)
    modo = st.session_state.get("modo")
    if modo == "admin":
        panel_admin(); return
    if modo == "agente":
        panel_agente(); return

    # 3) Pantalla pública con logins
    pantalla_login()

if __name__ == "__main__":
    main()
