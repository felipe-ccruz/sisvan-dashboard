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
  geo_pa_municipios.json  # malha municipal do PA (IBGE); id = código de 6 dígitos
api/
  sisvan.py            # cliente da API do SISVAN (paginação paralela + retry); Python puro
utils/
  data.py              # transformação/limpeza com pandas; puro (sem Streamlit)
  dimensoes.py         # leitura da dim_regiao e das malhas; puro (sem Streamlit)
components/
  painel.py            # corpo da página (busca, KPIs, gráficos, tabela) + cache
  filters.py           # filtros da sidebar (de API vs. de cliente)
  charts.py            # construtores de gráficos Plotly
  mapas.py             # mapas (malha + dimensão) e a seção do mapa na página
```

Camadas: `api/` e `utils/` não importam Streamlit (testáveis isoladamente). O cache
dos recortes fica em `components/painel.py`, envolvendo a chamada à API +
transformação. Ele é manual (dicionário global via `st.cache_resource`, validade de
1 h) e **não** `st.cache_data`: a carga desenha uma barra de progresso, e o
`st.cache_data` regrava elementos desenhados dentro da função e quebra
(`CacheReplayClosureError`) ao reaproveitar o cache. O progresso chega ao painel por
um callback (`ao_progredir`) do cliente da API, que continua sem Streamlit. A lista de municípios, que é estática, tem cache próprio em
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
- **Gráficos**: as cores vêm de uma paleta contínua do Plotly escolhida no topo da
  página (`PALETAS` em `components/charts.py`: Sunset — padrão —, Magma, Turbo,
  Mint, Viridis, Aggrnyl). Toda função de gráfico recebe `paleta: str =
  PALETA_PADRAO`; as pontas de cada escala são cortadas para ficarem visíveis nos
  temas claro e escuro. A cor fica presa à entidade (fase da vida, raça/cor, grupo
  nutricional), nunca à posição da barra. **Exceção: sexo** é sempre azul e rosa
  (`CORES_SEXO`), fora da paleta. Nos comparativos, a UF em foco
  (`UF_DESTAQUE_PADRAO = "PA"`) e as demais ficam nas duas pontas da paleta — é
  destaque, não categoria.
- **Mapas** (`components/mapas.py`): projeção `geo` do Plotly (só o estado na tela,
  sem mapa-base), **uma camada por mapa** (cada camada embute a malha inteira, ~700
  KB, reenviada a cada rerun) e contagens em faixas, não em escala contínua (Belém e
  Santarém apagariam o resto). O mapa de registros mostra onde a amostra baixada
  caiu — não é cobertura do SISVAN nem indicador; o texto da seção diz isso.

## Notas de domínio

- **API do SISVAN** (`estado-nutricional`): retorna **microdados** (1 registro por
  acompanhamento), embrulhados na chave `estados_nutricionais`. **Limite rígido de 20
  itens/página** → paginação obrigatória. Apesar de a documentação oficial dizer que
  `offset` é o número da página, na prática ele conta **registros** (`offset=1`
  começa no 2º item) → avançar `offset += len(pagina)`.
- **Um valor por requisição**: `codigo_municipio` e `ano_mes_competencia` só
  aceitam um valor. O cliente aceita listas nos dois e faz uma consulta por
  combinação (município x competência, `_desdobrar_filtros`), dividindo o teto em
  cotas iguais (um teto único consumido em sequência deixaria os últimos de fora —
  ex.: só janeiro de um ano). Na sidebar os valores saem em tuplas ordenadas:
  precisam ser hasheáveis para a chave do cache de recortes, e ordenadas para a
  mesma seleção cair na mesma entrada.
- **Sem ordenação; ano via competência**: a API ignora parâmetros de ordenação, não
  informa o total e devolve em ordem de inserção (≈ cronológica, do mais antigo):
  sem competência, os primeiros milhares de registros são de 2008. Para um ano, a
  sidebar tem "Ano (competência)" + "Meses" (vazio = 12), que viram uma competência
  `AAAAMM` por mês. A base da API vai de **2008 a 2021**; pedir um mês **sem dados**
  para uma UF inteira estoura o timeout (502 após 60 s) — por isso só esses anos são
  oferecidos (`ANOS_COMPETENCIA`). A latência por página cresce com o ano (Pará:
  ~1 s em 2010, ~12–17 s em 2019–2021). O slider de **período** (anos) continua como
  filtro de cliente, com a faixa que veio na busca (`renderizar_filtro_anos`). A
  faixa de idade saiu: a fase da vida já cobre esse recorte.
- **Dimensões já vêm traduzidas** pela API (município, fase da vida, raça/cor,
  escolaridade, estado nutricional…). Não é preciso replicar tabelas de código→rótulo.
  A parte geográfica (lat/lon, regiões de saúde) vem da `dimensoes/dim_regiao.parquet`,
  que só cobre o Pará; o join é `codigo_municipio` (API) = `mun_cod` (dimensão), ambos
  com 6 dígitos. As linhas com `mun_cod` negativo são sentinelas ("Em branco" etc.).
- **Orientação dos polígonos**: o GeoJSON do IBGE segue a RFC 7946 (contorno externo
  anti-horário), mas os mapas `geo` do Plotly (d3) esperam o horário — sem
  corrigir, cada município vira "o globo menos o município" e o mapa é uma mancha
  de cor com o hover funcionando. `carregar_malha_municipal` reorienta ao carregar
  (`orientar_para_plotly`); o arquivo fica como veio do IBGE.
- **Codificação inconsistente**: texto vem ora sem acento (`SEM INFORMACAO`), ora com
  bytes perdidos (`SEM INFORMA�O`). Corrigido em `utils/data.py` por comparação de
  "esqueleto" (só letras A-Z).
- **Estabilidade**: consultas filtradas retornam `502 Proxy Error` de forma intermitente
  → o cliente tem retry com backoff. Recortes específicos respondem melhor. As páginas
  são pedidas com até 5 requisições simultâneas (`REQUISICOES_PARALELAS`); mais que
  isso tende a piorar os erros sem ganho real.
- **Carga e progresso**: a API não informa o total do recorte, então o 100% da barra
  é o teto escolhido (`max_registros / 20` páginas). Só uma página **vazia** marca o
  fim do recorte (o total encolhe): a API às vezes devolve menos de 20 itens no meio
  dos dados (~0,5% dos registros somem, de forma intermitente), então página
  incompleta não é sinal de fim. Pelo mesmo motivo, o aviso "o recorte acabou antes
  do teto" vem do total de páginas ter encolhido, não da contagem de registros.
- **Filtros em formulário**: os filtros de API ficam num `st.form` na sidebar — só o
  botão dispara a busca, para o usuário fechar o recorte antes de uma carga longa (e
  para um clique no meio dela não interrompê-la). Sexo, raça/cor e período ficam
  fora do form.
- **Cache de recortes**: guarda o resultado por recorte + volume; filtros de cliente
  (sexo, raça/cor, período) refinam sem nova requisição. Como a UF entra nos filtros, Pará e
  nacional têm entradas separadas.
- **Recorte do Pará**: a SESPA é do Pará, então a página `paginas/para.py` prende a UF
  em `PA` e a nacional serve de comparação. Os municípios são escolhidos pelo nome,
  um ou mais (lista da `dim_regiao`, vazio = "Todos"); na página nacional o
  seletor fica travado, já que a dimensão só tem municípios do Pará.
