# Sistema de Marmitas

Sistema de gerenciamento de clientes e controle diário de marmitas desenvolvido em **Python**.

A aplicação possui uma interface gráfica para cadastrar e gerenciar clientes, definir dias fixos de atendimento, controlar exceções e pausas e gerar listas diárias em PDF.

## Funcionalidades

* Cadastro de clientes
* Quantidade de pessoas por cliente
* Cadastro de endereço
* Definição dos dias fixos de atendimento
* Cadastro de gostos e preferências
* Cadastro de alergias e restrições
* Ativação e desativação de clientes
* Controle de períodos de pausa
* Seleção de uma data específica
* Visualização da lista de clientes do dia
* Remoção de clientes em uma data específica
* Adição de clientes extras em uma data
* Restauração da regra fixa do cliente
* Edição de clientes cadastrados
* Geração de listas em PDF

## Tecnologias

* **Python**
* **Flet** — interface gráfica
* **SQLite** — armazenamento local dos dados
* **FPDF2** — geração dos arquivos PDF

## Estrutura

Atualmente, o projeto possui um único arquivo principal:

```text
marmitav2.py
```

O banco de dados e os arquivos PDF são gerados automaticamente durante a utilização da aplicação.

## Instalação

### 1. Clone o repositório

```bash
git clone <URL_DO_REPOSITORIO>
cd <NOME_DO_REPOSITORIO>
```

### 2. Instale as dependências

```bash
pip install -r requirements.txt
```

### 3. Execute o programa

```bash
python marmitav2.py
```

## Cadastro de clientes

Cada cliente pode possuir:

* Nome
* Quantidade de pessoas
* Endereço
* Dias fixos
* Gostos
* Alergias e restrições

Os dias da semana podem ser informados no formato:

```text
Seg,Ter,Qua
```

## Controle de dias

O sistema utiliza os dias fixos cadastrados para determinar automaticamente quais clientes devem aparecer na lista de determinada data.

Também é possível criar exceções individuais.

### Remover cliente de um dia

Um cliente pode ser removido de uma data específica sem alterar seus dias fixos.

### Adicionar cliente extra

Também é possível adicionar um cliente à lista de uma determinada data mesmo que aquele dia não esteja entre seus dias fixos.

### Restaurar regra

A exceção pode ser removida para que o cliente volte a seguir normalmente sua regra fixa.

## Período de pausa

Clientes podem possuir uma data inicial e uma data final de pausa.

Durante esse período, o cliente não aparece na lista diária.

## Geração de PDF

A aplicação permite gerar um PDF contendo a lista de clientes da data selecionada.

O documento apresenta informações como:

* Nome
* Quantidade de pessoas
* Endereço
* Alergias e restrições

Os arquivos são gerados automaticamente pela aplicação.

## Banco de dados

O sistema utiliza **SQLite** para armazenar os dados localmente.

O banco é criado automaticamente na inicialização do programa, não sendo necessário configurar um servidor ou banco de dados externo.

## Requisitos

* Python 3
* Flet
* FPDF2

As dependências podem ser instaladas através do:

```bash
pip install -r requirements.txt
```

## Status

Projeto em desenvolvimento.

## Licença

Este projeto ainda não possui uma licença definida.
