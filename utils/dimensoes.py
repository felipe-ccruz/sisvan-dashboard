"""Tabelas de dimensão locais (pasta ``dimensoes/``).

A ``dim_regiao`` traz os municípios do Pará com nome, código IBGE de 6 dígitos (a
mesma chave de ``codigo_municipio`` na API do SISVAN), coordenadas e regionalização
de saúde. Mantém-se puro (só pandas) para poder ser testado sem o Streamlit.
"""

import unicodedata
from pathlib import Path

import pandas as pd

# --------------------------------------
# CAMINHOS
# --------------------------------------
PASTA_DIMENSOES = Path(__file__).resolve().parent.parent / "dimensoes"
CAMINHO_DIM_REGIAO = PASTA_DIMENSOES / "dim_regiao.parquet"


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
        Colunas ``mun_cod`` (texto, 6 dígitos) e ``mun_nome``. Vazio quando a UF
        não está na dimensão.
    """
    dim = pd.read_parquet(caminho, columns=["mun_cod", "mun_nome", "uf_sigla"])
    municipios = dim[(dim["uf_sigla"] == uf) & (dim["mun_cod"] > 0)]
    return (
        municipios.assign(mun_cod=municipios["mun_cod"].astype(str))
        [["mun_cod", "mun_nome"]]
        .sort_values("mun_nome", key=lambda s: s.map(_chave_ordenacao))
        .reset_index(drop=True)
    )


def _chave_ordenacao(nome: str) -> str:
    """Ordena ignorando acentos, para "Óbidos" não ir parar depois de "Xinguara"."""
    return unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().upper()
