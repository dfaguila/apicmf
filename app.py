"""
Dashboard CMF Chile — Indicadores Financieros
UF · Dólar Observado · IPC

Para ejecutar:
    streamlit run app.py
"""

import sys
import os
from datetime import date, datetime
from decimal import Decimal

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Importar módulos del proyecto
sys.path.insert(0, os.path.dirname(__file__))
from models import Indicador, ConsultaHoy, ConsultaPeriodoMeses, ConsultaAnio
from client import CMFClient, CMFError

# -----------------------------------------------------------------------
# Configuración de página
# -----------------------------------------------------------------------
st.set_page_config(
    page_title="Indicadores CMF Chile",
    page_icon="🇨🇱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------
# CSS personalizado
# -----------------------------------------------------------------------
st.markdown(
    """
    <style>
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 12px;
        padding: 20px 24px;
        border-left: 4px solid;
        color: white;
    }
    .metric-label { font-size: 13px; opacity: 0.7; margin-bottom: 4px; }
    .metric-value { font-size: 32px; font-weight: 700; margin: 0; }
    .metric-sub   { font-size: 12px; opacity: 0.6; margin-top: 4px; }
    .uf-card    { border-color: #7c3aed; }
    .dolar-card { border-color: #059669; }
    .ipc-card   { border-color: #d97706; }
    .stAlert    { border-radius: 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------
# Estado de sesión
# -----------------------------------------------------------------------
if "cliente" not in st.session_state:
    st.session_state["cliente"] = None


# -----------------------------------------------------------------------
# Sidebar — Configuración
# -----------------------------------------------------------------------
with st.sidebar:
    st.image(
        "https://api.cmfchile.cl/img/logo-CMF-color.png",
        width=180,
    )
    st.markdown("## ⚙️ Configuración")

    api_key = st.text_input(
        "API Key CMF",
        type="password",
        placeholder="Ingresa tu API Key",
        help="Obtén tu clave gratuita en https://api.cmfchile.cl",
    )

    if api_key:
        st.session_state["cliente"] = CMFClient(api_key=api_key)
        st.success("✅ API Key configurada")
    else:
        st.warning("Ingresa tu API Key para continuar")

    st.markdown("---")
    st.markdown("### 📅 Período de consulta")

    anio_actual = date.today().year
    anio_inicio = st.number_input(
        "Año inicio", min_value=2010, max_value=anio_actual, value=anio_actual - 1
    )
    mes_inicio = st.selectbox(
        "Mes inicio",
        options=list(range(1, 13)),
        format_func=lambda m: datetime(2000, m, 1).strftime("%B").capitalize(),
        index=0,
    )
    anio_fin = st.number_input(
        "Año fin", min_value=2010, max_value=anio_actual, value=anio_actual
    )
    mes_fin = st.selectbox(
        "Mes fin",
        options=list(range(1, 13)),
        format_func=lambda m: datetime(2000, m, 1).strftime("%B").capitalize(),
        index=date.today().month - 1,
    )

    st.markdown("---")
    st.markdown(
        "<small>Datos provistos por la "
        "[API CMF Bancos v3](https://api.cmfchile.cl)</small>",
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------
# Encabezado
# -----------------------------------------------------------------------
st.title("🇨🇱 Indicadores Financieros CMF Chile")
st.caption(
    "Visualización de UF, Dólar Observado e IPC obtenidos directamente "
    "desde la API pública de la Comisión para el Mercado Financiero."
)

if not st.session_state["cliente"]:
    st.info("👈 Ingresa tu API Key en el panel lateral para comenzar.")
    st.stop()

cliente: CMFClient = st.session_state["cliente"]


# -----------------------------------------------------------------------
# Helper: cargar datos con caché
# -----------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def cargar_hoy(api_key: str):
    c = CMFClient(api_key)
    resultados = {}
    for ind in [Indicador.UF, Indicador.DOLAR, Indicador.IPC]:
        try:
            serie = c.obtener(ConsultaHoy(ind))
            resultados[ind] = serie
        except CMFError as e:
            resultados[ind] = str(e)
    return resultados


@st.cache_data(ttl=3600, show_spinner=False)
def cargar_periodo(
    api_key: str,
    indicador_value: str,
    anio_ini: int,
    mes_ini: int,
    anio_fin: int,
    mes_fin_: int,
):
    c = CMFClient(api_key)
    ind = Indicador(indicador_value)
    try:
        return c.obtener(
            ConsultaPeriodoMeses(ind, anio_ini, mes_ini, anio_fin, mes_fin_)
        )
    except CMFError as e:
        return str(e)


# -----------------------------------------------------------------------
# Tarjetas de valor actual
# -----------------------------------------------------------------------
st.subheader("📌 Valores actuales")

with st.spinner("Consultando la API CMF..."):
    datos_hoy = cargar_hoy(api_key)

col_uf, col_dolar, col_ipc = st.columns(3)

def fmt_valor(serie_o_error, decimales=2) -> str:
    if isinstance(serie_o_error, str):
        return "Error"
    ultimo = serie_o_error.ultimo
    if ultimo is None:
        return "Sin datos"
    return f"{float(ultimo.valor):,.{decimales}f}"

def fmt_fecha(serie_o_error) -> str:
    if isinstance(serie_o_error, str):
        return serie_o_error[:80]
    if serie_o_error.ultimo:
        return serie_o_error.ultimo.fecha.strftime("%d/%m/%Y")
    return "N/A"

with col_uf:
    st.markdown(
        f"""<div class="metric-card uf-card">
            <div class="metric-label">🟣 UF (Unidad de Fomento)</div>
            <div class="metric-value">$ {fmt_valor(datos_hoy[Indicador.UF])}</div>
            <div class="metric-sub">Al {fmt_fecha(datos_hoy[Indicador.UF])}</div>
        </div>""",
        unsafe_allow_html=True,
    )

with col_dolar:
    st.markdown(
        f"""<div class="metric-card dolar-card">
            <div class="metric-label">🟢 Dólar Observado</div>
            <div class="metric-value">$ {fmt_valor(datos_hoy[Indicador.DOLAR])}</div>
            <div class="metric-sub">Al {fmt_fecha(datos_hoy[Indicador.DOLAR])}</div>
        </div>""",
        unsafe_allow_html=True,
    )

with col_ipc:
    st.markdown(
        f"""<div class="metric-card ipc-card">
            <div class="metric-label">🟡 IPC (variación mensual)</div>
            <div class="metric-value">{fmt_valor(datos_hoy[Indicador.IPC], 1)} %</div>
            <div class="metric-sub">Al {fmt_fecha(datos_hoy[Indicador.IPC])}</div>
        </div>""",
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------
# Tabs de detalle por indicador
# -----------------------------------------------------------------------
tab_uf, tab_dolar, tab_ipc, tab_comparar = st.tabs(
    ["📈 UF", "💵 Dólar", "📊 IPC", "🔀 Comparar"]
)

COLORES = {
    Indicador.UF:    "#7c3aed",
    Indicador.DOLAR: "#059669",
    Indicador.IPC:   "#d97706",
}


def render_tab(indicador: Indicador, tab):
    with tab:
        with st.spinner(f"Cargando datos de {indicador.label}..."):
            serie = cargar_periodo(
                api_key,
                indicador.value,
                anio_inicio,
                mes_inicio,
                anio_fin,
                mes_fin,
            )

        if isinstance(serie, str):
            st.error(f"Error al obtener datos: {serie}")
            return

        if len(serie) == 0:
            st.warning("No se encontraron registros para el período indicado.")
            return

        df = pd.DataFrame(serie.to_records())
        df["fecha"] = pd.to_datetime(df["fecha"])

        # Métricas de resumen
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Último valor", f"{float(serie.ultimo.valor):,.4f}", 
                  delta=f"{float(serie.variacion_porcentual or 0):+.2f}% vs inicio")
        c2.metric("Promedio", f"{float(serie.promedio or 0):,.4f}")
        c3.metric("Máximo", f"{float(serie.maximo.valor):,.4f}",
                  delta=serie.maximo.fecha.strftime("%d/%m/%Y"))
        c4.metric("Mínimo", f"{float(serie.minimo.valor):,.4f}",
                  delta=serie.minimo.fecha.strftime("%d/%m/%Y"))

        st.markdown("---")

        # Gráfico de línea
        y_label = f"{indicador.label} ({indicador.unidad})"
        fig = px.line(
            df, x="fecha", y="valor",
            title=f"{indicador.label} — {anio_inicio}/{mes_inicio:02d} a {anio_fin}/{mes_fin:02d}",
            labels={"fecha": "Fecha", "valor": y_label},
            color_discrete_sequence=[COLORES[indicador]],
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            hovermode="x unified",
            xaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.2)"),
            yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.2)"),
        )
        fig.update_traces(line_width=2)
        st.plotly_chart(fig, use_container_width=True)

        # Tabla de datos
        with st.expander("📋 Ver tabla de datos"):
            df_display = df.copy()
            df_display["fecha"] = df_display["fecha"].dt.strftime("%d/%m/%Y")
            df_display.columns = ["Fecha", "Valor", "Indicador"]
            df_display = df_display.sort_values("Fecha", ascending=False)
            st.dataframe(df_display, use_container_width=True, hide_index=True)

            csv = df_display.to_csv(index=False, sep=";").encode("utf-8-sig")
            st.download_button(
                label="⬇️ Descargar CSV",
                data=csv,
                file_name=f"cmf_{indicador.value}_{anio_inicio}_{anio_fin}.csv",
                mime="text/csv",
            )


render_tab(Indicador.UF, tab_uf)
render_tab(Indicador.DOLAR, tab_dolar)
render_tab(Indicador.IPC, tab_ipc)


# -----------------------------------------------------------------------
# Tab Comparar
# -----------------------------------------------------------------------
with tab_comparar:
    st.markdown("### Comparación de indicadores en el período seleccionado")
    st.caption(
        "Los valores se normalizan (base 100 = primer registro) "
        "para hacer comparables series con distintas unidades."
    )

    indicadores_sel = st.multiselect(
        "Seleccionar indicadores a comparar",
        options=[i.label for i in Indicador],
        default=[Indicador.UF.label, Indicador.DOLAR.label],
    )

    label_to_ind = {i.label: i for i in Indicador}

    dfs_norm = []
    for label in indicadores_sel:
        ind = label_to_ind[label]
        with st.spinner(f"Cargando {label}..."):
            serie = cargar_periodo(
                api_key, ind.value,
                anio_inicio, mes_inicio, anio_fin, mes_fin,
            )
        if isinstance(serie, str) or len(serie) == 0:
            st.warning(f"Sin datos para {label}")
            continue
        df = pd.DataFrame(serie.to_records())
        df["fecha"] = pd.to_datetime(df["fecha"])
        # Normalizar base 100
        base = df["valor"].iloc[0]
        df["valor_norm"] = df["valor"] / base * 100
        df["serie"] = label
        dfs_norm.append(df)

    if dfs_norm:
        df_all = pd.concat(dfs_norm, ignore_index=True)
        colores_list = [COLORES[label_to_ind[l]] for l in indicadores_sel
                        if label_to_ind[l] in COLORES]
        fig2 = px.line(
            df_all, x="fecha", y="valor_norm", color="serie",
            title="Variación relativa (Base 100 = primer registro del período)",
            labels={"fecha": "Fecha", "valor_norm": "Índice (Base 100)", "serie": "Indicador"},
            color_discrete_sequence=colores_list or None,
        )
        fig2.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            hovermode="x unified",
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Selecciona al menos un indicador para visualizar.")


# -----------------------------------------------------------------------
# Footer
# -----------------------------------------------------------------------
st.markdown("---")
st.markdown(
    "<small>Fuente: [API CMF Bancos v3](https://api.cmfchile.cl) · "
    "Comisión para el Mercado Financiero · Chile</small>",
    unsafe_allow_html=True,
)
