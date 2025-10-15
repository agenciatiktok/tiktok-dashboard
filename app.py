# -*- coding: utf-8 -*-
# app_chat1_fixed_full.py — Vista pública filtrada + ocultamiento robusto + enriquecimiento de nombres
import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# Carga .env si existe (no romper si no está)
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

st.set_page_config(page_title="Sistema TikTok Live", page_icon="📊", layout="wide")

# ---- Estilos UI ----
st.markdown("""
<style>
:root{--tiktok-black:#000;--tiktok-cyan:#00f2ea;--tiktok-pink:#fe2c55;--tiktok-white:#fff;}
.stApp{background:#000;}
h1,h2,h3{color:var(--tiktok-cyan)!important;text-shadow:2px 2px 4px rgba(254,44,85,.3);}
div[data-testid="stDataFrame"] td,div[data-testid="stDataFrame"] th{ text-align:center!important;}
.stButton>button{background:linear-gradient(135deg,#00f2ea 0%,#fe2c55 100%);color:#fff;border:none;padding:10px 18px;border-radius:10px;font-weight:600;}
.stButton>button:hover{filter:brightness(1.1);}
</style>
""", unsafe_allow_html=True)

# =========================== Supabase helpers ================================
@st.cache_resource
def get_supabase():
    """Devuelve cliente de Supabase o None con mensaje de error amigable."""
    try:
        from supabase import create_client  # type: ignore
    except Exception:
        st.error("❌ Falta la librería `supabase`. Agrega a requirements.txt: `supabase`")
        return None

    def _get_secret(k, fallback_env=None):
        v = None
        try:
            v = st.secrets[k]
        except Exception:
            v = os.getenv(fallback_env or k)
        return (v or "").strip()

    url = _get_secret("SUPABASE_URL")
    key = _get_secret("SUPABASE_SERVICE_KEY") or _get_secret("SUPABASE_KEY")

    if not url or not key:
        st.error("❌ Faltan credenciales de Supabase. Define `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` (o `SUPABASE_KEY`) en Secrets.")
        return None

    try:
        return create_client(url, key)
    except Exception as e:
        st.error(f"❌ No se pudo crear el cliente de Supabase: {e}")
        return None

# =============================== Auth =======================================
def verificar_token_contrato(token: str):
    sb = get_supabase()
    if not sb: return None
    try:
        r = sb.table("contratos_tokens").select("*").eq("token", token).eq("activo", True).execute()
        if r.data:
            d = r.data[0]
            return d if d.get("tipo", "contrato") == "contrato" else None
    except Exception as e:
        st.error(f"Error consultando token: {e}")
    return None

def verificar_token_admin(token: str):
    sb = get_supabase()
    if not sb: return None
    try:
        r = sb.table("contratos_tokens").select("*").eq("token", token).eq("activo", True).execute()
        if r.data:
            d = r.data[0]
            return d if d.get("tipo", "") == "admin" else None
    except Exception as e:
        st.error(f"Error consultando token admin: {e}")
    return None

def verificar_login_agente(usuario: str, password: str):
    sb = get_supabase()
    if not sb: return None
    try:
        r = (sb.table("agentes_login").select("*")
             .eq("usuario", usuario).eq("password", password).eq("activo", True).execute())
        if r.data: return r.data[0]
    except Exception as e:
        st.error(f"Error en login de agente: {e}")
    return None

# =========================== Utilidades de datos =============================
def obtener_periodos_disponibles():
    sb = get_supabase()
    if not sb: return []
    try:
        r = sb.table("usuarios_tiktok").select("fecha_datos").execute()
        if not r.data: return []
        return sorted({row.get("fecha_datos") for row in r.data if row.get("fecha_datos")}, reverse=True)
    except Exception as e:
        st.error(f"Error leyendo periodos: {e}")
        return []

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
    if not sb: return pd.DataFrame()
    try:
        r = sb.table("incentivos_horizontales").select("*").order("acumulado").execute()
        return pd.DataFrame(r.data) if r.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Error leyendo incentivos: {e}")
        return pd.DataFrame()

def calcular_incentivos(df_inc, diamantes, nivel):
    if nivel == 0 or (diamantes or 0) <= 0: return (0, 0)
    fila = df_inc[df_inc.get("acumulado", 0) <= diamantes].sort_values("acumulado", ascending=False)
    if fila.empty: return (0, 0)
    f = fila.iloc[0]
    return (f.get(f"nivel_{nivel}_monedas", 0) or 0, f.get(f"nivel_{nivel}_paypal", 0) or 0)

@st.cache_data(ttl=300)
def _leer_reglas_ocultas():
    sb = get_supabase()
    if not sb: return []
    try:
        r = sb.table("config_columnas_ocultas").select("*").execute()
        return r.data or []
    except Exception:
        return []

# --------- Normalización/aliases para columnas a ocultar ----------
def _alias_oculto(col_raw: str) -> str:
    alias = {
        # base visibles
        "usuario":"usuario","username":"usuario","user":"usuario","nick":"usuario",
        "agencia":"agencia","agency":"agencia","Agencia":"agencia","AGENCIA":"agencia",
        "dias":"dias","días":"dias","Dias":"dias","Días":"dias",
        "duracion":"duracion","horas":"duracion","tiempo":"duracion",
        "diamantes":"diamantes",
        "nivel":"nivel","cumple":"cumple",
        # incentivos/pagos
        "coins":"incentivo_coins","incentivo coin":"incentivo_coins","incentivo_coins":"incentivo_coins",
        "paypal":"incentivo_paypal","incentivo paypal":"incentivo_paypal","incentivo_paypal":"incentivo_paypal",
        "sueldo":"paypal_bruto","paypal_bruto":"paypal_bruto","coins_bruto":"coins_bruto",
    }
    return alias.get(col_raw, col_raw.lower())

def obtener_columnas_ocultas(contrato: str):
    reglas = _leer_reglas_ocultas()
    ocultas = []
    for row in reglas:
        c = row.get("contrato")
        col_raw = str(row.get("columna", "")).strip()
        if not col_raw:
            continue
        col = _alias_oculto(col_raw)
        # Global o específica por contrato
        if (c is None) or (str(c).strip() == "") or (str(c).strip() == str(contrato).strip()):
            ocultas.append(col)
    return ocultas

# ---- Enriquecimiento de nombres desde histórico (cuando usuario está vacío)
def _col(df, *candidatos):
    for c in candidatos:
        if c in df.columns:
            return c
    return None

def enriquecer_nombres_desde_historial(df: pd.DataFrame, sb) -> pd.DataFrame:
    """
    Rellena 'usuario' cuando viene vacío usando historico_usuarios.
    Busca por id_tiktok (o usuario_id) y usa el último username conocido.
    """
    if df.empty or sb is None:
        return df

    col_user = _col(df, "usuario", "username", "user", "nick")
    col_id   = _col(df, "id_tiktok", "usuario_id", "user_id", "id_usuario")
    if not col_user or not col_id:
        return df

    mask_faltan = df[col_user].isna() | (df[col_user].astype(str).str.strip() == "")
    ids = (df.loc[mask_faltan, col_id].dropna().astype(str).unique().tolist())
    if not ids:
        return df

    mapping = {}
    CHUNK = 400
    for i in range(0, len(ids), CHUNK):
        lote = ids[i:i+CHUNK]
        rows = []
        # Intento 1: id_tiktok
        try:
            r = (sb.table("historico_usuarios")
                    .select("*")
                    .in_("id_tiktok", lote)
                    .order("fecha", desc=True)
                    .execute())
            rows = r.data or []
        except Exception:
            rows = []
        # Intento 2: usuario_id
        if not rows:
            try:
                r = (sb.table("historico_usuarios")
                        .select("*")
                        .in_("usuario_id", lote)
                        .order("fecha", desc=True)
                        .execute())
                rows = r.data or []
            except Exception:
                rows = []

        if not rows:
            continue

        h = pd.DataFrame(rows)
        col_hist_id   = _col(h, "id_tiktok", "usuario_id", "user_id")
        col_hist_user = _col(h, "usuario", "username", "user", "nick")
        if not col_hist_id or not col_hist_user:
            continue

        h["id_str"] = h[col_hist_id].astype(str)
        h = h.dropna(subset=[col_hist_user]).drop_duplicates(subset=["id_str"], keep="first")
        mapping.update(dict(zip(h["id_str"], h[col_hist_user])))

    if mapping:
        df[col_id] = df[col_id].astype(str)
        df.loc[mask_faltan, col_user] = df.loc[mask_faltan, col_id].map(mapping).fillna(df.loc[mask_faltan, col_user])

    return df

# =========================== Tablas / Formato ================================
def formatear_dataframe(df_input: pd.DataFrame, contrato: str, *, ocultar_publico: bool=False) -> pd.DataFrame:
    columnas_orden = [
        'usuario', 'agencia', 'dias', 'duracion', 'diamantes',
        'nivel', 'cumple', 'incentivo_coins', 'incentivo_paypal',
        'coins_bruto', 'paypal_bruto'
    ]
    # Cargar reglas y normalizarlas a minúsculas
    ocultas_cfg = {c.lower() for c in obtener_columnas_ocultas(contrato)}
    if ocultar_publico:
        ocultas_cfg.update({"agencia"})  # 👉 Forzar ocultar agencia en vista pública

    columnas_mostrar = [c for c in columnas_orden if c in df_input.columns and c.lower() not in ocultas_cfg]
    df_show = df_input[columnas_mostrar].copy()

    ren = {
        'usuario':'Usuario','agencia':'Agencia','dias':'Días','duracion':'Horas',
        'diamantes':'Diamantes','nivel':'Nivel','cumple':'Cumple',
        'incentivo_coins':'Incentivo Coin','incentivo_paypal':'Incentivo PayPal',
        'coins_bruto':'Coins Bruto','paypal_bruto':'PayPal Bruto'
    }
    df_show.rename(columns={k:v for k,v in ren.items() if k in df_show.columns}, inplace=True)

    if 'Horas' in df_show.columns and 'duracion' in df_input.columns:
        df_show['Horas'] = df_input['duracion'].apply(lambda m: m if isinstance(m, str) else f"{int(m//60)}h {int(m%60)}min")
    if 'Diamantes' in df_show.columns and 'diamantes' in df_input.columns:
        df_show['Diamantes'] = df_input['diamantes'].apply(lambda x: f"{int(x):,}" if pd.notnull(x) else "0")
    if 'Días' in df_show.columns and 'dias' in df_input.columns:
        df_show['Días'] = df_input['dias'].apply(lambda x: int(x) if pd.notnull(x) else 0)
    if 'Incentivo Coin' in df_show.columns and 'incentivo_coins' in df_input.columns:
        df_show['Incentivo Coin'] = df_input['incentivo_coins'].apply(lambda x: f"{int(x):,}" if pd.notnull(x) and x>0 else "0")
    if 'Incentivo PayPal' in df_show.columns and 'incentivo_paypal' in df_input.columns:
        df_show['Incentivo PayPal'] = df_input['incentivo_paypal'].apply(lambda x: f"${float(x):,.2f}" if pd.notnull(x) and x>0 else "$0.00")

    return df_show

# ======================== Carga y cálculo del contrato =======================
def obtener_datos_contrato(contrato: str, fecha_datos: str) -> pd.DataFrame:
    """Carga usuarios del periodo y FILTRA estrictamente por contrato/agencia.
    Enriquecer nombres, calcular nivel/cumple e incentivos, mapear paypal_bruto.
    """
    sb = get_supabase()
    if not sb: return pd.DataFrame()

    # Bandera nivel1_tabla3
    nivel1_tabla3 = False
    try:
        conf = sb.table("contratos").select("*").eq("codigo", contrato).execute()
        if conf.data:
            v = conf.data[0].get("nivel1_tabla3", False)
            if isinstance(v, str):
                nivel1_tabla3 = v.upper() in ["SI","SÍ","TRUE","YES","1"]
            else:
                nivel1_tabla3 = bool(v)
    except Exception:
        pass

    # Traer por periodo (amplio) y filtrar localmente
    try:
        r = (sb.table("usuarios_tiktok").select("*")
             .eq("fecha_datos", fecha_datos).execute())
    except Exception as e:
        st.error(f"Error leyendo usuarios del periodo: {e}")
        return pd.DataFrame()

    if not r.data:
        return pd.DataFrame()

    df = pd.DataFrame(r.data)

    # Filtro local ESTRICTO
    if "contrato" in df.columns:
        df = df[df["contrato"].astype(str).str.upper() == contrato.upper()]
    elif "agencia" in df.columns:
        df = df[df["agencia"].astype(str).str.upper() == contrato.upper()]

    if df.empty:
        return df

    # Enriquecer nombres si faltan
    df = enriquecer_nombres_desde_historial(df, sb)

    # Normalizar horas si vienen en minutos numéricos
    if "horas" in df.columns and "duracion" not in df.columns:
        # Si ya tienes minutos en "horas", adapta aquí. Por defecto, duracion = horas*60
        try:
            df["duracion"] = (pd.to_numeric(df["horas"], errors="coerce") * 60).fillna(0)
        except Exception:
            df["duracion"] = 0
    elif "duracion" not in df.columns:
        df["duracion"] = 0

    # Calcular nivel/cumple
    dias_col = "dias" if "dias" in df.columns else None
    horas_col = "horas" if "horas" in df.columns else None
    if dias_col and horas_col:
        df["nivel_original"] = df.apply(lambda row: determinar_nivel(row.get(dias_col,0), row.get(horas_col,0)), axis=1)
    else:
        # fallback de seguridad
        df["nivel_original"] = df.apply(lambda row: determinar_nivel(row.get("dias",0), row.get("duracion",0)/60.0), axis=1)
    df["cumple"] = df["nivel_original"].apply(lambda n: "SI" if n>0 else "NO")

    # Incentivos
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

    df.loc[df["cumple"]=="NO", ["incentivo_coins","incentivo_paypal"]] = 0

    # Mapear sueldo (paypal_bruto) con reportes_contratos
    try:
        rep = (sb.table("reportes_contratos").select("usuario_id, paypal_bruto")
               .eq("contrato", contrato).eq("periodo", fecha_datos).execute())
        if rep.data:
            m = pd.DataFrame(rep.data)
            if "id_tiktok" in df.columns:
                df["id_tiktok_str"] = df["id_tiktok"].astype(str)
                m["usuario_id_str"] = m["usuario_id"].astype(str)
                pmap = dict(zip(m["usuario_id_str"], m["paypal_bruto"]))
                df["paypal_bruto"] = df["id_tiktok_str"].map(pmap).fillna(0)
                df.drop(columns=["id_tiktok_str"], inplace=True, errors="ignore")
            else:
                df["paypal_bruto"] = 0
        else:
            df["paypal_bruto"] = 0
    except Exception:
        df["paypal_bruto"] = 0

    return df

# ================================ Gráficos ===================================
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

# ================================ Vistas =====================================
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
        st.dataframe(
            formatear_dataframe(df.sort_values("diamantes", ascending=False), contrato, ocultar_publico=True),
            use_container_width=True
        )
    with tab2:
        df_ok = df[df["cumple"]=="SI"].copy()
        st.caption(f"✅ Cumplen: {len(df_ok)}")
        st.dataframe(
            formatear_dataframe(df_ok.sort_values("diamantes", ascending=False), contrato, ocultar_publico=True),
            use_container_width=True
        )
    with tab3:
        df_no = df[df["cumple"]=="NO"].copy()
        st.caption(f"❌ No cumplen: {len(df_no)}")
        st.dataframe(
            formatear_dataframe(df_no.sort_values("diamantes", ascending=False), contrato, ocultar_publico=True),
            use_container_width=True
        )
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
            ag = verificar_login_agete(user, pwd) if (user and pwd) else None  # (puedes conectar tu vista de agente)
            if ag:
                st.session_state["modo"] = "agente"
                st.session_state["agente"] = ag
                st.rerun()
            else:
                st.error("Usuario o contraseña inválidos")

def panel_admin():
    st.title("🔐 Panel de Administración")
    st.info("Placeholder de administración.")

def panel_agente():
    st.title("👔 Panel del Agente")
    st.info("Placeholder del agente.")

# ================================ Router =====================================
def main():
    params = st.query_params
    token_url = params.get("token", [None])
    token_url = token_url[0] if isinstance(token_url, list) else token_url
    if token_url:
        td = verificar_token_contrato(token_url)
        if td:
            vista_publica_contrato(td); return
        else:
            st.error("❌ Token inválido o inactivo.")
            st.stop()

    modo = st.session_state.get("modo")
    if modo == "admin":
        panel_admin(); return
    if modo == "agente":
        panel_agente(); return
    pantalla_login()

if __name__ == "__main__":
    main()
