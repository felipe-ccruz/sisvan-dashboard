# CLAUDE.md

Guia para o Claude Code trabalhar neste repositório. Leia antes de começar qualquer tarefa.

## Sobre o projeto

**sisvan-dashboard** — dashboard interativo em Streamlit que consome a API pública do
SISVAN (Ministério da Saúde) e apresenta análises nutricionais com filtros dinâmicos e
gráficos. Foco em evitar download manual de relatórios: os dados vêm direto da API.

Detalhes de uso, instalação e deploy estão no [README.md](README.md). O dicionário de
campos da API está em [dicionario.md](dicionario.md).

## Convenções de commit

Seguir **[Conventional Commits](https://www.conventionalcommits.org/)**.

Formato: `<tipo>: <descrição no imperativo, em inglês>`

Tipos usados:

| Tipo       | Quando usar                                                       |
|------------|------------------------------------------------------------------|
| `feat`     | Nova funcionalidade                                              |
| `fix`      | Correção de bug                                                  |
| `docs`     | Apenas documentação (README, comentários, este arquivo)         |
| `refactor` | Mudança de código que não altera comportamento                  |
| `style`    | Formatação, sem efeito de lógica (espaços, lint)                |
| `chore`    | Build, dependências, configs (requirements.txt, .gitignore)     |
| `test`     | Adição ou ajuste de testes                                      |

### Regras

1. **Sempre em inglês.** Mensagem de commit no imperativo: `add filters sidebar`, não
   `added` nem `adding`.
2. **Sem marca d'água / assinatura.** Não incluir linhas `Co-Authored-By`, "Generated
   with Claude Code" ou qualquer rodapé automático nos commits.
3. **Uma task = um commit.** Dividir o trabalho em commits pequenos e coesos. Se a tarefa
   tocou em coisas distintas (ex: criar o cliente da API + ajustar o README), fazer
   commits separados — um `feat:` e um `docs:` — em vez de um commit único.

### Exemplos

```
feat: add SISVAN API client with configurable params
fix: handle empty response from API
docs: update project structure in README
refactor: extract chart builders into components/charts.py
chore: add requirements.txt
```

## Stack

- Python 3.11+
- Streamlit (dashboard) · Pandas (dados) · Plotly (gráficos) · Requests (API)

## Comandos

<!-- TODO: confirmar conforme o código for criado -->
```bash
python -m venv venv && venv\Scripts\activate   # Windows
pip install -r requirements.txt
streamlit run app.py
```

## Estrutura do projeto

```
app.py                 # ponto de entrada: st.set_page_config + st.navigation
paginas/
  para.py              # página do Pará (uf_fixa="PA")
  nacional.py          # página nacional (UF livre + comparação entre estados)
dimensoes/
  dim_regiao.parquet   # municípios do PA: código IBGE (6 dígitos), nome, lat/lon, regiões de saúde
api/
  sisvan.py            # cliente da API do SISVAN (paginação + retry); Python puro
utils/
  data.py              # transformação/limpeza com pandas; puro (sem Streamlit)
  dimensoes.py         # leitura da dim_regiao; puro (sem Streamlit)
components/
  painel.py            # corpo da página (busca, KPIs, gráficos, tabela) + cache
  filters.py           # filtros da sidebar (de API vs. de cliente)
  charts.py            # construtores de gráficos Plotly
```

Camadas: `api/` e `utils/` não importam Streamlit (testáveis isoladamente). O cache
de sessão (`st.cache_data`) fica em `components/painel.py`, envolvendo a chamada à
API + transformação. A lista de municípios, que é estática, tem cache próprio em
`components/filters.py`.

**Páginas.** As duas páginas são só duas chamadas de
`components.painel.renderizar_painel` com parâmetros diferentes — qualquer mudança de
layout deve entrar no painel, não ser duplicada nas páginas. O que as separa:
`uf_fixa` (trava o seletor de UF e entra em toda consulta) e `comparar_ufs` (exibe a
seção comparativa). Cada página usa uma `chave_estado` própria no `st.session_state`,
para que os dados de uma não vazem para a outra. A pasta se chama `paginas/` e não
`pages/` de propósito: com `st.navigation` os rótulos e ícones ficam explícitos no
`app.py`, e o autodescobrimento de `pages/` fica desligado.

## Convenções de código

- **Idioma da UI** (textos visíveis ao usuário): **português (BR)**.
- **Idioma do código** (variáveis, funções, comentários, docstrings): **português (BR)**,
  seguindo o estilo do projeto de referência (`tabviva`). Nomes de campos da API do
  SISVAN são mantidos como vêm (`codigo_municipio`, `fase_vida`, etc.).
- **Estilo**: PEP 8, aspas duplas, type hints quando ajudam a leitura. Comentários em
  blocos com cabeçalho `# ---` separando seções (padrão do `tabviva`).
- **Gráficos**: paleta categórica de ordem fixa em `components/charts.py`; barra de
  série única usa um único tom (a categoria já está no eixo). Nos gráficos
  comparativos, a UF em foco (`UF_DESTAQUE_PADRAO = "PA"`) ganha o verde e as demais
  ficam no azul — é destaque, não categoria.

## Notas de domínio

- **API do SISVAN** (`estado-nutricional`): retorna **microdados** (1 registro por
  acompanhamento), embrulhados na chave `estados_nutricionais`. **Limite rígido de 20
  itens/página** → paginação obrigatória. Apesar de a documentação oficial dizer que
  `offset` é o número da página, na prática ele conta **registros** (`offset=1`
  começa no 2º item) → avançar `offset += len(pagina)`.
- **Sem ordenação nem filtro de ano utilizável**: a API ignora parâmetros de
  ordenação, não informa o total e devolve em ordem de inserção (≈ cronológica, do
  mais antigo). Sem competência, os primeiros milhares de registros são de 2008; e o
  filtro `ano_mes_competencia` costuma estourar o timeout (502 após 60 s).
- **Dimensões já vêm traduzidas** pela API (município, fase da vida, raça/cor,
  escolaridade, estado nutricional…). Não é preciso replicar tabelas de código→rótulo.
  A parte geográfica (lat/lon, regiões de saúde) vem da `dimensoes/dim_regiao.parquet`,
  que só cobre o Pará; o join é `codigo_municipio` (API) = `mun_cod` (dimensão), ambos
  com 6 dígitos. As linhas com `mun_cod` negativo são sentinelas ("Em branco" etc.).
- **Codificação inconsistente**: texto vem ora sem acento (`SEM INFORMACAO`), ora com
  bytes perdidos (`SEM INFORMA�O`). Corrigido em `utils/data.py` por comparação de
  "esqueleto" (só letras A-Z).
- **Estabilidade**: consultas filtradas retornam `502 Proxy Error` de forma intermitente
  → o cliente tem retry com backoff. Recortes específicos respondem melhor.
- **Cache de sessão**: `st.cache_data` em `components/painel.py` guarda o resultado
  por recorte + volume; filtros de cliente (sexo, raça/cor) refinam sem nova
  requisição. Como a UF entra nos filtros, Pará e nacional têm entradas separadas.
- **Recorte do Pará**: a SESPA é do Pará, então a página `paginas/para.py` prende a UF
  em `PA` e a nacional serve de comparação. O município é escolhido pelo nome (lista
  da `dim_regiao`, padrão "Todos"); na página nacional o seletor fica travado, já
  que a dimensão só tem municípios do Pará.
