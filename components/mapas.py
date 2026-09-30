"""Mapas do dashboard (Plotly + malha municipal do IBGE).

Separado de :mod:`components.charts` porque um mapa depende de mais que o
``DataFrame``: precisa da malha (GeoJSON) e da dimensão de municípios, para que os
municípios sem nenhum registro também apareçam — é justamente o vazio que o mapa
quer mostrar.

Princípios:

- Só o estado na tela: projeção ajustada aos municípios e fundo desligado, sem
  vizinhos nem camadas de mapa-base baixadas da internet.
- Uma única camada (trace) por mapa. Cada camada embute a malha inteira (~700 KB)
  na figura, e a figura é reenviada ao navegador a cada rerun.
- Contagem em faixas, não em escala contínua: com um município muito maior que os
  outros (Belém), a escala contínua apagaria o resto do estado.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components import charts
from utils.dimensoes import carregar_malha_municipal, carregar_municipios

# --------------------------------------
# FAIXAS DE REGISTROS
# --------------------------------------
# (limite inferior, rótulo). O corte em 30 é o mínimo usual para uma proporção
# dentro do município (ex.: % de excesso de peso) começar a ter algum sentido.
FAIXAS_REGISTROS = [
    (0, "Nenhum"),
    (1, "1 a 9"),
    (10, "10 a 29"),
    (30, "30 a 99"),
    (100, "100 ou mais"),
]
MINIMO_PARA_PROPORCAO = 30

# Município sem registro: cinza translúcido, legível nos temas claro e escuro.
COR_SEM_REGISTRO = "rgba(138, 137, 132, 0.25)"
COR_BORDA = "rgba(128, 128, 128, 0.55)"


# --------------------------------------
# CARGA (com cache)
# --------------------------------------
@st.cache_resource(show_spinner=False)
def _malha(uf: str) -> dict | None:
    """Malha da UF. ``cache_resource`` devolve o mesmo objeto, sem copiar ~700 KB
    a cada rerun (a figura só lê a malha, nunca a altera)."""
    return carregar_malha_municipal(uf)


@st.cache_data(show_spinner=False)
def _municipios(uf: str) -> pd.DataFrame:
    return carregar_municipios(uf)


# --------------------------------------
# CONSTRUTOR
# --------------------------------------
def _faixa(contagem: pd.Series) -> pd.Series:
    """Índice da faixa (0 = nenhum registro) de cada contagem."""
    limites = [limite for limite, _ in FAIXAS_REGISTROS]
    return pd.Series(np.searchsorted(limites, contagem, side="right") - 1, index=contagem.index)


def _escala_em_degraus(cores: list[str]) -> list[list]:
    """Escala de cor com um degrau por faixa (z inteiro cai no meio do degrau)."""
    n = len(cores)
    escala = []
    for i, cor in enumerate(cores):
        escala += [[i / n, cor], [(i + 1) / n, cor]]
    return escala


def mapa_registros_por_municipio(
    df: pd.DataFrame,
    malha: dict,
    municipios: pd.DataFrame,
    paleta: str = charts.PALETA_PADRAO,
) -> go.Figure | None:
    """Mapa coroplético com quantos registros do recorte caíram em cada município.

    Parameters
    ----------
    df : pd.DataFrame
        Registros já filtrados (precisa de ``codigo_municipio``).
    malha : dict
        GeoJSON com ``id`` = código IBGE de 6 dígitos.
    municipios : pd.DataFrame
        Dimensão (``mun_cod``, ``mun_nome``, ``reg_saude_nome``): todos os
        municípios do estado, inclusive os que não aparecem no recorte.
    paleta : str
        Paleta dos gráficos (ver ``charts.PALETAS``).

    Returns
    -------
    go.Figure | None
        ``None`` se nenhum registro cair num município da malha.
    """
    if df.empty or "codigo_municipio" not in df.columns:
        return None

    contagem = df["codigo_municipio"].astype(str).value_counts()
    dados = municipios.assign(
        registros=municipios["mun_cod"].map(contagem).fillna(0).astype(int)
    )
    if dados["registros"].sum() == 0:
        return None
    dados["faixa"] = _faixa(dados["registros"])

    cores = [COR_SEM_REGISTRO] + charts.amostrar_paleta(paleta, len(FAIXAS_REGISTROS) - 1)
    fig = go.Figure(
        go.Choropleth(
            geojson=malha,
            featureidkey="id",
            locations=dados["mun_cod"],
            z=dados["faixa"],
            zmin=-0.5,
            zmax=len(FAIXAS_REGISTROS) - 0.5,
            colorscale=_escala_em_degraus(cores),
            marker_line_color=COR_BORDA,
            marker_line_width=0.5,
            colorbar=dict(
                title=dict(text="Registros", side="top"),
                tickvals=list(range(len(FAIXAS_REGISTROS))),
                ticktext=[rotulo for _, rotulo in FAIXAS_REGISTROS],
                thickness=14,
                len=0.75,
                outlinewidth=0,
            ),
            customdata=dados[["mun_nome", "reg_saude_nome", "registros"]],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Região de saúde: %{customdata[1]}<br>"
                "%{customdata[2]:,} registro(s)<extra></extra>"
            ),
        )
    )
    fig.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)")
    fig.update_layout(
        height=560,
        margin=dict(l=0, r=0, t=10, b=0),
        font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", size=13),
        separators=",.",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# --------------------------------------
# SEÇÃO DA PÁGINA
# --------------------------------------
def renderizar_mapa_registros(df: pd.DataFrame, uf: str, paleta: str) -> None:
    """Seção "Registros por município". Some quando a UF não tem malha."""
    malha = _malha(uf)
    municipios = _municipios(uf)
    if malha is None or municipios.empty:
        return

    fig = mapa_registros_por_municipio(df, malha, municipios, paleta=paleta)
    if fig is None:
        return

    contagem = df["codigo_municipio"].astype(str).value_counts()
    contagem = contagem[contagem.index.isin(municipios["mun_cod"])]
    total = len(municipios)
    com_registro = len(contagem)
    suficientes = int((contagem >= MINIMO_PARA_PROPORCAO).sum())

    st.subheader("Registros por município")
    st.caption(
        "Quantos registros **desta busca** caíram em cada município. Mostra onde a "
        "amostra baixada se concentra — não é a cobertura do SISVAN nem um "
        "indicador de saúde."
    )
    col1, col2, col3 = st.columns(3)
    col1.metric("Municípios com registro", f"{com_registro} de {total}")
    col2.metric("Sem nenhum registro", total - com_registro)
    col3.metric(
        f"Com {MINIMO_PARA_PROPORCAO} ou mais",
        suficientes,
        help=(
            f"Abaixo de {MINIMO_PARA_PROPORCAO} registros, proporções dentro do "
            "município (ex.: % de excesso de peso) oscilam demais para comparar."
        ),
    )
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False, "scrollZoom": False})
    st.markdown("---")
