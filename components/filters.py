"""Filtros da barra lateral.

Distingue dois tipos de filtro:

- **Filtros de API**: viram parâmetros de query e reduzem o volume baixado
  (município, ano/meses da competência, fase da vida, escolaridade, gestante). A UF
  não aparece: vem fixa da página (``uf_fixa``) e entra em toda consulta.
- **Filtros de cliente**: aplicados sobre o ``DataFrame`` já baixado, sem nova
  requisição (sexo, raça/cor, período). Assim o usuário refina a visualização de
  graça. O período (faixa de anos) é filtro de cliente porque a API só filtra por
  competência, um mês por vez — o ano do recorte é escolhido no formulário.

A função :func:`renderizar_sidebar` desenha os controles e devolve as escolhas; o
painel decide quando disparar a busca. Os municípios vêm da ``dim_regiao``, que
cobre o Pará.
"""

import unicodedata

import pandas as pd
import streamlit as st

from utils.dimensoes import carregar_municipios

# --------------------------------------
# TABELAS DE REFERÊNCIA (dicionario.md)
# --------------------------------------
# codigo_fase_vida -> rótulo
FASES_VIDA = {
    1: "Menor de 6 meses",
    2: "Entre 6 meses e 2 anos",
    3: "Entre 2 anos e 5 anos",
    4: "Entre 5 anos e 7 anos",
    5: "Entre 7 anos e 10 anos",
    6: "Adolescente",
    7: "Adulto",
    8: "Idoso",
}

# codigo_escolaridade -> rótulo (subconjunto documentado como filtrável)
ESCOLARIDADES = {
    1: "Creche",
    3: "Classe alfabetizada",
    4: "Ensino fundamental 1ª a 4ª séries",
    5: "Ensino fundamental 5ª a 8ª séries",
    6: "Ensino fundamental completo",
    15: "Nenhum",
    99: "Sem informação",
}

GESTANTE_OPCOES = {
    "Indiferente": None,
    "Apenas gestantes": 1,
    "Não gestantes": 0,
}

# Anos com dados na API (do mais novo para o mais antigo). A base da API termina em
# 2021; pedir um mês sem dados para uma UF inteira estoura o timeout (502 após
# 60 s), então anos posteriores não são oferecidos.
ANOS_COMPETENCIA = list(range(2021, 2007, -1))

MESES = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro",
    12: "Dezembro",
}


# --------------------------------------
# MUNICÍPIOS (dimensoes/dim_regiao.parquet)
# --------------------------------------
ROTULO_TODOS_MUNICIPIOS = "Todos"


@st.cache_data(show_spinner=False)
def _municipios_da_uf(uf: str) -> dict[str, str]:
    """Código IBGE (6 dígitos) -> nome, em ordem alfabética. Cacheado: é estático."""
    municipios = carregar_municipios(uf)
    return dict(zip(municipios["mun_cod"], municipios["mun_nome"]))


# --------------------------------------
# RENDERIZAÇÃO DA SIDEBAR
# --------------------------------------
def renderizar_sidebar(uf_fixa: str) -> dict:
    """Desenha os filtros e devolve as escolhas do usuário.

    Parameters
    ----------
    uf_fixa : str
        Sigla da UF à qual a página está presa (ex.: ``"PA"``). Não aparece na
        sidebar; entra em toda consulta e define a lista de municípios.

    Returns
    -------
    dict
        Com as chaves:
        - ``filtros_api``: parâmetros para :func:`api.sisvan.consultar_estado_nutricional`.
        - ``filtros_cliente``: dict de recortes aplicados no DataFrame.
        - ``max_registros``: teto de registros a baixar.
        - ``buscar``: ``True`` quando o botão "Buscar dados" foi clicado.
    """
    st.sidebar.header("🔎 Filtros de consulta")
    st.sidebar.caption(
        "A API do SISVAN retorna no máximo 20 registros por página; a busca pagina "
        "até o teto escolhido. Use recortes específicos para resultados mais rápidos."
    )

    # ---- Filtros de API ----
    # Ficam num formulário: mexer neles não dispara nada, só o botão envia. Assim o
    # usuário fecha o recorte antes de uma carga longa, e um clique no meio dela não
    # a interrompe à toa.
    formulario = st.sidebar.form("recorte_api", border=False)
    formulario.subheader("Recorte (enviado à API)")

    uf = uf_fixa
    codigos_municipio = _seletor_municipio(uf_fixa, formulario)

    ano = formulario.selectbox(
        "Ano (competência)",
        options=["Todos"] + ANOS_COMPETENCIA,
        help=(
            "Consulta mês a mês (competências AAAAMM) e divide o teto igualmente "
            "entre os meses. A API só tem dados de 2008 a 2021. Em \"Todos\", a API "
            "entrega do mais antigo para o mais novo (cargas pequenas ficam em 2008)."
        ),
    )
    meses = formulario.multiselect(
        "Meses",
        options=list(MESES),
        format_func=MESES.get,
        placeholder="Todos os meses",
        help="Vale só com um ano escolhido. Vazio = os 12 meses.",
    )

    fases_rotulos = formulario.multiselect(
        "Fase da vida",
        options=list(FASES_VIDA.values()),
        help="Selecione uma ou nenhuma (nenhuma = todas).",
    )

    escolaridade_rotulo = formulario.selectbox(
        "Escolaridade",
        options=["Todas"] + list(ESCOLARIDADES.values()),
        index=0,
    )

    gestante_rotulo = formulario.radio(
        "Gestante", options=list(GESTANTE_OPCOES.keys()), horizontal=True
    )

    # ---- Volume ----
    formulario.subheader("Volume")
    max_registros = formulario.slider(
        "Máximo de registros a baixar",
        min_value=100,
        max_value=5000,
        value=1000,
        step=100,
        help="Teto de paginação. Valores altos deixam a busca mais lenta.",
    )
    formulario.caption(
        "Referência: ~10 a 40 s a cada 1.000 registros — anos recentes são mais "
        "lentos (varia com a instabilidade da API)."
    )

    buscar = formulario.form_submit_button(
        "🔍 Buscar dados", type="primary", width="stretch"
    )

    # ---- Filtros de cliente ----
    # Fora do formulário: refinam o que já foi baixado, sem nova requisição.
    st.sidebar.subheader("Refinar (sem nova busca)")
    sexo = st.sidebar.multiselect("Sexo", options=["Feminino", "Masculino"])
    raca_cor = st.sidebar.multiselect(
        "Raça/Cor",
        options=["Branca", "Preta", "Amarela", "Parda", "Indígena", "Sem informação"],
    )
    # Faixa fixa (os anos que a API tem), sempre visível. Filtra só o que já foi
    # baixado: a API não filtra por faixa de anos, e o ano da busca é escolhido em
    # "Ano (competência)", no formulário.
    periodo = st.sidebar.slider(
        "Período (anos)",
        min_value=min(ANOS_COMPETENCIA),
        max_value=max(ANOS_COMPETENCIA),
        value=(min(ANOS_COMPETENCIA), max(ANOS_COMPETENCIA)),
        help=(
            "Filtra os anos dos dados já baixados, sem nova busca. Anos que não "
            "vieram na busca deixam os gráficos vazios — para buscar um ano, use "
            "\"Ano (competência)\" no recorte."
        ),
    )

    # ---- Monta os dicionários de filtro ----
    filtros_api = _montar_filtros_api(
        uf=uf,
        codigos_municipio=codigos_municipio,
        ano=ano,
        meses=meses,
        fases_rotulos=fases_rotulos,
        escolaridade_rotulo=escolaridade_rotulo,
        gestante_rotulo=gestante_rotulo,
    )

    filtros_cliente = {"sexo": sexo, "raca_cor": raca_cor, "anos": periodo}

    return {
        "filtros_api": filtros_api,
        "filtros_cliente": filtros_cliente,
        "max_registros": max_registros,
        "buscar": buscar,
    }


def _seletor_municipio(uf_fixa: str, recipiente) -> tuple[str, ...]:
    """Desenha o seletor de municípios em ``recipiente`` e devolve os códigos IBGE.

    Devolve uma tupla vazia para "Todos". A tupla sai ordenada para que a mesma
    seleção, feita em outra ordem, caia no mesmo recorte em cache.
    """
    municipios = _municipios_da_uf(uf_fixa)

    if not municipios:
        recipiente.selectbox(
            "Município",
            options=[ROTULO_TODOS_MUNICIPIOS],
            disabled=True,
            help=f"Não há lista de municípios para {uf_fixa}.",
        )
        return ()

    codigos = recipiente.multiselect(
        "Município",
        options=list(municipios),
        format_func=municipios.get,
        placeholder=ROTULO_TODOS_MUNICIPIOS,
        help=(
            f"Vazio = {uf_fixa} inteiro. Com vários municípios, cada um é consultado "
            "à parte e o teto de registros é dividido igualmente entre eles."
        ),
    )
    return tuple(sorted(codigos))


def _montar_filtros_api(
    uf: str,
    codigos_municipio: tuple[str, ...],
    ano: int | str,
    meses: list[int],
    fases_rotulos: list[str],
    escolaridade_rotulo: str,
    gestante_rotulo: str,
) -> dict:
    """Converte as escolhas da UI em parâmetros aceitos pela API."""
    filtros: dict = {"uf": uf}

    # A API aceita um município por requisição; com vários, o cliente faz uma
    # consulta para cada (ver api.sisvan.consultar_estado_nutricional).
    if codigos_municipio:
        filtros["codigo_municipio"] = codigos_municipio

    # A API aceita uma competência (AAAAMM) por requisição; com um ano escolhido, o
    # cliente faz uma consulta por mês. Sem ano, os meses são ignorados.
    if ano != "Todos":
        filtros["ano_mes_competencia"] = tuple(
            f"{ano}{mes:02d}" for mes in sorted(meses or MESES)
        )

    # A API aceita apenas uma fase por requisição; usa a primeira selecionada.
    if fases_rotulos:
        rotulo_para_codigo = {rotulo: codigo for codigo, rotulo in FASES_VIDA.items()}
        filtros["codigo_fase_vida"] = rotulo_para_codigo[fases_rotulos[0]]

    if escolaridade_rotulo and escolaridade_rotulo != "Todas":
        rotulo_para_codigo = {r: c for c, r in ESCOLARIDADES.items()}
        filtros["codigo_escolaridade"] = rotulo_para_codigo[escolaridade_rotulo]

    gestante = GESTANTE_OPCOES.get(gestante_rotulo)
    if gestante is not None:
        filtros["gestante"] = gestante

    return filtros


def aplicar_filtros_cliente(df: pd.DataFrame, filtros_cliente: dict) -> pd.DataFrame:
    """Aplica os recortes de sexo, raça/cor e período sobre o DataFrame já baixado."""
    if df.empty:
        return df

    resultado = df
    sexo = filtros_cliente.get("sexo")
    if sexo and "sexo" in resultado.columns:
        resultado = resultado[resultado["sexo"].isin(sexo)]

    raca_cor = filtros_cliente.get("raca_cor")
    if raca_cor and "raca_cor" in resultado.columns:
        # A API devolve raça/cor sem acento e em caixa alta ("INDIGENA"); compara
        # de forma insensível a acento e caixa para casar com os rótulos da UI.
        alvo = {_normalizar(r) for r in raca_cor}
        mascara = resultado["raca_cor"].map(_normalizar).isin(alvo)
        resultado = resultado[mascara]

    anos = filtros_cliente.get("anos")
    if anos and "ano" in resultado.columns:
        resultado = resultado[resultado["ano"].between(*anos)]

    return resultado


def _normalizar(texto: object) -> str:
    """Remove acentos e caixa para comparações tolerantes."""
    if not isinstance(texto, str):
        return ""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.upper().strip()
