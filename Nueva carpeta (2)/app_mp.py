# -*- coding: utf-8 -*-
# app.py — Panel Agente y Vista Pública con fixes de periodo, filtros y UI
# build: 2025-10-15b

import os
from datetime import datetime
import pandas as pd
import streamlit as st

# -----------------------------------------------------------------------------
# Configuración y Estilos
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Sistema TikTok Live", page_icon="📊", layout="wide")
st.caption("build: 2025-10-15b")

st.markdown("""
<style>
:root{--bg:#000;--card:#121317;--line:#1f2230;--muted:#9aa3b2;--accent:#00f2ea;}
.stApp{background:#000;}
h1,h2,h3{color:var(--accent)!important;text-shadow:2px 2px 4px rgba(254,44,85,.25);}

/* Métricas en alto contraste (sin degradados) */
[data-testid="stMetricValue"]{color:#fff!important;}
[data-testid="stMetric"]>div{
  background:#121317!important;border:1px solid #1f2230!important;border-radius:12px!important;padding:10px 14px!important;
}
[data-testid="stMetricLabel"]{color:#9aa3b2!important;}

/* Tablas compactas y centradas */
div[data-testid="stDataFrame"] table{font-size:13px;}
div[data-testid="stDataFrame"] td,div[data-testid="stDataFrame"] th{
  text-align:center!important;padding:6px 8px!important;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Supabase Helper
# -----------------------------------------------------------------------------
@st.cache_resource
def get_supabase():
    try:
        from supabase import create_client  # type: ignore
    except Exception:
        st.error("❌ Falta la librería `supabase` en requirements.txt")
        return None

    def _sec(k, env=None):
        try: return str(st.secrets[k]).strip()
        except Exception: return str(os.getenv(env or k, "")).strip()

    url = _sec("SUPABASE_URL")
    key = _sec("SUPABASE_SERVICE_KEY") or _sec("SUPABASE_KEY")
    if not url or not key:
        st.error("❌ Faltan `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` en Secrets.")
        return None

    try:
        return create_client(url, key)
    except Exception as e:
        st.error(f"❌ No se pudo crear el cliente de Supabase: {e}")
        return None

sb = get_supabase()

# -----------------------------------------------------------------------------
# Utilidades
# -----------------------------------------------------------------------------
MESES_ES = {
    1:"enero",2:"febrero",3:"marzo",4:"abril",5:"mayo",6:"junio",
    7:"julio",8:"agosto",9:"septiembre",10:"octubre",11:"noviembre",12:"diciembre"
}

def etiqueta_periodo_humano(periodo_yyyy_mm_dd: str) -> str:
    """YYYY-MM-DD → 'del 1 al <día> de <mes>'"""
    try:
        d = datetime.strptime(periodo_yyyy_mm_dd, "%Y-%m-%d")
        return f"del 1 al {d.day} de {MESES_ES[d.month]}"
    except Exception:
        return periodo_yyyy_mm_dd

def to_num(series_like, default=0.0):
    return pd.to_numeric(series_like, errors="coerce").fillna(default)

def filtrar_por_cumple(df: pd.DataFrame, valor: str) -> pd.DataFrame:
    """valor: 'SI' | 'NO' ; soporta bool y str."""
    if df.empty or "cumple" not in df.columns: 
        return df.iloc[0:0].copy()
    s = df["cumple"]
    if s.dtype == bool:
        return df[s] if valor == "SI" else df[~s]
    return df[s.astype(str).str.strip().str.upper() == valor]

# -----------------------------------------------------------------------------
# Carga de datos
# -----------------------------------------------------------------------------
@st.cache_data(ttl=300)
def obtener_periodos_disponibles():
    """
    De usuarios_tiktok tomamos la lista de periodos (fecha_datos) y los normalizamos a YYYY-MM-DD.
    """
    if not sb: return []
    try:
        r = sb.table("usuarios_tiktok").select("fecha_datos").execute()
        vals = [row["fecha_datos"] for row in (r.data or []) if row.get("fecha_datos")]
        ok = []
        for v in vals:
            try:
                d = datetime.strptime(v, "%Y-%m-%d")
                ok.append(d.strftime("%Y-%m-%d"))
            except Exception:
                pass
        return sorted(set(ok), reverse=True)
    except Exception:
        return []

def cargar_notas_contrato(contrato: str, periodo: str) -> pd.DataFrame:
    """Lee reportes_contratos (por contrato & periodo). Usa 'periodo' (no fecha_datos)."""
    if not sb: return pd.DataFrame()
    try:
        r = (sb.table("reportes_contratos")
               .select("*")
               .eq("contrato", contrato)
               .eq("periodo", periodo)
               .execute())
        df = pd.DataFrame(r.data or [])
        # Tipos numéricos seguros (en DB están como VARCHAR)
        for c in ["diamantes","nivel","dias","coins_incentivo","paypal_incentivo","coins_bruto","paypal_bruto"]:
            if c in df.columns:
                df[c] = to_num(df[c])
        return df
    except Exception as e:
        st.error(f"Error al cargar notas: {e}")
        return pd.DataFrame()

def cargar_resumen_contrato(contrato: str, periodo: str) -> pd.DataFrame:
    if not sb: return pd.DataFrame()
    try:
        r = (sb.table("resumen_contratos")
               .select("*")
               .eq("contrato", contrato)
               .eq("periodo", periodo)
               .execute())
        df = pd.DataFrame(r.data or [])
        if "total_final" in df.columns:
            df["total_final"] = to_num(df["total_final"])
        return df
    except Exception:
        return pd.DataFrame()

def cargar_token_contrato(token: str):
    if not sb: return None
    try:
        r = (sb.table("contratos_tokens")
               .select("*")
               .eq("token", token)
               .eq("activo", True)
               .execute())
        if r.data:
            return r.data[0]
    except Exception:
        pass
    return None

def cargar_contrato(codigo: str) -> dict:
    if not sb: return {}
    try:
        r = (sb.table("contratos")
               .select("*")
               .eq("codigo", codigo)
               .limit(1)
               .execute())
        return r.data[0] if r.data else {}
    except Exception:
        return {}

# -----------------------------------------------------------------------------
# UI helpers
# -----------------------------------------------------------------------------
def render_badge_whatsapp(contrato_row: dict):
    """
    Muestra el número con una línea de ayuda debajo (no altera tu lógica previa).
    Busca whatsapp/telefono/soporte.
    """
    wa = None
    for k in ("whatsapp","telefono","soporte"):
        v = str(contrato_row.get(k, "") or "").strip()
        if v: wa = v; break
    if not wa:
        return
    st.markdown(f"""
    <div style="display:flex;gap:10px;align-items:center;margin-top:6px;">
      <div style="background:#0a5;color:#fff;padding:6px 10px;border-radius:999px;font-weight:600;">
        🟢 Soporte
      </div>
      <div style="color:#8be9c7;font-weight:600;">📞 {wa}</div>
    </div>
    <div style="color:#cfd3d7;font-size:13px;margin:2px 0 10px 2px;">
      Dudas, quejas o comentarios · hablar con la administración
    </div>
    """, unsafe_allow_html=True)

def card_metrics_resumen(df_notas: pd.DataFrame, df_resumen: pd.DataFrame):
    """
    Pinta métricas sin duplicar montos.
    - Si total_final existe en resumen, se usa como fuente de verdad.
    - Si paypal_bruto == paypal_incentivo (scripts que guardan igual), no se duplica.
    """
    total_sueldo = float(to_num(df_notas.get("paypal_bruto", 0)).sum())
    total_coins = float(to_num(df_notas.get("coins_incentivo", 0)).sum())

    sueldo_series = to_num(df_notas.get("paypal_bruto", 0))
    inc_pp_series = to_num(df_notas.get("paypal_incentivo", 0))
    iguales = len(df_notas) > 0 and (sueldo_series.equals(inc_pp_series))
    total_paypal_incentivo = 0.0 if iguales else float(inc_pp_series.sum())

    total_general = None
    if not df_resumen.empty and "total_final" in df_resumen.columns:
        total_general = float(to_num(df_resumen["total_final"]).sum())
    if total_general is None:
        total_general = round(total_sueldo + total_paypal_incentivo, 2)

    c1,c2,c3 = st.columns(3)
    with c1: st.metric("💰 Total Sueldo Base", f"${total_sueldo:,.2f}")
    with c2: st.metric("💸 Total Incentivo PayPal", f"${total_paypal_incentivo:,.2f}")
    with c3: st.metric("✅ TOTAL A PAGAR", f"${total_general:,.2f}")

# -----------------------------------------------------------------------------
# Vistas
# -----------------------------------------------------------------------------
def vista_publica(contrato: str):
    st.title(f"📄 {contrato} – Vista pública")
    cinfo = cargar_contrato(contrato)
    render_badge_whatsapp(cinfo)

    periodos = obtener_periodos_disponibles()
    if not periodos:
        st.warning("No hay periodos disponibles.")
        return

    periodo = st.selectbox("🗓️ Periodo:", periodos, index=0, key="periodo_pub")
    st.caption(f"Periodo: {etiqueta_periodo_humano(periodo).capitalize()}")

    df = cargar_notas_contrato(contrato, periodo)
    if df.empty:
        st.info("Las notas estarán disponibles cuando se procese el cierre del periodo.")
        return

    tab1, tab2, tab3 = st.tabs(["📋 Todos","✅ Cumplen","❌ No cumplen"])
    with tab1:
        st.caption(f"{len(df)} usuarios")
        st.dataframe(df, use_container_width=True, hide_index=True)
    with tab2:
        df_ok = filtrar_por_cumple(df, "SI")
        st.caption(f"{len(df_ok)} usuarios")
        st.dataframe(df_ok, use_container_width=True, hide_index=True)
    with tab3:
        df_no = filtrar_por_cumple(df, "NO")
        st.caption(f"{len(df_no)} usuarios")
        st.dataframe(df_no, use_container_width=True, hide_index=True)

def panel_agente(contrato: str, nombre_mostrar: str):
    st.title(f"🧰 {contrato} - Panel de Agente")
    st.caption(nombre_mostrar)

    cinfo = cargar_contrato(contrato)
    render_badge_whatsapp(cinfo)

    # Periodos
    periodos = obtener_periodos_disponibles()
    if not periodos:
        st.warning("No hay periodos disponibles.")
        return
    periodo = st.selectbox("🗓️ Periodo:", periodos, index=0, key="periodo_agente")
    st.caption(f"Periodo: {etiqueta_periodo_humano(periodo).capitalize()}")

    # Tabs
    tab_todos, tab_cumplen, tab_notas, tab_resumen = st.tabs(["📋 Todos","✅ Cumplen","🧾 Notas del Periodo","📊 Resumen"])

    # Datos base
    df = cargar_notas_contrato(contrato, periodo)

    with tab_todos:
        st.caption(f"{len(df)} usuarios")
        st.dataframe(df, use_container_width=True, hide_index=True)

    with tab_cumplen:
        df_ok = filtrar_por_cumple(df, "SI")
        st.caption(f"{len(df_ok)} usuarios")
        st.dataframe(df_ok, use_container_width=True, hide_index=True)

    with tab_notas:
        st.subheader("Notas del Periodo")
        st.caption(f"Contrato: {contrato} | Periodo: {etiqueta_periodo_humano(periodo).capitalize()}")

        st.info("Las notas se generan automáticamente al cierre del periodo por los scripts Python 09–20. "
                "Cada nota contiene sueldo base + incentivos por usuario.")

        if df.empty:
            st.error("No hay notas disponibles aún para este periodo.")
        else:
            df_res = cargar_resumen_contrato(contrato, periodo)
            # Métricas (sin duplicado)
            card_metrics_resumen(df, df_res)

            # Tabla de notas
            st.caption("Detalle de notas")
            st.dataframe(df, use_container_width=True, hide_index=True)

    with tab_resumen:
        df_res = cargar_resumen_contrato(contrato, periodo)
        if df_res.empty:
            st.info("Aún no hay resumen consolidado para este periodo.")
        else:
            st.caption("Resumen consolidado (resumen_contratos)")
            st.dataframe(df_res, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# Router
# -----------------------------------------------------------------------------
def main():
    params = st.query_params
    token = params.get("token", [None])
    token = token[0] if isinstance(token, list) else token

    if token:
        tk = cargar_token_contrato(token)
        if not tk:
            st.error("Token inválido o inactivo.")
            return
        contrato = tk.get("contrato")
        vista_publica(contrato)
        return

    # Si no hay token, mostramos un selector simple (demo Panel Agente)
    st.sidebar.header("🔐 Panel Agente (demo)")
    contrato_demo = st.sidebar.text_input("Contrato", value="A001")
    nombre = st.sidebar.text_input("Nombre", value="Gestión Completa")
    if st.sidebar.button("Abrir Panel"):
        st.session_state["_go"] = True

    if st.session_state.get("_go"):
        panel_agente(contrato_demo, nombre)
    else:
        st.title("🎵 Sistema TikTok Live")
        st.info("Usa el panel lateral para abrir el Panel de Agente (demo) o agrega `?token=<...>` a la URL para la vista pública.")

if __name__ == "__main__":
    main()
