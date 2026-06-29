"""Tick Up — interface Flet (mobile-first; corre também na web e desktop).

Modelo simples (v0.3.0), com apenas dois ecrãs:
  • **Tarefas (board):** um único sítio com todas as tarefas por fazer (grupo e
    data opcionais) + as concluídas de hoje. Ao virar o dia, as concluídas saem
    do board (não são apagadas — ficam no Calendário).
  • **Calendário:** que tarefas foram feitas em cada dia do mês.

Grupos são chips de filtro no topo do board (sem menu lateral). Interação numa
linha: tocar no círculo = concluir/reabrir · tocar na linha = editar · deslizar
= apagar (com 'Anular'). Animações subtis: troca de ecrã, navegação de mês e o
painel do dia.

Toda a lógica vive no núcleo (`tickup`) via `AppController`. Aqui só há widgets.
"""
from __future__ import annotations

import calendar as _calendar
import os
import sys
from datetime import date, datetime
from pathlib import Path

# Permite `flet run app/main.py` encontrar o pacote `tickup` em ../src.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import flet as ft

from app.controller import ALL_GROUPS, AppController
from tickup.models import Priority, Task

ACCENT = ft.Colors.INDIGO

# Sentinela: "o utilizador não escolheu data" na barra de adição rápida.
_UNSET = object()

PRIORITY_COLOR = {
    Priority.URGENT: ft.Colors.RED_400,
    Priority.HIGH: ft.Colors.ORANGE_400,
    Priority.MEDIUM: ft.Colors.BLUE_400,
    Priority.NONE: ft.Colors.OUTLINE,
}

_PT_MONTHS = [
    "jan", "fev", "mar", "abr", "mai", "jun",
    "jul", "ago", "set", "out", "nov", "dez",
]
_PT_MONTHS_FULL = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]
_PT_WEEKDAYS = [
    "segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo",
]
_PT_WEEKDAYS_SHORT = ["S", "T", "Q", "Q", "S", "S", "D"]  # segunda → domingo

_FADE = ft.Animation(250, ft.AnimationCurve.EASE_OUT)


def _data_path() -> Path:
    """Onde guardar os dados. No mobile, Flet define FLET_APP_STORAGE_DATA."""
    base = os.environ.get("FLET_APP_STORAGE_DATA")
    if base:
        return Path(base) / "tickup.json"
    return Path(__file__).resolve().parent.parent / "storage" / "tickup.json"


def _fmt_date(d: date) -> str:
    return f"{d.day} {_PT_MONTHS[d.month - 1]}"


def _due_label(task: Task, today: date) -> tuple[str, str] | None:
    """(texto, cor) para a etiqueta de data, ou None se não houver data."""
    if task.due_date is None:
        return None
    if task.due_date < today:
        return ("Atrasada", ft.Colors.RED_400)
    if task.due_date == today:
        return ("Hoje", ACCENT)
    delta = (task.due_date - today).days
    if delta == 1:
        return ("Amanhã", ft.Colors.ON_SURFACE_VARIANT)
    if delta < 7:
        return (_PT_WEEKDAYS[task.due_date.weekday()].capitalize(), ft.Colors.ON_SURFACE_VARIANT)
    return (_fmt_date(task.due_date), ft.Colors.ON_SURFACE_VARIANT)


def make_task_row(
    task: Task,
    today: date,
    *,
    on_toggle,
    on_open,
    on_delete,
    list_label: str | None = None,
) -> ft.Control:
    """Linha de uma tarefa: círculo (concluir) + título/subtítulo (abrir) + swipe (apagar)."""
    done = task.completed

    # Círculo de conclusão (toca só aqui para concluir/reabrir). O ícone vive num
    # AnimatedSwitcher para a troca feito/por-fazer ter uma pequena transição.
    circle = ft.Container(
        ft.AnimatedSwitcher(
            ft.Icon(
                ft.Icons.CHECK_CIRCLE if done else ft.Icons.RADIO_BUTTON_UNCHECKED,
                color=ACCENT if done else PRIORITY_COLOR[task.priority],
                size=24,
            ),
            transition=ft.AnimatedSwitcherTransition.SCALE,
            duration=180,
            switch_in_curve=ft.AnimationCurve.EASE_OUT,
        ),
        on_click=lambda e: on_toggle(task.id),
        ink=True,
        border_radius=20,
        padding=4,
    )

    title = ft.Text(
        task.title,
        size=16,
        weight=ft.FontWeight.W_400,
        color=ft.Colors.ON_SURFACE_VARIANT if done else None,
        style=ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH) if done else None,
        max_lines=2,
        overflow=ft.TextOverflow.ELLIPSIS,
    )

    # Subtítulo: data + notas + grupo (só os que existirem).
    sub: list[ft.Control] = []
    label = _due_label(task, today)
    if label and not done:
        text, color = label
        sub.append(
            ft.Row(
                [ft.Icon(ft.Icons.EVENT, size=13, color=color), ft.Text(text, size=12, color=color)],
                spacing=3, tight=True,
            )
        )
    if task.notes.strip():
        sub.append(ft.Icon(ft.Icons.NOTES, size=13, color=ft.Colors.ON_SURFACE_VARIANT))
    if list_label:
        sub.append(
            ft.Row(
                [ft.Icon(ft.Icons.LABEL_OUTLINE, size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                 ft.Text(list_label, size=12, color=ft.Colors.ON_SURFACE_VARIANT)],
                spacing=3, tight=True,
            )
        )

    text_col = [title]
    if sub:
        text_col.append(ft.Row(sub, spacing=12, wrap=False))

    body = ft.Container(
        ft.Column(text_col, spacing=3, expand=True),
        on_click=lambda e: on_open(task.id),
        ink=True,
        expand=True,
        padding=ft.Padding.symmetric(vertical=14),
    )

    content = ft.Container(
        ft.Row(
            [circle, body],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding.only(left=14, right=16),
    )

    return ft.Dismissible(
        content=content,
        dismiss_direction=ft.DismissDirection.END_TO_START,
        on_dismiss=lambda e: on_delete(task.id),
        background=ft.Container(
            ft.Row(
                [ft.Icon(ft.Icons.DELETE_OUTLINE, color=ft.Colors.WHITE)],
                alignment=ft.MainAxisAlignment.END,
            ),
            bgcolor=ft.Colors.RED_400,
            padding=ft.Padding.symmetric(horizontal=20),
            border_radius=12,
        ),
        data=task.id,
    )


def _section_header(text: str, *, color: str | None = None) -> ft.Control:
    return ft.Container(
        ft.Text(text.upper(), size=12, weight=ft.FontWeight.BOLD,
                color=color or ft.Colors.ON_SURFACE_VARIANT),
        padding=ft.Padding.only(left=18, top=18, bottom=4),
    )


class TickUpApp:
    def __init__(self, page: ft.Page, controller: AppController) -> None:
        self.page = page
        self.c = controller
        # Estado da barra de adição rápida.
        self.add_priority: Priority = Priority.NONE
        self.add_due = _UNSET  # _UNSET, None ou date

        # --- Board ---
        self.chips_row = ft.Row(scroll=ft.ScrollMode.AUTO, spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        self.list_view = ft.ListView(expand=True, spacing=2, padding=ft.Padding.only(top=4, bottom=8))
        self.empty = ft.Container(alignment=ft.Alignment.CENTER, expand=True, visible=False)
        self.board_view = ft.Container(
            ft.Column(
                [
                    ft.Container(self.chips_row, padding=ft.Padding.only(left=12, right=12, top=6, bottom=2)),
                    ft.Divider(height=1),
                    ft.Stack([self.list_view, self.empty], expand=True),
                ],
                spacing=0, expand=True,
            ),
            expand=True,
        )

        # --- Calendário (reconstruído a cada refresh; muda de identidade para animar) ---
        self.calendar_view = ft.Container(expand=True)

        # Área central animada (troca Board ↔ Calendário e navegação de mês).
        self.switcher = ft.AnimatedSwitcher(
            self.board_view,
            transition=ft.AnimatedSwitcherTransition.FADE,
            duration=250,
            reverse_duration=200,
            switch_in_curve=ft.AnimationCurve.EASE_OUT,
            switch_out_curve=ft.AnimationCurve.EASE_IN,
            expand=True,
        )

        # --- Barra de adição rápida ---
        self.add_field = ft.TextField(
            hint_text="Adicionar tarefa…",
            border=ft.InputBorder.NONE,
            expand=True,
            on_submit=lambda e: self._on_add(),
            text_size=16,
        )
        self.prio_btn = ft.PopupMenuButton(
            icon=ft.Icons.FLAG_OUTLINED,
            tooltip="Prioridade",
            items=[
                ft.PopupMenuItem(content="P1 · Urgente", icon=ft.Icons.FLAG,
                                 on_click=lambda e: self._set_add_priority(Priority.URGENT)),
                ft.PopupMenuItem(content="P2 · Alta", icon=ft.Icons.FLAG,
                                 on_click=lambda e: self._set_add_priority(Priority.HIGH)),
                ft.PopupMenuItem(content="P3 · Média", icon=ft.Icons.FLAG,
                                 on_click=lambda e: self._set_add_priority(Priority.MEDIUM)),
                ft.PopupMenuItem(content="Sem prioridade", icon=ft.Icons.OUTLINED_FLAG,
                                 on_click=lambda e: self._set_add_priority(Priority.NONE)),
            ],
        )
        self.date_btn = ft.IconButton(
            icon=ft.Icons.EVENT_OUTLINED, tooltip="Data (opcional)",
            on_click=lambda e: self._open_add_datepicker(),
        )

    # --- construção do ecrã ---------------------------------------------------
    def build(self) -> None:
        page = self.page
        page.title = "Tick Up"
        page.theme = ft.Theme(color_scheme_seed=ACCENT)
        page.theme_mode = ft.ThemeMode.SYSTEM
        page.padding = 0

        self.appbar = ft.AppBar(
            title=ft.Text(self.c.view_title(), weight=ft.FontWeight.BOLD),
            center_title=False,
            bgcolor=ft.Colors.SURFACE,
            actions=[],
        )
        page.appbar = self.appbar

        # A NavigationBar tem de ter ≥2 destinos já no primeiro render (o Flutter
        # rebenta com a barra vazia → ecrã preto), por isso há sempre 2.
        self.nav = ft.NavigationBar(
            selected_index=0,
            on_change=self._on_nav,
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icon(ft.Icons.CHECKLIST), label="Tarefas"),
                ft.NavigationBarDestination(icon=ft.Icon(ft.Icons.CALENDAR_MONTH), label="Calendário"),
            ],
        )
        page.navigation_bar = self.nav

        self.add_bar = ft.Container(
            ft.Row(
                [self.prio_btn, self.date_btn, self.add_field,
                 ft.IconButton(ft.Icons.ARROW_UPWARD, icon_color=ACCENT,
                               tooltip="Adicionar", on_click=lambda e: self._on_add())],
                vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=2,
            ),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            padding=ft.Padding.symmetric(horizontal=8, vertical=2),
        )

        page.add(
            ft.SafeArea(
                ft.Column([self.switcher, self.add_bar], expand=True, spacing=0),
                expand=True,
            )
        )
        self.refresh()

    # --- navegação inferior ----------------------------------------------------
    def _on_nav(self, e) -> None:
        if e.control.selected_index == 0:
            self.c.set_board()
        else:
            self.c.set_calendar()
        self._sync_chrome()
        self.refresh()

    def _sync_chrome(self) -> None:
        """Atualiza título, ações da appbar e barra de adição conforme o ecrã."""
        view = self.c.current_view
        self.appbar.title.value = self.c.view_title()
        actions: list[ft.Control] = []
        if view == "board":
            actions.append(ft.IconButton(ft.Icons.SEARCH, tooltip="Pesquisar",
                                         on_click=self._open_search))
            grp = self.c.active_group()
            if grp is not None:
                actions.append(ft.IconButton(ft.Icons.EDIT_OUTLINED, tooltip="Editar grupo",
                                             on_click=lambda e, g=grp: self._open_group_menu(g)))
        self.appbar.actions = actions
        self.add_bar.visible = view == "board"
        self.nav.selected_index = 0 if view == "board" else 1

    # --- chips de grupo --------------------------------------------------------
    def _build_chips(self) -> None:
        chips: list[ft.Control] = []

        def chip(label: str, selected: bool, on_click) -> ft.Chip:
            return ft.Chip(
                label=ft.Text(label),
                selected=selected,
                show_checkmark=False,
                selected_color=ft.Colors.with_opacity(0.18, ACCENT),
                on_click=on_click,
            )

        chips.append(chip("Todos", self.c.group_filter is ALL_GROUPS,
                          lambda e: self._go_group(ALL_GROUPS)))
        for lst in self.c.lists():
            chips.append(chip(lst.name, self.c.group_filter == lst.id,
                              lambda e, lid=lst.id: self._go_group(lid)))
        chips.append(ft.Chip(
            label=ft.Text("Novo"),
            leading=ft.Icon(ft.Icons.ADD, size=18),
            on_click=lambda e: self._open_new_group(),
        ))
        self.chips_row.controls = chips

    def _go_group(self, value) -> None:
        self.c.set_group(value)
        self._sync_chrome()
        self.refresh()

    # --- adição rápida ---------------------------------------------------------
    def _set_add_priority(self, p: Priority) -> None:
        self.add_priority = p
        self.prio_btn.icon = ft.Icons.FLAG if p != Priority.NONE else ft.Icons.FLAG_OUTLINED
        self.prio_btn.icon_color = PRIORITY_COLOR[p] if p != Priority.NONE else None
        self.page.update()

    def _open_add_datepicker(self) -> None:
        def on_change(e):
            self.add_due = e.control.value.date()
            self.date_btn.icon = ft.Icons.EVENT
            self.date_btn.icon_color = ACCENT
            self.page.update()
        self.page.show_dialog(ft.DatePicker(
            first_date=datetime(2000, 1, 1), last_date=datetime(2100, 12, 31),
            value=datetime.now(), on_change=on_change,
        ))

    def _reset_add_options(self) -> None:
        self.add_priority = Priority.NONE
        self.add_due = _UNSET
        self.prio_btn.icon = ft.Icons.FLAG_OUTLINED
        self.prio_btn.icon_color = None
        self.date_btn.icon = ft.Icons.EVENT_OUTLINED
        self.date_btn.icon_color = None

    def _on_add(self) -> None:
        kwargs = {"priority": self.add_priority}
        if self.add_due is not _UNSET:
            kwargs["due_date"] = self.add_due
        if self.c.add_quick(self.add_field.value, **kwargs):
            self.add_field.value = ""
            self._reset_add_options()
            self.add_field.focus()
            self.refresh()

    # --- detalhe / edição ------------------------------------------------------
    def _open_detail(self, task_id: str) -> None:
        task = self.c.get(task_id)
        if task is None:
            return

        title_f = ft.TextField(label="Título", value=task.title, autofocus=False)
        notes_f = ft.TextField(label="Notas", value=task.notes, multiline=True, min_lines=2, max_lines=5)

        prio_seg = ft.SegmentedButton(
            segments=[
                ft.Segment(value="1", label=ft.Text("P1")),
                ft.Segment(value="2", label=ft.Text("P2")),
                ft.Segment(value="3", label=ft.Text("P3")),
                ft.Segment(value="4", label=ft.Text("—")),
            ],
            selected=[str(int(task.priority))],
            allow_empty_selection=False,
            allow_multiple_selection=False,
        )

        chosen = {"due": task.due_date}
        due_text = ft.Text()

        def render_due():
            due_text.value = _fmt_date(chosen["due"]) if chosen["due"] else "Sem data"
            self.page.update()

        def pick_date(e):
            def on_change(ev):
                chosen["due"] = ev.control.value.date()
                render_due()
            self.page.show_dialog(ft.DatePicker(
                first_date=datetime(2000, 1, 1), last_date=datetime(2100, 12, 31),
                value=datetime.combine(chosen["due"] or date.today(), datetime.min.time()),
                on_change=on_change,
            ))

        def set_due(d):
            chosen["due"] = d
            render_due()

        due_row = ft.Row([
            ft.OutlinedButton(icon=ft.Icons.EVENT, content=due_text, on_click=pick_date),
            ft.TextButton("Hoje", on_click=lambda e: set_due(self.c.today())),
            ft.TextButton("Limpar", on_click=lambda e: set_due(None)),
        ], wrap=True)
        due_text.value = _fmt_date(task.due_date) if task.due_date else "Sem data"

        group_dd = ft.Dropdown(
            label="Grupo",
            value=task.list_id or "",
            options=[ft.DropdownOption(key="", text="Sem grupo")]
            + [ft.DropdownOption(key=l.id, text=l.name) for l in self.c.lists()],
        )

        def save(e):
            new_title = title_f.value.strip()
            if not new_title:
                title_f.error_text = "O título não pode estar vazio."
                self.page.update()
                return
            self.c.update(
                task.id,
                title=new_title,
                notes=notes_f.value,
                priority=Priority(int(prio_seg.selected[0])),
                due_date=chosen["due"],
                list_id=(group_dd.value or None),
            )
            self.page.pop_dialog()
            self.refresh()

        def delete(e):
            self.page.pop_dialog()
            self._delete_with_undo(task.id)

        sheet = ft.BottomSheet(
            ft.Container(
                ft.Column([
                    ft.Row([
                        ft.Text("Editar tarefa", size=18, weight=ft.FontWeight.BOLD, expand=True),
                        ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=ft.Colors.RED_400,
                                      tooltip="Apagar", on_click=delete),
                    ]),
                    title_f, notes_f,
                    ft.Text("Prioridade", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                    prio_seg,
                    ft.Text("Data", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                    due_row,
                    group_dd,
                    ft.FilledButton("Guardar", icon=ft.Icons.CHECK, on_click=save,
                                    width=10000, height=46),
                ], spacing=12, tight=True, scroll=ft.ScrollMode.AUTO),
                padding=20,
            ),
            show_drag_handle=True,
        )
        self.page.show_dialog(sheet)

    # --- apagar com 'anular' ---------------------------------------------------
    def _on_delete(self, task_id: str) -> None:
        # Chamado pelo swipe; a linha já desapareceu visualmente.
        self.c.delete(task_id)
        self._show_undo()
        self.refresh()

    def _delete_with_undo(self, task_id: str) -> None:
        self.c.delete(task_id)
        self._show_undo()
        self.refresh()

    def _show_undo(self) -> None:
        self.page.show_dialog(ft.SnackBar(
            content=ft.Text("Tarefa apagada"),
            action=ft.SnackBarAction(label="Anular", on_click=lambda e: self._undo()),
            behavior=ft.SnackBarBehavior.FLOATING,
        ))

    def _undo(self) -> None:
        if self.c.undo_delete():
            self.refresh()

    # --- pesquisa --------------------------------------------------------------
    def _open_search(self, e) -> None:
        field = ft.TextField(hint_text="Pesquisar tarefas…", autofocus=True,
                             value=self.c.query,
                             on_submit=lambda ev: do_search())

        def do_search():
            self.c.set_search(field.value.strip())
            self.page.pop_dialog()
            self._sync_chrome()
            self.refresh()

        def clear():
            self.c.clear_search()
            self.page.pop_dialog()
            self._sync_chrome()
            self.refresh()

        self.page.show_dialog(ft.AlertDialog(
            title=ft.Text("Pesquisar"),
            content=field,
            actions=[
                ft.TextButton("Limpar", on_click=lambda ev: clear()),
                ft.FilledButton("Pesquisar", on_click=lambda ev: do_search()),
            ],
        ))

    # --- grupos ----------------------------------------------------------------
    def _open_new_group(self) -> None:
        field = ft.TextField(label="Nome do grupo", autofocus=True,
                             on_submit=lambda e: create())

        def create():
            name = field.value.strip()
            if not name:
                return
            lst = self.c.add_list(name)
            self.page.pop_dialog()
            self.c.set_group(lst.id)  # passa logo a filtrar pelo novo grupo
            self._sync_chrome()
            self.refresh()

        self.page.show_dialog(ft.AlertDialog(
            title=ft.Text("Novo grupo"),
            content=field,
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.page.pop_dialog()),
                ft.FilledButton("Criar", on_click=lambda e: create()),
            ],
        ))

    def _open_group_menu(self, lst) -> None:
        def rename():
            self.page.pop_dialog()
            field = ft.TextField(label="Nome", value=lst.name, autofocus=True,
                                 on_submit=lambda e: do_rename())

            def do_rename():
                if field.value.strip():
                    self.c.rename_list(lst.id, field.value)
                self.page.pop_dialog()
                self._sync_chrome()
                self.refresh()

            self.page.show_dialog(ft.AlertDialog(
                title=ft.Text("Renomear grupo"), content=field,
                actions=[ft.TextButton("Cancelar", on_click=lambda e: self.page.pop_dialog()),
                         ft.FilledButton("Guardar", on_click=lambda e: do_rename())],
            ))

        def delete():
            self.c.delete_list(lst.id, delete_tasks=False)
            self.page.pop_dialog()
            self._sync_chrome()
            self.refresh()

        self.page.show_dialog(ft.AlertDialog(
            title=ft.Text(lst.name),
            content=ft.Text("As tarefas ficam sem grupo se apagares o grupo."),
            actions=[
                ft.TextButton("Renomear", on_click=lambda e: rename()),
                ft.TextButton("Apagar", style=ft.ButtonStyle(color=ft.Colors.RED_400),
                              on_click=lambda e: delete()),
                ft.TextButton("Fechar", on_click=lambda e: self.page.pop_dialog()),
            ],
        ))

    # --- render ----------------------------------------------------------------
    def refresh(self) -> None:
        if self.c.current_view == "board":
            self._render_board()
            self.switcher.content = self.board_view
        else:
            self.switcher.content = self._build_calendar()
        self.page.update()

    def _render_board(self) -> None:
        today = self.c.today()
        self._build_chips()

        rows: list[ft.Control] = []
        show_group_label = self.c.group_filter is ALL_GROUPS

        def add_rows(tasks):
            for t in tasks:
                lbl = self.c.list_name(t.list_id) if (show_group_label and t.list_id) else None
                rows.append(make_task_row(
                    t, today, on_toggle=self._on_toggle, on_open=self._open_detail,
                    on_delete=self._on_delete, list_label=lbl,
                ))

        active = self.c.visible_tasks()
        add_rows(active)

        done_today = self.c.completed_today()
        if done_today:
            rows.append(_section_header(f"Feitas hoje · {len(done_today)}"))
            add_rows(done_today)

        self.list_view.controls = rows
        has_rows = bool(rows)
        if not has_rows:
            if self.c.query.strip():
                msg, icon = ("Sem resultados", ft.Icons.SEARCH_OFF)
            else:
                msg, icon = ("Tudo em dia! Adiciona uma tarefa.", ft.Icons.TASK_ALT)
            self.empty.content = ft.Column(
                [ft.Icon(icon, size=56, color=ft.Colors.OUTLINE),
                 ft.Text(msg, size=18, color=ft.Colors.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER)],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8,
            )
        self.empty.visible = not has_rows
        self.list_view.visible = has_rows

    # --- calendário ------------------------------------------------------------
    def _build_calendar(self) -> ft.Control:
        today = self.c.today()
        year, month = self.c.calendar_year, self.c.calendar_month
        by_day = self.c.calendar_days()

        header = ft.Row(
            [
                ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=lambda e: self._calendar_nav(-1)),
                ft.Text(f"{_PT_MONTHS_FULL[month - 1]} {year}", size=18,
                        weight=ft.FontWeight.BOLD, expand=True, text_align=ft.TextAlign.CENTER),
                ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=lambda e: self._calendar_nav(1)),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        weekday_row = ft.Row(
            [ft.Container(ft.Text(w, size=12, weight=ft.FontWeight.BOLD,
                                  color=ft.Colors.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER),
                          expand=True, alignment=ft.Alignment.CENTER)
             for w in _PT_WEEKDAYS_SHORT],
        )

        cal = _calendar.Calendar(firstweekday=0)  # segunda-feira
        weeks: list[ft.Control] = []
        for week in cal.monthdatescalendar(year, month):
            cells: list[ft.Control] = []
            for day in week:
                cells.append(self._calendar_cell(day, month, today, by_day.get(day, [])))
            weeks.append(ft.Row(cells, spacing=4))

        total = sum(len(v) for v in by_day.values())
        footer = ft.Container(
            ft.Text(
                f"{total} tarefa(s) concluída(s) este mês" if total else "Nada concluído este mês",
                size=12, color=ft.Colors.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER,
            ),
            padding=ft.Padding.only(top=12),
            alignment=ft.Alignment.CENTER,
        )

        return ft.Container(
            ft.Column(
                [header, ft.Divider(height=1), weekday_row, *weeks, footer],
                spacing=6, scroll=ft.ScrollMode.AUTO,
            ),
            padding=ft.Padding.symmetric(horizontal=10, vertical=8),
            expand=True,
        )

    def _calendar_cell(self, day: date, month: int, today: date, done: list[Task]) -> ft.Control:
        in_month = day.month == month
        is_today = day == today
        has_done = bool(done)

        children: list[ft.Control] = [
            ft.Text(
                str(day.day), size=14,
                weight=ft.FontWeight.BOLD if is_today else ft.FontWeight.W_400,
                color=(ACCENT if is_today else
                       (ft.Colors.ON_SURFACE if in_month else ft.Colors.with_opacity(0.35, ft.Colors.ON_SURFACE))),
            )
        ]
        if has_done and in_month:
            children.append(ft.Container(
                ft.Text(str(len(done)), size=10, color=ft.Colors.WHITE,
                        weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                bgcolor=ACCENT, width=16, height=16, border_radius=8,
                alignment=ft.Alignment.CENTER,
            ))
        else:
            children.append(ft.Container(height=16))

        cell = ft.Container(
            ft.Column(children, spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            expand=True,
            height=52,
            padding=ft.Padding.symmetric(vertical=4),
            border_radius=10,
            bgcolor=ft.Colors.with_opacity(0.08, ACCENT) if is_today else None,
            alignment=ft.Alignment.CENTER,
            ink=has_done and in_month,
            on_click=(lambda e, d=day: self._open_day_detail(d)) if (has_done and in_month) else None,
            animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
        )
        return cell

    def _calendar_nav(self, direction: int) -> None:
        if direction < 0:
            self.c.calendar_prev_month()
        else:
            self.c.calendar_next_month()
        self.refresh()

    def _open_day_detail(self, day: date) -> None:
        tasks = self.c.completed_on(day)
        weekday = _PT_WEEKDAYS[day.weekday()].capitalize()
        rows: list[ft.Control] = []
        for t in tasks:
            grp = self.c.list_name(t.list_id) if t.list_id else None
            sub: list[ft.Control] = []
            if t.completed_at is not None:
                hhmm = t.completed_at.astimezone().strftime("%H:%M")
                sub.append(ft.Text(hhmm, size=12, color=ft.Colors.ON_SURFACE_VARIANT))
            if grp:
                sub.append(ft.Row(
                    [ft.Icon(ft.Icons.LABEL_OUTLINE, size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                     ft.Text(grp, size=12, color=ft.Colors.ON_SURFACE_VARIANT)],
                    spacing=3, tight=True))
            col = [ft.Text(t.title, size=15,
                           style=ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH),
                           color=ft.Colors.ON_SURFACE_VARIANT)]
            if sub:
                col.append(ft.Row(sub, spacing=12))
            rows.append(ft.Row(
                [ft.Icon(ft.Icons.CHECK_CIRCLE, color=ACCENT, size=20),
                 ft.Column(col, spacing=2, expand=True)],
                vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=10,
            ))

        body = ft.Column(
            [
                ft.Text(f"{weekday}, {_fmt_date(day)}", size=18, weight=ft.FontWeight.BOLD),
                ft.Text(f"{len(tasks)} concluída(s)", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Divider(),
                *rows,
            ],
            spacing=10, tight=True, scroll=ft.ScrollMode.AUTO,
        )
        self.page.show_dialog(ft.BottomSheet(
            ft.Container(body, padding=20),
            show_drag_handle=True,
        ))

    def _on_toggle(self, task_id: str) -> None:
        self.c.toggle(task_id)
        self.refresh()


def main(page: ft.Page) -> None:
    controller = AppController(_data_path())
    app = TickUpApp(page, controller)
    app.build()
    app._sync_chrome()
    page.update()


if __name__ == "__main__":
    ft.app(main)
