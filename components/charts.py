"""Construtores de gráficos (Plotly) para a dashboard.

Cada função recebe o ``DataFrame`` já tratado e devolve uma figura Plotly. Segue
alguns princípios de visualização:

- Todos os gráficos (menos o de sexo) tiram as cores de **uma paleta contínua do
  Plotly**, escolhida no topo da página (``paleta``, padrão ``"Sunset"``).
- A cor fica presa à entidade (fase da vida, raça/cor, grupo nutricional), nunca à
  posição da barra: um filtro que tira categorias não repinta as que sobram.
- Sexo tem cores fixas (azul e rosa), independentes da paleta.
- Rótulos diretos seletivos (contagem na ponta da barra); grade discreta.
"""

import unicodedata

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.colors import sample_colorscale

from components.filters import FASES_VIDA
from utils.data import (
    ORDEM_GRUPOS_ESTADO_NUTRICIONAL,
    agrupar_estado_nutricional,
    posicao_estado_nutricional,
)

# --------------------------------------
# PALETAS
# --------------------------------------
# Escalas contínuas do Plotly oferecidas no seletor, com o trecho útil de cada uma.
# As pontas são cortadas porque o extremo escuro de algumas some no tema escuro e o
# claro de outras some no tema claro; o corte mantém contraste de ~1,8:1 ou mais
# nos dois fundos.
PALETAS = {
    "Sunset": (0.35, 1.0),
    "Magma": (0.38, 0.80),
    "Turbo": (0.10, 0.90),
    "Mint": (0.40, 1.0),
    "Viridis": (0.22, 0.80),
    "Aggrnyl": (0.08, 0.78),
}
PALETA_PADRAO = "Sunset"


def _cores_em(paleta: str, fracoes: list[float]) -> list[str]:
    """Cores da paleta nas frações dadas (0 = início do trecho útil, 1 = fim)."""
    if paleta not in PALETAS:
        raise ValueError(f"Paleta desconhecida: {paleta!r}. Opções: {', '.join(PALETAS)}")
    inicio, fim = PALETAS[paleta]
    escala = px.colors.get_colorscale(paleta)
    return sample_colorscale(escala, [inicio + f * (fim - inicio) for f in fracoes])


def amostrar_paleta(paleta: str, n: int) -> list[str]:
    """``n`` cores espaçadas por igual ao longo do trecho útil da paleta."""
    return _cores_em(paleta, [0.5] if n == 1 else [i / (n - 1) for i in range(n)])


def _cor_principal(paleta: str) -> str:
    """Tom único da paleta para gráficos de uma série só (linha do tempo)."""
    return _cores_em(paleta, [0.75])[0]


def _cores_comparacao(paleta: str) -> tuple[str, str]:
    """(demais, destaque): as duas pontas da paleta, o par mais separado possível."""
    demais, destaque = _cores_em(paleta, [0.0, 1.0])
    return demais, destaque


# Sexo fica fora da paleta: azul e rosa escolhidos à mão, iguais em qualquer escolha.
CORES_SEXO = {"Feminino": "#e87ba4", "Masculino": "#2a78d6"}

# Cinza para o que não tem categoria conhecida. O mesmo cinza, translúcido, marca
# "Sem informação" — a falta de dado fica visível sem competir com as categorias.
NEUTRO = "#8a8984"
NEUTRO_SEM_INFORMACAO = "rgba(138, 137, 132, 0.4)"

# Grade translúcida: discreta tanto no tema claro quanto no escuro do Streamlit.
COR_GRADE = "rgba(128, 128, 128, 0.18)"

# Nos gráficos comparativos, a UF em foco fica numa ponta da paleta e as demais na
# outra — é destaque, não categoria.
UF_DESTAQUE_PADRAO = "PA"
ROTULO_DEMAIS_UFS = "Demais estados"


def cores_estado_nutricional(paleta: str = PALETA_PADRAO) -> dict[str, str]:
    """Cor de cada grupo nutricional, espaçada na paleta do déficit ao excesso."""
    cores = amostrar_paleta(paleta, len(ORDEM_GRUPOS_ESTADO_NUTRICIONAL))
    return dict(zip(ORDEM_GRUPOS_ESTADO_NUTRICIONAL, cores))


def _aplicar_tema(fig: go.Figure) -> go.Figure:
    """Aplica layout consistente a todas as figuras."""
    fig.update_layout(
        template="plotly_white",
        font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", size=13),
        margin=dict(l=10, r=10, t=50, b=10),
        title=dict(font=dict(size=16), x=0, xanchor="left"),
        legend=dict(title_text=""),
        separators=",.",  # pt-BR: 1.524 e 41,2%
        # Fundo transparente: o gráfico herda o tema (claro ou escuro) da página.
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor=COR_GRADE)
    return fig


# --------------------------------------
# RÓTULOS DE EXIBIÇÃO
# --------------------------------------
# A API manda parte do texto em caixa alta e sem acento ("INDIGENA"). O gráfico
# mostra a forma do dicionário do SISVAN quando a conhece.
ROTULOS_FASE_VIDA = list(FASES_VIDA.values())
ROTULOS_RACA_COR = ["Branca", "Preta", "Amarela", "Parda", "Indígena"]

_SEM_INFORMACAO = {"SEM INFORMACAO", "NAO INFORMADO", "INVALIDO"}


def _chave(valor: str) -> str:
    """Maiúsculas, sem acento e com espaços simples, para casar variações."""
    sem_acento = unicodedata.normalize("NFKD", valor).encode("ascii", "ignore").decode()
    return " ".join(sem_acento.upper().split())


def _contar_rotulos(serie: pd.Series, canonicos: list[str]) -> pd.Series:
    """Contagem por rótulo de exibição (variações do mesmo valor somadas)."""
    por_chave = {_chave(rotulo): rotulo for rotulo in canonicos}

    def exibir(valor: object) -> str:
        texto = str(valor)
        padrao = texto.capitalize() if texto.isupper() else texto
        return por_chave.get(_chave(texto), padrao)

    return serie.dropna().map(exibir).value_counts()


def _sem_informacao(rotulo: str) -> bool:
    return _chave(rotulo) in _SEM_INFORMACAO


def _percentual(fracao: float, casas: int) -> str:
    """Percentual em pt-BR; uma fatia que arredondaria para zero vira "<1%"."""
    minimo = 10 ** -casas
    if 0 < fracao * 100 < minimo:
        return f"<{minimo:g}%".replace(".", ",")
    return f"{fracao * 100:.{casas}f}%".replace(".", ",")


# --------------------------------------
# BARRAS HORIZONTAIS (base dos gráficos de distribuição)
# --------------------------------------
ALTURA_BARRAS = 340
# Com poucas categorias, o eixo reserva espaço para este número de barras: uma
# categoria só não vira um bloco do tamanho do gráfico, e as alturas batem entre
# os gráficos lado a lado.
MIN_FAIXAS = 6


def _barras_horizontais(
    rotulos: list[str],
    registros: list[int],
    cores: list[str],
    titulo: str,
) -> go.Figure:
    """Barras horizontais na ordem dada (de cima para baixo), uma cor por barra.

    Cada barra leva o rótulo direto (contagem e percentual do recorte), então o
    eixo de valores e a grade saem.
    """
    total = sum(registros)
    fig = go.Figure(
        go.Bar(
            x=registros,
            y=rotulos,
            orientation="h",
            marker=dict(color=cores, cornerradius=4, line_width=0),
            customdata=[
                (_percentual(r / total, 0), _percentual(r / total, 1)) for r in registros
            ],
            texttemplate="%{x:,}  ·  %{customdata[0]}",
            textposition="outside",
            cliponaxis=False,
            hovertemplate=(
                "%{y}<br>%{x:,} registros<br>%{customdata[1]} do recorte<extra></extra>"
            ),
        )
    )
    faixas = max(len(rotulos), MIN_FAIXAS)
    fig.update_layout(
        title=titulo,
        height=max(ALTURA_BARRAS, 60 + 34 * len(rotulos)),
        bargap=0.3,
        showlegend=False,
    )
    # Eixo invertido: a primeira categoria fica no topo.
    fig.update_yaxes(
        range=[faixas - 0.5, -0.5], showgrid=False, title=None, ticks="", automargin=True
    )
    fig.update_xaxes(visible=False, range=[0, max(registros) * 1.35])
    return _aplicar_tema(fig)


def _cor_categoria(rotulo: str, cores: dict[str, str]) -> str:
    """Cor da categoria conhecida; cinza apagado para "Sem informação", cinza
    cheio para o que não se conhece."""
    if rotulo in cores:
        return cores[rotulo]
    return NEUTRO_SEM_INFORMACAO if _sem_informacao(rotulo) else NEUTRO


def _cores_por_magnitude(valores: list[int], paleta: str) -> list[str]:
    """Cor pela magnitude (valor / maior valor), para barras sem categoria fixa."""
    maior = max(valores)
    return _cores_em(paleta, [v / maior for v in valores])


# --------------------------------------
# GRÁFICOS ESPECÍFICOS
# --------------------------------------
def grafico_estado_nutricional(
    df: pd.DataFrame, paleta: str = PALETA_PADRAO
) -> go.Figure | None:
    """Distribuição do estado nutricional (unificado por faixa etária).

    Segue a ordem clínica (do déficit, no topo, ao excesso), não o ranking, e cada
    barra leva a cor do seu grupo, espaçada na paleta na mesma ordem.
    """
    if df.empty or "estado_nutricional" not in df.columns:
        return None
    contagem = df["estado_nutricional"].dropna().value_counts()
    if contagem.empty:
        return None

    dados = contagem.rename_axis("rotulo").reset_index(name="registros")
    dados["grupo"] = agrupar_estado_nutricional(dados["rotulo"])
    # Rótulo fora da escala conhecida vai para o fim.
    dados["posicao"] = posicao_estado_nutricional(dados["rotulo"]).fillna(len(dados) + 99)
    dados = dados.sort_values(["posicao", "registros"], ascending=[True, False])
    cores = dados["grupo"].map(cores_estado_nutricional(paleta)).fillna(NEUTRO)

    return _barras_horizontais(
        dados["rotulo"].tolist(), dados["registros"].tolist(), cores.tolist(),
        "Estado nutricional",
    )


def grafico_fase_vida(df: pd.DataFrame, paleta: str = PALETA_PADRAO) -> go.Figure | None:
    """Distribuição por fase da vida, na ordem do curso da vida."""
    if df.empty or "fase_vida" not in df.columns:
        return None
    contagem = _contar_rotulos(df["fase_vida"], ROTULOS_FASE_VIDA)
    if contagem.empty:
        return None

    ordem = {rotulo: i for i, rotulo in enumerate(ROTULOS_FASE_VIDA)}
    rotulos = sorted(contagem.index, key=lambda r: (ordem.get(r, len(ordem)), -contagem[r]))
    # A cor segue a fase (posição fixa na paleta), não a posição da barra.
    cores_fase = dict(zip(ROTULOS_FASE_VIDA, amostrar_paleta(paleta, len(ROTULOS_FASE_VIDA))))
    cores = [_cor_categoria(r, cores_fase) for r in rotulos]
    return _barras_horizontais(
        rotulos, [int(contagem[r]) for r in rotulos], cores, "Fase da vida"
    )


def grafico_raca_cor(df: pd.DataFrame, paleta: str = PALETA_PADRAO) -> go.Figure | None:
    """Distribuição por raça/cor ("Sem informação" por último, em cinza)."""
    if df.empty or "raca_cor" not in df.columns:
        return None
    contagem = _contar_rotulos(df["raca_cor"], ROTULOS_RACA_COR)
    if contagem.empty:
        return None

    rotulos = sorted(contagem.index, key=lambda r: (_sem_informacao(r), -contagem[r]))
    # Cor presa a cada raça/cor (posição fixa na paleta).
    cores_raca = dict(zip(ROTULOS_RACA_COR, amostrar_paleta(paleta, len(ROTULOS_RACA_COR))))
    cores = [_cor_categoria(r, cores_raca) for r in rotulos]
    return _barras_horizontais(
        rotulos, [int(contagem[r]) for r in rotulos], cores, "Raça/Cor"
    )


def grafico_municipios(
    df: pd.DataFrame, top_n: int = 10, paleta: str = PALETA_PADRAO
) -> go.Figure | None:
    """Top municípios por número de acompanhamentos (cor pela magnitude)."""
    if df.empty or "municipio" not in df.columns:
        return None
    contagem = df["municipio"].dropna().value_counts().head(top_n)
    if contagem.empty:
        return None

    registros = contagem.astype(int).tolist()
    return _barras_horizontais(
        contagem.index.tolist(), registros, _cores_por_magnitude(registros, paleta),
        f"Municípios (top {top_n})",
    )


def grafico_sexo(df: pd.DataFrame) -> go.Figure | None:
    """Proporção por sexo (rosca). Cores fixas (azul e rosa), fora da paleta."""
    if df.empty or "sexo" not in df.columns:
        return None
    contagem = df["sexo"].dropna().value_counts()
    if contagem.empty:
        return None

    # Rótulo direto fora da fatia (legível em qualquer tema), total no centro; a
    # legenda sairia repetindo o que já está escrito.
    fig = go.Figure(
        go.Pie(
            labels=contagem.index,
            values=contagem.values,
            hole=0.62,
            sort=False,
            direction="clockwise",
            marker=dict(colors=[CORES_SEXO.get(s, NEUTRO) for s in contagem.index]),
            texttemplate="%{label}<br><b>%{percent:.0%}</b>",
            textposition="outside",
            hovertemplate="%{label}<br>%{value:,} registros<br>%{percent:.1%}<extra></extra>",
        )
    )
    total = f"{int(contagem.sum()):,}".replace(",", ".")
    fig.update_layout(
        title="Sexo",
        height=ALTURA_BARRAS,
        showlegend=False,
        annotations=[dict(
            text=f"<b>{total}</b><br>registros", showarrow=False, font=dict(size=16),
        )],
    )
    return _aplicar_tema(fig)


def grafico_imc(df: pd.DataFrame, paleta: str = PALETA_PADRAO) -> go.Figure | None:
    """Histograma da distribuição de IMC, cada faixa colorida pela posição na escala."""
    if df.empty or "imc" not in df.columns:
        return None
    imc = df.loc[df["imc"].between(10, 60), "imc"]  # descarta outliers claramente inválidos
    if imc.empty:
        return None

    # Faixas calculadas aqui (e não pelo px.histogram) para cada uma ter a sua cor.
    contagens, bordas = np.histogram(imc, bins=30)
    faixas = [
        f"{a:.1f}–{b:.1f}".replace(".", ",") for a, b in zip(bordas[:-1], bordas[1:])
    ]
    fig = go.Figure(
        go.Bar(
            x=(bordas[:-1] + bordas[1:]) / 2,
            y=contagens,
            width=(bordas[1] - bordas[0]) * 0.9,
            marker=dict(color=amostrar_paleta(paleta, len(contagens)), line_width=0),
            customdata=faixas,
            hovertemplate="IMC %{customdata}<br>%{y:,} registros<extra></extra>",
        )
    )
    fig.update_layout(title="Distribuição de IMC", showlegend=False)
    fig.update_xaxes(title_text="IMC")
    fig.update_yaxes(title_text="Registros")
    return _aplicar_tema(fig)


def grafico_estado_nutricional_por_ano(
    df: pd.DataFrame, paleta: str = PALETA_PADRAO
) -> go.Figure | None:
    """Casos registrados por ano, uma linha por estado nutricional (agrupado).

    Só faz sentido com pelo menos dois anos no recorte.
    """
    if df.empty or not {"ano", "estado_nutricional"}.issubset(df.columns):
        return None

    dados = df.assign(
        grupo=agrupar_estado_nutricional(df["estado_nutricional"])
    ).dropna(subset=["ano", "grupo"])
    if dados["ano"].nunique() < 2:
        return None

    # Grade ano x grupo: num ano com dados, um grupo sem casos vale 0. Já um ano sem
    # nenhum registro baixado fica vazio (NaN) e quebra a linha, em vez de ligar os
    # vizinhos como se houvesse medição no meio.
    tabela = pd.crosstab(dados["ano"].astype(int), dados["grupo"])
    ordem = [g for g in ORDEM_GRUPOS_ESTADO_NUTRICIONAL if g in tabela.columns]
    anos = range(tabela.index.min(), tabela.index.max() + 1)
    tabela = (
        tabela[ordem]
        .reindex(anos)
        .rename_axis(index="ano", columns="grupo")
        .reset_index()
        .melt(id_vars="ano", var_name="grupo", value_name="registros")
    )

    fig = px.line(
        tabela, x="ano", y="registros", color="grupo", markers=True,
        title="Casos registrados por ano, por estado nutricional",
        color_discrete_map=cores_estado_nutricional(paleta),
        category_orders={"grupo": ordem},
        labels={"ano": "Ano", "registros": "Registros", "grupo": "Estado nutricional"},
    )
    fig.update_traces(
        line_width=2, marker_size=8, hovertemplate="%{y} registros"
    )
    fig.update_layout(hovermode="x unified")
    fig.update_xaxes(dtick=1, tickformat="d")
    return _aplicar_tema(fig)


def grafico_estado_por_sexo(df: pd.DataFrame) -> go.Figure | None:
    """Estado nutricional por sexo (barras agrupadas, duas séries)."""
    if df.empty or "estado_nutricional" not in df.columns or "sexo" not in df.columns:
        return None
    dados = df.dropna(subset=["estado_nutricional", "sexo"])
    if dados.empty:
        return None

    tabela = (
        dados.groupby(["estado_nutricional", "sexo"]).size().reset_index(name="registros")
    )
    fig = px.bar(
        tabela, x="estado_nutricional", y="registros", color="sexo",
        barmode="group", title="Estado nutricional por sexo",
        color_discrete_map=CORES_SEXO,
        labels={"estado_nutricional": "Estado nutricional",
                "registros": "Registros", "sexo": "Sexo"},
    )
    return _aplicar_tema(fig)


# --------------------------------------
# GRÁFICOS COMPARATIVOS ENTRE UFs
# --------------------------------------
def grafico_ufs(
    df: pd.DataFrame,
    top_n: int = 15,
    uf_destaque: str = UF_DESTAQUE_PADRAO,
    paleta: str = PALETA_PADRAO,
) -> go.Figure | None:
    """Acompanhamentos por UF, com a UF em foco na outra ponta da paleta.

    Só faz sentido quando o recorte trouxe mais de uma UF (página nacional).
    """
    if df.empty or "uf" not in df.columns:
        return None

    contagem = df["uf"].dropna().value_counts()
    if contagem.size < 2:
        return None
    contagem = contagem.head(top_n)

    demais, destaque = _cores_comparacao(paleta)
    cores = [destaque if uf == uf_destaque else demais for uf in contagem.index]
    return _barras_horizontais(
        contagem.index.tolist(), contagem.astype(int).tolist(), cores,
        f"Acompanhamentos por UF (top {top_n})",
    )


def grafico_estado_nutricional_comparado(
    df: pd.DataFrame,
    uf_destaque: str = UF_DESTAQUE_PADRAO,
    paleta: str = PALETA_PADRAO,
) -> go.Figure | None:
    """Estado nutricional: UF em foco x demais estados, em percentual.

    Compara a **distribuição** (não a contagem) porque os dois grupos têm tamanhos
    muito diferentes — só o percentual dentro de cada grupo é comparável.
    """
    if df.empty or not {"uf", "estado_nutricional"}.issubset(df.columns):
        return None

    dados = df.dropna(subset=["uf", "estado_nutricional"])
    if dados.empty:
        return None

    grupo = dados["uf"].eq(uf_destaque).map({True: uf_destaque, False: ROTULO_DEMAIS_UFS})
    if grupo.nunique() < 2:  # sem os dois lados não há comparação
        return None

    tabela = (
        dados.assign(grupo=grupo)
        .groupby(["estado_nutricional", "grupo"])
        .size()
        .reset_index(name="registros")
    )
    total_por_grupo = tabela.groupby("grupo")["registros"].transform("sum")
    tabela["percentual"] = tabela["registros"] / total_por_grupo * 100

    demais, destaque = _cores_comparacao(paleta)
    fig = px.bar(
        tabela, x="estado_nutricional", y="percentual", color="grupo",
        barmode="group", title=f"Estado nutricional — {uf_destaque} x demais estados",
        color_discrete_map={uf_destaque: destaque, ROTULO_DEMAIS_UFS: demais},
        labels={"estado_nutricional": "Estado nutricional",
                "percentual": "% do grupo", "grupo": ""},
        custom_data=["registros"],
    )
    fig.update_traces(
        hovertemplate="%{x}<br>%{y:.1f}% do grupo<br>%{customdata[0]} registros<extra></extra>"
    )
    fig.update_yaxes(ticksuffix="%")
    return _aplicar_tema(fig)
