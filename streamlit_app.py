import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import datetime
import streamlit.components.v1 as components

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
    .main { background-color: #f4f6fb; }

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

    /* KPI UNIFORMES */
    .kpi-card {
        background: white;
        border-radius: 10px;
        padding: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        text-align: center;
        border-left: 6px solid #004a8f;
        height: 110px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .kpi-card.blue2 { border-left-color: #0072c6; }
    .kpi-card.blue3 { border-left-color: #2f80ed; }
    .kpi-card.blue4 { border-left-color: #56a3ff; }

    .kpi-value { font-size: 1.9rem; font-weight: 800; color: #1a2540; }
    .kpi-label { font-size: 0.72rem; color: #6b7a99; margin-top: 4px; }
    .kpi-sub   { font-size: 0.75rem; color: #0072c6; }

    .section-title {
        font-size: 0.88rem;
        font-weight: 700;
        color: #1a2540;
        text-transform: uppercase;
        border-bottom: 2px solid #004a8f;
        padding-bottom: 4px;
    }

    /* BARRA DE FILTROS GLOBALES */
    .filter-bar {
        background: white;
        border-radius: 10px;
        padding: 14px 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.07);
        margin-bottom: 16px;
        border-left: 6px solid #0072c6;
    }

    /* Estilo radio horizontal compacto */
    div[data-testid="stHorizontalBlock"] .stRadio > label {
        font-size: 0.78rem !important;
        font-weight: 600;
        color: #1a2540;
    }

    #MainMenu, footer { visibility: hidden; }
    .block-container { padding-top: 1rem !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CARGA DE DATOS
# ─────────────────────────────────────────────
from io import BytesIO

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
    df.columns = df.columns.str.strip()

    num_cols = [
        "# DE CIUDADANOS ENCUESTADOS",
        "# DE ACTAS DE DEFUNCION (ENTREGADAS POR LA MUNICIPALIDAD)",
        "# DE TACHAS Y RECLAMOS",
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    date_cols = [
        "FECHA DE INICIO DE PUBLICACIÓN",
        "FECHA DE FIN DE PUBLICACIÓN",
        "FECHA DE ARRIBO AL DISTRITO",
    ]
    for c in date_cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce", dayfirst=True)

    kit_col = "EL PUBLICADOR YA CUENTA CON EL KIT"
    if kit_col in df.columns:
        df["KIT_PUBLICADOR"] = df[kit_col].str.strip().str.upper()

    if "DESCRIPCIÓN" in df.columns:
        df["DESCRIPCIÓN"] = df["DESCRIPCIÓN"].str.strip().str.upper()

    return df

df = limpiar(df_raw)
df["DIST_KEY"] = df["PROVINCIA"].str.strip() + " | " + df["DISTRITO"].str.strip()
df["DEPARTAMENTO"] = df["DEPARTAMENTO"].str.upper().str.strip()
df["DISTRITO"] = df["DISTRITO"].str.strip()

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
    Dashboard actualizado cada 30 seg
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# ★ BARRA DE FILTROS GLOBALES ★
# ─────────────────────────────────────────────
st.markdown('<div class="filter-bar">', unsafe_allow_html=True)
st.markdown("**🔎 Filtros globales** — aplican a KPIs, mapa, gráficos, tabla e incidencias")

fcol1, fcol2, fcol3 = st.columns([1.4, 1, 1.6])

with fcol1:
    # Fechas disponibles en los datos
    fechas_disponibles = (
        df["FECHA DE INICIO DE PUBLICACIÓN"]
        .dropna()
        .dt.normalize()
        .unique()
    )
    fechas_disponibles = sorted(fechas_disponibles)
    etiquetas_fecha = ["Todas las fechas"] + [
        pd.Timestamp(f).strftime("%d/%m/%Y") for f in fechas_disponibles
    ]
    sel_fecha_label = st.radio(
        "📅 Fecha de inicio de publicación",
        etiquetas_fecha,
        horizontal=True,
        key="filtro_fecha",
    )

with fcol2:
    sel_jne = st.radio(
        "👁️ Presencia del JNE",
        ["Todos", "Sí", "No"],
        horizontal=True,
        key="filtro_jne",
    )

with fcol3:
    sel_tipo = st.radio(
        "👤 Tipo de publicador",
        ["Todos", "CONTRATADO", "PERSONAL DRE", "EN AGENCIA"],
        horizontal=True,
        key="filtro_tipo",
    )

st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CONSTRUIR df_filtrado A PARTIR DE LOS 3 FILTROS
# ─────────────────────────────────────────────
df_filtrado = df.copy()

# Filtro 1: Fecha
if sel_fecha_label != "Todas las fechas":
    fecha_sel = pd.to_datetime(sel_fecha_label, dayfirst=True).normalize()
    df_filtrado = df_filtrado[
        df_filtrado["FECHA DE INICIO DE PUBLICACIÓN"].dt.normalize() == fecha_sel
    ]

# Filtro 2: JNE
if sel_jne != "Todos":
    jne_val = "SI" if sel_jne == "Sí" else "NO"
    df_filtrado = df_filtrado[
        df_filtrado["PRESENCIA DEL JNE"].str.strip().str.upper() == jne_val
    ]

# Filtro 3: Tipo publicador
if sel_tipo != "Todos":
    df_filtrado = df_filtrado[df_filtrado["DESCRIPCIÓN"] == sel_tipo]

# Indicador visual de registros activos
n_filtrados = len(df_filtrado)
n_total = len(df)
if n_filtrados < n_total:
    st.info(
        f"🔍 Filtros activos: mostrando **{n_filtrados}** de **{n_total}** registros",
        icon="📊"
    )

# ─────────────────────────────────────────────
# LÓGICA DE NEGOCIO SOBRE df_filtrado
# ─────────────────────────────────────────────
total_distritos = df_filtrado["DIST_KEY"].nunique()

pub_col = next(
    (c for c in df_filtrado.columns if "SE REALIZ" in c.upper() and "PUBLICACI" in c.upper()),
    None
)
if pub_col:
    distritos_publicando = df_filtrado[
        df_filtrado[pub_col].str.strip().str.upper() == "SI"
    ]["DIST_KEY"].nunique()
else:
    distritos_publicando = 0

distritos_agencia    = df_filtrado[df_filtrado["DESCRIPCIÓN"] == "EN AGENCIA"]["DIST_KEY"].nunique()
distritos_contratado = df_filtrado[df_filtrado["DESCRIPCIÓN"] == "CONTRATADO"]["DIST_KEY"].nunique()
distritos_dre        = df_filtrado[df_filtrado["DESCRIPCIÓN"] == "PERSONAL DRE"]["DIST_KEY"].nunique()

ciudadanos_enc = pd.to_numeric(
    df_filtrado.get("# DE CIUDADANOS ENCUESTADOS", pd.Series()), errors="coerce"
).sum()
actas_def = pd.to_numeric(
    df_filtrado.get("# DE ACTAS DE DEFUNCION (ENTREGADAS POR LA MUNICIPALIDAD)", pd.Series()), errors="coerce"
).sum()
tachas_rec = pd.to_numeric(
    df_filtrado.get("# DE TACHAS Y RECLAMOS", pd.Series()), errors="coerce"
).sum()

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
    <div class="kpi-card blue2">
      <div class="kpi-value">{distritos_contratado}</div>
      <div class="kpi-label">PUBLICADORES</div>
      <div class="kpi-sub">Personal externo contratado</div>
    </div>""", unsafe_allow_html=True)

with k3:
    st.markdown(f"""
    <div class="kpi-card blue3">
      <div class="kpi-value">{distritos_dre}</div>
      <div class="kpi-label">PUBLICADORES</div>
      <div class="kpi-sub">Personal DRE</div>
    </div>""", unsafe_allow_html=True)

with k4:
    st.markdown(f"""
    <div class="kpi-card blue4">
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
# STORY CARD: AVANCE DE PUBLICACIÓN
# ─────────────────────────────────────────────
total_distritos_global = df["DIST_KEY"].nunique()  # siempre sobre base completa
porc_publicacion = (
    distritos_publicando / total_distritos_global * 100
    if total_distritos_global else 0
)

components.html(f"""
<div style="
    background:white;
    border-radius:12px;
    padding:18px 20px;
    box-shadow:0 2px 10px rgba(0,0,0,0.08);
    border-left:6px solid #1a9e5c;
    font-family:sans-serif;
    margin-bottom:14px;
">
    <div style="font-size:0.85rem;font-weight:700;color:#1a2540;margin-bottom:10px;">
        📍 Avance de publicación de LPI
        {"&nbsp;&nbsp;<span style='font-size:0.75rem;color:#0072c6;font-weight:400;'>(" + sel_fecha_label + " · JNE: " + sel_jne + " · Tipo: " + sel_tipo + ")</span>" if any(x != y for x, y in [
            (sel_fecha_label, "Todas las fechas"), (sel_jne, "Todos"), (sel_tipo, "Todos")
        ]) else ""}
    </div>
    <div style="display:flex;justify-content:space-between;align-items:baseline;">
        <div style="font-size:2.3rem;font-weight:800;">{distritos_publicando}</div>
        <div style="font-size:1.1rem;font-weight:600;color:#1a9e5c;">{porc_publicacion:.1f}%</div>
    </div>
    <div style="font-size:0.8rem;color:#6b7a99;margin-top:6px;">
        de {total_distritos_global} distritos a nivel nacional
    </div>
    <div style="margin-top:12px;background:#e6ecf5;border-radius:10px;height:10px;overflow:hidden;">
        <div style="width:{porc_publicacion}%;height:10px;background:linear-gradient(90deg,#56a3ff,#1a9e5c);"></div>
    </div>
</div>
""", height=140)

# ─────────────────────────────────────────────
# FILA PRINCIPAL: MAPA + GRÁFICOS
# ─────────────────────────────────────────────
col_mapa, col_charts = st.columns([2.2, 1], gap="medium")

# ── MAPA ──────────────────────────────────────
with col_mapa:
    st.markdown(
        '<div class="section-title">🗺️ Mapa de distritos por departamento</div>',
        unsafe_allow_html=True
    )

    with open("peru_departamental_simple.geojson", "r", encoding="utf-8") as f:
        geojson = json.load(f)

    # El mapa usa df_filtrado (ya viene filtrado por JNE y fecha)
    # El selector de tipo aquí solo sirve de referencia visual adicional
    # (el filtro global ya aplica)
    df_map = df_filtrado.copy()

    def lista_distritos(x):
        distritos = sorted(x.dropna().unique())
        MAX = 20
        if len(distritos) > MAX:
            return "<br>".join(distritos[:MAX]) + f"<br>... (+{len(distritos)-MAX} más)"
        return "<br>".join(distritos)

    dep_data = (
        df_map
        .groupby("DEPARTAMENTO")
        .agg(
            num_distritos=("DISTRITO", "nunique"),
            distritos=("DISTRITO", lista_distritos)
        )
        .reset_index()
    )

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

    fig_map.update_traces(
        hovertemplate=(
            "<b>%{location}</b><br>"
            "Distritos: %{z}<br><br>"
            "<b>Listado:</b><br>%{customdata}<extra></extra>"
        ),
        customdata=dep_data["distritos"]
    )

    fig_map.update_geos(fitbounds="locations", visible=False, projection_scale=4.2)
    fig_map.update_layout(
        height=650,
        margin=dict(l=0, r=0, t=0, b=0),
        coloraxis_colorbar=dict(title="N° distritos"),
    )

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

    for _, row in dep_data.iterrows():
        coords = DEP_COORDS.get(row["DEPARTAMENTO"], None)
        if coords:
            fig_map.add_trace(go.Scattergeo(
                lon=[coords["lon"]],
                lat=[coords["lat"]],
                mode="markers+text",
                text=[str(row["num_distritos"])],
                textfont=dict(size=10, color="white"),
                marker=dict(size=28, color="#003f7f", line=dict(color="white", width=1)),
                showlegend=False,
                hoverinfo="skip"
            ))

    st.plotly_chart(fig_map, use_container_width=True)

# ── GRÁFICOS CIRCULARES ────────────────────────
with col_charts:
    st.markdown(
        '<div class="section-title">📊 Indicadores de publicación</div>',
        unsafe_allow_html=True
    )

    # Base: 1 fila por distrito sobre df_filtrado
    df_dist = df_filtrado.groupby("DIST_KEY", as_index=False).agg({
        "PRESENCIA DEL JNE": "first",
        "FECHA DE INICIO DE PUBLICACIÓN": "min",
    })

    # ── Gráfico 1: Presencia JNE ──
    jne_col = "PRESENCIA DEL JNE"
    if jne_col in df_dist.columns:
        jne_counts = (
            df_dist[jne_col]
            .fillna("Sin información")
            .str.strip()
            .str.upper()
            .replace({"NAN": "SIN INFORMACIÓN", "": "SIN INFORMACIÓN"})
        )
        jne_val_df = jne_counts.value_counts().reset_index()
        jne_val_df.columns = ["Estado", "Cantidad"]
    else:
        jne_val_df = pd.DataFrame({"Estado": ["Sin información"], "Cantidad": [total_distritos]})

    color_jne = {"SI": "#1a9e5c", "NO": "#c0392b", "SIN INFORMACIÓN": "#aab4c2"}

    fig_jne = px.pie(
        jne_val_df,
        names="Estado",
        values="Cantidad",
        hole=0.55,
        color="Estado",
        color_discrete_map=color_jne,
        title="Presencia del JNE en la publicación",
    )
    fig_jne.update_traces(
        textinfo="percent+label",
        hovertemplate="%{label}: %{value} distritos"
    )
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
    if fecha_col in df_dist.columns:
        fechas = df_dist[fecha_col].dropna()
        if len(fechas) > 0:
            fecha_dist = (
                fechas.dt.strftime("%d/%m/%Y")
                .value_counts()
                .reset_index()
            )
            fecha_dist.columns = ["Fecha", "Cantidad"]
            fecha_dist = fecha_dist.sort_values("Fecha")
        else:
            fecha_dist = pd.DataFrame({"Fecha": ["Sin datos"], "Cantidad": [total_distritos]})
    else:
        fecha_dist = pd.DataFrame({"Fecha": ["Sin datos"], "Cantidad": [total_distritos]})

    fig_fecha = px.pie(
        fecha_dist,
        names="Fecha",
        values="Cantidad",
        hole=0.55,
        title="Fecha de inicio de publicación",
        color_discrete_sequence=px.colors.sequential.Blues_r,
    )
    fig_fecha.update_traces(
        textinfo="percent+label",
        hovertemplate="%{label}: %{value} distritos"
    )
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

# ─────────────────────────────────────────────
# TABLA DE INCIDENCIAS
# ─────────────────────────────────────────────
st.markdown(
    '<div class="section-title" style="margin-top:12px">🚨 Incidencias reportadas</div>',
    unsafe_allow_html=True
)

inc_cols = [
    "INCIDENCIAS PREVIAS",
    "INCIDENCIAS (22/04)",
    "INCIDENCIAS (23/04)",
    "INCIDENCIAS (24/04)",
    "INCIDENCIAS (25/04)",
    "INCIDENCIAS (26/04)",
]
inc_cols = [c for c in inc_cols if c in df_filtrado.columns]

if len(inc_cols) == 0:
    st.info("No se encontraron columnas de incidencias.", icon="⚠️")
else:
    tabs = st.tabs(inc_cols)

    st.markdown("""
        <style>
        .stDataFrame div[data-testid="stDataFrame"] td {
            white-space: normal !important;
            word-wrap: break-word !important;
        }
        </style>
    """, unsafe_allow_html=True)

    for tab, col in zip(tabs, inc_cols):
        with tab:
            df_inc = df_filtrado[
                df_filtrado[col].notna() & (df_filtrado[col].astype(str).str.strip() != "")
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
                st.info("Sin incidencias para este día (con los filtros activos).", icon="✅")

# ─────────────────────────────────────────────
# TABLA CON FILTROS ADICIONALES (Depto / Provincia)
# ─────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    '<div class="section-title">📋 Detalle por distrito — Filtros por departamento y provincia</div>',
    unsafe_allow_html=True
)

f1, f2, f3 = st.columns([1, 1, 1])
with f1:
    depts = sorted(df_filtrado["DEPARTAMENTO"].dropna().unique().tolist())
    sel_dept = st.multiselect("Departamento", depts, placeholder="Todos los departamentos")

with f2:
    if sel_dept:
        provs = sorted(
            df_filtrado[df_filtrado["DEPARTAMENTO"].isin(sel_dept)]["PROVINCIA"]
            .dropna().unique().tolist()
        )
    else:
        provs = sorted(df_filtrado["PROVINCIA"].dropna().unique().tolist())
    sel_prov = st.multiselect("Provincia", provs, placeholder="Todas las provincias")

# Filtrar tabla desde df_filtrado
df_tab = df_filtrado.copy()
if sel_dept:
    df_tab = df_tab[df_tab["DEPARTAMENTO"].isin(sel_dept)]
if sel_prov:
    df_tab = df_tab[df_tab["PROVINCIA"].isin(sel_prov)]

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

rename_map = {
    "PRESENCIA DEL JNE": "¿Presencia del JNE?",
    "DESCRIPCIÓN": "PERSONAL",
    "FECHA DE INICIO DE PUBLICACIÓN": "F. Inicio",
    "FECHA DE FIN DE PUBLICACIÓN": "F. Fin",
    "# DE CIUDADANOS ENCUESTADOS": "Ciudadanos encuestados",
    "# DE ACTAS DE DEFUNCION (ENTREGADAS POR LA MUNICIPALIDAD)": "# Actas Def.",
    "# DE TACHAS Y RECLAMOS": "# Tachas/Reclamos",
}
df_mostrar = df_mostrar.rename(columns=rename_map)

st.markdown(f"**{len(df_mostrar)} registros** encontrados")
st.dataframe(df_mostrar, use_container_width=True, height=380)

# ─────────────────────────────────────────────
# PIE DE PÁGINA
# ─────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; font-size:0.72rem; color:#aab4c2; margin-top:20px;
            border-top:1px solid #e0e4ef; padding-top:10px;">
  RENIEC Electoral · Subdirección de Procedimiento Electoral y Georreferenciación (SDPEG)
  · Dirección de Registro Electoral (DRE)<br>
  Datos actualizados automáticamente cada 30 seg
</div>
""", unsafe_allow_html=True)
