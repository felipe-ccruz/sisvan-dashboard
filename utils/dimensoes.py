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
    ``codigo_municipio`` da API e ``mun_cod`` da dimensão).
    """
    caminho = MALHAS_MUNICIPAIS.get(uf)
    if caminho is None or not caminho.exists():
        return None
    with open(caminho, encoding="utf-8") as arquivo:
        return json.load(arquivo)


def _chave_ordenacao(nome: str) -> str:
    """Ordena ignorando acentos, para "Óbidos" não ir parar depois de "Xinguara"."""
    return unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().upper()
