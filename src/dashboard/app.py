from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# CONFIGURACIÓN
# ============================================================
st.set_page_config(
    page_title="Corredor de Altura | Inteligencia de Exposición",
    layout="wide",
    initial_sidebar_state="collapsed",
)

ROOT = Path(__file__).resolve().parents[2]
INDEX_PATH = ROOT / "data" / "processed" / "indice_exposicion_segmentos.csv"
MASTER_PATH = ROOT / "data" / "processed" / "features_segmentos_master.csv"
GEO_PATH = ROOT / "data" / "processed" / "segmentos_indice_exposicion.geojson"

# ============================================================
# ESTILO
# ============================================================
st.markdown(
    """
<style>
:root{
  --bg:#0a0f15;
  --panel:#101720;
  --panel2:#0d141c;
  --line:#22303d;
  --text:#f0f4f7;
  --muted:#8e9aa7;
  --muted2:#667483;
  --amber:#d8a43f;
  --orange:#df7f32;
  --red:#d85b57;
  --white:#f8fafc;
}
.stApp{
    background:
        radial-gradient(circle at 82% -12%, rgba(216,164,63,.08), transparent 28%),
        linear-gradient(180deg,#0b1016 0%,#090e14 100%);
    color:var(--text);
}
.block-container{
    max-width:1540px;
    padding-top:1.15rem;
    padding-bottom:4rem;
}
[data-testid="stHeader"]{background:transparent;}
#MainMenu, footer{visibility:hidden;}

.kicker{
    color:#aab5bf;
    font-size:.66rem;
    letter-spacing:.17em;
    text-transform:uppercase;
    font-weight:800;
}
.title{
    color:#f5f7f9;
    font-size:2.6rem;
    line-height:1;
    letter-spacing:-.04em;
    font-weight:800;
    margin:.28rem 0 .38rem 0;
}
.subtitle{
    color:#8d99a6;
    font-size:.91rem;
}
.rule{
    height:1px;
    background:linear-gradient(90deg,#2b3947 0%,#2b3947 72%,transparent 100%);
    margin:1rem 0 1.15rem 0;
}
.section{
    color:#b6c0ca;
    font-size:.67rem;
    letter-spacing:.16em;
    text-transform:uppercase;
    font-weight:800;
    margin:1.35rem 0 .55rem 0;
}
.section-title{
    color:#f2f5f7;
    font-size:1.45rem;
    letter-spacing:-.02em;
    font-weight:760;
    margin:.15rem 0 .35rem 0;
}
.section-sub{
    color:#7f8c99;
    font-size:.82rem;
    margin-bottom:.75rem;
}
.card{
    background:linear-gradient(180deg,#111922 0%,#0e151d 100%);
    border:1px solid #22303d;
    border-radius:8px;
    padding:1rem 1.05rem;
    min-height:108px;
}
.card .label{
    color:#8e9aa7;
    font-size:.62rem;
    letter-spacing:.12em;
    text-transform:uppercase;
    font-weight:800;
}
.card .value{
    color:#f4f7f9;
    font-size:1.85rem;
    line-height:1.08;
    letter-spacing:-.04em;
    font-weight:800;
    margin-top:.35rem;
}
.card .meta{
    color:#6f7c89;
    font-size:.72rem;
    margin-top:.35rem;
}
.note{
    border-left:2px solid #d8a43f;
    background:#0f171f;
    color:#98a5b1;
    padding:.78rem .95rem;
    font-size:.78rem;
}
.inspector{
    background:linear-gradient(180deg,#111922 0%,#0d141c 100%);
    border:1px solid #263544;
    border-radius:8px;
    padding:1rem 1.1rem;
}
.inspector .km{
    color:#f4f7f9;
    font-size:1.55rem;
    font-weight:800;
}
.inspector .score{
    font-size:3.25rem;
    line-height:1;
    font-weight:850;
    letter-spacing:-.06em;
    margin:.42rem 0 .18rem 0;
}
.inspector .class{
    color:#bec7d0;
    font-size:.7rem;
    letter-spacing:.13em;
    text-transform:uppercase;
    font-weight:800;
}
.dim-row{
    display:grid;
    grid-template-columns:104px 1fr 44px;
    align-items:center;
    gap:8px;
    margin:.58rem 0;
    font-size:.75rem;
}
.dim-label{color:#b4bec8;}
.dim-track{
    height:7px;
    border-radius:999px;
    background:#202c37;
    overflow:hidden;
}
.dim-fill{
    height:100%;
    border-radius:999px;
    background:linear-gradient(90deg,#d7a23d,#de7c31);
}
.dim-val{text-align:right;color:#e9eef2;font-weight:750;}
.reading{
    background:#101820;
    border:1px solid #243240;
    border-radius:8px;
    padding:1rem 1.05rem;
    color:#aab5bf;
    font-size:.82rem;
    line-height:1.55;
}
.reading strong{color:#f1f5f8;}
.glossary{
    background:#0f161e;
    border:1px solid #22303d;
    border-radius:8px;
    padding:1rem 1.05rem;
    color:#9ca8b4;
    font-size:.78rem;
    line-height:1.6;
}
.stTabs [data-baseweb="tab-list"]{
    gap:1.6rem;
    border-bottom:1px solid #21303d;
}
.stTabs [data-baseweb="tab"]{
    color:#83909d;
    font-size:.76rem;
    letter-spacing:.08em;
    text-transform:uppercase;
}
.stTabs [aria-selected="true"]{color:#f1f4f6!important;}
div[data-testid="stMetric"]{
    background:#111821;
    border:1px solid #22303d;
    border-radius:8px;
    padding:.75rem .85rem;
}
div[data-testid="stMetricLabel"]{color:#8e9aa7;}
div[data-testid="stMetricValue"]{color:#f0f4f7;}
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# DATOS
# ============================================================
@st.cache_data
def cargar_datos():
    indice = pd.read_csv(INDEX_PATH)
    master = pd.read_csv(MASTER_PATH)
    geo = gpd.read_file(GEO_PATH)

    df = indice.merge(
        master,
        on=["km_inicio", "km_fin"],
        how="left",
        suffixes=("", "_master"),
    )

    df["km_inicio"] = df["km_inicio"].astype(int)
    df["km_fin"] = df["km_fin"].astype(int)
    df["clase_mostrar"] = (
        df["clase_exposicion"]
        .astype(str)
        .str.replace("_", " ", regex=False)
        .str.title()
    )

    variables = [
        "pendiente_media_abs_pct",
        "pendiente_terreno_p90_pct",
        "n_drenajes_principales_50m",
        "area_aportante_max_50m_km2",
        "precipitacion_diaria_p95_mm",
        "viento_p95_ms",
        "fraccion_horas_nieve_ge50pct",
    ]

    for c in variables:
        if c in df.columns:
            df[c + "_percentil_corredor"] = df[c].rank(pct=True, method="average") * 100

    dims = {
        "Topografía": "subindice_topografia",
        "Hidrología": "subindice_hidrologia",
        "Clima": "subindice_clima",
    }
    df["dimension_dominante"] = (
        df[list(dims.values())]
        .idxmax(axis=1)
        .map({v: k for k, v in dims.items()})
    )
    return df, geo

df, geo = cargar_datos()

COLORES_CLASE = {
    "Muy Baja": "#6f7d89",
    "Baja": "#a5925c",
    "Media": "#c8a447",
    "Alta": "#dc7b2f",
    "Muy Alta": "#d85b57",
}

# ============================================================
# FUNCIONES
# ============================================================
def tarjeta(etiqueta, valor, meta=""):
    return f"""
    <div class="card">
      <div class="label">{etiqueta}</div>
      <div class="value">{valor}</div>
      <div class="meta">{meta}</div>
    </div>
    """

def barra_dimension(nombre, valor):
    pct = float(np.clip(valor * 100, 0, 100))
    return f'<div class="dim-row"><div class="dim-label">{nombre}</div><div class="dim-track"><div class="dim-fill" style="width:{pct:.1f}%"></div></div><div class="dim-val">{pct:.0f}</div></div>'

def grafico_perfil(data, km_sel):
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=data["km_inicio"] + .5,
        y=data["indice_exposicion"],
        mode="lines",
        line=dict(color="#697988", width=1.7),
        hoverinfo="skip",
        showlegend=False,
    ))

    for clase in ["Muy Baja", "Baja", "Media", "Alta", "Muy Alta"]:
        d = data[data["clase_mostrar"] == clase]
        if d.empty:
            continue
        fig.add_trace(go.Scatter(
            x=d["km_inicio"] + .5,
            y=d["indice_exposicion"],
            mode="markers",
            marker=dict(size=7, color=COLORES_CLASE[clase]),
            name=clase,
            customdata=np.stack(
                [d["km_inicio"], d["km_fin"], d["ranking_exposicion"]],
                axis=-1
            ),
            hovertemplate=(
                "<b>km %{customdata[0]:.0f}–%{customdata[1]:.0f}</b><br>"
                "Índice de exposición: %{y:.2f}<br>"
                "Posición: #%{customdata[2]:.0f} de 130<extra></extra>"
            ),
        ))

    sel = data[data["km_inicio"] == km_sel]
    if not sel.empty:
        s = sel.iloc[0]
        fig.add_trace(go.Scatter(
            x=[km_sel + .5],
            y=[s["indice_exposicion"]],
            mode="markers",
            marker=dict(size=16, color="#f4f7fa", line=dict(color="#0a0f15", width=3)),
            hoverinfo="skip",
            showlegend=False,
        ))

    fig.update_layout(
        height=365,
        margin=dict(l=5, r=5, t=25, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#0f151d",
        font=dict(color="#9aa6b2", size=11),
        legend=dict(orientation="h", y=1.02, x=0),
        xaxis=dict(
            title="Progresiva (km)",
            range=[0, 130],
            dtick=10,
            gridcolor="#1c2732",
            zeroline=False,
        ),
        yaxis=dict(
            title="Índice de exposición relativa",
            range=[0, max(80, float(data["indice_exposicion"].max()) + 5)],
            gridcolor="#1c2732",
            zeroline=False,
        ),
    )
    return fig

def grafico_mapa(gdf, km_sel):
    fig = go.Figure()
    g = gdf.to_crs(4326).copy()

    if "clase_mostrar" not in g.columns:
        g["clase_mostrar"] = (
            g["clase_exposicion"]
            .astype(str)
            .str.replace("_", " ", regex=False)
            .str.title()
        )

    for _, row in g.iterrows():
        geom = row.geometry
        if geom is None:
            continue
        geoms = list(geom.geoms) if geom.geom_type == "MultiLineString" else [geom]

        for line in geoms:
            xs, ys = line.xy
            seleccionado = int(row["km_inicio"]) == km_sel

            fig.add_trace(go.Scattergeo(
                lon=list(xs),
                lat=list(ys),
                mode="lines",
                line=dict(
                    width=6 if seleccionado else 3.5,
                    color="#f6f8fa" if seleccionado else COLORES_CLASE.get(row["clase_mostrar"], "#81909d"),
                ),
                customdata=[
                    [
                        int(row["km_inicio"]),
                        int(row["km_fin"]),
                        float(row["indice_exposicion"]),
                        row["clase_mostrar"],
                    ]
                ] * len(xs),
                hovertemplate=(
                    "<b>km %{customdata[0]}–%{customdata[1]}</b><br>"
                    "Índice: %{customdata[2]:.2f}<br>"
                    "Clase: %{customdata[3]}<extra></extra>"
                ),
                showlegend=False,
            ))

    fig.update_geos(
        fitbounds="locations",
        visible=False,
        bgcolor="#0f151d",
        projection_type="mercator",
    )
    fig.update_layout(
        height=500,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig

def tabla_variables(row):
    specs = [
        (
            "Topografía",
            "Pendiente longitudinal media absoluta",
            "pendiente_media_abs_pct",
            "{:.1f} %",
            "Promedio de la pendiente absoluta a lo largo del segmento."
        ),
        (
            "Topografía",
            "Pendiente del terreno — percentil 90",
            "pendiente_terreno_p90_pct",
            "{:.1f} %",
            "Percentil 90: el 90 % de los valores de pendiente del entorno queda por debajo de este valor."
        ),
        (
            "Hidrología",
            "Cantidad de drenajes principales a 50 m",
            "n_drenajes_principales_50m",
            "{:.0f}",
            "Número de cauces o drenajes principales detectados dentro de una franja de 50 m."
        ),
        (
            "Hidrología",
            "Área aportante máxima",
            "area_aportante_max_50m_km2",
            "{:.2f} km²",
            "Superficie máxima que puede concentrar escurrimiento hacia el entorno del segmento."
        ),
        (
            "Clima",
            "Precipitación diaria — percentil 95",
            "precipitacion_diaria_p95_mm",
            "{:.1f} mm",
            "Percentil 95: valor de precipitación diaria que solo es superado aproximadamente el 5 % de los días."
        ),
        (
            "Clima",
            "Velocidad del viento — percentil 95",
            "viento_p95_ms",
            "{:.1f} m/s",
            "Percentil 95: valor de viento que solo es superado aproximadamente el 5 % del tiempo."
        ),
        (
            "Clima",
            "Fracción de horas con condición de nieve ≥ 50 %",
            "fraccion_horas_nieve_ge50pct",
            "{:.1%}",
            "Proporción de horas clasificadas con una condición de nieve igual o superior al 50 %."
        ),
    ]

    filas = []
    for dim, nombre, col, formato, explicacion in specs:
        if col in row.index:
            filas.append({
                "Dimensión": dim,
                "Variable": nombre,
                "Valor": formato.format(row[col]),
                "Percentil dentro del corredor": round(
                    float(row.get(col + "_percentil_corredor", np.nan)), 1
                ),
                "Qué significa": explicacion,
            })

    return pd.DataFrame(filas)

def grafico_percentiles(row):
    t = tabla_variables(row)

    fig = go.Figure(go.Bar(
        x=t["Percentil dentro del corredor"],
        y=t["Variable"],
        orientation="h",
        marker=dict(color="#d7a23d"),
        text=[f"{v:.0f}°" for v in t["Percentil dentro del corredor"]],
        textposition="outside",
        hovertemplate=(
            "%{y}<br>"
            "Posición relativa: percentil %{x:.1f}<extra></extra>"
        ),
    ))

    fig.update_layout(
        height=345,
        margin=dict(l=0, r=55, t=8, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#0f151d",
        font=dict(color="#9aa6b2", size=10),
        xaxis=dict(
            range=[0, 105],
            title="Percentil dentro de los 130 segmentos",
            gridcolor="#1c2732",
        ),
        yaxis=dict(autorange="reversed"),
        showlegend=False,
    )
    return fig

def lectura_segmento(row):
    dimension = row["dimension_dominante"]
    clase = row["clase_mostrar"].lower()

    candidatos = []
    nombres = {
        "pendiente_media_abs_pct": "pendiente longitudinal",
        "pendiente_terreno_p90_pct": "pendiente del terreno",
        "n_drenajes_principales_50m": "presencia de drenajes principales",
        "area_aportante_max_50m_km2": "área aportante",
        "precipitacion_diaria_p95_mm": "precipitación diaria extrema",
        "viento_p95_ms": "viento extremo",
        "fraccion_horas_nieve_ge50pct": "condición de nieve",
    }

    for col, nombre in nombres.items():
        pct = row.get(col + "_percentil_corredor", np.nan)
        if pd.notna(pct):
            candidatos.append((float(pct), nombre))

    candidatos = sorted(candidatos, reverse=True)[:2]
    top_txt = " y ".join([f"{n} (percentil {p:.0f})" for p, n in candidatos])

    return (
        f"El segmento presenta una exposición relativa <strong>{clase}</strong>. "
        f"La dimensión dominante es <strong>{dimension}</strong>. "
        f"Entre las variables que más se destacan frente al resto del corredor se encuentran "
        f"**{top_txt}**. "
        f"Esta lectura sirve para orientar revisión e inspección; no representa una predicción de falla."
    )

# ============================================================
# ENCABEZADO
# ============================================================
st.markdown(
    """
<div class="kicker">Inteligencia de Exposición Operacional</div>
<div class="title">CORREDOR DE ALTURA</div>
<div class="subtitle">
Corredor Este · Proyecto Vicuña · km 0–130 · 130 segmentos de 1 km · Modelo analítico v1
</div>
<div class="rule"></div>
""",
    unsafe_allow_html=True,
)

# ============================================================
# CONTROL GLOBAL
# ============================================================
sel_col, exp_col, note_col = st.columns([1.35, 1, 4.2])

with sel_col:
    km_seleccionado = st.selectbox(
        "SEGMENTO SELECCIONADO",
        options=df["km_inicio"].tolist(),
        index=int(df["indice_exposicion"].idxmax()),
        format_func=lambda x: f"km {int(x)}–{int(x)+1}",
    )

seleccionado = df.loc[df["km_inicio"] == km_seleccionado].iloc[0]

with exp_col:
    st.metric("EXPOSICIÓN ACTUAL", f"{seleccionado['indice_exposicion']:.2f}")

with note_col:
    st.markdown(
        """
<div class="note">
El índice mide <b>exposición relativa dentro de este corredor</b>.
No representa riesgo absoluto ni predice fallas, accidentes o cierres.
</div>
""",
        unsafe_allow_html=True,
    )

tab_diag, tab_seg, tab_met = st.tabs(
    ["DIAGNÓSTICO DEL CORREDOR", "ANÁLISIS DE SEGMENTO", "METODOLOGÍA Y EVIDENCIA"]
)

# ============================================================
# TAB 1 — DIAGNÓSTICO DEL CORREDOR
# ============================================================
with tab_diag:
    st.markdown('<div class="section">Lectura ejecutiva</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">¿Dónde se concentra la exposición?</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-sub">Resumen orientado a priorización y lectura operativa del corredor completo.</div>',
        unsafe_allow_html=True,
    )

    max_row = df.loc[df["indice_exposicion"].idxmax()]
    media = float(df["indice_exposicion"].mean())
    alta_muy_alta = int(df["clase_mostrar"].isin(["Alta", "Muy Alta"]).sum())
    top10_share = 100 * df.nlargest(10, "indice_exposicion")["indice_exposicion"].sum() / df["indice_exposicion"].sum()

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(
            tarjeta("Exposición media", f"{media:.1f}", "promedio del corredor"),
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            tarjeta("Alta + Muy Alta", f"{alta_muy_alta} km", f"{alta_muy_alta/len(df):.0%} del corredor"),
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            tarjeta(
                "Mayor exposición",
                f"{max_row['indice_exposicion']:.1f}",
                f"km {int(max_row['km_inicio'])}–{int(max_row['km_fin'])}",
            ),
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            tarjeta("Concentración Top 10", f"{top10_share:.0f} %", "participación relativa del Top 10 en la suma total"),
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section">Perfil longitudinal</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Exposición a lo largo de los 130 km</div>', unsafe_allow_html=True)
    st.plotly_chart(
        grafico_perfil(df, km_seleccionado),
        use_container_width=True,
        config={"displayModeBar": False},
        key="v2_diag_perfil",
    )

    col_mapa, col_detalle = st.columns([1.65, 1], gap="large")

    with col_mapa:
        st.markdown('<div class="section">Distribución espacial</div>', unsafe_allow_html=True)
        st.plotly_chart(
            grafico_mapa(geo, km_seleccionado),
            use_container_width=True,
            config={"displayModeBar": False},
            key="v2_diag_mapa",
        )

    with col_detalle:
        st.markdown('<div class="section">Lectura del segmento</div>', unsafe_allow_html=True)

        color = COLORES_CLASE.get(seleccionado["clase_mostrar"], "#d7a23d")

        st.markdown(
            f"""
<div class="inspector">
  <div class="kicker">Segmento seleccionado</div>
  <div class="km">KM {int(seleccionado.km_inicio)}–{int(seleccionado.km_fin)}</div>
  <div class="score" style="color:{color}">{seleccionado.indice_exposicion:.2f}</div>
  <div class="class">{seleccionado.clase_mostrar} · posición #{int(seleccionado.ranking_exposicion)} de 130</div>
  <div style="height:14px"></div>
  <div class="kicker">Intensidad por dimensión</div>
  {barra_dimension("Topografía", seleccionado.subindice_topografia)}
  {barra_dimension("Hidrología", seleccionado.subindice_hidrologia)}
  {barra_dimension("Clima", seleccionado.subindice_clima)}
  <div style="margin-top:10px;color:#8d99a6;font-size:.74rem;">
    Dimensión dominante: <b style="color:#eef3f7">{seleccionado.dimension_dominante}</b>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

        st.markdown('<div class="section">Interpretación</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="reading">{lectura_segmento(seleccionado)}</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section">Priorización</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Segmentos prioritarios para revisión</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-sub">Ordenados por mayor exposición relativa. No implica ocurrencia de falla.</div>',
        unsafe_allow_html=True,
    )

    top10 = df.nlargest(10, "indice_exposicion")[
        [
            "ranking_exposicion",
            "km_inicio",
            "km_fin",
            "indice_exposicion",
            "clase_mostrar",
            "dimension_dominante",
        ]
    ].copy()

    top10["Segmento"] = top10.apply(
        lambda r: f"km {int(r.km_inicio)}–{int(r.km_fin)}", axis=1
    )
    top10["indice_exposicion"] = top10["indice_exposicion"].round(2)

    top10 = top10[
        [
            "ranking_exposicion",
            "Segmento",
            "indice_exposicion",
            "clase_mostrar",
            "dimension_dominante",
        ]
    ].rename(
        columns={
            "ranking_exposicion": "Prioridad",
            "indice_exposicion": "Índice de exposición",
            "clase_mostrar": "Clase de exposición",
            "dimension_dominante": "Dimensión dominante",
        }
    )

    st.dataframe(
        top10,
        use_container_width=True,
        hide_index=True,
        height=390,
    )

# ============================================================
# TAB 2 — ANÁLISIS DE SEGMENTO
# ============================================================
with tab_seg:
    st.markdown('<div class="section">Diagnóstico específico</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="section-title">Segmento km {int(seleccionado.km_inicio)}–{int(seleccionado.km_fin)}</div>',
        unsafe_allow_html=True,
    )

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Índice de exposición", f"{seleccionado.indice_exposicion:.2f}")
    s2.metric("Clase", seleccionado.clase_mostrar)
    s3.metric("Posición", f"#{int(seleccionado.ranking_exposicion)} de 130")
    s4.metric("Dimensión dominante", seleccionado.dimension_dominante)

    left, right = st.columns([1.1, 1], gap="large")

    with left:
        st.markdown('<div class="section">Variables del modelo</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-sub">Valor físico observado y posición relativa de cada variable frente a los 130 segmentos.</div>',
            unsafe_allow_html=True,
        )
        st.dataframe(
            tabla_variables(seleccionado),
            use_container_width=True,
            hide_index=True,
            height=355,
        )

        st.markdown('<div class="section">Posición relativa</div>', unsafe_allow_html=True)
        st.plotly_chart(
            grafico_percentiles(seleccionado),
            use_container_width=True,
            config={"displayModeBar": False},
            key="v2_seg_percentiles",
        )

    with right:
        st.markdown('<div class="section">Contexto espacial</div>', unsafe_allow_html=True)
        st.plotly_chart(
            grafico_mapa(geo, km_seleccionado),
            use_container_width=True,
            config={"displayModeBar": False},
            key="v2_seg_mapa",
        )

        st.markdown('<div class="section">Lectura automática</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="reading">{lectura_segmento(seleccionado)}</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section">Contexto local</div>', unsafe_allow_html=True)
    local = df[
        (df["km_inicio"] >= max(0, km_seleccionado - 5))
        & (df["km_inicio"] <= min(129, km_seleccionado + 5))
    ]

    fig_local = grafico_perfil(local, km_seleccionado)
    fig_local.update_xaxes(
        range=[max(0, km_seleccionado - 5), min(130, km_seleccionado + 6)],
        dtick=1,
    )

    st.plotly_chart(
        fig_local,
        use_container_width=True,
        config={"displayModeBar": False},
        key="v2_seg_contexto",
    )

# ============================================================
# TAB 3 — METODOLOGÍA Y EVIDENCIA
# ============================================================
with tab_met:
    st.markdown('<div class="section">Arquitectura analítica</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Cómo se construye el índice</div>', unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(tarjeta("Unidad analítica", "1 km", "130 segmentos"), unsafe_allow_html=True)
    with m2:
        st.markdown(tarjeta("Tabla maestra", "130 × 46", "sin valores faltantes"), unsafe_allow_html=True)
    with m3:
        st.markdown(tarjeta("Variables del índice", "7", "3 dimensiones"), unsafe_allow_html=True)
    with m4:
        st.markdown(tarjeta("Clima histórico", "25 años", "ERA5-Land · 2001–2025"), unsafe_allow_html=True)

    st.markdown(
        """
<div class="note">
Flujo metodológico:
OpenStreetMap + puntos de campo → traza calibrada → segmentos de 1 km →
topografía / hidrología / clima → tabla analítica → subíndices →
índice compuesto → validación independiente → mapa y dashboard.
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section">Variables y significado</div>', unsafe_allow_html=True)

    metodo = pd.DataFrame([
        ["Topografía", "1/3", "Pendiente longitudinal media absoluta", "Representa la inclinación media del trazado dentro del segmento."],
        ["Topografía", "1/3", "Pendiente del terreno — percentil 90", "Resume condiciones de pendiente elevada en el entorno del segmento."],
        ["Hidrología", "1/3", "Cantidad de drenajes principales a 50 m", "Indica cuántos cauces relevantes intersectan o se aproximan al segmento."],
        ["Hidrología", "1/3", "Área aportante máxima", "Aproxima la superficie capaz de concentrar escurrimiento hacia el sector."],
        ["Clima", "1/3", "Precipitación diaria — percentil 95", "Representa un valor alto de precipitación diaria, superado solo ~5 % de los días."],
        ["Clima", "1/3", "Velocidad del viento — percentil 95", "Representa un valor alto de viento, superado solo ~5 % del tiempo."],
        ["Clima", "1/3", "Fracción de horas con condición de nieve ≥ 50 %", "Resume recurrencia relativa de condiciones asociadas a nieve."],
    ], columns=["Dimensión", "Peso de la dimensión", "Variable", "Interpretación"])

    st.dataframe(
        metodo,
        use_container_width=True,
        hide_index=True,
        height=320,
    )

    st.markdown('<div class="section">Glosario para lectura ejecutiva</div>', unsafe_allow_html=True)
    st.markdown(
        """
<div class="glossary">
<b>Percentil 95 (P95)</b>: valor que deja aproximadamente al 95 % de las observaciones por debajo.
En términos simples, representa una condición alta o poco frecuente.<br><br>

<b>Percentil 90 (P90)</b>: valor que deja aproximadamente al 90 % de las observaciones por debajo.
Se usa para resumir condiciones elevadas sin depender únicamente del máximo.<br><br>

<b>Percentil dentro del corredor</b>: compara un segmento con los otros 129.
Por ejemplo, percentil 90 significa que ese valor es mayor que aproximadamente el 90 % de los segmentos.<br><br>

<b>Subíndice</b>: puntuación normalizada de una dimensión específica — topografía, hidrología o clima.<br><br>

<b>Índice de exposición relativa</b>: combinación de las tres dimensiones. Sirve para comparar y priorizar segmentos dentro de este corredor.
No equivale a probabilidad de falla ni riesgo absoluto.
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section">Evidencia y limitaciones</div>', unsafe_allow_html=True)

    e1, e2 = st.columns(2, gap="large")
    with e1:
        st.markdown(
            """
**Validación independiente**

- El IPER y la evidencia de campo no se usan como objetivo de entrenamiento.
- Se emplean como contraste externo de coherencia.
- El modelo busca exposición relativa, no reproducir literalmente una clasificación operativa previa.

**Validación del modelo digital de elevación**

MDE-Ar v2.1:
- Error absoluto medio: 2.88 m
- Raíz del error cuadrático medio: 3.53 m
- Sesgo medio: -0.58 m
"""
        )

    with e2:
        st.markdown(
            """
**Limitaciones**

- No predice fallas, accidentes ni cierres.
- La resolución climática es más gruesa que la unidad de 1 km.
- La resolución del terreno limita detalle local.
- La evidencia operacional no es homogénea en todo el corredor.
- La cobertura analítica validada finaliza en el km 130.
"""
        )
