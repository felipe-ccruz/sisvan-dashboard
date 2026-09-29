"""Painel do dashboard (corpo da página).

Reúne o fluxo completo de uma página de análise: sidebar → busca na API → KPIs →
gráficos → tabela. Existe para que as páginas (nacional e Pará) compartilhem
exatamente a mesma estrutura, mudando apenas o recorte de UF: a página do Pará
passa ``uf_fixa="PA"`` e a nacional deixa a UF livre, ganhando em troca a seção de
comparação entre estados.

O cache de sessão (``st.cache_data``) mora aqui, envolvendo a chamada à API mais a
transformação — é o ponto onde as duas coisas se juntam.
"""

import pandas as pd
import streamlit as st

from api.sisvan import SisvanAPIError, consultar_estado_nutricional
from components import charts
from components.filters import aplicar_filtros_cliente, renderizar_sidebar
from utils.data import registros_para_df


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
# BLOCOS DA PÁGINA
# --------------------------------------
def _mostrar(coluna, figura) -> None:
    """Renderiza a figura na coluna, ou uma mensagem se não houver dados."""
    if figura is not None:
        coluna.plotly_chart(figura, width="stretch")
    else:
        coluna.info("Sem dados suficientes para este gráfico.")


def _renderizar_kpis(df: pd.DataFrame, df_bruto: pd.DataFrame, max_registros: int) -> None:
    """Linha de indicadores + nota sobre o volume baixado."""
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Registros", f"{len(df):,}".replace(",", "."))
    col2.metric("Municípios", df["municipio"].nunique() if "municipio" in df else 0)

    imc_medio = df["imc"].mean() if "imc" in df else float("nan")
    col3.metric("IMC médio", f"{imc_medio:.1f}" if pd.notna(imc_medio) else "—")

    if "ano_mes_competencia" in df:
        competencias = df["ano_mes_competencia"].dropna().astype(str)
        periodo = (
            f"{competencias.min()}–{competencias.max()}" if not competencias.empty else "—"
        )
    else:
        periodo = "—"
    col4.metric("Competências", periodo)

    st.caption(
        f"Baixados {len(df_bruto):,} registros (teto: {max_registros:,}). "
        "Amostra da base — não representa o total do recorte.".replace(",", ".")
    )


def _renderizar_comparacao_ufs(df: pd.DataFrame, uf_destaque: str) -> None:
    """Seção que confronta a UF em foco com os demais estados do recorte."""
    fig_ufs = charts.grafico_ufs(df, uf_destaque=uf_destaque)
    fig_comparado = charts.grafico_estado_nutricional_comparado(
        df, uf_destaque=uf_destaque
    )
    if fig_ufs is None and fig_comparado is None:
        return

    st.subheader(f"Comparação entre estados ({uf_destaque} em destaque)")
    if fig_ufs is not None:
        st.plotly_chart(fig_ufs, width="stretch")
    if fig_comparado is not None:
        st.plotly_chart(fig_comparado, width="stretch")
    st.markdown("---")


def _renderizar_graficos(df: pd.DataFrame) -> None:
    """Grade de gráficos comum às duas páginas."""
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
        st.plotly_chart(fig_estado_sexo, width="stretch")

    fig_temporal = charts.grafico_serie_temporal(df)
    if fig_temporal is not None:
        st.plotly_chart(fig_temporal, width="stretch")


def _renderizar_tabela(df: pd.DataFrame, nome_arquivo: str) -> None:
    """Tabela de dados + botão de download."""
    st.markdown("---")
    with st.expander("📋 Ver tabela de dados"):
        st.dataframe(df, width="stretch")
        st.download_button(
            "⬇️ Baixar CSV",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name=nome_arquivo,
            mime="text/csv",
        )


# --------------------------------------
# PAINEL COMPLETO
# --------------------------------------
def renderizar_painel(
    titulo: str,
    descricao: str,
    chave_estado: str,
    nome_arquivo_csv: str,
    uf_fixa: str | None = None,
    comparar_ufs: bool = False,
    uf_destaque: str = charts.UF_DESTAQUE_PADRAO,
) -> None:
    """Desenha a página inteira: cabeçalho, sidebar, KPIs, gráficos e tabela.

    Parameters
    ----------
    titulo : str
        Título exibido no topo da página.
    descricao : str
        Linha de apoio logo abaixo do título.
    chave_estado : str
        Chave usada no ``st.session_state`` para guardar o DataFrame baixado. Cada
        página usa a sua, para que os dados de uma não vazem para a outra.
    nome_arquivo_csv : str
        Nome do arquivo oferecido no botão de download.
    uf_fixa : str | None
        UF à qual a página está presa. ``None`` deixa o seletor de UF livre.
    comparar_ufs : bool
        Quando ``True``, exibe a seção comparativa entre estados (só faz sentido
        na página nacional, onde o recorte pode trazer mais de uma UF).
    uf_destaque : str
        UF realçada nos gráficos comparativos.
    """
    st.title(titulo)
    st.caption(descricao)

    opcoes = renderizar_sidebar(uf_fixa=uf_fixa)

    # Guarda o último resultado na sessão para sobreviver a reruns de filtros de cliente.
    if opcoes["buscar"]:
        try:
            with st.spinner(
                "Consultando a API do SISVAN… isso pode levar alguns segundos."
            ):
                st.session_state[chave_estado] = carregar_dados(
                    opcoes["filtros_api"], opcoes["max_registros"]
                )
        except SisvanAPIError as erro:
            st.error(
                "Não foi possível consultar a API do SISVAN. Ela costuma ficar instável "
                f"em consultas filtradas — tente novamente ou refine o recorte.\n\n{erro}"
            )

    # ---- Estado inicial (antes da primeira busca) ----
    if chave_estado not in st.session_state:
        st.info(
            "👈 Defina os filtros na barra lateral e clique em **Buscar dados** para "
            "começar.\n\nDica: a API retorna no máximo 20 registros por página, então "
            "recortes específicos (município + competência) trazem resultados mais "
            "rápidos e representativos."
        )
        st.stop()

    # ---- Aplica filtros de cliente ----
    df_bruto: pd.DataFrame = st.session_state[chave_estado]

    if df_bruto.empty:
        st.warning(
            "A consulta não retornou registros para esse recorte. Ajuste os filtros."
        )
        st.stop()

    df = aplicar_filtros_cliente(df_bruto, opcoes["filtros_cliente"])

    if df.empty:
        st.warning(
            "Nenhum registro após aplicar os filtros de sexo/raça. Ajuste-os na sidebar."
        )
        st.stop()

    # ---- Conteúdo ----
    _renderizar_kpis(df, df_bruto, opcoes["max_registros"])
    st.markdown("---")
    if comparar_ufs:
        _renderizar_comparacao_ufs(df, uf_destaque)
    _renderizar_graficos(df)
    _renderizar_tabela(df, nome_arquivo_csv)

    st.caption("Fonte: API pública do SISVAN / Ministério da Saúde · Projeto PET-Saúde.")
