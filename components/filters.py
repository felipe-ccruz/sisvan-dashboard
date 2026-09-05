"""Filtros da barra lateral.

Distingue dois tipos de filtro:

- **Filtros de API**: viram parâmetros de query e reduzem o volume baixado
  (UF, município, competência, fase da vida, escolaridade, gestante, idade).
- **Filtros de cliente**: aplicados sobre o ``DataFrame`` já baixado, sem nova
  requisição (sexo, raça/cor). Assim o usuário refina a visualização de graça.

A função :func:`renderizar_sidebar` desenha os controles e devolve as escolhas; o
painel decide quando disparar a busca. Passando ``uf_fixa``, a UF deixa de ser
escolhível e todas as consultas da página ficam presas àquele estado — é o que
separa a página do Pará da página nacional.
"""

import unicodedata

import pandas as pd
import streamlit as st

# --------------------------------------
# TABELAS DE REFERÊNCIA (dicionario.md)
# --------------------------------------
UFS = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
]

# Dois primeiros dígitos do código IBGE do município, por UF. Serve para avisar
# quando o município digitado não pertence à UF fixada da página.
CODIGOS_IBGE_UF = {
    "RO": "11", "AC": "12", "AM": "13", "RR": "14", "PA": "15", "AP": "16",
    "TO": "17", "MA": "21", "PI": "22", "CE": "23", "RN": "24", "PB": "25",
    "PE": "26", "AL": "27", "SE": "28", "BA": "29", "MG": "31", "ES": "32",
    "RJ": "33", "SP": "35", "PR": "41", "SC": "42", "RS": "43", "MS": "50",
    "MT": "51", "GO": "52", "DF": "53",
}

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


# --------------------------------------
# RENDERIZAÇÃO DA SIDEBAR
# --------------------------------------
def renderizar_sidebar(uf_fixa: str | None = None) -> dict:
    """Desenha os filtros e devolve as escolhas do usuário.

    Parameters
    ----------
    uf_fixa : str | None
        Sigla da UF à qual a página está presa (ex.: ``"PA"``). Quando informada, o
        seletor de estado vira apenas um indicador e a UF entra em toda consulta.
        ``None`` mantém o seletor livre (página nacional).

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
    st.sidebar.subheader("Recorte (enviado à API)")

    if uf_fixa:
        uf = uf_fixa
        st.sidebar.selectbox(
            "Estado (UF)",
            options=[uf_fixa],
            index=0,
            disabled=True,
            help="Esta página analisa apenas este estado.",
        )
    else:
        uf = st.sidebar.selectbox("Estado (UF)", options=["Todos"] + UFS, index=0)

    prefixo_ibge = CODIGOS_IBGE_UF.get(uf_fixa or "")
    codigo_municipio = st.sidebar.text_input(
        "Código IBGE do município",
        help=(
            f"Opcional. Deve ser um município do {uf_fixa} (o código começa com "
            f"{prefixo_ibge}). Deixe vazio para não filtrar."
            if prefixo_ibge
            else "Opcional. Ex.: 355030 (São Paulo). Deixe vazio para não filtrar."
        ),
        placeholder=f"começa com {prefixo_ibge}" if prefixo_ibge else "ex.: 355030",
    ).strip()

    # Município fora da UF fixada zeraria o resultado (a API combina os filtros).
    if codigo_municipio and prefixo_ibge and not codigo_municipio.startswith(prefixo_ibge):
        st.sidebar.warning(
            f"O código {codigo_municipio} não é de um município do {uf_fixa}; "
            "a consulta deve voltar vazia."
        )

    competencia = st.sidebar.text_input(
        "Competência (AAAAMM)",
        help="Ano e mês do acompanhamento. Ex.: 202301 para jan/2023.",
        placeholder="ex.: 202301",
    ).strip()

    fases_rotulos = st.sidebar.multiselect(
        "Fase da vida",
        options=list(FASES_VIDA.values()),
        help="Selecione uma ou nenhuma (nenhuma = todas).",
    )

    escolaridade_rotulo = st.sidebar.selectbox(
        "Escolaridade",
        options=["Todas"] + list(ESCOLARIDADES.values()),
        index=0,
    )

    gestante_rotulo = st.sidebar.radio(
        "Gestante", options=list(GESTANTE_OPCOES.keys()), horizontal=True
    )

    idade_min, idade_max = st.sidebar.slider(
        "Faixa de idade (anos)", min_value=0, max_value=120, value=(0, 120)
    )

    # ---- Filtros de cliente ----
    st.sidebar.subheader("Refinar (sem nova busca)")
    sexo = st.sidebar.multiselect("Sexo", options=["Feminino", "Masculino"])
    raca_cor = st.sidebar.multiselect(
        "Raça/Cor",
        options=["Branca", "Preta", "Amarela", "Parda", "Indígena", "Sem informação"],
    )

    # ---- Volume ----
    st.sidebar.subheader("Volume")
    max_registros = st.sidebar.slider(
        "Máximo de registros a baixar",
        min_value=100,
        max_value=5000,
        value=1000,
        step=100,
        help="Teto de paginação. Valores altos deixam a busca mais lenta.",
    )

    buscar = st.sidebar.button("🔍 Buscar dados", type="primary", use_container_width=True)

    # ---- Monta os dicionários de filtro ----
    filtros_api = _montar_filtros_api(
        uf=uf,
        codigo_municipio=codigo_municipio,
        competencia=competencia,
        fases_rotulos=fases_rotulos,
        escolaridade_rotulo=escolaridade_rotulo,
        gestante_rotulo=gestante_rotulo,
        idade_min=idade_min,
        idade_max=idade_max,
    )

    filtros_cliente = {"sexo": sexo, "raca_cor": raca_cor}

    return {
        "filtros_api": filtros_api,
        "filtros_cliente": filtros_cliente,
        "max_registros": max_registros,
        "buscar": buscar,
    }


def _montar_filtros_api(
    uf: str,
    codigo_municipio: str,
    competencia: str,
    fases_rotulos: list[str],
    escolaridade_rotulo: str,
    gestante_rotulo: str,
    idade_min: int,
    idade_max: int,
) -> dict:
    """Converte as escolhas da UI em parâmetros aceitos pela API."""
    filtros: dict = {}

    if uf and uf != "Todos":
        filtros["uf"] = uf
    if codigo_municipio:
        filtros["codigo_municipio"] = codigo_municipio
    if competencia:
        filtros["ano_mes_competencia"] = competencia

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

    # Só envia idade quando difere do intervalo completo (evita filtro à toa).
    if idade_min > 0:
        filtros["idade_minima"] = idade_min
    if idade_max < 120:
        filtros["idade_maxima"] = idade_max

    return filtros


def aplicar_filtros_cliente(df: pd.DataFrame, filtros_cliente: dict) -> pd.DataFrame:
    """Aplica os recortes de sexo e raça/cor sobre o DataFrame já baixado."""
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

    return resultado


def _normalizar(texto: object) -> str:
    """Remove acentos e caixa para comparações tolerantes."""
    if not isinstance(texto, str):
        return ""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.upper().strip()
