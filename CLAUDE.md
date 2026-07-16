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
app.py                 # ponto de entrada do Streamlit (header, KPIs, gráficos, tabela)
api/
  sisvan.py            # cliente da API do SISVAN (paginação + retry); Python puro
utils/
  data.py              # transformação/limpeza com pandas; puro (sem Streamlit)
components/
  filters.py           # filtros da sidebar (de API vs. de cliente)
  charts.py            # construtores de gráficos Plotly
```

Camadas: `api/` e `utils/` não importam Streamlit (testáveis isoladamente). O cache
de sessão (`st.cache_data`) fica no `app.py`, envolvendo a chamada à API + transformação.

## Convenções de código

- **Idioma da UI** (textos visíveis ao usuário): **português (BR)**.
- **Idioma do código** (variáveis, funções, comentários, docstrings): **português (BR)**,
  seguindo o estilo do projeto de referência (`tabviva`). Nomes de campos da API do
  SISVAN são mantidos como vêm (`codigo_municipio`, `fase_vida`, etc.).
- **Estilo**: PEP 8, aspas duplas, type hints quando ajudam a leitura. Comentários em
  blocos com cabeçalho `# ---` separando seções (padrão do `tabviva`).
- **Gráficos**: paleta categórica de ordem fixa em `components/charts.py`; barra de
  série única usa um único tom (a categoria já está no eixo).

## Notas de domínio

- **API do SISVAN** (`estado-nutricional`): retorna **microdados** (1 registro por
  acompanhamento), embrulhados na chave `estados_nutricionais`. **Limite rígido de 20
  itens/página** → paginação obrigatória (`offset` = número da página, começa em 0).
- **Dimensões já vêm traduzidas** pela API (município, fase da vida, raça/cor,
  escolaridade, estado nutricional…). Não é preciso replicar tabelas de código→rótulo.
  A única dimensão ausente é geográfica (lat/lon do município) — mapa fica para depois.
- **Codificação inconsistente**: texto vem ora sem acento (`SEM INFORMACAO`), ora com
  bytes perdidos (`SEM INFORMA�O`). Corrigido em `utils/data.py` por comparação de
  "esqueleto" (só letras A-Z).
- **Estabilidade**: consultas filtradas retornam `502 Proxy Error` de forma intermitente
  → o cliente tem retry com backoff. Recortes específicos respondem melhor.
- **Cache de sessão**: `st.cache_data` no `app.py` guarda o resultado por recorte +
  volume; filtros de cliente (sexo, raça/cor) refinam sem nova requisição.
