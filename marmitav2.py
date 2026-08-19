import sqlite3
import datetime
import os
from contextlib import contextmanager
from fpdf import FPDF
import flet as ft

DB_NAME = "marmita.db"

_PDF_MARGEM_INFERIOR_MM = 20
_PDF_ALTURA_LINHA_MM = 8
_PDF_COLUNAS = [
    ("Nome", 50),
    ("Pessoas", 25),
    ("Endereco", 55),
    ("Alergias/Restricoes", 60),
]


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _migrar_unique_excecoes(conn):
    # Bancos criados antes desta versao nao tinham UNIQUE(id_cliente, data_excecao)
    # em `excecoes`, entao INSERT OR REPLACE nunca substituia nada: cada exclusao/
    # inclusao gerava uma linha nova e a mais antiga podia "vencer" na leitura.
    # Isto detecta a ausencia da constraint e migra o banco, mantendo so a
    # exececao mais recente de cada par cliente/data. Seguro rodar toda vez.
    indices = conn.execute("PRAGMA index_list('excecoes')").fetchall()
    tem_unique = any(idx["unique"] == 1 for idx in indices)
    if tem_unique:
        return

    conn.execute("""
        CREATE TABLE IF NOT EXISTS excecoes_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_cliente INTEGER NOT NULL,
            data_excecao TEXT NOT NULL,
            acao INTEGER NOT NULL,
            FOREIGN KEY(id_cliente) REFERENCES clientes(id),
            UNIQUE(id_cliente, data_excecao)
        )
    """)
    conn.execute("""
        INSERT OR IGNORE INTO excecoes_new (id_cliente, data_excecao, acao)
        SELECT id_cliente, data_excecao, acao
        FROM excecoes e1
        WHERE id = (
            SELECT MAX(id) FROM excecoes e2
            WHERE e2.id_cliente = e1.id_cliente
              AND e2.data_excecao = e1.data_excecao
        )
    """)
    conn.execute("DROP TABLE excecoes")
    conn.execute("ALTER TABLE excecoes_new RENAME TO excecoes")


def init_db():
    with get_conn() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                qtd_pessoas INTEGER DEFAULT 1,
                endereco TEXT,
                dias_fixos TEXT,
                ativo INTEGER DEFAULT 1,
                pausa_inicio TEXT,
                pausa_fim TEXT,
                gostos TEXT,
                alergias TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS excecoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_cliente INTEGER NOT NULL,
                data_excecao TEXT NOT NULL,
                acao INTEGER NOT NULL,
                FOREIGN KEY(id_cliente) REFERENCES clientes(id),
                UNIQUE(id_cliente, data_excecao)
            )
        ''')
        _migrar_unique_excecoes(conn)


def validar_data(data_str):
    if not data_str:
        return True
    try:
        datetime.datetime.strptime(data_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _validar_dados_cliente(nome, qtd, pausa_inicio, pausa_fim):
    if not nome or not nome.strip():
        raise ValueError("O nome do cliente e obrigatorio.")
    if qtd is None or qtd < 1:
        raise ValueError("Quantidade de pessoas deve ser pelo menos 1.")
    if not validar_data(pausa_inicio):
        raise ValueError("Data de inicio da pausa invalida (use AAAA-MM-DD).")
    if not validar_data(pausa_fim):
        raise ValueError("Data de fim da pausa invalida (use AAAA-MM-DD).")


def dias_semana_para_indices(dias_str):
    mapa = {"Seg": 0, "Ter": 1, "Qua": 2, "Qui": 3, "Sex": 4, "Sab": 5, "Dom": 6}
    if not dias_str:
        return ""
    partes = [p.strip() for p in dias_str.split(',')]
    indices = [str(mapa[p]) for p in partes if p in mapa]
    return ",".join(indices)


def indice_para_dias_semana(indices_str):
    mapa_reverso = {0: "Seg", 1: "Ter", 2: "Qua", 3: "Qui", 4: "Sex", 5: "Sab", 6: "Dom"}
    if not indices_str:
        return ""
    indices = [int(i) for i in indices_str.split(',') if i.strip().isdigit()]
    return ",".join([mapa_reverso[i] for i in indices])


def obter_lista_do_dia(data_str):
    data_obj = datetime.datetime.strptime(data_str, "%Y-%m-%d")
    dia_semana = data_obj.weekday()

    with get_conn() as conn:
        linhas = conn.execute('''
            SELECT c.id, c.nome, c.qtd_pessoas, c.endereco, c.dias_fixos,
                   c.gostos, c.alergias, e.acao
            FROM clientes c
            LEFT JOIN excecoes e
                ON e.id_cliente = c.id AND e.data_excecao = ?
            WHERE c.ativo = 1
              AND (
                    c.pausa_inicio IS NULL
                    OR c.pausa_fim IS NULL
                    OR ? NOT BETWEEN c.pausa_inicio AND c.pausa_fim
                  )
        ''', (data_str, data_str)).fetchall()

    lista_final = []
    for row in linhas:
        dias_fixos = row["dias_fixos"]
        dias_lista = [int(d.strip()) for d in dias_fixos.split(',')] if dias_fixos else []
        eh_dia_fixo = dia_semana in dias_lista

        acao = row["acao"]
        if acao is not None:
            incluir = (acao == 1)
        else:
            incluir = eh_dia_fixo

        if incluir:
            lista_final.append({
                "id": row["id"],
                "nome": row["nome"],
                "qtd_pessoas": row["qtd_pessoas"],
                "endereco": row["endereco"],
                "gostos": row["gostos"] or "",
                "alergias": row["alergias"] or "",
            })

    return sorted(lista_final, key=lambda x: x['nome'])


def obter_cliente_por_id(id_cli):
    with get_conn() as conn:
        row = conn.execute('''
            SELECT id, nome, qtd_pessoas, endereco, dias_fixos, gostos,
                   alergias, ativo, pausa_inicio, pausa_fim
            FROM clientes WHERE id = ?
        ''', (id_cli,)).fetchone()
    return tuple(row) if row else None


def listar_todos_clientes():
    with get_conn() as conn:
        linhas = conn.execute('''
            SELECT id, nome, qtd_pessoas, endereco, dias_fixos, ativo,
                   pausa_inicio, pausa_fim, gostos, alergias
            FROM clientes
            ORDER BY nome
        ''').fetchall()
    return [tuple(r) for r in linhas]


def adicionar_excecao(id_cliente, data_str, acao):
    with get_conn() as conn:
        conn.execute('''
            INSERT OR REPLACE INTO excecoes (id_cliente, data_excecao, acao)
            VALUES (?, ?, ?)
        ''', (id_cliente, data_str, acao))


def restaurar_regra(id_cliente, data_str):
    with get_conn() as conn:
        conn.execute('''
            DELETE FROM excecoes
            WHERE id_cliente = ? AND data_excecao = ?
        ''', (id_cliente, data_str))


def cadastrar_cliente(nome, qtd, endereco, dias_str, gostos, alergias):
    _validar_dados_cliente(nome, qtd, None, None)
    dias_indices = dias_semana_para_indices(dias_str)
    with get_conn() as conn:
        conn.execute('''
            INSERT INTO clientes(nome, qtd_pessoas, endereco, dias_fixos, gostos, alergias, ativo)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        ''', (nome.strip(), qtd, endereco, dias_indices, gostos, alergias))


def atualizar_cliente(id_cli, nome, qtd, endereco, dias_str, gostos, alergias,
                       ativo, pausa_inicio, pausa_fim):
    _validar_dados_cliente(nome, qtd, pausa_inicio, pausa_fim)
    dias_indices = dias_semana_para_indices(dias_str)
    with get_conn() as conn:
        conn.execute('''
            UPDATE clientes
            SET nome=?, qtd_pessoas=?, endereco=?, dias_fixos=?, gostos=?,
                alergias=?, ativo=?, pausa_inicio=?, pausa_fim=?
            WHERE id=?
        ''', (nome.strip(), qtd, endereco, dias_indices, gostos, alergias,
              ativo, pausa_inicio or None, pausa_fim or None, id_cli))


def _pdf_texto(valor):
    # Fontes core do fpdf2 (Arial etc.) so suportam Latin-1. Sem isto, um
    # caractere fora desse conjunto derruba a geracao do PDF.
    texto = str(valor)
    return texto.encode('latin-1', 'replace').decode('latin-1')


def _truncar(texto, tamanho):
    texto = texto or ""
    if len(texto) <= tamanho:
        return texto
    return texto[:max(tamanho - 3, 0)] + "..."


def _desenhar_cabecalho_tabela(pdf):
    pdf.set_font('Arial', 'B', 10)
    for titulo, largura in _PDF_COLUNAS:
        pdf.cell(largura, 10, titulo, border=1, align='C')
    pdf.ln()
    pdf.set_font('Arial', '', 9)


def gerar_pdf(data_str, lista_clientes):
    if not lista_clientes:
        return None

    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(190, 10, _pdf_texto(f'Lista de Clientes - {data_str}'), ln=True, align='C')
    pdf.ln(10)

    _desenhar_cabecalho_tabela(pdf)

    altura_pagina = pdf.h - pdf.b_margin
    for cliente in lista_clientes:
        if pdf.get_y() + _PDF_ALTURA_LINHA_MM > altura_pagina - _PDF_MARGEM_INFERIOR_MM:
            pdf.add_page()
            _desenhar_cabecalho_tabela(pdf)

        nome = _truncar(cliente['nome'], 25)
        endereco = _truncar(cliente['endereco'], 30)
        alergias = _truncar(cliente['alergias'], 35) or "Nenhuma"

        pdf.cell(50, _PDF_ALTURA_LINHA_MM, _pdf_texto(nome), border=1)
        pdf.cell(25, _PDF_ALTURA_LINHA_MM, _pdf_texto(cliente['qtd_pessoas']), border=1, align='C')
        pdf.cell(55, _PDF_ALTURA_LINHA_MM, _pdf_texto(endereco), border=1)
        pdf.cell(60, _PDF_ALTURA_LINHA_MM, _pdf_texto(alergias), border=1)
        pdf.ln()

    os.makedirs("pdfs", exist_ok=True)
    caminho = f"pdfs/lista_{data_str}.pdf"
    pdf.output(caminho)
    return caminho


def main(page: ft.Page):
    page.title = "Marmitas"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.window.width = 900
    page.window.height = 650

    data_selecionada = datetime.datetime.now().strftime("%Y-%m-%d")
    lista_atual = []

    tabela_container = ft.Container()
    label_data_atual = ft.Text(f"Data atual: {data_selecionada}", size=14, weight=ft.FontWeight.W_500)

    def notificar(mensagem):
        page.show_dialog(ft.SnackBar(ft.Text(mensagem)))

    def atualizar_tabela(data_str):
        nonlocal lista_atual
        lista_atual = obter_lista_do_dia(data_str)
        if not lista_atual:
            tabela_container.content = ft.Text("Nenhum cliente para este dia.", size=14, weight=ft.FontWeight.BOLD)
            page.update()
            return
        linhas = []
        for cli in lista_atual:
            btn_remover = ft.IconButton(
                icon=ft.Icons.REMOVE_CIRCLE_OUTLINE,
                icon_color=ft.Colors.RED_400,
                tooltip="Remover deste dia especifico",
                on_click=lambda e, id_cli=cli['id'], data_str=data_str: remover_do_dia(id_cli, data_str)
            )
            btn_restaurar = ft.IconButton(
                icon=ft.Icons.RESTORE_PAGE,
                icon_color=ft.Colors.BLUE_400,
                tooltip="Restaurar regra fixa (cancelar excecao)",
                on_click=lambda e, id_cli=cli['id'], data_str=data_str: restaurar_regra_callback(id_cli, data_str)
            )
            acoes = ft.Row([btn_remover, btn_restaurar], spacing=0)
            linhas.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(cli['nome'], weight=ft.FontWeight.W_500)),
                        ft.DataCell(ft.Text(str(cli['qtd_pessoas']), text_align=ft.TextAlign.CENTER)),
                        ft.DataCell(ft.Text(cli['endereco'] or "")),
                        ft.DataCell(ft.Text(cli['alergias'] if cli['alergias'] else "Nenhuma")),
                        ft.DataCell(acoes),
                    ]
                )
            )
        tabela = ft.DataTable(
            columns=[
                ft.DataColumn(label=ft.Text("Nome")),
                ft.DataColumn(label=ft.Text("Pessoas"), numeric=True),
                ft.DataColumn(label=ft.Text("Endereco")),
                ft.DataColumn(label=ft.Text("Alergias / Restricoes")),
                ft.DataColumn(label=ft.Text("Acoes")),
            ],
            rows=linhas,
            heading_row_color=ft.Colors.GREY_800 if page.theme_mode == ft.ThemeMode.DARK else ft.Colors.BLUE_GREY_100,
            border=ft.Border.all(1, ft.Colors.GREY_400),
            vertical_lines=ft.BorderSide(1, ft.Colors.GREY_300),
            horizontal_lines=ft.BorderSide(1, ft.Colors.GREY_300),
        )
        tabela_container.content = ft.Column([
            ft.Text(f"Lista para {data_str} - {len(lista_atual)} clientes", size=16, weight=ft.FontWeight.BOLD),
            tabela,
        ])
        page.update()

    def remover_do_dia(id_cliente, data_str):
        adicionar_excecao(id_cliente, data_str, acao=0)
        atualizar_tabela(data_str)
        notificar(f"Cliente removido do dia {data_str}!")

    def restaurar_regra_callback(id_cliente, data_str):
        restaurar_regra(id_cliente, data_str)
        atualizar_tabela(data_str)
        notificar("Excecao removida! Cliente segue a regra fixa.")

    def adicionar_cliente_extra_dialog(e):
        todos = listar_todos_clientes()
        if not todos:
            notificar("Cadastre um cliente primeiro!")
            return
        opcoes = [ft.DropdownOption(key=str(cli[0]), text=cli[1]) for cli in todos]
        dropdown = ft.Dropdown(
            options=opcoes,
            hint_text="Selecione um cliente",
            width=300,
        )

        def confirmar_extra(e):
            if dropdown.value:
                id_cli = int(dropdown.value)
                adicionar_excecao(id_cli, data_selecionada, acao=1)
                atualizar_tabela(data_selecionada)
                page.pop_dialog()
                notificar("Cliente adicionado extra!")

        dialog = ft.AlertDialog(
            title=ft.Text("Adicionar Cliente Extra"),
            content=ft.Column([
                ft.Text("Escolha o cliente para adicionar HOJE:", size=14),
                dropdown
            ], height=100, width=350),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                ft.Button("Adicionar", on_click=confirmar_extra),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(dialog)

    def gerar_pdf_action(e):
        if not lista_atual:
            notificar("A lista esta vazia! Nao ha PDF para gerar.")
            return
        caminho = gerar_pdf(data_selecionada, lista_atual)
        if caminho:
            notificar(f"PDF salvo em: {caminho}")

    def on_date_change(e):
        nonlocal data_selecionada
        if e.control.value:
            data_selecionada = e.control.value.strftime("%Y-%m-%d")
            label_data_atual.value = f"Data atual: {data_selecionada}"
            atualizar_tabela(data_selecionada)

    date_picker = ft.DatePicker(
        first_date=datetime.datetime(2024, 1, 1),
        last_date=datetime.datetime(2030, 12, 31),
        on_change=on_date_change,
    )

    btn_calendario = ft.Button(
        "Selecionar Data",
        icon=ft.Icons.CALENDAR_MONTH,
        on_click=lambda e: page.show_dialog(date_picker)
    )

    barra_superior = ft.Row([
        btn_calendario,
        label_data_atual,
        ft.Button("Extra HOJE", on_click=adicionar_cliente_extra_dialog, icon=ft.Icons.PERSON_ADD),
        ft.Button("Gerar PDF", on_click=gerar_pdf_action, icon=ft.Icons.PICTURE_AS_PDF, color=ft.Colors.WHITE, bgcolor=ft.Colors.GREEN_700),
    ], alignment=ft.MainAxisAlignment.START, spacing=10)

    def abrir_cadastro(e):
        nome_field = ft.TextField(label="Nome", width=300)
        qtd_field = ft.TextField(label="Quantas pessoas", width=150, value="1")
        end_field = ft.TextField(label="Endereco", width=350)
        dias_field = ft.TextField(label="Dias (ex: Seg,Ter,Qua)", width=250, hint_text="Seg,Qua,Sex")
        gostos_field = ft.TextField(label="Gostos (opcional)", width=300)
        alergias_field = ft.TextField(label="Alergias/Nao gosta (opcional)", width=300)

        def salvar_cadastro(e):
            try:
                qtd = int(qtd_field.value) if qtd_field.value.isdigit() else 1
                cadastrar_cliente(
                    nome_field.value,
                    qtd,
                    end_field.value,
                    dias_field.value,
                    gostos_field.value,
                    alergias_field.value
                )
                page.pop_dialog()
                notificar(f"Cliente {nome_field.value} cadastrado!")
                atualizar_tabela(data_selecionada)
            except Exception as ex:
                notificar(f"Erro: {ex}")

        dialog_cad = ft.AlertDialog(
            title=ft.Text("Novo Cliente"),
            content=ft.Column([
                nome_field,
                ft.Row([qtd_field, ft.Text("pessoas")]),
                end_field,
                dias_field,
                gostos_field,
                alergias_field,
            ], height=350, width=400, scroll=ft.ScrollMode.AUTO),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                ft.Button("Salvar", on_click=salvar_cadastro),
            ],
        )
        page.show_dialog(dialog_cad)

    def abrir_edicao_cliente(id_cli):
        dados = obter_cliente_por_id(id_cli)
        if not dados:
            return
        (_, nome, qtd, endereco, dias_fixos, gostos, alergias,
         ativo, pausa_inicio, pausa_fim) = dados

        nome_field = ft.TextField(label="Nome", value=nome, width=300)
        qtd_field = ft.TextField(label="Quantas pessoas", value=str(qtd), width=150)
        end_field = ft.TextField(label="Endereco", value=endereco or "", width=350)
        dias_exib = indice_para_dias_semana(dias_fixos) if dias_fixos else ""
        dias_field = ft.TextField(label="Dias (ex: Seg,Ter,Qua)", value=dias_exib, width=250)
        gostos_field = ft.TextField(label="Gostos (opcional)", value=gostos or "", width=300)
        alergias_field = ft.TextField(label="Alergias/Nao gosta", value=alergias or "", width=300)
        ativo_check = ft.Checkbox(label="Ativo", value=bool(ativo))
        pausa_inicio_field = ft.TextField(label="Inicio da pausa (AAAA-MM-DD)", value=pausa_inicio or "", width=200)
        pausa_fim_field = ft.TextField(label="Fim da pausa (AAAA-MM-DD)", value=pausa_fim or "", width=200)

        def salvar_edicao(e):
            try:
                qtd_val = int(qtd_field.value) if qtd_field.value.isdigit() else 1
                ativo_val = 1 if ativo_check.value else 0
                atualizar_cliente(
                    id_cli,
                    nome_field.value,
                    qtd_val,
                    end_field.value,
                    dias_field.value,
                    gostos_field.value,
                    alergias_field.value,
                    ativo_val,
                    pausa_inicio_field.value.strip(),
                    pausa_fim_field.value.strip()
                )
                page.pop_dialog()
                notificar(f"Cliente {nome_field.value} atualizado!")
                atualizar_tabela(data_selecionada)
            except Exception as ex:
                notificar(f"Erro: {ex}")

        dialog_edit = ft.AlertDialog(
            title=ft.Text(f"Editando: {nome}"),
            content=ft.Column([
                nome_field,
                ft.Row([qtd_field, ft.Text("pessoas")]),
                end_field,
                dias_field,
                gostos_field,
                alergias_field,
                ft.Row([pausa_inicio_field, pausa_fim_field]),
                ativo_check,
            ], height=400, width=450, scroll=ft.ScrollMode.AUTO),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                ft.Button("Salvar Alteracoes", on_click=salvar_edicao),
            ],
        )
        page.show_dialog(dialog_edit)

    def abrir_gerenciar(e):
        todos = listar_todos_clientes()
        if not todos:
            texto = ft.Text("Nenhum cliente cadastrado.")
        else:
            linhas = []
            for cli in todos:
                id_cli, nome, qtd, end, dias_idx, ativo, p_inicio, p_fim, gostos, alergias = cli
                dias_exib = indice_para_dias_semana(dias_idx) if dias_idx else "Nenhum"
                status = "Ativo" if ativo == 1 else "Inativo"
                pausa = f"Pausa: {p_inicio} ate {p_fim}" if p_inicio and p_fim else "Sem pausa"

                btn_editar = ft.IconButton(
                    icon=ft.Icons.EDIT,
                    icon_color=ft.Colors.BLUE_400,
                    tooltip="Editar cliente",
                    on_click=lambda e, id_cli=id_cli: abrir_edicao_cliente(id_cli)
                )

                linhas.append(
                    ft.Row([
                        ft.Text(f"{nome} | {qtd} pessoas | {dias_exib} | {status} | {pausa}", expand=True),
                        btn_editar
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                )
            texto = ft.Column(linhas, spacing=10, scroll=ft.ScrollMode.AUTO)

        dialog_ger = ft.AlertDialog(
            title=ft.Text("Gerenciar Clientes"),
            content=ft.Container(texto, width=550, height=400, padding=10),
            actions=[
                ft.TextButton("Fechar", on_click=lambda e: page.pop_dialog()),
            ],
        )
        page.show_dialog(dialog_ger)

    page.add(
        ft.Row([
            ft.Icon(ft.Icons.RESTAURANT, size=30, color=ft.Colors.ORANGE_800),
            ft.Text("Sistema de Marmitas - Painel Diario", size=24, weight=ft.FontWeight.BOLD),
        ]),
        ft.Divider(height=10),
        barra_superior,
        ft.Divider(height=10),
        ft.Row([
            ft.Button("Novo Cliente", icon=ft.Icons.PERSON_ADD_ALT_1, on_click=abrir_cadastro),
            ft.Button("Ver Todos Clientes", icon=ft.Icons.LIST_ALT, on_click=abrir_gerenciar),
        ]),
        ft.Divider(height=10),
        tabela_container,
    )

    atualizar_tabela(data_selecionada)


if __name__ == "__main__":
    init_db()
    ft.run(main)