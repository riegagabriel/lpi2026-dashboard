import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import requests
from io import StringIO
import datetime
import json
import plotly.express as px
import plotly.graph_objects as go


# ─────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard LPI – RENIEC Electoral",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# CSS PERSONALIZADO
# ─────────────────────────────────────────────
st.markdown("""
<style>
    /* Fondo general */
    .main { background-color: #f4f6fb; }
    
    /* Encabezado */
    .header-bar {
        background: linear-gradient(90deg, #004a8f 0%, #0072c6 100%);
        color: white;
        padding: 18px 30px 14px 30px;
        border-radius: 10px;
        margin-bottom: 18px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .header-bar h1 { margin: 0; font-size: 1.35rem; font-weight: 700; }
    .header-bar p  { margin: 0; font-size: 0.82rem; opacity: 0.85; }

    /* Value boxes */
    .kpi-card {
        background: white;
        border-radius: 10px;
        padding: 14px 18px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        text-align: center;
        border-left: 5px solid #0072c6;
        height: 100%;
    }
    .kpi-card.green  { border-left-color: #1a9e5c; }
    .kpi-card.orange { border-left-color: #e07b00; }
    .kpi-card.purple { border-left-color: #7b2d8b; }
    .kpi-card.red    { border-left-color: #c0392b; }
    .kpi-card.teal   { border-left-color: #007b8a; }

    .kpi-value { font-size: 2rem; font-weight: 800; color: #1a2540; line-height: 1.1; }
    .kpi-label { font-size: 0.72rem; color: #6b7a99; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.04em; }
    .kpi-sub   { font-size: 0.78rem; color: #3d8bcd; margin-top: 2px; }

    /* Sección de gráficos */
    .section-title {
        font-size: 0.88rem;
        font-weight: 700;
        color: #1a2540;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
        border-bottom: 2px solid #0072c6;
        padding-bottom: 4px;
    }

    /* Ocultar menú hamburguesa */
    #MainMenu, footer { visibility: hidden; }
    
    /* Reducir padding superior */
    .block-container { padding-top: 1rem !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CARGA DE DATOS
# ─────────────────────────────────────────────
# REEMPLAZA ESTA URL con la URL de tu Google Sheets publicado como CSV
# Formato: https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/export?format=csv&gid=SHEET_GID
from io import BytesIO  # cambia StringIO por BytesIO

GOOGLE_SHEETS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTZg_SVgWbOOH6lIVBHZL-f6Xn2798eK7xE6IDGMdALdYmpQ6skscAq5xjfumiXvJHHLSapPA7A_tKV/pub?output=csv"

@st.cache_data(ttl=30)
def cargar_datos(url: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(url, dtype=str, skiprows=1)
    except Exception as e:
        st.error(f"No se pudo cargar la hoja: {e}")
        st.stop()
    return df

df_raw = cargar_datos(GOOGLE_SHEETS_URL)

# ─────────────────────────────────────────────
# LIMPIEZA / TIPADO BÁSICO
# ─────────────────────────────────────────────
def limpiar(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    
    # Normalizar nombres de columnas (strip espacios)
    df.columns = df.columns.str.strip()

    # Columnas numéricas
    num_cols = [
        "# DE CIUDADANOS ENCUESTADOS",
        "# DE ACTAS DE DEFUNCION (ENTREGADAS POR LA MUNICIPALIDAD)",
        "# DE TACHAS Y RECLAMOS",
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Fechas
    date_cols = [
        "FECHA DE INICIO DE PUBLICACIÓN",
        "FECHA DE FIN DE PUBLICACIÓN",
        "FECHA DE ARRIBO AL DISTRITO",
    ]
    for c in date_cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce", dayfirst=True)

    # Estatus Kit llegó al publicador
    kit_col = "EL PUBLICADOR YA CUENTA CON EL KIT"
    if kit_col in df.columns:
        df["KIT_PUBLICADOR"] = df[kit_col].str.strip().str.upper()

    # Descripción
    if "DESCRIPCIÓN" in df.columns:
        df["DESCRIPCIÓN"] = df["DESCRIPCIÓN"].str.strip().str.upper()

    return df

df = limpiar(df_raw)

# ─────────────────────────────────────────────
# LÓGICA DE NEGOCIO
# ─────────────────────────────────────────────

# Clave única por distrito
df["DIST_KEY"] = df["PROVINCIA"].str.strip() + " | " + df["DISTRITO"].str.strip()

# Total distritos únicos
total_distritos = df["DIST_KEY"].nunique()

# Distritos publicando: columna ¿SE REALIZÓ LA PUBLICACIÓN?
pub_col = next((c for c in df.columns if "SE REALIZ" in c.upper() and "PUBLICACI" in c.upper()), None)
if pub_col:
    distritos_publicando = df[df[pub_col].str.strip().str.upper() == "SI"]["DIST_KEY"].nunique()
else:
    distritos_publicando = 0

# EN AGENCIA
df["PUBLICA_AGENCIA"] = df["DESCRIPCIÓN"] == "EN AGENCIA"
distritos_agencia = df[df["PUBLICA_AGENCIA"]]["DIST_KEY"].nunique()

# CONTRATADO
df["PUBLICA_CONTRATADO"] = df["DESCRIPCIÓN"] == "CONTRATADO"
distritos_contratado = df[df["PUBLICA_CONTRATADO"]]["DIST_KEY"].nunique()

# PERSONAL DRE
df["PUBLICA_DRE"] = df["DESCRIPCIÓN"] == "PERSONAL DRE"
distritos_dre = df[df["PUBLICA_DRE"]]["DIST_KEY"].nunique()

# DESISTIÓ
distritos_desistio = df[df["DESCRIPCIÓN"] == "DESISTIO"]["DIST_KEY"].nunique()

# Kit entregado
df["PUBLICA"] = df["DESCRIPCIÓN"].isin(["CONTRATADO", "PERSONAL DRE"])
kit_ok = df.get("EL PUBLICADOR YA CUENTA CON EL KIT", pd.Series(dtype=str)).str.strip().str.upper() == "SI"
df["PUBLICACION_CONFIRMADA"] = df["PUBLICA"] & kit_ok
distritos_confirmados = df[df["PUBLICACION_CONFIRMADA"]]["DIST_KEY"].nunique()

# Columnas numéricas
ciudadanos_enc = pd.to_numeric(df.get("# DE CIUDADANOS ENCUESTADOS", pd.Series()), errors="coerce").sum()
actas_def      = pd.to_numeric(df.get("# DE ACTAS DE DEFUNCION (ENTREGADAS POR LA MUNICIPALIDAD)", pd.Series()), errors="coerce").sum()
tachas_rec     = pd.to_numeric(df.get("# DE TACHAS Y RECLAMOS", pd.Series()), errors="coerce").sum()

# ─────────────────────────────────────────────
# KPIs GLOBALES
# ─────────────────────────────────────────────

# Columnas numéricas
ciudadanos_enc  = pd.to_numeric(df.get("# DE CIUDADANOS ENCUESTADOS", pd.Series()), errors="coerce").sum()
actas_def       = pd.to_numeric(df.get("# DE ACTAS DE DEFUNCION (ENTREGADAS POR LA MUNICIPALIDAD)", pd.Series()), errors="coerce").sum()
tachas_rec      = pd.to_numeric(df.get("# DE TACHAS Y RECLAMOS", pd.Series()), errors="coerce").sum()

# ─────────────────────────────────────────────
# ENCABEZADO
# ─────────────────────────────────────────────
st.markdown("""
<div class="header-bar">
  <div>
    <h1>📋 Publicación de las Listas del Padrón Inicial – ERM 2026</h1>
    <p>RENIEC Electoral · Dirección de Registro Electoral (DRE) · Panel de seguimiento de monitoreo</p>
  </div>
  <div style="text-align:right; font-size:0.78rem; opacity:0.85;">
    Dashboard actualizado cada 5 min
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# FILA DE KPIs
# ─────────────────────────────────────────────

k1, k2, k3, k4, k5, k6, k7 = st.columns(7)

with k1:
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-value">{total_distritos}</div>
      <div class="kpi-label">Total Distritos</div>
      <div class="kpi-sub">con publicación de LPI</div>
    </div>""", unsafe_allow_html=True)

with k2:
    st.markdown(f"""
    <div class="kpi-card green">
      <div class="kpi-value">{distritos_contratado}</div>
      <div class="kpi-label">PUBLICADORES</div>
      <div class="kpi-sub">Personal externo contratado</div>
    </div>""", unsafe_allow_html=True)

with k3:
    st.markdown(f"""
    <div class="kpi-card teal">
      <div class="kpi-value">{distritos_dre}</div>
      <div class="kpi-label">PUBLICADORES</div>
      <div class="kpi-sub">Personal DRE</div>
    </div>""", unsafe_allow_html=True)

with k4:
    st.markdown(f"""
    <div class="kpi-card orange">
      <div class="kpi-value">{distritos_agencia}</div>
      <div class="kpi-label">DISTRITOS</div>
      <div class="kpi-sub">Con Publicación en agencia</div>
    </div>""", unsafe_allow_html=True)

with k5:
    st.markdown(f"""
    <div class="kpi-card teal">
      <div class="kpi-value">{int(ciudadanos_enc) if not pd.isna(ciudadanos_enc) else '—'}</div>
      <div class="kpi-label">Ciudadanos Encuestados</div>
      <div class="kpi-sub">total nacional</div>
    </div>""", unsafe_allow_html=True)

with k6:
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-value">{int(actas_def) if not pd.isna(actas_def) else '—'}</div>
      <div class="kpi-label">Actas de Defunción</div>
      <div class="kpi-sub">entregadas municipalidad</div>
    </div>""", unsafe_allow_html=True)

with k7:
    st.markdown(f"""
    <div class="kpi-card red">
      <div class="kpi-value">{int(tachas_rec) if not pd.isna(tachas_rec) else '—'}</div>
      <div class="kpi-label">Tachas y Reclamos</div>
      <div class="kpi-sub">presentados</div>
    </div>""", unsafe_allow_html=True)
    
st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# FILA PRINCIPAL: MAPA + GRÁFICOS
# ─────────────────────────────────────────────
col_mapa, col_charts = st.columns([1.6, 1], gap="medium")

# ── MAPA ──────────────────────────────────────
with col_mapa:
    st.markdown(
        '<div class="section-title">🗺️ Mapa de distritos por departamento</div>',
        unsafe_allow_html=True
    )
    st.write("Última actualización:", datetime.datetime.now())

    import json
    import plotly.express as px
    import plotly.graph_objects as go

    # ── CARGAR GEOJSON ──
    with open("peru_departamental_simple.geojson", "r", encoding="utf-8") as f:
        geojson = json.load(f)

    # ── LIMPIEZA ──
    df["DEPARTAMENTO"] = df["DEPARTAMENTO"].str.upper().str.strip()
    df["DISTRITO"] = df["DISTRITO"].str.strip()
    df["DESCRIPCIÓN"] = df["DESCRIPCIÓN"].str.strip().str.upper()

    # ── SELECTOR CORREGIDO ──
    modo = st.selectbox(
        "Tipo de publicación",
        ["Todos", "PERSONAL DRE", "CONTRATADO", "EN AGENCIA"]
    )

    df_map = df.copy()

    if modo != "Todos":
        df_map = df[df["DESCRIPCIÓN"] == modo]

    # ── AGRUPACIÓN ──
    dep_data = (
        df_map
        .groupby("DEPARTAMENTO")
        .agg(
            num_distritos=("DISTRITO", "nunique"),
            # 🔥 LISTA VERTICAL
            distritos=("DISTRITO", lambda x: "<br>".join(sorted(x.dropna().unique()[:25])))
        )
        .reset_index()
    )

    # ── MAPA BASE ──
    fig_map = px.choropleth(
        dep_data,
        geojson=geojson,
        locations="DEPARTAMENTO",
        featureidkey="properties.NOMBDEP",
        color="num_distritos",
        color_continuous_scale=[
            [0, "#dce6f2"],
            [0.5, "#6ea8fe"],
            [1, "#003f7f"]
        ],
    )

    # ── HOVER MEJORADO ──
    fig_map.update_traces(
        hovertemplate=(
            "<b>%{location}</b><br>"
            "Distritos: %{z}<br><br>"
            "<b>Listado:</b><br>%{customdata}<extra></extra>"
        ),
        customdata=dep_data["distritos"]
    )

    # ── LAYOUT ──
    fig_map.update_geos(
        fitbounds="locations",
        visible=False
    )

    fig_map.update_layout(
        height=520,
        margin=dict(l=0, r=0, t=0, b=0),
        coloraxis_colorbar=dict(title="N° distritos"),
    )

    # ── CENTROIDES ──
    DEP_COORDS = {
        "AMAZONAS": {"lat": -5.5, "lon": -78.1},
        "ANCASH": {"lat": -9.53, "lon": -77.53},
        "APURIMAC": {"lat": -14.05, "lon": -73.09},
        "AREQUIPA": {"lat": -16.41, "lon": -71.54},
        "AYACUCHO": {"lat": -13.16, "lon": -74.22},
        "CAJAMARCA": {"lat": -7.16, "lon": -78.51},
        "CUSCO": {"lat": -13.52, "lon": -71.97},
        "HUANCAVELICA": {"lat": -12.79, "lon": -74.97},
        "HUANUCO": {"lat": -9.93, "lon": -76.24},
        "ICA": {"lat": -14.07, "lon": -75.73},
        "JUNIN": {"lat": -11.16, "lon": -75.23},
        "LA LIBERTAD": {"lat": -8.12, "lon": -78.12},
        "LAMBAYEQUE": {"lat": -6.77, "lon": -79.84},
        "LIMA": {"lat": -12.04, "lon": -76.95},
        "LORETO": {"lat": -4.0, "lon": -75.0},
        "MADRE DE DIOS": {"lat": -11.0, "lon": -70.5},
        "MOQUEGUA": {"lat": -17.19, "lon": -70.93},
        "PASCO": {"lat": -10.66, "lon": -76.25},
        "PIURA": {"lat": -5.19, "lon": -80.63},
        "PUNO": {"lat": -15.84, "lon": -70.02},
        "SAN MARTIN": {"lat": -7.0, "lon": -76.5},
        "TACNA": {"lat": -18.01, "lon": -70.25},
        "UCAYALI": {"lat": -8.38, "lon": -74.55},
    }

    # ── BADGES ──
    for _, row in dep_data.iterrows():
        coords = DEP_COORDS.get(row["DEPARTAMENTO"], None)
        if coords:
            fig_map.add_trace(go.Scattergeo(
                lon=[coords["lon"]],
                lat=[coords["lat"]],
                mode="markers+text",
                text=[str(row["num_distritos"])],
                textfont=dict(size=10, color="white"),
                marker=dict(
                    size=28,
                    color="#003f7f",
                    line=dict(color="white", width=1)
                ),
                showlegend=False,
                hoverinfo="skip"
            ))

    st.plotly_chart(fig_map, use_container_width=True)

# ── GRÁFICOS CIRCULARES ────────────────────────
with col_charts:
    st.markdown('<div class="section-title">📊 Indicadores de publicación</div>', unsafe_allow_html=True)

    # ── Gráfico 1: Presencia JNE ──────────────────
    jne_col = "PRESENCIA DEL JNE"
    if jne_col in df.columns:
        jne_counts = df[jne_col].fillna("Sin información").str.strip().str.upper()
        jne_counts = jne_counts.replace({"NAN": "Sin información", "": "Sin información"})
        jne_val = jne_counts.value_counts().reset_index()
        jne_val.columns = ["Estado", "Cantidad"]
    else:
        jne_val = pd.DataFrame({"Estado": ["Sin información"], "Cantidad": [len(df)]})

    color_jne = {"SI": "#1a9e5c", "NO": "#c0392b", "SIN INFORMACIÓN": "#aab4c2"}
    fig_jne = px.pie(
        jne_val,
        names="Estado",
        values="Cantidad",
        hole=0.55,
        color="Estado",
        color_discrete_map=color_jne,
        title="Presencia del JNE en la publicación",
    )
    fig_jne.update_traces(textinfo="percent+label", hovertemplate="%{label}: %{value} distritos")
    fig_jne.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=40, b=10),
        title_font=dict(size=12, color="#1a2540"),
        legend=dict(font=dict(size=10)),
        height=220,
        showlegend=True,
    )
    st.plotly_chart(fig_jne, use_container_width=True)

    # ── Gráfico 2: Fecha de inicio de publicación ──
    fecha_col = "FECHA DE INICIO DE PUBLICACIÓN"
    if fecha_col in df.columns:
        fechas = df[fecha_col].dropna()
        if len(fechas) > 0:
            fecha_dist = fechas.dt.strftime("%d/%m/%Y").value_counts().reset_index()
            fecha_dist.columns = ["Fecha", "Cantidad"]
            fecha_dist = fecha_dist.sort_values("Fecha")
        else:
            fecha_dist = pd.DataFrame({"Fecha": ["Sin datos"], "Cantidad": [len(df)]})
    else:
        fecha_dist = pd.DataFrame({"Fecha": ["Sin datos"], "Cantidad": [len(df)]})

    fig_fecha = px.pie(
        fecha_dist,
        names="Fecha",
        values="Cantidad",
        hole=0.55,
        title="Fecha de inicio de publicación",
        color_discrete_sequence=px.colors.sequential.Blues_r,
    )
    fig_fecha.update_traces(textinfo="percent+label", hovertemplate="%{label}: %{value} distritos")
    fig_fecha.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=40, b=10),
        title_font=dict(size=12, color="#1a2540"),
        legend=dict(font=dict(size=10)),
        height=220,
        showlegend=True,
    )
    st.plotly_chart(fig_fecha, use_container_width=True)
    
# ── Tabla de Incidencias por día ──
st.markdown(
    '<div class="section-title" style="margin-top:12px">🚨 Incidencias reportadas</div>',
    unsafe_allow_html=True
)

# Columnas de incidencias
inc_cols = [
    "INCIDENCIAS PREVIAS",
    "INCIDENCIAS (22/04)",
    "INCIDENCIAS (23/04)",
    "INCIDENCIAS (24/04)",
    "INCIDENCIAS (25/04)",
    "INCIDENCIAS (26/04)",
]

# Filtrar solo las que existen en el dataframe
inc_cols = [c for c in inc_cols if c in df.columns]

if len(inc_cols) == 0:
    st.info("No se encontraron columnas de incidencias.", icon="⚠️")
else:

    # 🔥 crear pestañas
    tabs = st.tabs(inc_cols)

    # CSS para texto multilínea
    st.markdown("""
        <style>
        .stDataFrame div[data-testid="stDataFrame"] td {
            white-space: normal !important;
            word-wrap: break-word !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # 🔁 recorrer cada pestaña
    for tab, col in zip(tabs, inc_cols):
        with tab:

            df_inc = df[
                df[col].notna() & (df[col].str.strip() != "")
            ][["DEPARTAMENTO", "DISTRITO", col]].copy()

            df_inc.columns = ["Departamento", "Distrito", "Incidencia"]
            df_inc = df_inc.reset_index(drop=True)

            if len(df_inc) > 0:
                st.dataframe(
                    df_inc,
                    use_container_width=True,
                    height=500,
                    column_config={
                        "Departamento": st.column_config.TextColumn("Departamento", width="small"),
                        "Distrito": st.column_config.TextColumn("Distrito", width="small"),
                        "Incidencia": st.column_config.TextColumn("Incidencia", width="large"),
                    }
                )
            else:
                st.info("Sin incidencias para este día.", icon="✅")

# ─────────────────────────────────────────────
# TABLA CON FILTROS
# ─────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="section-title">📋 Detalle por distrito — Filtros por departamento y provincia</div>', unsafe_allow_html=True)

f1, f2, f3 = st.columns([1, 1, 1])
with f1:
    depts = sorted(df["DEPARTAMENTO"].dropna().unique().tolist())
    sel_dept = st.multiselect("Departamento", depts, placeholder="Todos los departamentos")

with f2:
    if sel_dept:
        provs = sorted(df[df["DEPARTAMENTO"].isin(sel_dept)]["PROVINCIA"].dropna().unique().tolist())
    else:
        provs = sorted(df["PROVINCIA"].dropna().unique().tolist())
    sel_prov = st.multiselect("Provincia", provs, placeholder="Todas las provincias")


# Filtrar
df_tab = df.copy()
if sel_dept:
    df_tab = df_tab[df_tab["DEPARTAMENTO"].isin(sel_dept)]
if sel_prov:
    df_tab = df_tab[df_tab["PROVINCIA"].isin(sel_prov)]
    
# Columnas a mostrar
COLS_TABLA = [
    "DEPARTAMENTO",
    "PROVINCIA",
    "DISTRITO",
    "DESCRIPCIÓN",
    "PRESENCIA DEL JNE",
    "FECHA DE INICIO DE PUBLICACIÓN",
    "FECHA DE FIN DE PUBLICACIÓN",
    "# DE CIUDADANOS ENCUESTADOS",
    "# DE ACTAS DE DEFUNCION (ENTREGADAS POR LA MUNICIPALIDAD)",
    "# DE TACHAS Y RECLAMOS",
]
cols_pres = [c for c in COLS_TABLA if c in df_tab.columns]
df_mostrar = df_tab[cols_pres].reset_index(drop=True)

# Renombrar para tabla compacta
rename_map = {
    "PRESENCIA DEL JNE": "¿Presencia del JNE?",
    "DESCRIPCIÓN":"PERSONAL",
    "FECHA DE INICIO DE PUBLICACIÓN": "F. Inicio",
    "FECHA DE FIN DE PUBLICACIÓN": "F. Fin",
    "# DE CIUDADANOS ENCUESTADOS": "Ciudadanos",
    "# DE ACTAS DE DEFUNCION (ENTREGADAS POR LA MUNICIPALIDAD)": "Actas Def.",
    "# DE TACHAS Y RECLAMOS": "Tachas/Reclamos",
}
df_mostrar = df_mostrar.rename(columns=rename_map)

st.markdown(f"**{len(df_mostrar)} registros** encontrados")
st.dataframe(df_mostrar, use_container_width=True, height=380)

# ─────────────────────────────────────────────
# PIE DE PÁGINA
# ─────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; font-size:0.72rem; color:#aab4c2; margin-top:20px; border-top:1px solid #e0e4ef; padding-top:10px;">
  RENIEC Electoral · Subdirección de Procedimiento Electoral y Georreferenciación (SDPEG) · Dirección de Registro Electoral (DRE)<br>
  Datos actualizados automáticamente cada 5 min
</div>
""", unsafe_allow_html=True)
