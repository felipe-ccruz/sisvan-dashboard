"""Painel do dashboard (corpo da página).

Reúne o fluxo completo de uma página de análise: sidebar → busca na API → KPIs →
gráficos → tabela. Existe para que as páginas (nacional e Pará) compartilhem
exatamente a mesma estrutura, mudando apenas o recorte de UF: a página do Pará
passa ``uf_fixa="PA"`` e a nacional deixa a UF livre, ganhando em troca a seção de
comparação entre estados.

O cache dos recortes baixados mora aqui, envolvendo a chamada à API mais a
transformação — é o ponto onde as duas coisas se juntam.
"""

import math
import time

import pandas as pd
import streamlit as st

from api.sisvan import LIMITE_MAXIMO_API, SisvanAPIError, consultar_estado_nutricional
from components import charts
from components.filters import aplicar_filtros_cliente, renderizar_sidebar
from utils.data import registros_para_df

# --------------------------------------
# CACHE DE RECORTES
# --------------------------------------
# Não dá para usar ``st.cache_data`` na carga: ele regrava os elementos desenhados
# dentro da função (a barra de progresso) e quebra ao reaproveitar o cache. Por isso
# o cache é um dicionário global simples, com validade e limite de entradas.
VALIDADE_CACHE_S = 3600
MAX_RECORTES_EM_CACHE = 20


@st.cache_resource
def _recortes_em_cache() -> dict:
    """Armazém global (compartilhado entre sessões): chave -> (instante, DataFrame)."""
    return {}


def _chave_recorte(filtros_api: dict, max_registros: int) -> tuple:
    return tuple(sorted(filtros_api.items())), max_registros


def _ler_cache(chave: tuple) -> pd.DataFrame | None:
    entrada = _recortes_em_cache().get(chave)
    if entrada is None:
        return None
    instante, df = entrada
    if time.monotonic() - instante > VALIDADE_CACHE_S:
        _recortes_em_cache().pop(chave, None)
        return None
    return df.copy()


def _gravar_cache(chave: tuple, df: pd.DataFrame) -> None:
    cache = _recortes_em_cache()
    cache[chave] = (time.monotonic(), df)
    # Descarta os recortes mais antigos quando passa do limite.
    while len(cache) > MAX_RECORTES_EM_CACHE:
        mais_antiga = min(cache, key=lambda c: cache[c][0])
        cache.pop(mais_antiga)


# --------------------------------------
# CARGA DE DADOS (com tela de progresso)
# --------------------------------------
def _formatar_numero(valor: int) -> str:
    return f"{valor:,}".replace(",", ".")


def _formatar_duracao(segundos: float) -> str:
    segundos = round(segundos)
    if segundos < 60:
        return f"{segundos} s"
    return f"{segundos // 60} min {segundos % 60:02d} s"


def carregar_dados(filtros_api: dict, max_registros: int) -> pd.DataFrame:
    """Baixa e trata os dados da API, mostrando o progresso por página.

    O 100% da barra é o teto escolhido (a API não informa o total do recorte). Se o
    recorte acabar antes, a barra se ajusta e o resumo avisa. Recortes já baixados
    voltam do cache, sem nova requisição.
    """
    chave = _chave_recorte(filtros_api, max_registros)
    em_cache = _ler_cache(chave)
    if em_cache is not None:
        st.toast("Esse recorte já estava carregado — dados reaproveitados.", icon="♻️")
        return em_cache

    total_paginas = math.ceil(max_registros / LIMITE_MAXIMO_API)
    inicio = time.monotonic()

    with st.status("Carregando dados do SISVAN…", expanded=True) as status:
        barra = st.progress(0.0, text="0%")
        detalhe = st.empty()
        detalhe.caption(
            f"{total_paginas} páginas de {LIMITE_MAXIMO_API} registros a consultar…"
        )

        def ao_progredir(concluidas: int, total: int, registros: int) -> None:
            fracao = concluidas / total if total else 1.0
            decorrido = time.monotonic() - inicio
            restante = decorrido / concluidas * (total - concluidas) if concluidas else 0
            barra.progress(fracao, text=f"{fracao:.0%}")
            detalhe.caption(
                f"Página {concluidas} de {total} · {_formatar_numero(registros)} "
                f"registros · {_formatar_duracao(decorrido)} decorridos · "
                f"~{_formatar_duracao(restante)} restantes"
            )

        try:
            registros = consultar_estado_nutricional(
                filtros=filtros_api,
                max_registros=max_registros,
                ao_progredir=ao_progredir,
            )
        except SisvanAPIError:
            status.update(label="Falha ao carregar os dados do SISVAN", state="error")
            raise

        df = registros_para_df(registros)
        duracao = _formatar_duracao(time.monotonic() - inicio)
        resumo = f"{_formatar_numero(len(df))} registros carregados em {duracao}"
        if len(df) < max_registros:
            resumo += " — o recorte acabou antes do teto"
        status.update(label=resumo, state="complete", expanded=False)

    _gravar_cache(chave, df)
    return df


# --------------------------------------
# BLOCOS DA PÁGINA
# --------------------------------------
# A paleta escolhida vale para as duas páginas: fica numa chave própria da sessão.
CHAVE_PALETA = "paleta_graficos"


def _renderizar_seletor_paleta() -> str:
    """Seletor da paleta dos gráficos, com uma faixa de amostra ao lado."""
    # Streamlit apaga o estado de um widget quando a página troca; regravar a chave
    # antes de desenhá-lo mantém a escolha ao navegar entre as páginas.
    st.session_state[CHAVE_PALETA] = st.session_state.get(
        CHAVE_PALETA, charts.PALETA_PADRAO
    )
    coluna_seletor, coluna_amostra = st.columns([1, 3], vertical_alignment="bottom")
    paleta = coluna_seletor.selectbox(
        "Paleta dos gráficos",
        options=list(charts.PALETAS),
        key=CHAVE_PALETA,
        help="Vale para todos os gráficos, menos o de sexo (sempre azul e rosa).",
    )
    gradiente = ", ".join(charts.amostrar_paleta(paleta, 9))
    coluna_amostra.markdown(
        f'<div style="height: 14px; border-radius: 7px; margin-bottom: 14px; '
        f'background: linear-gradient(90deg, {gradiente});"></div>',
        unsafe_allow_html=True,
    )
    return paleta


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


def _renderizar_comparacao_ufs(df: pd.DataFrame, uf_destaque: str, paleta: str) -> None:
    """Seção que confronta a UF em foco com os demais estados do recorte."""
    fig_ufs = charts.grafico_ufs(df, uf_destaque=uf_destaque, paleta=paleta)
    fig_comparado = charts.grafico_estado_nutricional_comparado(
        df, uf_destaque=uf_destaque, paleta=paleta
    )
    if fig_ufs is None and fig_comparado is None:
        return

    st.subheader(f"Comparação entre estados ({uf_destaque} em destaque)")
    if fig_ufs is not None:
        st.plotly_chart(fig_ufs, width="stretch")
    if fig_comparado is not None:
        st.plotly_chart(fig_comparado, width="stretch")
    st.markdown("---")


def _renderizar_graficos(df: pd.DataFrame, paleta: str) -> None:
    """Grade de gráficos comum às duas páginas."""
    linha1_esq, linha1_dir = st.columns(2)
    _mostrar(linha1_esq, charts.grafico_estado_nutricional(df, paleta=paleta))
    _mostrar(linha1_dir, charts.grafico_fase_vida(df, paleta=paleta))

    linha2_esq, linha2_dir = st.columns(2)
    _mostrar(linha2_esq, charts.grafico_sexo(df))
    _mostrar(linha2_dir, charts.grafico_raca_cor(df, paleta=paleta))

    linha3_esq, linha3_dir = st.columns(2)
    _mostrar(linha3_esq, charts.grafico_imc(df, paleta=paleta))
    _mostrar(linha3_dir, charts.grafico_municipios(df, paleta=paleta))

    # Gráficos de largura total (quando fizerem sentido).
    fig_estado_sexo = charts.grafico_estado_por_sexo(df)
    if fig_estado_sexo is not None:
        st.plotly_chart(fig_estado_sexo, width="stretch")

    fig_por_ano = charts.grafico_estado_nutricional_por_ano(df, paleta=paleta)
    if fig_por_ano is not None:
        st.plotly_chart(fig_por_ano, width="stretch")
    else:
        # Aviso em vez de sumir: com a API entregando do mais antigo para o mais
        # novo, cargas pequenas costumam cobrir um ano só.
        st.info(
            "O gráfico de estado nutricional por ano precisa de pelo menos dois anos "
            "no recorte. A API entrega os registros do mais antigo para o mais novo, "
            "então cargas pequenas costumam cobrir um ano só — aumente o teto ou "
            "refine o recorte (ex.: um município)."
        )

    fig_temporal = charts.grafico_serie_temporal(df, paleta=paleta)
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
    paleta = _renderizar_seletor_paleta()

    opcoes = renderizar_sidebar(uf_fixa=uf_fixa)

    # Guarda o último resultado na sessão para sobreviver a reruns de filtros de cliente.
    if opcoes["buscar"]:
        try:
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
        _renderizar_comparacao_ufs(df, uf_destaque, paleta)
    _renderizar_graficos(df, paleta)
    _renderizar_tabela(df, nome_arquivo_csv)

    st.caption("Fonte: API pública do SISVAN / Ministério da Saúde · Projeto PET-Saúde.")
