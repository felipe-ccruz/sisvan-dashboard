# 📊 sisvan-dashboard

Dashboard interativo para análise de dados nutricionais do SISVAN, com filtros dinâmicos e visualizações geradas a partir da API pública do Ministério da Saúde.

---

## 🗂️ Sumário

- [Sobre o projeto](#sobre-o-projeto)
- [Tecnologias utilizadas](#tecnologias-utilizadas)
- [Pré-requisitos](#pré-requisitos)
- [Instalação e execução local](#instalação-e-execução-local)
- [Páginas](#páginas)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Deploy na nuvem](#deploy-na-nuvem)
- [Como usar o dashboard](#como-usar-o-dashboard)

---

## Sobre o projeto

O **sisvan-dashboard** foi desenvolvido para facilitar a análise de dados do Sistema de Vigilância Alimentar e Nutricional (SISVAN). O objetivo é eliminar a necessidade de baixar relatórios manualmente: os dados são consultados diretamente via API pública do Ministério da Saúde e apresentados em um dashboard interativo com filtros e visualizações.

### Funcionalidades

- Foco no **Pará** (recorte fixo da SESPA): toda consulta já sai filtrada pela UF `PA`
- Consulta à API do SISVAN com parâmetros configuráveis (município, ano e meses, fase de vida, etc.)
- Filtros interativos para exploração dos dados retornados
- Visualizações gráficas de estados nutricionais (IMC, peso por fase de vida, distribuição por sexo, raça/cor, entre outros)
- Cache dos dados em sessão para evitar requisições repetidas durante a navegação
- Mapa do Pará com quantos registros da busca caíram em cada município (página do Pará)

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

## Recorte do Pará

O dashboard tem uma página só, a do **Pará** (uso da SESPA). A UF não aparece na barra lateral: toda consulta já sai filtrada por `PA`, e os demais filtros (município, ano, fase da vida, escolaridade) recortam dentro do estado. Os municípios são escolhidos pelo nome, um ou mais (padrão: todos). Há ainda o mapa **Registros por município**, que mostra onde a amostra baixada se concentra (e quais municípios ficaram sem nenhum registro).

A página nacional, com a comparação entre estados, foi retirada: com a amostra que a API permite baixar, as comparações entre UFs não se sustentam.

---

## Estrutura do projeto

```
sisvan-dashboard/
│
├── app.py                  # Ponto de entrada: configura a página e a navegação
├── requirements.txt        # Dependências do projeto
├── README.md
│
├── paginas/
│   └── para.py             # Página do Pará (UF presa em PA)
│
├── dimensoes/
│   ├── dim_regiao.parquet  # Municípios do Pará (código IBGE, nome, regionalização)
│   └── geo_pa_municipios.json  # Malha municipal do Pará (IBGE)
│
├── api/
│   └── sisvan.py           # Funções para consumir a API do SISVAN
│
├── components/
│   ├── painel.py           # Corpo da página (busca, KPIs, gráficos, tabela)
│   ├── filters.py          # Componentes de filtro da sidebar
│   ├── charts.py           # Funções de geração de gráficos
│   └── mapas.py            # Mapas (malha municipal + dados)
│
└── utils/
    ├── data.py             # Transformações e limpeza dos dados com pandas
    └── dimensoes.py        # Leitura das dimensões e da malha municipal
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

1. **Selecione os filtros principais** na barra lateral (município, ano e meses da competência, fase de vida, escolaridade, gestante). A UF já é `PA`; dá para escolher um ou mais municípios pelo nome (padrão: todos — com vários, o teto de registros é dividido igualmente entre eles). Escolhendo um **ano** (2008–2021, o que a API tem), cada mês é consultado à parte e o teto é dividido entre os meses
2. Clique em **"Buscar dados"** — o sistema consultará a API do SISVAN com os parâmetros escolhidos
3. Use os **filtros secundários** (sexo, raça/cor e o slider de **período**, de 2008 a 2021) para refinar a visualização sem fazer uma nova requisição. O período filtra só o que veio na busca: anos que não foram baixados deixam os gráficos vazios — para consultar um ano específico, use o filtro de ano no passo 1
4. Explore os gráficos e a tabela de dados gerados automaticamente

---

## Licença

Este projeto é de uso interno. Dados fornecidos pela API pública do [SISVAN / Ministério da Saúde](https://sisaps.saude.gov.br/sisvan/).