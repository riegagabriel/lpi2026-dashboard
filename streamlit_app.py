import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
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
# CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #f4f6fb; }
    .header-bar {
        background: linear-gradient(90deg, #004a8f 0%, #0072c6 100%);
        color: white; padding: 18px 30px 14px 30px;
        border-radius: 10px; margin-bottom: 18px;
        display: flex; align-items: center; justify-content: space-between;
    }
    .kpi-card {
        background: white; border-radius: 10px; padding: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center;
        border-left: 6px solid #004a8f; height: 110px;
        display: flex; flex-direction: column; justify-content: center;
    }
    .kpi-card.blue2 { border-left-color: #0072c6; }
    .kpi-card.blue3 { border-left-color: #2f80ed; }
    .kpi-card.blue4 { border-left-color: #56a3ff; }
    .kpi-card.green { border-left-color: #1a9e5c; }
    .kpi-value { font-size: 1.9rem; font-weight: 800; color: #1a2540; }
    .kpi-label { font-size: 0.72rem; color: #6b7a99; margin-top: 4px; }
    .kpi-sub   { font-size: 0.75rem; color: #0072c6; }
    .section-title {
        font-size: 0.88rem; font-weight: 700; color: #1a2540;
        text-transform: uppercase; border-bottom: 2px solid #004a8f; padding-bottom: 4px;
    }
    .filter-bar {
        background: white; border-radius: 10px; padding: 14px 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.07);
        margin-bottom: 16px; border-left: 6px solid #0072c6;
    }
    #MainMenu, footer { visibility: hidden; }
    .block-container { padding-top: 1rem !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CARGA DE DATOS
# ─────────────────────────────────────────────

RUTA_EXCEL = "MONITOREO_LPI.xlsx"

@st.cache_data(ttl=30)
def cargar_datos(ruta: str) -> pd.DataFrame:
    try:
        df = pd.read_excel(ruta, dtype=str)
    except Exception as e:
        st.error(f"No se pudo cargar el archivo Excel: {e}")
        st.stop()
    return df

df_raw = cargar_datos(RUTA_EXCEL)

# ─────────────────────────────────────────────
# LIMPIEZA
# ─────────────────────────────────────────────
def limpiar(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.str.strip()
    for c in ["# DE CIUDADANOS QUE SE HAN ACERCADO A LA LPI",
              "# DE CIUDADANOS QUE SE LES HA APLICADO LA ENCUESTA CIUDADANA",
              "# DE ACTAS DE DEFUNCION (ENTREGADAS POR LA MUNICIPALIDAD)",
              "# DE TACHAS Y ELIMINACIÓN",
              "# DE RECLAMOS"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in ["FECHA DE INICIO DE PUBLICACIÓN",
              "FECHA DE FIN DE PUBLICACIÓN",
              "FECHA DE ARRIBO AL DISTRITO"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce", dayfirst=True)
    if "DESCRIPCIÓN" in df.columns:
        df["DESCRIPCIÓN"] = df["DESCRIPCIÓN"].str.strip().str.upper()
    if "PRESENCIA DEL JNE" in df.columns:
        df["PRESENCIA DEL JNE"] = df["PRESENCIA DEL JNE"].str.strip().str.upper()
    if "¿SE REALIZÓ LA PUBLICACIÓN?" in df.columns:
        df["¿SE REALIZÓ LA PUBLICACIÓN?"] = df["¿SE REALIZÓ LA PUBLICACIÓN?"].str.strip().str.upper()
    return df

df = limpiar(df_raw)
# ─────────────────────────────────────────────
# LIMPIEZA DE FECHAS INVÁLIDAS
# ─────────────────────────────────────────────
fecha_min = pd.to_datetime("22/04/2026", dayfirst=True)
fecha_max = pd.to_datetime("28/04/2026", dayfirst=True)

df = df[
    (df["FECHA DE INICIO DE PUBLICACIÓN"].isna()) |
    (
        (df["FECHA DE INICIO DE PUBLICACIÓN"] >= fecha_min) &
        (df["FECHA DE INICIO DE PUBLICACIÓN"] <= fecha_max)
    )
]

df["DEPARTAMENTO"] = df["DEPARTAMENTO"].str.upper().str.strip()
df["DISTRITO"]     = df["DISTRITO"].str.strip()
df["PROVINCIA"]    = df["PROVINCIA"].str.strip()
df["DIST_KEY"]     = df["UBIGEO RENIEC"].astype(str).str.strip()

# ─────────────────────────────────────────────
# KPIs FIJOS — toda la base, 1 fila por distrito
# ─────────────────────────────────────────────
df_dist_global = (
    df.sort_values("DESCRIPCIÓN")
    .groupby("DIST_KEY", as_index=False)
    .agg(DESCRIPCION=("DESCRIPCIÓN", "first"))
)

TOTAL_DISTRITOS_GLOBAL = df_dist_global["DIST_KEY"].nunique()
KPI_CONTRATADO         = (df_dist_global["DESCRIPCION"] == "CONTRATADO").sum()
KPI_DRE                = (df_dist_global["DESCRIPCION"] == "PERSONAL DRE").sum()
KPI_AGENCIA            = (df_dist_global["DESCRIPCION"] == "EN AGENCIA").sum()

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
# FILTROS GLOBALES
# ─────────────────────────────────────────────
st.markdown('<div class="filter-bar">', unsafe_allow_html=True)
st.markdown("**🔎 Filtros globales**")
st.caption("ℹ️ Los filtros aplicados afectan únicamente a los indicadores, gráficos y tablas dinámicas mostradas a continuación. Nuestros indicadores generales se mantienen a nivel nacional.")

fcol1, fcol2 = st.columns([1.6, 1])

with fcol1:
    fechas_disponibles = sorted(
        df["FECHA DE INICIO DE PUBLICACIÓN"].dropna().dt.normalize().unique()
    )
    etiquetas_fecha = ["Todas las fechas"] + [
        pd.Timestamp(f).strftime("%d/%m/%Y") for f in fechas_disponibles
    ]
    sel_fecha_label = st.radio(
        "📅 Fecha de inicio de publicación",
        etiquetas_fecha, horizontal=True, key="filtro_fecha",
    )

with fcol2:
    sel_jne = st.radio(
        "👁️ Presencia del JNE",
        ["Todos", "Sí", "No"], horizontal=True, key="filtro_jne",
    )

st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CONSTRUIR df_filtrado y df_dist_filtrado
# ─────────────────────────────────────────────
df_filtrado = df.copy()

if sel_fecha_label != "Todas las fechas":
    fecha_sel = pd.to_datetime(sel_fecha_label, dayfirst=True).normalize()
    df_filtrado = df_filtrado[
        df_filtrado["FECHA DE INICIO DE PUBLICACIÓN"].dt.normalize() == fecha_sel
    ]

if sel_jne != "Todos":
    jne_val = "SI" if sel_jne == "Sí" else "NO"
    df_filtrado = df_filtrado[
        df_filtrado["PRESENCIA DEL JNE"] == jne_val
    ]

# 1 fila por distrito dentro del conjunto filtrado
df_dist_filtrado = (
    df_filtrado.sort_values("DESCRIPCIÓN")
    .groupby("DIST_KEY", as_index=False)
    .agg(
        DESCRIPCION =("DESCRIPCIÓN",                    "first"),
        JNE         =("PRESENCIA DEL JNE",              "first"),
        SE_REALIZO  =("¿SE REALIZÓ LA PUBLICACIÓN?",    "first"),
        FECHA_INICIO=("FECHA DE INICIO DE PUBLICACIÓN", "min"),
        CIUDADANOS  =("# DE CIUDADANOS QUE SE HAN ACERCADO A LA LPI", "sum"),
        ACTAS_DEF   =("# DE ACTAS DE DEFUNCION (ENTREGADAS POR LA MUNICIPALIDAD)", "sum"),
        TACHAS      =("# DE TACHAS Y ELIMINACIÓN",         "sum"),
        DEPARTAMENTO=("DEPARTAMENTO",                   "first"),
        PROVINCIA   =("PROVINCIA",                      "first"),
        DISTRITO    =("DISTRITO",                       "first"),
    )
)

# KPIs dinámicos
distritos_publicando = (df_dist_filtrado["SE_REALIZO"] == "SI").sum()
ciudadanos_enc       = df_dist_filtrado["CIUDADANOS"].sum()
actas_def            = df_dist_filtrado["ACTAS_DEF"].sum()
tachas_rec           = df_dist_filtrado["TACHAS"].sum()

# ─────────────────────────────────────────────
# FILA ÚNICA DE KPIs (4 fijos + 3 dinámicos)
# ─────────────────────────────────────────────
k1, k2, k3, k4, k5, k6, k7 = st.columns(7)

with k1:
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-value">{TOTAL_DISTRITOS_GLOBAL}</div>
      <div class="kpi-label">Total Distritos</div>
      <div class="kpi-sub">a nivel nacional</div>
    </div>""", unsafe_allow_html=True)

with k2:
    st.markdown(f"""
    <div class="kpi-card blue2">
      <div class="kpi-value">{KPI_CONTRATADO}</div>
      <div class="kpi-label">PUBLICADORES</div>
      <div class="kpi-sub">Personal externo contratado</div>
    </div>""", unsafe_allow_html=True)

with k3:
    st.markdown(f"""
    <div class="kpi-card blue3">
      <div class="kpi-value">{KPI_DRE}</div>
      <div class="kpi-label">PUBLICADORES</div>
      <div class="kpi-sub">Personal DRE</div>
    </div>""", unsafe_allow_html=True)

with k4:
    st.markdown(f"""
    <div class="kpi-card blue4">
      <div class="kpi-value">{KPI_AGENCIA}</div>
      <div class="kpi-label">DISTRITOS</div>
      <div class="kpi-sub">Con Publicación en agencia</div>
    </div>""", unsafe_allow_html=True)

with k5:
    st.markdown(f"""
    <div class="kpi-card green">
      <div class="kpi-value">{int(ciudadanos_enc) if not pd.isna(ciudadanos_enc) else '—'}</div>
      <div class="kpi-label">Ciudadanos que se han acerdado a la LPI</div>
      <div class="kpi-sub">total nacional</div>
    </div>""", unsafe_allow_html=True)

with k6:
    st.markdown(f"""
    <div class="kpi-card green">
      <div class="kpi-value">{int(actas_def) if not pd.isna(actas_def) else '—'}</div>
      <div class="kpi-label">Actas de Defunción</div>
      <div class="kpi-sub">entregadas municipalidad</div>
    </div>""", unsafe_allow_html=True)

with k7:
    st.markdown(f"""
    <div class="kpi-card green">
      <div class="kpi-value">{int(tachas_rec) if not pd.isna(tachas_rec) else '—'}</div>
      <div class="kpi-label">Tachas y Eliminación</div>
      <div class="kpi-sub">presentados</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# BARRA DE AVANCE — dinámica
# ─────────────────────────────────────────────
porc_publicacion = (
    distritos_publicando / TOTAL_DISTRITOS_GLOBAL * 100
    if TOTAL_DISTRITOS_GLOBAL else 0
)

components.html(f"""
<div style="background:white;border-radius:12px;padding:18px 20px;
    box-shadow:0 2px 10px rgba(0,0,0,0.08);border-left:6px solid #1a9e5c;
    font-family:sans-serif;margin-bottom:14px;">
    <div style="font-size:0.85rem;font-weight:700;color:#1a2540;margin-bottom:10px;">
        📍 Avance de publicación de LPI
    </div>
    <div style="display:flex;justify-content:space-between;align-items:baseline;">
        <div style="font-size:2.3rem;font-weight:800;">{distritos_publicando}</div>
        <div style="font-size:1.1rem;font-weight:600;color:#1a9e5c;">{porc_publicacion:.1f}%</div>
    </div>
    <div style="font-size:0.8rem;color:#6b7a99;margin-top:6px;">
        distritos confirmaron publicación · de {TOTAL_DISTRITOS_GLOBAL} a nivel nacional
    </div>
    <div style="margin-top:12px;background:#e6ecf5;border-radius:10px;height:10px;overflow:hidden;">
        <div style="width:{porc_publicacion}%;height:10px;
                    background:linear-gradient(90deg,#56a3ff,#1a9e5c);"></div>
    </div>
</div>
""", height=140)

# ─────────────────────────────────────────────
# MAPA + GRÁFICOS — dinámicos
# ─────────────────────────────────────────────
col_mapa, col_charts = st.columns([2.2, 1], gap="medium")

with col_mapa:
    st.markdown(
        '<div class="section-title">🗺️ Mapa de distritos por departamento</div>',
        unsafe_allow_html=True
    )

    with open("peru_departamental_simple.geojson", "r", encoding="utf-8") as f:
        geojson = json.load(f)

    modo_mapa = st.selectbox(
        "Tipo de publicación (solo mapa)",
        ["Todos", "PERSONAL DRE", "CONTRATADO", "EN AGENCIA"]
    )

    df_map = df_filtrado.copy()
    if modo_mapa != "Todos":
        df_map = df_map[df_map["DESCRIPCIÓN"] == modo_mapa]

    def lista_distritos(x):
        distritos = sorted(x.dropna().unique())
        MAX = 20
        if len(distritos) > MAX:
            return "<br>".join(distritos[:MAX]) + f"<br>... (+{len(distritos)-MAX} más)"
        return "<br>".join(distritos)

    dep_data = (
        df_map.groupby("DEPARTAMENTO")
        .agg(num_distritos=("DISTRITO", "nunique"), distritos=("DISTRITO", lista_distritos))
        .reset_index()
    )

    fig_map = px.choropleth(
        dep_data, geojson=geojson,
        locations="DEPARTAMENTO", featureidkey="properties.NOMBDEP",
        color="num_distritos",
        color_continuous_scale=[[0,"#dce6f2"],[0.5,"#6ea8fe"],[1,"#003f7f"]],
    )
    fig_map.update_traces(
        hovertemplate=(
            "<b>%{location}</b><br>Distritos: %{z}<br><br>"
            "<b>Listado:</b><br>%{customdata}<extra></extra>"
        ),
        customdata=dep_data["distritos"]
    )
    fig_map.update_geos(fitbounds="locations", visible=False, projection_scale=4.2)
    fig_map.update_layout(
        height=650, margin=dict(l=0,r=0,t=0,b=0),
        coloraxis_colorbar=dict(title="N° distritos"),
    )

    DEP_COORDS = {
        "AMAZONAS":     {"lat":-5.5,  "lon":-78.1},
        "ANCASH":       {"lat":-9.53, "lon":-77.53},
        "APURIMAC":     {"lat":-14.05,"lon":-73.09},
        "AREQUIPA":     {"lat":-16.41,"lon":-71.54},
        "AYACUCHO":     {"lat":-13.16,"lon":-74.22},
        "CAJAMARCA":    {"lat":-7.16, "lon":-78.51},
        "CUSCO":        {"lat":-13.52,"lon":-71.97},
        "HUANCAVELICA": {"lat":-12.79,"lon":-74.97},
        "HUANUCO":      {"lat":-9.93, "lon":-76.24},
        "ICA":          {"lat":-14.07,"lon":-75.73},
        "JUNIN":        {"lat":-11.16,"lon":-75.23},
        "LA LIBERTAD":  {"lat":-8.12, "lon":-78.12},
        "LAMBAYEQUE":   {"lat":-6.77, "lon":-79.84},
        "LIMA":         {"lat":-12.04,"lon":-76.95},
        "LORETO":       {"lat":-4.0,  "lon":-75.0},
        "MADRE DE DIOS":{"lat":-11.0, "lon":-70.5},
        "MOQUEGUA":     {"lat":-17.19,"lon":-70.93},
        "PASCO":        {"lat":-10.66,"lon":-76.25},
        "PIURA":        {"lat":-5.19, "lon":-80.63},
        "PUNO":         {"lat":-15.84,"lon":-70.02},
        "SAN MARTIN":   {"lat":-7.0,  "lon":-76.5},
        "TACNA":        {"lat":-18.01,"lon":-70.25},
        "UCAYALI":      {"lat":-8.38, "lon":-74.55},
    }

    for _, row in dep_data.iterrows():
        coords = DEP_COORDS.get(row["DEPARTAMENTO"])
        if coords:
            fig_map.add_trace(go.Scattergeo(
                lon=[coords["lon"]], lat=[coords["lat"]],
                mode="markers+text", text=[str(row["num_distritos"])],
                textfont=dict(size=10, color="white"),
                marker=dict(size=28, color="#003f7f", line=dict(color="white", width=1)),
                showlegend=False, hoverinfo="skip"
            ))

    st.plotly_chart(fig_map, use_container_width=True)

with col_charts:
    st.markdown(
        '<div class="section-title">📊 Indicadores de publicación</div>',
        unsafe_allow_html=True
    )

    # ─────────────────────────────────────────────
    # Gráfico: Lugar de publicación (Barras horizontales)
    # ─────────────────────────────────────────────

    df_filtrado["LUGAR DE LA PUBLICACIÓN"] = (
        df_filtrado["LUGAR DE LA PUBLICACIÓN"]
        .astype(str)
        .str.strip()
        .str.title()
    )

    df_filtrado["LUGAR DE LA PUBLICACIÓN"] = df_filtrado["LUGAR DE LA PUBLICACIÓN"].replace({
        "Local Vecinal ": "Local Vecinal",
        "Comunidad Vecinal ": "Comunidad Vecinal",
        "Sub Prefectura": "Subprefectura",
    })

    lugar_counts = (
    df_filtrado["LUGAR DE LA PUBLICACIÓN"]
    .replace("", pd.NA)
    .dropna()
    .value_counts()
    .reset_index()
    )
    lugar_counts.columns = ["Lugar", "Cantidad"]

    otros = lugar_counts[lugar_counts["Lugar"] == "Otros"]
    resto = lugar_counts[lugar_counts["Lugar"] != "Otros"]
    resto = resto.sort_values("Cantidad", ascending=True)

    lugar_counts = pd.concat([resto, otros], ignore_index=True)

    fig_lugar = px.bar(
        lugar_counts,
        x="Cantidad",
        y="Lugar",
        orientation="h",
        title="Lugar de la publicación",
        color="Cantidad",
        color_continuous_scale="Blues"
    )

    fig_lugar.update_layout(
        height=350,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis_title="",
        xaxis_title="N° de publicaciones",
    )

    st.plotly_chart(fig_lugar, use_container_width=True)

    # ─────────────────────────────────────────────
    # Gráfico 1: Presencia JNE
    # ─────────────────────────────────────────────
    jne_counts = (
        df_dist_filtrado["JNE"]
        .fillna("SIN INFORMACIÓN").str.strip().str.upper()
        .replace({"NAN":"SIN INFORMACIÓN","":"SIN INFORMACIÓN"})
        .value_counts().reset_index()
    )
    jne_counts.columns = ["Estado", "Cantidad"]

    fig_jne = px.pie(
        jne_counts, names="Estado", values="Cantidad", hole=0.55,
        color="Estado",
        color_discrete_map={"SI":"#1a9e5c","NO":"#c0392b","SIN INFORMACIÓN":"#aab4c2"},
        title="Presencia del JNE en la publicación",
    )
    fig_jne.update_traces(textinfo="percent+label", hovertemplate="%{label}: %{value} distritos")
    fig_jne.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10,r=10,t=40,b=10),
        title_font=dict(size=12,color="#1a2540"),
        legend=dict(font=dict(size=10)), height=220, showlegend=True,
    )
    st.plotly_chart(fig_jne, use_container_width=True)

    # ─────────────────────────────────────────────
    # Gráfico 2: Fecha de inicio
    # ─────────────────────────────────────────────
    fechas_dist = df_dist_filtrado["FECHA_INICIO"].dropna()
    if len(fechas_dist) > 0:
        fecha_dist_df = (
            fechas_dist.dt.strftime("%d/%m/%Y")
            .value_counts().reset_index()
        )
        fecha_dist_df.columns = ["Fecha", "Cantidad"]
        fecha_dist_df = fecha_dist_df.sort_values("Fecha")
    else:
        fecha_dist_df = pd.DataFrame({"Fecha":["Sin datos"], "Cantidad":[0]})

    fig_fecha = px.pie(
        fecha_dist_df, names="Fecha", values="Cantidad", hole=0.55,
        title="Fecha de inicio de publicación",
        color_discrete_sequence=px.colors.sequential.Blues_r,
    )
    fig_fecha.update_traces(textinfo="percent+label", hovertemplate="%{label}: %{value} distritos")
    fig_fecha.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10,r=10,t=40,b=10),
        title_font=dict(size=12,color="#1a2540"),
        legend=dict(font=dict(size=10)), height=220, showlegend=True,
    )
    st.plotly_chart(fig_fecha, use_container_width=True)

# ─────────────────────────────────────────────
# INCIDENCIAS — dinámicas
# ─────────────────────────────────────────────
st.markdown(
    '<div class="section-title" style="margin-top:12px">🚨 Incidencias reportadas</div>',
    unsafe_allow_html=True
)

inc_cols = [c for c in [
    "INCIDENCIAS PREVIAS","INCIDENCIAS (22/04)","INCIDENCIAS (23/04)",
    "INCIDENCIAS (24/04)","INCIDENCIAS (25/04)","INCIDENCIAS (26/04)",
] if c in df_filtrado.columns]

if not inc_cols:
    st.info("No se encontraron columnas de incidencias.", icon="⚠️")
else:
    st.markdown("""
        <style>
        .stDataFrame div[data-testid="stDataFrame"] td {
            white-space: normal !important; word-wrap: break-word !important;
        }
        </style>
    """, unsafe_allow_html=True)
    for tab, col in zip(st.tabs(inc_cols), inc_cols):
        with tab:
            df_inc = df_filtrado[
                df_filtrado[col].notna() &
                (df_filtrado[col].astype(str).str.strip() != "")
            ][["DEPARTAMENTO","DISTRITO", col]].copy()
            df_inc.columns = ["Departamento","Distrito","Incidencia"]
            df_inc = df_inc.reset_index(drop=True)
            if len(df_inc) > 0:
                st.dataframe(
                    df_inc, use_container_width=True, height=500,
                    column_config={
                        "Departamento": st.column_config.TextColumn("Departamento", width="small"),
                        "Distrito":     st.column_config.TextColumn("Distrito",     width="small"),
                        "Incidencia":   st.column_config.TextColumn("Incidencia",   width="large"),
                    }
                )
            else:
                st.info("Sin incidencias para este día.", icon="✅")

# ─────────────────────────────────────────────
# TABLA DETALLE — dinámica, 1 fila por distrito
# ─────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    '<div class="section-title">📋 Detalle por distrito — Filtros por departamento y provincia</div>',
    unsafe_allow_html=True
)

f1, f2, _ = st.columns([1, 1, 1])
with f1:
    depts = sorted(df_dist_filtrado["DEPARTAMENTO"].dropna().unique().tolist())
    sel_dept = st.multiselect("Departamento", depts, placeholder="Todos los departamentos")
with f2:
    base_prov = (
        df_dist_filtrado[df_dist_filtrado["DEPARTAMENTO"].isin(sel_dept)]
        if sel_dept else df_dist_filtrado
    )
    provs = sorted(base_prov["PROVINCIA"].dropna().unique().tolist())
    sel_prov = st.multiselect("Provincia", provs, placeholder="Todas las provincias")

df_tab = df_dist_filtrado.copy()
if sel_dept:
    df_tab = df_tab[df_tab["DEPARTAMENTO"].isin(sel_dept)]
if sel_prov:
    df_tab = df_tab[df_tab["PROVINCIA"].isin(sel_prov)]

df_mostrar = df_tab.rename(columns={
    "DESCRIPCION":  "PERSONAL",
    "JNE":          "¿Presencia del JNE?",
    "FECHA_INICIO": "F. Inicio",
    "CIUDADANOS":   "# de Ciudadanos que se han acercado a LPI",  # ✅ CORRECTO
    "ACTAS_DEF":    "# Actas Def.",
    "TACHAS":       "# Tachas/Reclamos",
})[[
    "DEPARTAMENTO","PROVINCIA","DISTRITO","PERSONAL",
    "¿Presencia del JNE?","F. Inicio",
    "# de Ciudadanos que se han acercado a LPI",
    "# Actas Def.","# Tachas/Reclamos"
]].reset_index(drop=True)

st.markdown(f"**{len(df_mostrar)} distritos** encontrados")
st.dataframe(df_mostrar, use_container_width=True, height=380)

# ─────────────────────────────────────────────
# PIE DE PÁGINA
# ─────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;font-size:0.72rem;color:#aab4c2;margin-top:20px;
            border-top:1px solid #e0e4ef;padding-top:10px;">
  RENIEC Electoral · Subdirección de Procedimiento Electoral y Georreferenciación (SDPEG)
  · Dirección de Registro Electoral (DRE)<br>
  Datos actualizados automáticamente cada 30 seg
</div>
""", unsafe_allow_html=True)
