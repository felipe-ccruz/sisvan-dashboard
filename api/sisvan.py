"""Cliente da API pública de Estado Nutricional do SISVAN.

A API retorna microdados (um registro por acompanhamento individual) e possui um
limite rígido de 20 itens por requisição. Para montar recortes com mais registros é
preciso paginar. Este módulo isola essa lógica e não depende do Streamlit — é Python
puro, para poder ser testado e reaproveitado.

Referência: https://apidadosabertos.saude.gov.br/sisvan/estado-nutricional
"""

import math
import time
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait

import requests

# --------------------------------------
# CONSTANTES
# --------------------------------------
URL_BASE = "https://apidadosabertos.saude.gov.br/sisvan/estado-nutricional"

# Cap rígido imposto pela API: "limit deve ser menor ou igual a 20".
LIMITE_MAXIMO_API = 20

# Chave que embrulha a lista de registros na resposta JSON.
CHAVE_RESPOSTA = "estados_nutricionais"

# Requisições simultâneas. A API é instável (502 intermitente); mais que isso tende a
# piorar a taxa de erro sem ganho real de velocidade.
REQUISICOES_PARALELAS = 5

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
# CONSULTA PAGINADA (em paralelo)
# --------------------------------------
# Assinatura do aviso de progresso: (páginas concluídas, total de páginas, registros).
AoProgredir = Callable[[int, int, int], None]


def consultar_estado_nutricional(
    filtros: dict | None = None,
    max_registros: int = 1000,
    timeout: int = 60,
    tentativas: int = 3,
    pausa: float = 1.0,
    paralelas: int = REQUISICOES_PARALELAS,
    ao_progredir: AoProgredir | None = None,
) -> list[dict]:
    """Pagina a API até reunir ``max_registros`` (ou até acabarem os dados).

    Como a API limita cada requisição a 20 itens, o teto vira um número conhecido de
    páginas, baixadas com até ``paralelas`` requisições simultâneas. A API não
    informa o total do recorte: quando uma página volta vazia, os dados acabaram, e
    as páginas seguintes deixam de ser pedidas (o total encolhe). Página incompleta
    não basta como sinal de fim — a API às vezes devolve menos de 20 no meio dos
    dados.

    Parameters
    ----------
    filtros : dict | None
        Parâmetros de query da API. ``codigo_municipio`` e ``ano_mes_competencia``
        podem ser listas: a API só aceita um valor por requisição, então cada
        combinação (município x competência) vira uma consulta própria e o teto é
        dividido entre elas (ver :func:`_consultar_varios_recortes`).
    max_registros : int
        Teto de registros a baixar. Protege contra baixar a base inteira.
    timeout, tentativas, pausa
        Repassados para :func:`requisitar_pagina`.
    paralelas : int
        Número máximo de requisições simultâneas.
    ao_progredir : callable | None
        Chamado a cada página concluída com ``(paginas_concluidas, total_paginas,
        registros)``. ``total_paginas`` parte do teto e diminui se o recorte acabar
        antes. Roda na thread de quem chamou (seguro para atualizar a interface).

    Returns
    -------
    list[dict]
        Registros reunidos, na ordem da API (no máximo ``max_registros``).

    Raises
    ------
    SisvanAPIError
        Se alguma página falhar mesmo após as tentativas.
    """
    recortes = _desdobrar_filtros(filtros)
    if len(recortes) > 1:
        return _consultar_varios_recortes(
            recortes,
            max_registros,
            timeout=timeout,
            tentativas=tentativas,
            pausa=pausa,
            paralelas=paralelas,
            ao_progredir=ao_progredir,
        )
    filtros = recortes[0]

    total_paginas = math.ceil(max_registros / LIMITE_MAXIMO_API)
    paginas: dict[int, list[dict]] = {}
    pendentes: dict[Future, int] = {}
    proxima = 0

    executor = ThreadPoolExecutor(max_workers=paralelas)
    try:
        while True:
            # Mantém a janela cheia enquanto houver páginas dentro do total.
            while len(pendentes) < paralelas and proxima < total_paginas:
                futuro = executor.submit(
                    requisitar_pagina,
                    filtros=filtros,
                    # O offset conta registros, não páginas (ver requisitar_pagina).
                    offset=proxima * LIMITE_MAXIMO_API,
                    limite=LIMITE_MAXIMO_API,
                    timeout=timeout,
                    tentativas=tentativas,
                    pausa=pausa,
                )
                pendentes[futuro] = proxima
                proxima += 1

            if not pendentes:
                break

            concluidos, _ = wait(pendentes, return_when=FIRST_COMPLETED)
            for futuro in concluidos:
                indice = pendentes.pop(futuro)
                pagina = futuro.result()  # propaga SisvanAPIError
                paginas[indice] = pagina

                # Só página vazia marca o fim. A API às vezes devolve menos de 20
                # itens no meio dos dados (registros perdidos no servidor, de forma
                # intermitente); parar numa página incompleta cortaria o resto.
                if not pagina:
                    total_paginas = min(total_paginas, indice)

            validas = [i for i in paginas if i < total_paginas]
            if ao_progredir is not None:
                ao_progredir(
                    len(validas),
                    total_paginas,
                    sum(len(paginas[i]) for i in validas),
                )

            # Todas as páginas úteis chegaram; as que sobraram em voo são além do fim.
            if len(validas) == total_paginas:
                break
    finally:
        # Em caso de erro, não espera as requisições em voo nem começa as da fila.
        executor.shutdown(wait=False, cancel_futures=True)

    registros = [
        registro for indice in range(total_paginas) for registro in paginas[indice]
    ]
    return registros[:max_registros]


# --------------------------------------
# VÁRIOS RECORTES (municípios x competências)
# --------------------------------------
# Parâmetros que aceitam lista na interface, embora a API receba um valor por vez.
PARAMETROS_MULTIPLOS = ("codigo_municipio", "ano_mes_competencia")


def _valores(valor: object) -> list[str]:
    """Normaliza um parâmetro (valor único ou lista) para uma lista de textos."""
    if valor in (None, ""):
        return []
    if isinstance(valor, (list, tuple, set)):
        return [str(item) for item in valor if item not in (None, "")]
    return [str(valor)]


def _desdobrar_filtros(filtros: dict | None) -> list[dict]:
    """Expande os parâmetros com lista em filtros de valor único.

    Devolve uma lista com um filtro por combinação (produto dos municípios pelas
    competências), na ordem município -> competência. Sem listas, devolve só o
    próprio filtro.
    """
    recortes = [dict(filtros or {})]
    for parametro in PARAMETROS_MULTIPLOS:
        valores = _valores((filtros or {}).get(parametro))
        if not valores:
            for recorte in recortes:
                recorte.pop(parametro, None)
            continue
        recortes = [
            {**recorte, parametro: valor} for recorte in recortes for valor in valores
        ]
    return recortes


def _dividir_teto(max_registros: int, partes: int) -> list[int]:
    """Divide o teto em cotas quase iguais (as primeiras levam a sobra).

    Cada parte recebe ao menos 1 registro, mesmo que isso passe do teto quando há
    mais partes que registros — melhor que deixar um recorte escolhido de fora.
    """
    base, sobra = divmod(max_registros, partes)
    return [max(base + (1 if i < sobra else 0), 1) for i in range(partes)]


def _consultar_varios_recortes(
    recortes: list[dict],
    max_registros: int,
    ao_progredir: AoProgredir | None = None,
    **opcoes,
) -> list[dict]:
    """Faz uma consulta paginada por recorte (município x competência) e junta tudo.

    O teto é dividido igualmente entre os recortes: se fosse um teto único
    consumido em sequência, o primeiro poderia esgotá-lo e os demais ficariam de
    fora (ex.: só janeiro de um ano inteiro). O progresso é reportado como uma
    única barra, somando as páginas de todos (o total encolhe quando algum recorte
    acaba antes da cota).
    """
    cotas = _dividir_teto(max_registros, len(recortes))
    planejadas = [math.ceil(cota / LIMITE_MAXIMO_API) for cota in cotas]

    registros: list[dict] = []
    paginas_feitas = 0  # páginas dos municípios já concluídos

    for indice, (recorte, cota) in enumerate(zip(recortes, cotas)):
        restantes = sum(planejadas[indice + 1 :])
        total_atual = [planejadas[indice]]

        def repassar(concluidas: int, total: int, baixados: int) -> None:
            total_atual[0] = total
            if ao_progredir is not None:
                ao_progredir(
                    paginas_feitas + concluidas,
                    paginas_feitas + total + restantes,
                    # As páginas chegam inteiras (20); a cota corta o excedente.
                    len(registros) + min(baixados, cota),
                )

        registros.extend(
            consultar_estado_nutricional(
                filtros=recorte,
                max_registros=cota,
                ao_progredir=repassar,
                **opcoes,
            )
        )
        paginas_feitas += total_atual[0]

    return registros
