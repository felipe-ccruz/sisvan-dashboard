"""Cliente da API pública de Estado Nutricional do SISVAN.

A API retorna microdados (um registro por acompanhamento individual) e possui um
limite rígido de 20 itens por requisição. Para montar recortes com mais registros é
preciso paginar. Este módulo isola essa lógica e não depende do Streamlit — é Python
puro, para poder ser testado e reaproveitado.

Referência: https://apidadosabertos.saude.gov.br/sisvan/estado-nutricional
"""

import time

import requests

# --------------------------------------
# CONSTANTES
# --------------------------------------
URL_BASE = "https://apidadosabertos.saude.gov.br/sisvan/estado-nutricional"

# Cap rígido imposto pela API: "limit deve ser menor ou igual a 20".
LIMITE_MAXIMO_API = 20

# Chave que embrulha a lista de registros na resposta JSON.
CHAVE_RESPOSTA = "estados_nutricionais"

# Filtros aceitos pela API (parâmetros de query). Sexo e raça/cor NÃO estão aqui de
# propósito: são aplicados no lado do cliente, sobre o DataFrame já baixado.
PARAMETROS_API = {
    "codigo_municipio",
    "uf",
    "codigo_cnes",
    "idade_minima",
    "idade_maxima",
    "codigo_fase_vida",
    "codigo_povo_comunidade",
    "codigo_escolaridade",
    "ano_mes_competencia",
    "gestante",
}


class SisvanAPIError(Exception):
    """Erro ao consultar a API do SISVAN."""


# --------------------------------------
# REQUISIÇÃO DE UMA PÁGINA
# --------------------------------------
def _limpar_filtros(filtros: dict | None) -> dict:
    """Mantém apenas parâmetros válidos e com valor preenchido."""
    if not filtros:
        return {}
    return {
        chave: valor
        for chave, valor in filtros.items()
        if chave in PARAMETROS_API and valor not in (None, "", [])
    }


def requisitar_pagina(
    filtros: dict | None = None,
    offset: int = 0,
    limite: int = LIMITE_MAXIMO_API,
    timeout: int = 60,
    tentativas: int = 3,
    pausa: float = 1.0,
) -> list[dict]:
    """Requisita uma única página da API.

    Parameters
    ----------
    filtros : dict | None
        Parâmetros de query aceitos pela API (ver ``PARAMETROS_API``).
    offset : int
        Quantos registros pular (começa em 0). A documentação oficial chama de
        "número da página", mas a API desloca por registro: ``offset=1`` começa
        no 2º item, não no 21º.
    limite : int
        Itens por página. É truncado para ``LIMITE_MAXIMO_API`` (20).
    timeout : int
        Tempo máximo de espera, em segundos, por tentativa.
    tentativas : int
        Número de tentativas em caso de erro transitório (ex.: 502 Proxy Error).
    pausa : float
        Segundos de espera entre tentativas (backoff linear).

    Returns
    -------
    list[dict]
        Lista de registros da página. Vazia quando não há mais dados.
    """
    parametros = _limpar_filtros(filtros)
    parametros["limit"] = min(limite, LIMITE_MAXIMO_API)
    parametros["offset"] = offset

    ultimo_erro: Exception | None = None
    for tentativa in range(1, tentativas + 1):
        try:
            resposta = requests.get(
                URL_BASE,
                params=parametros,
                headers={"accept": "application/json"},
                timeout=timeout,
            )
            resposta.raise_for_status()
            corpo = resposta.json()
            return corpo.get(CHAVE_RESPOSTA, []) or []
        except (requests.RequestException, ValueError) as erro:
            # A API costuma responder 502 (Proxy Error) de forma intermitente em
            # consultas filtradas; tenta de novo com uma pausa crescente.
            ultimo_erro = erro
            if tentativa < tentativas:
                time.sleep(pausa * tentativa)

    raise SisvanAPIError(
        f"Falha ao consultar a API após {tentativas} tentativas "
        f"(offset={offset}): {ultimo_erro}"
    )


# --------------------------------------
# CONSULTA PAGINADA
# --------------------------------------
def consultar_estado_nutricional(
    filtros: dict | None = None,
    max_registros: int = 1000,
    timeout: int = 60,
    tentativas: int = 3,
    pausa: float = 1.0,
) -> list[dict]:
    """Pagina a API até reunir ``max_registros`` (ou até acabarem os dados).

    Como a API limita cada requisição a 20 itens, esta função percorre páginas
    consecutivas. A busca para quando: (a) atinge ``max_registros``, ou (b) uma
    página retorna menos itens que o limite — sinal de que os dados terminaram.

    Parameters
    ----------
    filtros : dict | None
        Parâmetros de query da API.
    max_registros : int
        Teto de registros a baixar. Protege contra baixar a base inteira.
    timeout, tentativas, pausa
        Repassados para :func:`requisitar_pagina`.

    Returns
    -------
    list[dict]
        Registros reunidos (no máximo ``max_registros``).
    """
    registros: list[dict] = []
    offset = 0

    while len(registros) < max_registros:
        pagina = requisitar_pagina(
            filtros=filtros,
            offset=offset,
            limite=LIMITE_MAXIMO_API,
            timeout=timeout,
            tentativas=tentativas,
            pausa=pausa,
        )
        if not pagina:
            break

        registros.extend(pagina)

        # Página incompleta => acabaram os dados desse recorte.
        if len(pagina) < LIMITE_MAXIMO_API:
            break

        # O offset conta registros, não páginas: avançar de 1 em 1 repetiria até
        # 20 vezes cada registro.
        offset += len(pagina)

    return registros[:max_registros]
