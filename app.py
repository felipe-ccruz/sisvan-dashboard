"""Dashboard SISVAN — Estado Nutricional.

Ponto de entrada do Streamlit. Consome a API pública do SISVAN ao vivo, com cache
de sessão, e apresenta os microdados de estado nutricional com filtros e gráficos.

Uma página: o **Pará**, com as consultas presas à UF ``PA`` (uso da SESPA). A
página nacional saiu — comparações entre estados não se sustentam com a amostra
que a API permite baixar.

Execução: ``streamlit run app.py``
"""

import streamlit as st

# --------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# --------------------------------------
st.set_page_config(
    page_title="SISVAN — Estado Nutricional",
    page_icon="🥗",
    layout="wide",
)

# --------------------------------------
# NAVEGAÇÃO
# --------------------------------------
# As páginas ficam em ``paginas/`` (e não em ``pages/``) porque a navegação é
# declarada aqui: assim os rótulos e ícones ficam explícitos, sem depender do
# nome do arquivo.
paginas = [
    st.Page("paginas/para.py", title="Pará", icon="🌳", default=True),
]

st.navigation(paginas).run()
