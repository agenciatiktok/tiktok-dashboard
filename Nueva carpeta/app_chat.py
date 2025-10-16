# app.py
import os
import re
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client, Client

# =========================
# Config de página
# =========================
st.set_page_config(page_title="Sistema TikTok Live", layout="wide")

# =========================
# Credenciales Supabase
# - Funciona en local (.env) y en Streamlit Cloud (st.secrets)
# =========================
load_dotenv()  # en Cloud no afecta; en local lee .env

def _pick(*vals):
    for v in vals:
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return ""

# URL siempre requerida
SUPABASE_URL = _pick(
    st.secrets.get("SUPABASE_URL") if hasattr(st, "secrets") else None,
    os.getenv("SUPABASE_URL")
)

# Prefiere SERVICE_KEY; cae a anon si no hay
SUPABASE_KEY = _pick(
    (st.secrets.get("SUPABASE_SERVICE_KEY") if hasattr(st, "secrets") else None),
    os.getenv("SUPABASE_SERVICE_KEY"),
    (st.secrets.get("SUPABASE_KEY") if hasattr(st, "secrets") else None),
    os.getenv("SUPABASE_KEY")
)

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Faltan credenciales de Supabase. Define SUPABASE_URL y SUPABASE_SERVICE_KEY (o SUPABASE_KEY).")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# Helpers de tipos y reglas
# =========================
def _to_int(x, default=0):
    try:
        if x is None: return default
        if isinstance(x, bool): return int(x)
        if isinstance(x, (int, float)): return int(x)
        s = str(x).strip().replace(",", "")
        if s == "" or s.lower() in ("none", "nan", "null"): return default
        return int(float(s))
    except Exception:
        return default

def _to_float(x, default=0.0):
    try:
        if x is None: return default
        if isinstance(x, (int, float)): return float(x)
        s = str(x).strip().replace(",", "")
        if s == "" or s.lower() in ("none", "nan", "null"): return default
        return float(s)
    except Exception:
        return default

def _to_str(x, default=""):
    if x is None: return default
    s = str(x).strip()
    return "" if s.lower() in ("none", "nan", "null") else s

def parse_horas(duracion_txt):
    if not duracion_txt:
        return 0.0
    s = str(duracion_txt)
    h = re.search(r"(\d+)\s*h", s)
    m = re.search(r"(\d+)\s*min", s)
    sec = re.search(r"(\d+)\s*s", s)
    hh = int(h.group(1)) if h else 0
    mm = int(m.group(1)) if m else 0
    ss = int(sec.group(1)) if sec else 0
    return hh + (mm/60.0) + (ss/3600.0)

def nivel_from(dias, horas):
    return 1 if (dias >= 7 and horas >= 15) else 0

# =========================
# Consultas cacheadas
# =========================
@st.cache_data(ttl=300)
def get_periodos():
    res = supabase.table("usuarios_tiktok").select("fecha_datos").order("fecha_datos", desc=True).execute()
    fechas = sorted({r["fecha_datos"] for r in (res.data or [])}, reverse=True)
    return fechas

@st.cache_data(ttl=300)
def get_contratos_activos():
    res = supabase.table("contratos").select("*").eq("estado", "Activo").execute()
    df = pd.DataFrame(res.data or [])
    if df.empty:
        return pd.DataFrame(columns=["codigo", "nombre", "tipo_logica"])
    df["codigo"] = df["codigo"].astype(str).str.strip().str.upper()
    df["nombre"] = df["nombre"].astype(str).str.strip()
    return df[["codigo", "nombre", "tipo_logica"]].sort_values("codigo")

@st.cache_data(ttl=300)
def get_tokens_activos():
    res = supabase.table("contratos_tokens").select("contrato,nombre,activo").eq("activo", True).execute()
    return pd.DataFrame(res.data or [])

@st.cache_data(ttl=300)
def fetch_usuarios(periodo: str):
    res = supabase.table("usuarios_tiktok").select("*").eq("fecha_datos", periodo).execute()
    df = pd.DataFrame(res.data or [])
    if df.empty:
        return df

    # Normaliza columnas
    if "dias" not in df.columns and "Dias" in df.columns:
        df["dias"] = df["Dias"]
    if "duracion" not in df.columns and "Duracion" in df.columns:
        df["duracion"] = df["Duracion"]
    if "horas" not in df.columns:
        df["horas"] = None

    # Horas preferente numérico; si no, parsea desde 'duracion'
    df["horas"] = df.apply(
        lambda r: _to_float(r.get("horas")) if _to_float(r.get("horas")) > 0
        else parse_horas(r.get("duracion")),
        axis=1
    )
    df["dias"] = df["dias"].apply(_to_int)

    # Nivel/cumple si faltan
    if "nivel" not in df.columns:
        df["nivel"] = df.apply(lambda r: nivel_from(_to_int(r["dias"]), _to_float(r["horas"])), axis=1)
    if "cumple" not in df.columns:
        df["cumple"] = df["nivel"].apply(lambda n: True if n > 0 else False)

    for c in ("diamantes", "nivel", "dias"):
        if c in df.columns:
            df[c] = df[c].apply(_to_int)

    df["cumple"] = df["cumple"].astype(bool)
    df["cumple_str"] = df["cumple"].apply(lambda x: "SI" if x else "NO")
    if "id_tiktok" not in df.columns:
        df["id_tiktok"] = df.get("usuario_id")
    return df

@st.cache_data(ttl=300)
def fetch_reportes(periodo: str, contrato: str):
    # reportes_contratos usa 'periodo' (no 'fecha_datos')
    res = supabase.table("reportes_contratos").select("*").eq("periodo", periodo).eq("contrato", contrato).execute()
    df = pd.DataFrame(res.data or [])
    if df.empty:
        return df
    for c in ("paypal_bruto", "paypal_incentivo", "coins_bruto", "coins_incentivo"):
        if c in df.columns:
            df[c] = df[c].apply(_to_float)
    if "usuario_id" not in df.columns and "id_tiktok" in df.columns:
        df["usuario_id"] = df["id_tiktok"]
    return df

# =========================
# Combinación y métricas
# =========================
def combinar_usuarios_y_reportes(df_users: pd.DataFrame, df_rep: pd.DataFrame):
    if df_users.empty:
        return df_users
    df = df_users.copy()
    if not df_rep.empty:
        rep = df_rep[["usuario_id", "paypal_bruto", "paypal_incentivo", "coins_bruto", "coins_incentivo"]].copy()
        rep.rename(columns={"usuario_id": "id_tiktok"}, inplace=True)
        df = df.merge(rep, on="id_tiktok", how="left")
    else:
        for c in ("paypal_bruto", "paypal_incentivo", "coins_bruto", "coins_incentivo"):
            df[c] = 0.0
    for c in ("usuario", "contrato", "agencia", "agente", "duracion"):
        if c not in df.columns:
            df[c] = ""
    if "diamantes" in df.columns:
        df = df.sort_values("diamantes", ascending=False)
    return df

def cuadro_metricas(df: pd.DataFrame):
    total = len(df)
    cumplen = int((df["cumple"] == True).sum()) if not df.empty else 0
    no_cumplen = total - cumplen
    diamantes_total = _to_int(df["diamantes"].sum()) if "diamantes" in df.columns else 0
    sueldo_total = df["paypal_bruto"].sum() if "paypal_bruto" in df.columns else 0.0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Usuarios", f"{total:,}")
    c2.metric("Cumplen", f"{cumplen:,}")
    c3.metric("Diamantes (total)", f"{diamantes_total:,}")
    c4.metric("Sueldo PayPal (total)", f"${sueldo_total:,.2f}")

# =========================
# UI
# =========================
st.title("🧮 Sistema TikTok Live · Dashboard")

# Botón de refresco duro
col_refresh, _ = st.columns([1, 6])
with col_refresh:
    if st.button("🔄 Actualizar ahora"):
        st.cache_data.clear()
        st.rerun()

periodos = get_periodos()
if not periodos:
    st.warning("No hay periodos disponibles en usuarios_tiktok.")
    st.stop()

colA, colB = st.columns([2, 3])
with colA:
    periodo_sel = st.selectbox("Periodo", periodos, index=0)
with colB:
    contratos_df = get_contratos_activos()
    tokens_df = get_tokens_activos()
    opciones = []
    if not contratos_df.empty:
        for _, r in contratos_df.iterrows():
            codigo = r["codigo"]
            nombre = r["nombre"]
            alias = tokens_df.loc[tokens_df["contrato"] == codigo, "nombre"]
            etiqueta = f"{codigo} – {alias.iloc[0]}" if not alias.empty else f"{codigo} – {nombre}"
            opciones.append((etiqueta, codigo))
    else:
        opciones = [("A001 – javaco83", "A001")]
    etiqueta_sel = st.selectbox("Contrato", [e for e, _ in opciones])
    contrato_sel = dict(opciones).get(etiqueta_sel, "A001")

st.divider()

with st.spinner("Cargando usuarios del periodo…"):
    df_users = fetch_usuarios(periodo_sel)

with st.spinner("Cargando reportes/notas del periodo…"):
    df_rep = fetch_reportes(periodo_sel, contrato_sel)

df = combinar_usuarios_y_reportes(df_users[df_users["contrato"].astype(str).str.upper() == contrato_sel], df_rep)

tab1, tab2, tab3, tab4 = st.tabs(["👥 Todos", "✅ Cumplen", "📄 Notas del Periodo", "📊 Resumen"])

with tab1:
    st.markdown("### 👥 Todos los usuarios del contrato")
    if df.empty:
        st.info("No hay usuarios para este contrato en el periodo seleccionado.")
    else:
        view_cols = ["usuario", "id_tiktok", "contrato", "diamantes", "dias", "horas", "nivel", "cumple_str", "paypal_bruto", "duracion", "agencia", "agente"]
        view_cols = [c for c in view_cols if c in df.columns]
        st.dataframe(df[view_cols], use_container_width=True, hide_index=True)
    st.caption("Sueldo PayPal proviene de 'reportes_contratos' para el periodo seleccionado.")

with tab2:
    st.markdown("### ✅ Solo quienes cumplen (≥7 días y ≥15h)")
    if df.empty:
        st.info("No hay datos.")
    else:
        cumple_df = df[df["cumple"] == True]
        if cumple_df.empty:
            st.warning("Nadie cumple en este corte. Es normal si el periodo es parcial.")
        else:
            view_cols = ["usuario", "id_tiktok", "contrato", "diamantes", "dias", "horas", "nivel", "paypal_bruto"]
            view_cols = [c for c in view_cols if c in cumple_df.columns]
            st.dataframe(cumple_df[view_cols], use_container_width=True, hide_index=True)

with tab3:
    st.markdown("### 📄 Notas del periodo (reportes_contratos)")
    if df_rep.empty:
        st.caption("No hay notas para este contrato y periodo. Se generan al correr los scripts 09–20.")
        st.dataframe(pd.DataFrame(columns=["contrato", "usuario", "paypal_bruto", "coins_bruto"]), use_container_width=True, hide_index=True)
    else:
        cols = ["usuario", "usuario_id", "dias", "duracion", "diamantes", "cumple", "nivel", "coins_incentivo", "paypal_incentivo", "coins_bruto", "paypal_bruto", "agente", "agencia"]
        cols = [c for c in cols if c in df_rep.columns]
        st.dataframe(df_rep[cols].sort_values("paypal_bruto", ascending=False), use_container_width=True, hide_index=True)

with tab4:
    st.markdown("### 📊 Resumen")
    cuadro_metricas(df)
    if not df.empty:
        by_nivel = df.groupby("nivel").size().reset_index(name="usuarios")
        st.bar_chart(by_nivel.set_index("nivel"))
