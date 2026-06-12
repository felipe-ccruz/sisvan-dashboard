# 📊 sisvan-dashboard

Dashboard interativo para análise de dados nutricionais do SISVAN, com filtros dinâmicos e visualizações geradas a partir da API pública do Ministério da Saúde.

---

## 🗂️ Sumário

- [Sobre o projeto](#sobre-o-projeto)
- [Tecnologias utilizadas](#tecnologias-utilizadas)
- [Pré-requisitos](#pré-requisitos)
- [Instalação e execução local](#instalação-e-execução-local)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Deploy na nuvem](#deploy-na-nuvem)
- [Como usar o dashboard](#como-usar-o-dashboard)

---

## Sobre o projeto

O **sisvan-dashboard** foi desenvolvido para facilitar a análise de dados do Sistema de Vigilância Alimentar e Nutricional (SISVAN). O objetivo é eliminar a necessidade de baixar relatórios manualmente: os dados são consultados diretamente via API pública do Ministério da Saúde e apresentados em um dashboard interativo com filtros e visualizações.

### Funcionalidades

- Consulta à API do SISVAN com parâmetros configuráveis (UF, município, fase de vida, período, etc.)
- Filtros interativos para exploração dos dados retornados
- Visualizações gráficas de estados nutricionais (IMC, peso por fase de vida, distribuição por sexo, raça/cor, entre outros)
- Cache dos dados em sessão para evitar requisições repetidas durante a navegação

---

## Tecnologias utilizadas

- [Python 3.11+](https://www.python.org/)
- [Streamlit](https://streamlit.io/) — framework de dashboard
- [Pandas](https://pandas.pydata.org/) — manipulação e filtragem de dados
- [Plotly](https://plotly.com/python/) — gráficos interativos
- [Requests](https://docs.python-requests.org/) — chamadas à API do SISVAN

---

## Pré-requisitos

Antes de começar, você precisa ter instalado na sua máquina:

- [Python 3.11 ou superior](https://www.python.org/downloads/)
- [Git](https://git-scm.com/)

---

## Instalação e execução local

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/sisvan-dashboard.git
cd sisvan-dashboard
```

### 2. Crie e ative um ambiente virtual

```bash
# Criar o ambiente virtual
python -m venv venv

# Ativar no Windows
venv\Scripts\activate

# Ativar no Linux/macOS
source venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Execute o dashboard

```bash
streamlit run app.py
```

O Streamlit abrirá automaticamente no navegador em `http://localhost:8501`.

---

## Estrutura do projeto

```
sisvan-dashboard/
│
├── app.py                  # Ponto de entrada do Streamlit
├── requirements.txt        # Dependências do projeto
├── README.md
│
├── api/
│   └── sisvan.py           # Funções para consumir a API do SISVAN
│
├── components/
│   ├── filters.py          # Componentes de filtro da sidebar
│   └── charts.py           # Funções de geração de gráficos
│
└── utils/
    └── data.py             # Transformações e limpeza dos dados com pandas
```

---

## Deploy na nuvem

O dashboard pode ser publicado gratuitamente no **Streamlit Community Cloud**, tornando-o acessível via navegador sem necessidade de instalação.

### Passo a passo

1. Suba o projeto no GitHub (repositório público ou privado)
2. Acesse [share.streamlit.io](https://share.streamlit.io) e faça login com sua conta do GitHub
3. Clique em **"New app"**
4. Selecione o repositório `sisvan-dashboard` e o arquivo principal `app.py`
5. Clique em **"Deploy"**

Após o deploy, você receberá um link público que pode ser compartilhado com qualquer pessoa — sem instalação, direto no navegador.

> Toda vez que você fizer um `git push` na branch principal, o Streamlit Community Cloud atualiza o dashboard automaticamente.

---

## Como usar o dashboard

1. **Selecione os filtros principais** na barra lateral (UF, município, fase de vida, período)
2. Clique em **"Buscar dados"** — o sistema consultará a API do SISVAN com os parâmetros escolhidos
3. Use os **filtros secundários** (sexo, raça/cor, faixa de IMC) para refinar a visualização sem fazer uma nova requisição
4. Explore os gráficos e a tabela de dados gerados automaticamente

---

## Licença

Este projeto é de uso interno. Dados fornecidos pela API pública do [SISVAN / Ministério da Saúde](https://sisaps.saude.gov.br/sisvan/).