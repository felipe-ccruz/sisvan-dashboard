"""Dashboard SISVAN — Estado Nutricional.

Ponto de entrada do Streamlit. Consome a API pública do SISVAN ao vivo, com cache
de sessão, e apresenta os microdados de estado nutricional com filtros e gráficos.

Execução: ``streamlit run app.py``
"""

import streamlit as st

from components.painel import renderizar_painel

# --------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# --------------------------------------
st.set_page_config(
    page_title="SISVAN — Estado Nutricional",
    page_icon="🥗",
    layout="wide",
)

renderizar_painel(
    titulo="🥗 SISVAN — Estado Nutricional",
    descricao=(
        "Análise dos microdados de acompanhamento nutricional do SISVAN, "
        "consultados ao vivo na API pública do Ministério da Saúde."
    ),
    chave_estado="df",
    nome_arquivo_csv="sisvan_estado_nutricional.csv",
)
