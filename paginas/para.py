"""Página do Pará — recorte estadual da SESPA.

Mesma estrutura da página nacional, com uma diferença: a UF fica presa em ``PA``,
então toda consulta à API já nasce filtrada pelo estado.
"""

from components.painel import renderizar_painel

UF = "PA"

renderizar_painel(
    titulo="🌳 SISVAN — Pará",
    descricao=(
        "Microdados de acompanhamento nutricional do estado do Pará. Todas as "
        "consultas desta página já saem filtradas pela UF PA — use os demais "
        "filtros para recortar por município, competência ou fase da vida."
    ),
    chave_estado="df_para",
    nome_arquivo_csv="sisvan_estado_nutricional_para.csv",
    uf_fixa=UF,
)
