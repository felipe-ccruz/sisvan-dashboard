"""Transformação e limpeza dos microdados do SISVAN.

Recebe a lista de registros crua da API (:mod:`api.sisvan`) e devolve um
``DataFrame`` pronto para os filtros e gráficos. Mantém-se puro (só pandas) para
poder ser testado sem o Streamlit.

Notas sobre os dados brutos:
- A API já entrega as dimensões traduzidas (município, fase da vida, raça/cor…),
  então não é preciso replicar as tabelas de código→rótulo do dicionário.
- O texto vem com codificação inconsistente: ora sem acento (``SEM INFORMACAO``),
  ora com bytes perdidos (``SEM INFORMA�O``). Corrigimos os casos conhecidos.
- O estado nutricional está espalhado em várias colunas por faixa etária; elas são
  mutuamente exclusivas e as unificamos em ``estado_nutricional``.
"""

import re

import pandas as pd

# --------------------------------------
# CORREÇÃO DE TEXTO
# --------------------------------------
# A API mistura acentuação removida com mojibake irrecuperável (caractere U+FFFD).
# Como os bytes originais se perdem no "�", não dá para casar a string exata. Em vez
# disso, comparamos o "esqueleto" do valor (apenas letras A-Z e espaços), que é estável
# independentemente de quais bytes se perderam.
TEXTO_CORRIGIDO = {
    "SEM INFORMACAO": "Sem informação",  # acento removido
    "SEM INFORMAO": "Sem informação",    # mojibake (Ç/Ã viraram U+FFFD)
    "NAO INFORMADO": "Não informado",
    "NO INFORMADO": "Não informado",
}


def _esqueleto(valor: str) -> str:
    """Reduz o texto a letras A-Z e espaços, em maiúsculas, para casar valores
    com codificação inconsistente."""
    return re.sub(r"[^A-Z ]", "", valor.upper()).strip()

# Colunas de estado nutricional por faixa etária, em ordem de prioridade para
# unificar num único campo. Cada registro preenche apenas uma delas.
COLUNAS_ESTADO_NUTRICIONAL = [
    "codigo_estado_nutricional_adulto",
    "codigo_estado_nutricional_idoso",
    "adolescente_imc_x_idade",
    "crianca_imc_x_idade",
]

MAPA_SEXO = {"F": "Feminino", "M": "Masculino"}

# Colunas numéricas que vêm como texto ("70", "1.58").
COLUNAS_NUMERICAS = ["peso", "altura", "imc", "imc_pre_gestacional"]

# Rótulos amigáveis para exibição (tabelas e eixos de gráfico).
COLUNAS_ROTULOS = {
    "uf": "UF",
    "municipio": "Município",
    "idade": "Idade",
    "fase_vida": "Fase da vida",
    "sexo": "Sexo",
    "raca_cor": "Raça/Cor",
    "escolaridade": "Escolaridade",
    "povo_comunidade": "Povo/Comunidade",
    "peso": "Peso (kg)",
    "altura": "Altura (m)",
    "imc": "IMC",
    "estado_nutricional": "Estado nutricional",
    "ano_mes_competencia": "Competência",
    "ano": "Ano",
    "mes": "Mês",
    "sistema_origem_acompanhamento": "Sistema de origem",
}


# --------------------------------------
# FUNÇÕES AUXILIARES
# --------------------------------------
def _corrigir_texto(serie: pd.Series) -> pd.Series:
    """Normaliza valores de texto com codificação quebrada."""

    def corrigir(valor: object) -> object:
        if not isinstance(valor, str):
            return valor
        return TEXTO_CORRIGIDO.get(_esqueleto(valor), valor)

    return serie.map(corrigir)


def _para_numero(serie: pd.Series) -> pd.Series:
    """Converte texto ("1.58") para número, virando NaN quando inválido."""
    return pd.to_numeric(serie, errors="coerce")


def _unificar_estado_nutricional(df: pd.DataFrame) -> pd.Series:
    """Combina as colunas de estado nutricional por faixa em uma só."""
    disponiveis = [c for c in COLUNAS_ESTADO_NUTRICIONAL if c in df.columns]
    if not disponiveis:
        return pd.Series(pd.NA, index=df.index, dtype="object")

    estado = df[disponiveis[0]]
    for coluna in disponiveis[1:]:
        estado = estado.fillna(df[coluna])
    return estado


# --------------------------------------
# TRANSFORMAÇÃO PRINCIPAL
# --------------------------------------
def registros_para_df(registros: list[dict]) -> pd.DataFrame:
    """Converte a lista de registros da API em um ``DataFrame`` tratado.

    Parameters
    ----------
    registros : list[dict]
        Saída de :func:`api.sisvan.consultar_estado_nutricional`.

    Returns
    -------
    pd.DataFrame
        DataFrame limpo. Vazio (sem colunas) quando não há registros.
    """
    if not registros:
        return pd.DataFrame()

    df = pd.DataFrame(registros)

    # Corrige codificação em todas as colunas de texto.
    colunas_texto = df.select_dtypes(include="object").columns
    for coluna in colunas_texto:
        df[coluna] = _corrigir_texto(df[coluna])

    # Converte colunas numéricas.
    for coluna in COLUNAS_NUMERICAS:
        if coluna in df.columns:
            df[coluna] = _para_numero(df[coluna])

    # Traduz sexo para exibição.
    if "sexo" in df.columns:
        df["sexo"] = df["sexo"].map(MAPA_SEXO).fillna(df["sexo"])

    # Deriva ano e mês a partir da competência (formato YYYYMM).
    if "ano_mes_competencia" in df.columns:
        competencia = df["ano_mes_competencia"].astype(str)
        df["ano"] = pd.to_numeric(competencia.str[:4], errors="coerce").astype("Int64")
        df["mes"] = pd.to_numeric(competencia.str[4:6], errors="coerce").astype("Int64")

    # Data do acompanhamento como datetime.
    if "data_acompanhamento" in df.columns:
        df["data_acompanhamento"] = pd.to_datetime(
            df["data_acompanhamento"], errors="coerce"
        )

    # Unifica o estado nutricional por faixa etária.
    df["estado_nutricional"] = _unificar_estado_nutricional(df)

    return df


def rotular(colunas: list[str] | str) -> list[str] | str:
    """Devolve o(s) rótulo(s) amigável(is) de uma ou mais colunas."""
    if isinstance(colunas, str):
        return COLUNAS_ROTULOS.get(colunas, colunas)
    return [COLUNAS_ROTULOS.get(coluna, coluna) for coluna in colunas]


# --------------------------------------
# AGRUPAMENTO DO ESTADO NUTRICIONAL
# --------------------------------------
# Cada faixa etária usa a própria escala (criança: "Eutrofia"; adulto e idoso:
# "Adequado ou eutrófico"; o adulto ainda divide a obesidade em graus). Para
# acompanhar o recorte inteiro ao longo do tempo, os rótulos equivalentes viram um
# grupo só. A ordem vai do déficit ao excesso, com a eutrofia no meio.
GRUPOS_ESTADO_NUTRICIONAL = {
    "Magreza acentuada": ["Magreza acentuada"],
    "Magreza / baixo peso": ["Magreza", "Baixo peso"],
    "Eutrofia": ["Eutrofia", "Adequado ou eutrófico"],
    "Risco de sobrepeso": ["Risco de sobrepeso"],
    "Sobrepeso": ["Sobrepeso"],
    "Obesidade": [
        "Obesidade",
        "Obesidade Grau I",
        "Obesidade Grau II",
        "Obesidade Grau III",
    ],
}
ORDEM_GRUPOS_ESTADO_NUTRICIONAL = list(GRUPOS_ESTADO_NUTRICIONAL)

# Casamento pelo esqueleto do texto, tolerante a acento perdido e caixa.
_GRUPO_POR_ESQUELETO = {
    _esqueleto(rotulo): grupo
    for grupo, rotulos in GRUPOS_ESTADO_NUTRICIONAL.items()
    for rotulo in rotulos
}


def agrupar_estado_nutricional(serie: pd.Series) -> pd.Series:
    """Converte os rótulos de estado nutricional nos grupos harmonizados.

    Rótulos desconhecidos (ou ausentes) viram ``NA``.
    """

    def agrupar(valor: object) -> object:
        if not isinstance(valor, str):
            return pd.NA
        return _GRUPO_POR_ESQUELETO.get(_esqueleto(valor), pd.NA)

    return serie.map(agrupar)
