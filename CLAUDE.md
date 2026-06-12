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

Estrutura planejada (ver README para detalhes). Conforme os arquivos forem criados,
manter esta seção atualizada.

```
app.py            # ponto de entrada do Streamlit
api/sisvan.py     # consumo da API do SISVAN
components/        # filters.py (sidebar), charts.py (gráficos)
utils/data.py     # transformação e limpeza com pandas
```

## Convenções de código

<!-- TODO: preencher junto -->
- Idioma da UI (textos visíveis ao usuário): ___
- Idioma de código (nomes de variáveis, funções, comentários): ___
- Estilo / formatação: ___

## Notas de domínio

<!-- TODO: preencher junto -->
- API do SISVAN: ___
- Cache de dados em sessão: ___
