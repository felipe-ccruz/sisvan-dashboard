"""Dashboard SISVAN — Estado Nutricional.

Ponto de entrada do Streamlit. Consome a API pública do SISVAN ao vivo, com cache
de sessão, e apresenta os microdados de estado nutricional com filtros e gráficos.

Execução: ``streamlit run app.py``
"""

import pandas as pd
import streamlit as st

from api.sisvan import SisvanAPIError, consultar_estado_nutricional
from components import charts
from components.filters import aplicar_filtros_cliente, renderizar_sidebar
from utils.data import registros_para_df

# --------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# --------------------------------------
st.set_page_config(
    page_title="SISVAN — Estado Nutricional",
    page_icon="🥗",
    layout="wide",
)


# --------------------------------------
# CARGA DE DADOS (com cache de sessão)
# --------------------------------------
@st.cache_data(show_spinner=False, ttl=3600)
def carregar_dados(filtros_api: dict, max_registros: int) -> pd.DataFrame:
    """Baixa e trata os dados da API. Cacheado por recorte + volume.

    O cache evita repetir requisições paginadas quando o usuário só mexe nos
    filtros de cliente (sexo, raça/cor).
    """
    registros = consultar_estado_nutricional(
        filtros=filtros_api, max_registros=max_registros
    )
    return registros_para_df(registros)


# --------------------------------------
# CABEÇALHO
# --------------------------------------
st.title("🥗 SISVAN — Estado Nutricional")
st.caption(
    "Análise dos microdados de acompanhamento nutricional do SISVAN, "
    "consultados ao vivo na API pública do Ministério da Saúde."
)

opcoes = renderizar_sidebar()

# Guarda o último resultado na sessão para sobreviver a reruns de filtros de cliente.
if opcoes["buscar"]:
    try:
        with st.spinner("Consultando a API do SISVAN… isso pode levar alguns segundos."):
            st.session_state["df"] = carregar_dados(
                opcoes["filtros_api"], opcoes["max_registros"]
            )
        st.session_state["filtros_api"] = opcoes["filtros_api"]
    except SisvanAPIError as erro:
        st.error(
            "Não foi possível consultar a API do SISVAN. Ela costuma ficar instável "
            f"em consultas filtradas — tente novamente ou refine o recorte.\n\n{erro}"
        )

# --------------------------------------
# ESTADO INICIAL (antes da primeira busca)
# --------------------------------------
if "df" not in st.session_state:
    st.info(
        "👈 Defina os filtros na barra lateral e clique em **Buscar dados** para começar.\n\n"
        "Dica: a API retorna no máximo 20 registros por página, então recortes "
        "específicos (município + competência) trazem resultados mais rápidos e "
        "representativos."
    )
    st.stop()

# --------------------------------------
# APLICA FILTROS DE CLIENTE
# --------------------------------------
df_bruto: pd.DataFrame = st.session_state["df"]

if df_bruto.empty:
    st.warning("A consulta não retornou registros para esse recorte. Ajuste os filtros.")
    st.stop()

df = aplicar_filtros_cliente(df_bruto, opcoes["filtros_cliente"])

if df.empty:
    st.warning("Nenhum registro após aplicar os filtros de sexo/raça. Ajuste-os na sidebar.")
    st.stop()

# --------------------------------------
# INDICADORES (KPIs)
# --------------------------------------
col1, col2, col3, col4 = st.columns(4)
col1.metric("Registros", f"{len(df):,}".replace(",", "."))
col2.metric("Municípios", df["municipio"].nunique() if "municipio" in df else 0)

imc_medio = df["imc"].mean() if "imc" in df else float("nan")
col3.metric("IMC médio", f"{imc_medio:.1f}" if pd.notna(imc_medio) else "—")

if "ano_mes_competencia" in df:
    competencias = df["ano_mes_competencia"].dropna().astype(str)
    periodo = f"{competencias.min()}–{competencias.max()}" if not competencias.empty else "—"
else:
    periodo = "—"
col4.metric("Competências", periodo)

st.caption(
    f"Baixados {len(df_bruto):,} registros (teto: {opcoes['max_registros']:,}). "
    "Amostra da base — não representa o total do recorte."
    .replace(",", ".")
)
st.markdown("---")

# --------------------------------------
# GRÁFICOS
# --------------------------------------
def _mostrar(coluna, figura) -> None:
    """Renderiza a figura na coluna, ou uma mensagem se não houver dados."""
    if figura is not None:
        coluna.plotly_chart(figura, use_container_width=True)
    else:
        coluna.info("Sem dados suficientes para este gráfico.")


linha1_esq, linha1_dir = st.columns(2)
_mostrar(linha1_esq, charts.grafico_estado_nutricional(df))
_mostrar(linha1_dir, charts.grafico_fase_vida(df))

linha2_esq, linha2_dir = st.columns(2)
_mostrar(linha2_esq, charts.grafico_sexo(df))
_mostrar(linha2_dir, charts.grafico_raca_cor(df))

linha3_esq, linha3_dir = st.columns(2)
_mostrar(linha3_esq, charts.grafico_imc(df))
_mostrar(linha3_dir, charts.grafico_municipios(df))

# Gráficos de largura total (quando fizerem sentido).
fig_estado_sexo = charts.grafico_estado_por_sexo(df)
if fig_estado_sexo is not None:
    st.plotly_chart(fig_estado_sexo, use_container_width=True)

fig_temporal = charts.grafico_serie_temporal(df)
if fig_temporal is not None:
    st.plotly_chart(fig_temporal, use_container_width=True)

# --------------------------------------
# TABELA E DOWNLOAD
# --------------------------------------
st.markdown("---")
with st.expander("📋 Ver tabela de dados"):
    st.dataframe(df, use_container_width=True)
    st.download_button(
        "⬇️ Baixar CSV",
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name="sisvan_estado_nutricional.csv",
        mime="text/csv",
    )

st.caption("Fonte: API pública do SISVAN / Ministério da Saúde · Projeto PET-Saúde.")
