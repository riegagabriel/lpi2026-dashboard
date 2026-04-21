import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import requests
from io import StringIO
import datetime

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

# Clave única por distrito: Provincia + Distrito
df["DIST_KEY"] = df["PROVINCIA"].str.strip() + " | " + df["DISTRITO"].str.strip()

# Total distritos únicos (ahora son 404)
total_distritos = df["DIST_KEY"].nunique()

# Distritos publicando: basado en la columna "¿SE REALIZÓ LA PUBLICACIÓN?"
pub_col = next((c for c in df.columns if "SE REALIZ" in c and "PUBLICACI" in c), None)
if pub_col:
    distritos_publicando = df[df[pub_col].str.strip().str.upper() == "SI"]["DIST_KEY"].nunique()
else:
    distritos_publicando = 0

# Distritos EN AGENCIA: basado en columna DESCRIPCIÓN
df["PUBLICA_AGENCIA"] = df["DESCRIPCIÓN"] == "EN AGENCIA"
distritos_agencia = df[df["PUBLICA_AGENCIA"]]["DIST_KEY"].nunique()

# Publicación con publicador = CONTRATADO o PERSONAL DRE
df["PUBLICA"] = df["DESCRIPCIÓN"].isin(["CONTRATADO", "PERSONAL DRE"])
df["CON_PUBLICADOR"] = df["PUBLICA"]

# Kit entregado y publicación confirmada
kit_ok = df.get("EL PUBLICADOR YA CUENTA CON EL KIT", pd.Series(dtype=str)).str.strip().str.upper() == "SI"
df["PUBLICACION_CONFIRMADA"] = df["PUBLICA"] & kit_ok
distritos_publicador = df[df["CON_PUBLICADOR"]]["DIST_KEY"].nunique()
distritos_confirmados = df[df["PUBLICACION_CONFIRMADA"]]["DIST_KEY"].nunique()

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
    <h1>📋 Publicación de las Listas del Padrón Inicial – EG 2026</h1>
    <p>RENIEC Electoral · Dirección de Registro Electoral (DRE) · Panel de seguimiento en tiempo real</p>
  </div>
  <div style="text-align:right; font-size:0.78rem; opacity:0.85;">
    Datos actualizados automáticamente<br>desde Google Sheets
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
      <div class="kpi-sub">en el padrón</div>
    </div>""", unsafe_allow_html=True)

with k2:
    st.markdown(f"""
    <div class="kpi-card green">
      <div class="kpi-value">{distritos_publicando}</div>
      <div class="kpi-label">Publicando</div>
      <div class="kpi-sub">con publicador o agencia</div>
    </div>""", unsafe_allow_html=True)

with k3:
    st.markdown(f"""
    <div class="kpi-card orange">
      <div class="kpi-value">{distritos_agencia}</div>
      <div class="kpi-label">En Agencia</div>
      <div class="kpi-sub">sin publicador externo</div>
    </div>""", unsafe_allow_html=True)

with k4:
    st.markdown(f"""
    <div class="kpi-card purple">
      <div class="kpi-value">{distritos_confirmados}</div>
      <div class="kpi-label">Kit Entregado</div>
      <div class="kpi-sub">publicación confirmada</div>
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
      <div class="kpi-sub">entregadas por municipalidad</div>
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
    st.markdown('<div class="section-title">🗺️ Mapa de publicación por departamento y distrito</div>', unsafe_allow_html=True)
    st.write("Última versión:", datetime.datetime.now())

    # Coordenadas aproximadas de capitales departamentales (centroide)
    DEP_COORDS = {
        "AMAZONAS":     {"lat": -5.5,   "lon": -78.1},
        "ANCASH":       {"lat": -9.53,  "lon": -77.53},
        "APURIMAC":     {"lat": -14.05, "lon": -73.09},
        "AREQUIPA":     {"lat": -16.41, "lon": -71.54},
        "AYACUCHO":     {"lat": -13.16, "lon": -74.22},
        "CAJAMARCA":    {"lat": -7.16,  "lon": -78.51},
        "CUSCO":        {"lat": -13.52, "lon": -71.97},
        "HUANCAVELICA": {"lat": -12.79, "lon": -74.97},
        "HUANUCO":      {"lat": -9.93,  "lon": -76.24},
        "ICA":          {"lat": -14.07, "lon": -75.73},
        "JUNIN":        {"lat": -11.16, "lon": -75.23},
        "LA LIBERTAD":  {"lat": -8.12,  "lon": -78.12},
        "LAMBAYEQUE":   {"lat": -6.77,  "lon": -79.84},
        "LIMA":         {"lat": -12.04, "lon": -76.95},
        "LORETO":       {"lat": -4.0,   "lon": -75.0},
        "MADRE DE DIOS":{"lat": -11.0,  "lon": -70.5},
        "MOQUEGUA":     {"lat": -17.19, "lon": -70.93},
        "PASCO":        {"lat": -10.66, "lon": -76.25},
        "PIURA":        {"lat": -5.19,  "lon": -80.63},
        "PUNO":         {"lat": -15.84, "lon": -70.02},
        "SAN MARTIN":   {"lat": -7.0,   "lon": -76.5},
        "TACNA":        {"lat": -18.01, "lon": -70.25},
        "UCAYALI":      {"lat": -8.38,  "lon": -74.55},
    }

    # Agrupar distritos por departamento
    dep_distritos = (
        df[df["PUBLICA"]]
        .groupby("DEPARTAMENTO")
        .agg(
            num_distritos=("DISTRITO", "nunique"),
            distritos=("DISTRITO", lambda x: "<br>".join(sorted(x.dropna().unique()[:40])))
        )
        .reset_index()
    )
    dep_distritos["lat"] = dep_distritos["DEPARTAMENTO"].map(lambda d: DEP_COORDS.get(d, {}).get("lat", 0))
    dep_distritos["lon"] = dep_distritos["DEPARTAMENTO"].map(lambda d: DEP_COORDS.get(d, {}).get("lon", 0))
    dep_distritos["hover"] = dep_distritos.apply(
        lambda r: f"<b>{r['DEPARTAMENTO']}</b><br>Distritos: {r['num_distritos']}<br><br>{r['distritos']}",
        axis=1
    )

    fig_map = go.Figure()

    fig_map.add_trace(go.Scattergeo(
        lon=dep_distritos["lon"],
        lat=dep_distritos["lat"],
        text=dep_distritos["hover"],
        hoverinfo="text",
        mode="markers+text",
        textposition="top center",
        textfont=dict(size=8, color="white"),
        marker=dict(
            size=dep_distritos["num_distritos"] / dep_distritos["num_distritos"].max() * 35 + 10,
            color=dep_distritos["num_distritos"],
            colorscale="Blues",
            reversescale=False,
            showscale=True,
            colorbar=dict(title="Distritos", thickness=12, len=0.6),
            line=dict(width=1, color="white"),
        ),
    ))

    # Añadir etiquetas de nombre de departamento
    fig_map.add_trace(go.Scattergeo(
        lon=dep_distritos["lon"],
        lat=dep_distritos["lat"],
        text=dep_distritos["DEPARTAMENTO"].str.title(),
        mode="text",
        textfont=dict(size=7, color="#1a2540"),
        hoverinfo="skip",
    ))

    fig_map.update_layout(
        geo=dict(
            scope="south america",
            showland=True,
            landcolor="#e8ecf2",
            showocean=True,
            oceancolor="#d0e8f5",
            showcountries=True,
            countrycolor="#aab4c2",
            showsubunits=True,
            subunitcolor="#0072c6",
            subunitwidth=1,
            center=dict(lat=-9.5, lon=-75),
            projection_scale=3.5,
            lataxis_range=[-19, 0],
            lonaxis_range=[-82, -68],
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
        height=480,
        showlegend=False,
    )

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

    # ── Gráfico 3: Estado del kit por departamento (barras pequeñas) ──
    st.markdown('<div class="section-title" style="margin-top:6px">📦 Kit entregado al publicador</div>', unsafe_allow_html=True)
    kit_col = "EL PUBLICADOR YA CUENTA CON EL KIT"
    if kit_col in df.columns:
        kit_dep = df.groupby("DEPARTAMENTO")[kit_col].apply(
            lambda x: (x.str.strip().str.upper() == "SI").sum()
        ).reset_index()
        kit_dep.columns = ["Departamento", "Con Kit"]
        total_dep = df.groupby("DEPARTAMENTO")["DISTRITO"].nunique().reset_index()
        total_dep.columns = ["Departamento", "Total"]
        kit_dep = kit_dep.merge(total_dep, on="Departamento")
        kit_dep["% Kit"] = (kit_dep["Con Kit"] / kit_dep["Total"] * 100).round(1)
        kit_dep = kit_dep.sort_values("% Kit", ascending=True).tail(12)

        fig_kit = px.bar(
            kit_dep,
            x="% Kit",
            y="Departamento",
            orientation="h",
            text="% Kit",
            color="% Kit",
            color_continuous_scale="Blues",
            range_x=[0, 105],
        )
        fig_kit.update_traces(texttemplate="%{text}%", textposition="outside")
        fig_kit.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=30, t=5, b=5),
            height=260,
            coloraxis_showscale=False,
            xaxis_title="% con kit",
            yaxis_title="",
            font=dict(size=9),
        )
        st.plotly_chart(fig_kit, use_container_width=True)

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

with f3:
    sel_publica = st.selectbox(
        "Estado de publicación",
        ["Todos", "Con publicador", "En agencia", "Kit entregado", "Desistió"],
    )

# Filtrar
df_tab = df.copy()
if sel_dept:
    df_tab = df_tab[df_tab["DEPARTAMENTO"].isin(sel_dept)]
if sel_prov:
    df_tab = df_tab[df_tab["PROVINCIA"].isin(sel_prov)]
if sel_publica == "Con publicador":
    df_tab = df_tab[df_tab["CON_PUBLICADOR"]]
elif sel_publica == "En agencia":
    df_tab = df_tab[df_tab["PUBLICA_AGENCIA"]]
elif sel_publica == "Kit entregado":
    df_tab = df_tab[df_tab["PUBLICACION_CONFIRMADA"]]
elif sel_publica == "Desistió":
    df_tab = df_tab[df_tab["DESCRIPCIÓN"] == "DESISTIO"]

# Columnas a mostrar
COLS_TABLA = [
    "DEPARTAMENTO",
    "PROVINCIA",
    "DISTRITO",
    "DESCRIPCIÓN",
    "EL PUBLICADOR YA CUENTA CON EL KIT",
    "PRESENCIA DEL JNE",
    "FECHA DE INICIO DE PUBLICACIÓN",
    "FECHA DE FIN DE PUBLICACIÓN",
    "ACTA DE APERTURA VALIDADA",
    "ACTA DE CIERRE VALIDADA",
    "# DE CIUDADANOS ENCUESTADOS",
    "# DE ACTAS DE DEFUNCION (ENTREGADAS POR LA MUNICIPALIDAD)",
    "# DE TACHAS Y RECLAMOS",
    "INCIDENCIAS",
]
cols_pres = [c for c in COLS_TABLA if c in df_tab.columns]
df_mostrar = df_tab[cols_pres].reset_index(drop=True)

# Renombrar para tabla compacta
rename_map = {
    "EL PUBLICADOR YA CUENTA CON EL KIT": "Kit",
    "PRESENCIA DEL JNE": "JNE",
    "FECHA DE INICIO DE PUBLICACIÓN": "F. Inicio",
    "FECHA DE FIN DE PUBLICACIÓN": "F. Fin",
    "ACTA DE APERTURA VALIDADA": "Acta Apertura",
    "ACTA DE CIERRE VALIDADA": "Acta Cierre",
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
  Datos actualizados automáticamente desde Google Sheets
</div>
""", unsafe_allow_html=True)
