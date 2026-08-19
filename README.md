# Sistema de Marmitas

Sistema desktop para gerenciamento de clientes e geração diária de listas de marmitas.

O projeto permite cadastrar clientes, definir os dias fixos de atendimento, controlar pausas, registrar alergias e restrições, adicionar ou remover clientes de dias específicos e gerar uma lista em PDF para utilização no dia.

## Funcionalidades

* Cadastro de clientes
* Definição da quantidade de pessoas por cliente
* Cadastro de endereço
* Definição dos dias fixos de atendimento
* Cadastro de gostos e preferências
* Cadastro de alergias e restrições
* Ativação e desativação de clientes
* Definição de períodos de pausa
* Visualização da lista de clientes de uma data específica
* Remoção de um cliente de um dia específico
* Adição de clientes extras em uma data
* Restauração da regra fixa de um cliente
* Edição dos dados cadastrados
* Geração de PDF da lista diária
* Banco de dados SQLite local
* Migração automática da estrutura do banco para versões antigas

## Tecnologias

* Python
* Flet
* SQLite
* FPDF / fpdf2

Principais módulos utilizados:

```python
import sqlite3
import datetime
import os
from contextlib import contextmanager
from fpdf import FPDF
import flet as ft
```

## Estrutura do projeto

Uma estrutura recomendada para o repositório:

```text
marmitas/
├── main.py
├── marmita.db
├── pdfs/
│   └── lista_YYYY-MM-DD.pdf
├── README.md
├── DOCUMENTACAO.md
└── requirements.txt
```

> O banco de dados e os PDFs são gerados/utilizados localmente pela aplicação.

## Instalação

### 1. Clone o repositório

```bash
git clone <URL_DO_REPOSITORIO>
cd marmitas
```

### 2. Crie um ambiente virtual

Linux/macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

Windows:

```powershell
python -m venv venv
venv\Scripts\activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

Caso o arquivo ainda não exista, as dependências utilizadas diretamente pelo projeto são:

```text
flet
fpdf2
```

O SQLite já faz parte da biblioteca padrão do Python.

### 4. Execute

```bash
python main.py
```

Na primeira execução, o sistema cria automaticamente o banco `marmita.db`.

## Uso

### Cadastro de cliente

No painel principal, utilize **Novo Cliente**.

São cadastrados:

* Nome
* Quantidade de pessoas
* Endereço
* Dias fixos
* Gostos
* Alergias/restrições

Os dias devem ser informados utilizando o formato:

```text
Seg,Ter,Qua
```

O sistema converte esses dias para índices numéricos internamente.

### Lista diária

A aplicação inicia utilizando a data atual.

É possível selecionar outra data através do botão **Selecionar Data**.

A lista considera:

1. Se o cliente está ativo.
2. Se a data está dentro de um período de pausa.
3. Se o dia da semana corresponde aos dias fixos do cliente.
4. Se existe uma exceção específica para aquela data.

### Exceções

Um cliente pode ser removido de uma data específica sem alterar sua regra fixa.

Também é possível adicionar um cliente extra para uma determinada data.

Isso permite, por exemplo:

```text
Cliente:
Seg, Qua, Sex

Exceção:
2026-08-18 → remover
```

A regra fixa continua sendo:

```text
Seg, Qua, Sex
```

mas o cliente não aparece especificamente em `2026-08-18`.

Da mesma forma, um cliente pode ser adicionado excepcionalmente em uma data na qual normalmente não receberia marmita.

### Gerenciamento

A opção **Ver Todos Clientes** mostra os clientes cadastrados e permite editar seus dados.

É possível alterar:

* Nome
* Quantidade de pessoas
* Endereço
* Dias
* Gostos
* Alergias/restrições
* Status ativo/inativo
* Início da pausa
* Fim da pausa

### Geração de PDF

O botão **Gerar PDF** cria um arquivo contendo a lista do dia.

Os PDFs são armazenados em:

```text
pdfs/
```

Com o padrão:

```text
lista_YYYY-MM-DD.pdf
```

O documento contém:

| Campo               | Descrição                           |
| ------------------- | ----------------------------------- |
| Nome                | Nome do cliente                     |
| Pessoas             | Quantidade de pessoas               |
| Endereço            | Endereço cadastrado                 |
| Alergias/Restrições | Informações alimentares cadastradas |

O PDF utiliza formato A4 e cria novas páginas automaticamente quando necessário.

## Banco de dados

O sistema utiliza SQLite através do arquivo:

```text
marmita.db
```

### Tabela `clientes`

| Campo          | Tipo    | Descrição                      |
| -------------- | ------- | ------------------------------ |
| `id`           | INTEGER | Identificador único            |
| `nome`         | TEXT    | Nome do cliente                |
| `qtd_pessoas`  | INTEGER | Quantidade de pessoas          |
| `endereco`     | TEXT    | Endereço                       |
| `dias_fixos`   | TEXT    | Dias fixos em formato numérico |
| `ativo`        | INTEGER | Status do cliente              |
| `pausa_inicio` | TEXT    | Início da pausa                |
| `pausa_fim`    | TEXT    | Fim da pausa                   |
| `gostos`       | TEXT    | Gostos/preferências            |
| `alergias`     | TEXT    | Alergias/restrições            |

### Tabela `excecoes`

| Campo          | Tipo    | Descrição           |
| -------------- | ------- | ------------------- |
| `id`           | INTEGER | Identificador único |
| `id_cliente`   | INTEGER | Cliente relacionado |
| `data_excecao` | TEXT    | Data da exceção     |
| `acao`         | INTEGER | Ação da exceção     |

A combinação:

```text
id_cliente + data_excecao
```

é única.

Isso permite manter apenas uma regra específica por cliente e data.

## Tratamento de dados

As operações com o banco utilizam um context manager para abrir, confirmar ou desfazer transações e fechar a conexão automaticamente.

O sistema também valida:

* Nome obrigatório
* Quantidade mínima de uma pessoa
* Formato das datas
* Existência de dados válidos antes de operações no banco

## Migração do banco

O sistema possui uma rotina de migração para bancos criados em versões anteriores.

A função `_migrar_unique_excecoes()` verifica se a tabela `excecoes` possui a restrição `UNIQUE(id_cliente, data_excecao)` e, caso necessário, cria uma nova tabela, preserva a exceção mais recente e substitui a tabela antiga.

Isso permite atualizar a estrutura do banco sem exigir que o usuário recrie manualmente todos os dados.

## Licença

Defina aqui a licença escolhida para o projeto.

Exemplo:

```text
MIT License
```

## Status

Projeto em desenvolvimento.

---

Desenvolvido em Python.
