"""Página nacional — todos os estados.

Mantém o seletor de UF livre: serve tanto para o panorama do Brasil quanto para
olhar um estado específico. Quando o recorte traz mais de uma UF, exibe a seção de
comparação, com o Pará em destaque.
"""

from components.painel import renderizar_painel

renderizar_painel(
    titulo="🇧🇷 SISVAN — Panorama nacional",
    descricao=(
        "Microdados de acompanhamento nutricional de todo o Brasil, consultados ao "
        "vivo na API pública do Ministério da Saúde. Use o filtro de UF para trocar "
        "de estado e comparar com o Pará."
    ),
    chave_estado="df_nacional",
    nome_arquivo_csv="sisvan_estado_nutricional_brasil.csv",
    comparar_ufs=True,
)
