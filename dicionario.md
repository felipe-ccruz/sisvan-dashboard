# 📖 Dicionário de Dados — SISVAN
**Microdados dos acompanhamentos de Estado Nutricional**

Este documento descreve as variáveis exportadas pelo Sistema de Vigilância Alimentar e Nutricional (SISVAN).

---

## Tipos de Campo

| Tipo | Descrição |
|---|---|
| **Campo Obrigatório** | Ausência impossibilita a inclusão do registro no sistema |
| **Campo Opcional** | Preenchido apenas quando necessário |
| **Campo Interno** | Preenchido automaticamente pelo sistema |

---

## Variáveis

### Identificação

| Nome do Campo | Tipo | Variável | Características | Descrição |
|---|---|---|---|---|
| Código do Acompanhamento | NUMBER | `CO_ACOMPANHAMENTO` | Campo Interno | Código único que identifica o acompanhamento realizado pelo indivíduo |
| Código do Indivíduo | NUMBER | `CO_PESSOA_SISVAN` | Campo Interno | Código único que identifica o indivíduo |
| Código do Município | VARCHAR2(6) | `CO_MUNICIPIO_IBGE` | Campo Obrigatório | Código IBGE do município onde foi realizado o acompanhamento |
| Código do CNES | VARCHAR2(7) | `CO_CNES` | Campo Obrigatório | Código CNES do estabelecimento de saúde onde foi realizado o acompanhamento |

---

### Participação em Programas

| Nome do Campo | Tipo | Variável | Características | Descrição |
|---|---|---|---|---|
| Status Participa ANDI | VARCHAR2(1) | `ST_PARTICIPA_ANDI` | Campo Interno | Indica se o município participa do programa Atenção Nutricional à Desnutrição Infantil. `S` = Sim, `N` = Não |

---

### Dados Demográficos

| Nome do Campo | Tipo | Variável | Características | Descrição |
|---|---|---|---|---|
| Idade em Anos | NUMBER | `NU_IDADE_ANO` | Campo Interno | Anos de vida do indivíduo no momento do acompanhamento. Calculado a partir da Data de Nascimento |
| Código da Fase da Vida | NUMBER | `NU_FASE_VIDA` | Campo Interno | Fase da vida calculada em dias de vida. Ver tabela de fases abaixo |
| Fase da Vida | VARCHAR2(22) | `DS_FASE_VIDA` | Campo Interno | Descrição textual da fase da vida |
| Sexo | VARCHAR2(2) | `SG_SEXO` | Campo Obrigatório | `M` = Masculino, `F` = Feminino |
| Código da Raça/Cor | VARCHAR2(2) | `CO_RACA_COR` | Campo Obrigatório | Código da raça/cor declarada. Ver tabela abaixo |
| Raça/Cor | VARCHAR2(25) | `DS_RACA_COR` | Campo Interno | Descrição da raça/cor |
| Código do Povo ou Comunidade Tradicional | NUMBER | `CO_POVO_COMUNIDADE` | Campo Opcional | Código do povo e/ou comunidade tradicional. Ver tabela abaixo |
| Descrição do Povo ou Comunidade Tradicional | VARCHAR2(300) | `DS_POVO_COMUNIDADE` | Campo Opcional | Descrição do povo ou comunidade |
| Código da Escolaridade | NUMBER | `CO_ESCOLARIDADE` | Campo Opcional | Código do nível de escolaridade. Ver tabela abaixo |
| Descrição da Escolaridade | VARCHAR2(150) | `DS_ESCOLARIDADE` | Campo Opcional | Descrição do nível de escolaridade |

---

### Acompanhamento Nutricional

| Nome do Campo | Tipo | Variável | Características | Descrição |
|---|---|---|---|---|
| Data do Acompanhamento | DATE | `DT_ACOMPANHAMENTO` | Campo Obrigatório | Data do acompanhamento nutricional do indivíduo |
| Competência do Acompanhamento | — | `NU_COMPETENCIA` | Campo Interno | Competência no formato `YYYYMM`. Gerado automaticamente a partir da data do acompanhamento |
| Peso | VARCHAR2(7) | `NU_PESO` | Campo Obrigatório | Peso do indivíduo em quilos |
| Altura | VARCHAR2(7) | `NU_ALTURA` | Campo Obrigatório | Altura do indivíduo em centímetros |
| IMC | VARCHAR2(7) | `DS_IMC` | Campo Interno | Calculado automaticamente a partir do peso e altura |
| IMC Pré-Gestacional | VARCHAR2(7) | `DS_IMC_PRE_GESTACIONAL` | Campo Interno | Calculado automaticamente a partir do peso e altura da gestante |

---

### Estado Nutricional

| Nome do Campo | Tipo | Variável | Características | Descrição |
|---|---|---|---|---|
| Peso x Idade (crianças 0–10 anos) | NUMBER(2,0) | `PESO X IDADE` | Campo Interno | Muito baixo peso / Baixo peso / Peso adequado / Peso elevado |
| Peso x Altura (crianças 0–10 anos) | NUMBER(2,0) | `PESO X ALTURA` | Campo Interno | Magreza acentuada / Magreza / Eutrófico / Risco de sobrepeso / Sobrepeso / Obesidade |
| Altura x Idade — Crianças (0–10 anos) | NUMBER(2,0) | `CRI. ALTURA X IDADE` | Campo Interno | Muito baixa estatura / Baixa estatura / Estatura adequada |
| IMC x Idade — Crianças (0–10 anos) | NUMBER(2,0) | `CRI. IMC X IDADE` | Campo Interno | Magreza acentuada / Magreza / Eutrofia / Risco de sobrepeso / Sobrepeso / Obesidade |
| Altura x Idade — Adolescentes (10–20 anos) | NUMBER(2,0) | `ADO. ALTURA X IDADE` | Campo Interno | Muito baixa estatura / Baixa estatura / Estatura adequada |
| IMC x Idade — Adolescentes (10–20 anos) | NUMBER(2,0) | `ADO. IMC X IDADE` | Campo Interno | Magreza acentuada / Magreza / Eutrofia / Risco de sobrepeso / Sobrepeso / Obesidade |
| Estado Nutricional de Adultos (20–60 anos) | NUMBER(2,0) | `CO_ESTADO_NUTRI_ADULTO` | Campo Interno | Baixo peso / Eutrófico / Sobrepeso / Obesidade Grau I / Obesidade Grau II / Obesidade Grau III |
| Estado Nutricional de Idosos (60+ anos) | NUMBER(2,0) | `CO_ESTADO_NUTRI_IDOSO` | Campo Interno | Baixo peso / Eutrófico / Sobrepeso |
| Estado Nutricional de Gestantes | NUMBER(2,0) | `CO_ESTADO_NUTRI_IMC_SEMGEST` | Campo Interno | Baixo peso / Eutrófico / Sobrepeso / Obesidade. **Disponível apenas até 2021** |

---

### Sistema de Origem

| Nome do Campo | Tipo | Variável | Características | Descrição |
|---|---|---|---|---|
| Código do Sistema de Origem | NUMBER(2,0) | `CO_SISTEMA_ORIGEM_ACOMP` | Campo Interno | Identificador do sistema de origem. Ver tabela abaixo |
| Sistema de Origem | VARCHAR2(14) | `DS_SISTEMA_ORIGEM_ACOMP` | Campo Interno | Descrição do sistema de origem |

---

## Tabelas de Referência

### Fases da Vida (`NU_FASE_VIDA`)

| Código | Descrição |
|---|---|
| 1 | Menor de 6 meses |
| 2 | Entre 6 meses e 2 anos |
| 3 | Entre 2 anos e 5 anos |
| 4 | Entre 5 anos e 7 anos |
| 5 | Entre 7 anos e 10 anos |
| 6 | Adolescente |
| 7 | Adulto |
| 8 | Idoso |

---

### Raça/Cor (`CO_RACA_COR`)

| Código | Descrição |
|---|---|
| X | Inválido |
| 01 | Branca |
| 02 | Preta |
| 03 | Amarela |
| 04 | Parda |
| 05 | Indígena |
| 99 | Sem informação |

---

### Povo ou Comunidade Tradicional (`CO_POVO_COMUNIDADE`)

| Código | Descrição |
|---|---|
| 1 | Povos Quilombolas |
| 2 | Agroextrativistas |
| 3 | Caatingueiros |
| 4 | Caiçaras |
| 5 | Comunidades de Fundo e Fecho de Pasto |
| 6 | Comunidades do Cerrado |
| 7 | Extrativistas |
| 8 | Faxinalenses |
| 9 | Geraizeiros |
| 10 | Marisqueiros |
| 11 | Pantaneiros |
| 12 | Pescadores Artesanais |
| 13 | Pomeranos |
| 14 | Povos Ciganos |
| 15 | Povos de Terreiro |
| 16 | Quebradeiras de Coco-de-Babaçu |
| 17 | Retireiros |
| 18 | Ribeirinhos |
| 19 | Seringueiros |
| 20 | Vazanteiros |
| 21 | Outros |

---

### Escolaridade (`CO_ESCOLARIDADE`)

| Código | Descrição |
|---|---|
| 1 | Creche |
| 2 | Pré-escola (exceto CA) |
| 3 | Classe Alfabetizada - CA |
| 4 | Ensino Fundamental 1ª a 4ª séries |
| 5 | Ensino Fundamental 5ª a 8ª séries |
| 6 | Ensino Fundamental Completo |
| 7 | Ensino Fundamental Especial |
| 8 | Ensino Fundamental EJA — séries iniciais (Supletivo 1ª a 4ª) |
| 9 | Ensino Fundamental EJA — séries finais (Supletivo 5ª a 8ª) |
| 10 | Ensino Médio, Médio 2º Ciclo (Científico, Técnico, etc.) |
| 11 | Ensino Médio Especial |
| 12 | Ensino Médio EJA (Supletivo) |
| 13 | Superior, Aperfeiçoamento, Especialização, Mestrado, Doutorado |
| 14 | Alfabetização para Adultos (Mobral, etc.) |
| 15 | Nenhum |
| 99 | Sem informação |

---

### Sistema de Origem (`CO_SISTEMA_ORIGEM_ACOMP`)

| Código | Descrição |
|---|---|
| 1 | SISVAN Web |
| 2 | Auxílio Brasil |
| 4 | e-SUS AB |

---

> Documento baseado no **Dicionário de Dados — SISVAN** publicado pelo Ministério da Saúde.