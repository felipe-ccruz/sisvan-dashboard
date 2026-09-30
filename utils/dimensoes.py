"""Tabelas de dimensão e malhas locais (pasta ``dimensoes/``).

A ``dim_regiao`` traz os municípios do Pará com nome, código IBGE de 6 dígitos (a
mesma chave de ``codigo_municipio`` na API do SISVAN), coordenadas e regionalização
de saúde. A malha municipal (GeoJSON do IBGE) usa esse mesmo código de 6 dígitos
como ``id`` de cada município. Mantém-se puro (sem Streamlit) para poder ser
testado isoladamente.
"""

import json
import unicodedata
from pathlib import Path

import pandas as pd

# --------------------------------------
# CAMINHOS
# --------------------------------------
PASTA_DIMENSOES = Path(__file__).resolve().parent.parent / "dimensoes"
CAMINHO_DIM_REGIAO = PASTA_DIMENSOES / "dim_regiao.parquet"

# Malhas municipais por UF (GeoJSON do IBGE, gerado pelo script malha_ibge.py do
# tabviva). Por enquanto só o Pará.
MALHAS_MUNICIPAIS = {"PA": PASTA_DIMENSOES / "geo_pa_municipios.json"}


# --------------------------------------
# MUNICÍPIOS
# --------------------------------------
def carregar_municipios(uf: str, caminho: Path = CAMINHO_DIM_REGIAO) -> pd.DataFrame:
    """Lista os municípios de uma UF, em ordem alfabética.

    As linhas-sentinela da dimensão ("Não se aplica", "Em branco", "Não
    encontrado") têm código negativo e ficam de fora.

    Parameters
    ----------
    uf : str
        Sigla da UF (ex.: ``"PA"``).
    caminho : Path
        Arquivo parquet da ``dim_regiao``.

    Returns
    -------
    pd.DataFrame
        Colunas ``mun_cod`` (texto, 6 dígitos), ``mun_nome`` e ``reg_saude_nome``.
        Vazio quando a UF não está na dimensão.
    """
    dim = pd.read_parquet(
        caminho, columns=["mun_cod", "mun_nome", "uf_sigla", "reg_saude_nome"]
    )
    municipios = dim[(dim["uf_sigla"] == uf) & (dim["mun_cod"] > 0)]
    return (
        municipios.assign(mun_cod=municipios["mun_cod"].astype(str))
        [["mun_cod", "mun_nome", "reg_saude_nome"]]
        .sort_values("mun_nome", key=lambda s: s.map(_chave_ordenacao))
        .reset_index(drop=True)
    )


# --------------------------------------
# MALHAS
# --------------------------------------
def carregar_malha_municipal(uf: str) -> dict | None:
    """GeoJSON dos municípios da UF, ou ``None`` se não houver malha para ela.

    O ``id`` de cada feature é o código IBGE de 6 dígitos (chave de junção com
    ``codigo_municipio`` da API e ``mun_cod`` da dimensão). Os polígonos já saem na
    orientação que o Plotly espera (ver :func:`orientar_para_plotly`).
    """
    caminho = MALHAS_MUNICIPAIS.get(uf)
    if caminho is None or not caminho.exists():
        return None
    with open(caminho, encoding="utf-8") as arquivo:
        return orientar_para_plotly(json.load(arquivo))


def orientar_para_plotly(geojson: dict) -> dict:
    """Põe o contorno externo de cada polígono no sentido horário (furos no anti).

    O GeoJSON do IBGE segue a RFC 7946: contorno externo anti-horário. Os mapas
    ``geo`` do Plotly usam o d3, que espera o contrário e lê um polígono
    anti-horário como "o globo inteiro menos o município" — o mapa vira uma mancha
    de cor cobrindo tudo, com o hover ainda funcionando. Altera ``geojson`` no
    lugar e o devolve.
    """
    for feature in geojson["features"]:
        geometria = feature["geometry"]
        if geometria["type"] == "Polygon":
            poligonos = [geometria["coordinates"]]
        elif geometria["type"] == "MultiPolygon":
            poligonos = geometria["coordinates"]
        else:
            continue
        for aneis in poligonos:
            for indice, anel in enumerate(aneis):
                externo = indice == 0
                # Área com sinal (fórmula do laço): > 0 = anti-horário.
                anti_horario = _area_com_sinal(anel) > 0
                if externo == anti_horario:
                    anel.reverse()
    return geojson


def _area_com_sinal(anel: list) -> float:
    """Área (em graus², com sinal) de um anel de coordenadas [lon, lat]."""
    return sum(
        x1 * y2 - x2 * y1 for (x1, y1, *_), (x2, y2, *_) in zip(anel, anel[1:] + anel[:1])
    ) / 2


def _chave_ordenacao(nome: str) -> str:
    """Ordena ignorando acentos, para "Óbidos" não ir parar depois de "Xinguara"."""
    return unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().upper()
