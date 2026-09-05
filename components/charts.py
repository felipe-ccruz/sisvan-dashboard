"""Construtores de gráficos (Plotly) para a dashboard.

Cada função recebe o ``DataFrame`` já tratado e devolve uma figura Plotly. Segue
alguns princípios de visualização:

- Gráfico de série única usa **um único tom** (a categoria já está no eixo; colorir
  cada barra de uma cor seria redundante).
- Gráficos com duas dimensões usam a **paleta categórica em ordem fixa**, com a cor
  presa à entidade (ex.: sexo), nunca ao ranking.
- Rótulos diretos seletivos (contagem na ponta da barra); grade discreta.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.data import rotular

# --------------------------------------
# PALETA E TEMA
# --------------------------------------
# Paleta categórica validada (ordem fixa — a ordem é o mecanismo de segurança para
# daltonismo, não estética).
PALETA_CATEGORICA = [
    "#2a78d6",  # azul
    "#008300",  # verde
    "#e87ba4",  # magenta
    "#eda100",  # amarelo
    "#1baf7a",  # aqua
    "#eb6834",  # laranja
    "#4a3aa7",  # violeta
    "#e34948",  # vermelho
]
AZUL = PALETA_CATEGORICA[0]

# Cores presas a entidades (não mudam se o recorte muda).
CORES_SEXO = {"Feminino": "#e87ba4", "Masculino": "#2a78d6"}

# Nos gráficos comparativos, a UF em foco ganha um tom próprio e as demais ficam no
# azul padrão — é destaque, não categoria.
VERDE = PALETA_CATEGORICA[1]
UF_DESTAQUE_PADRAO = "PA"
ROTULO_DEMAIS_UFS = "Demais estados"


def _aplicar_tema(fig: go.Figure) -> go.Figure:
    """Aplica layout consistente a todas as figuras."""
    fig.update_layout(
        template="plotly_white",
        font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", size=13),
        margin=dict(l=10, r=10, t=50, b=10),
        title=dict(font=dict(size=16)),
        colorway=PALETA_CATEGORICA,
        legend=dict(title_text=""),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#e1e0d9")
    return fig


# --------------------------------------
# GRÁFICOS DE SÉRIE ÚNICA (contagem por categoria)
# --------------------------------------
def barras_contagem(
    df: pd.DataFrame,
    coluna: str,
    titulo: str,
    horizontal: bool = False,
    ordenar_por_valor: bool = True,
    top_n: int | None = None,
) -> go.Figure | None:
    """Barra de contagem de registros por categoria (série única, um tom só)."""
    if df.empty or coluna not in df.columns:
        return None

    contagem = df[coluna].dropna().value_counts()
    if contagem.empty:
        return None
    if not ordenar_por_valor:
        contagem = contagem.sort_index()
    if top_n:
        contagem = contagem.head(top_n)

    dados = contagem.rename_axis(coluna).reset_index(name="registros")
    rotulo = rotular(coluna)

    if horizontal:
        dados = dados.iloc[::-1]  # maior no topo
        fig = px.bar(
            dados, x="registros", y=coluna, orientation="h",
            text="registros", title=titulo,
            labels={"registros": "Registros", coluna: rotulo},
        )
    else:
        fig = px.bar(
            dados, x=coluna, y="registros",
            text="registros", title=titulo,
            labels={"registros": "Registros", coluna: rotulo},
        )

    fig.update_traces(marker_color=AZUL, textposition="outside", cliponaxis=False)
    return _aplicar_tema(fig)


# --------------------------------------
# GRÁFICOS ESPECÍFICOS
# --------------------------------------
def grafico_estado_nutricional(df: pd.DataFrame) -> go.Figure | None:
    """Distribuição do estado nutricional (unificado por faixa etária)."""
    return barras_contagem(
        df, "estado_nutricional", "Estado nutricional", horizontal=True
    )


def grafico_fase_vida(df: pd.DataFrame) -> go.Figure | None:
    """Distribuição por fase da vida."""
    return barras_contagem(df, "fase_vida", "Fase da vida", horizontal=True)


def grafico_raca_cor(df: pd.DataFrame) -> go.Figure | None:
    """Distribuição por raça/cor."""
    return barras_contagem(df, "raca_cor", "Raça/Cor", horizontal=True)


def grafico_municipios(df: pd.DataFrame, top_n: int = 10) -> go.Figure | None:
    """Top municípios por número de acompanhamentos."""
    return barras_contagem(
        df, "municipio", f"Municípios (top {top_n})", horizontal=True, top_n=top_n
    )


def grafico_sexo(df: pd.DataFrame) -> go.Figure | None:
    """Proporção por sexo (rosca). Duas categorias com cor presa à entidade."""
    if df.empty or "sexo" not in df.columns:
        return None
    contagem = df["sexo"].dropna().value_counts()
    if contagem.empty:
        return None

    fig = px.pie(
        names=contagem.index,
        values=contagem.values,
        hole=0.55,
        title="Sexo",
        color=contagem.index,
        color_discrete_map=CORES_SEXO,
    )
    fig.update_traces(textinfo="percent+label")
    return _aplicar_tema(fig)


def grafico_imc(df: pd.DataFrame) -> go.Figure | None:
    """Histograma da distribuição de IMC."""
    if df.empty or "imc" not in df.columns:
        return None
    dados = df[df["imc"].between(10, 60)]  # descarta outliers claramente inválidos
    if dados.empty:
        return None

    fig = px.histogram(dados, x="imc", nbins=30, title="Distribuição de IMC",
                       labels={"imc": "IMC"})
    fig.update_traces(marker_color=AZUL)
    fig.update_yaxes(title_text="Registros")
    return _aplicar_tema(fig)


def grafico_serie_temporal(df: pd.DataFrame) -> go.Figure | None:
    """Acompanhamentos por competência (linha). Só faz sentido com >1 competência."""
    if df.empty or "ano_mes_competencia" not in df.columns:
        return None
    contagem = df["ano_mes_competencia"].dropna().value_counts()
    if contagem.size < 2:
        return None

    dados = contagem.rename_axis("competencia").reset_index(name="registros")
    dados = dados.sort_values("competencia")

    fig = px.line(dados, x="competencia", y="registros", markers=True,
                  title="Acompanhamentos por competência",
                  labels={"competencia": "Competência", "registros": "Registros"})
    fig.update_traces(line_color=AZUL, line_width=2)
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
) -> go.Figure | None:
    """Acompanhamentos por UF, com a UF em foco destacada em outro tom.

    Só faz sentido quando o recorte trouxe mais de uma UF (página nacional).
    """
    if df.empty or "uf" not in df.columns:
        return None

    contagem = df["uf"].dropna().value_counts()
    if contagem.size < 2:
        return None
    contagem = contagem.head(top_n)

    dados = contagem.rename_axis("uf").reset_index(name="registros")
    dados = dados.iloc[::-1]  # maior no topo

    fig = px.bar(
        dados, x="registros", y="uf", orientation="h",
        text="registros", title=f"Acompanhamentos por UF (top {top_n})",
        labels={"registros": "Registros", "uf": "UF"},
    )
    cores = [VERDE if uf == uf_destaque else AZUL for uf in dados["uf"]]
    fig.update_traces(marker_color=cores, textposition="outside", cliponaxis=False)
    return _aplicar_tema(fig)


def grafico_estado_nutricional_comparado(
    df: pd.DataFrame,
    uf_destaque: str = UF_DESTAQUE_PADRAO,
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

    fig = px.bar(
        tabela, x="estado_nutricional", y="percentual", color="grupo",
        barmode="group", title=f"Estado nutricional — {uf_destaque} x demais estados",
        color_discrete_map={uf_destaque: VERDE, ROTULO_DEMAIS_UFS: AZUL},
        labels={"estado_nutricional": "Estado nutricional",
                "percentual": "% do grupo", "grupo": ""},
        custom_data=["registros"],
    )
    fig.update_traces(
        hovertemplate="%{x}<br>%{y:.1f}% do grupo<br>%{customdata[0]} registros<extra></extra>"
    )
    fig.update_yaxes(ticksuffix="%")
    return _aplicar_tema(fig)
