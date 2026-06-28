"""Tick Up — interface Flet (mobile-first; corre também na web e desktop).

Layout inspirado nas apps populares (Todoist, Things 3, Microsoft To Do):
  • menu lateral: vistas inteligentes (com contagens) + listas/projetos + pesquisa
  • barra de navegação inferior: Hoje / Próximos / Inbox / Concluídos
  • lista de tarefas com secções (Atrasadas/Hoje, por data nos Próximos)
  • tocar no círculo = concluir · tocar na linha = editar · deslizar = apagar (com 'Anular')
  • adição rápida com escolha de prioridade e data

Toda a lógica vive no núcleo (`tickup`) via `AppController`. Aqui só há widgets.
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime
from pathlib import Path

# Permite `flet run app/main.py` encontrar o pacote `tickup` em ../src.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import flet as ft

from app.controller import SMART_VIEWS, VIEWS, AppController
from tickup.models import Priority, Task

ACCENT = ft.Colors.INDIGO

# Sentinela: "o utilizador não escolheu data" (mantém o automatismo da vista Hoje).
_UNSET = object()

VIEW_ICONS = {
    "today": ft.Icons.TODAY,
    "upcoming": ft.Icons.UPCOMING,
    "overdue": ft.Icons.WARNING_AMBER_ROUNDED,
    "inbox": ft.Icons.INBOX,
    "completed": ft.Icons.CHECK_CIRCLE_OUTLINE,
}

PRIORITY_COLOR = {
    Priority.URGENT: ft.Colors.RED_400,
    Priority.HIGH: ft.Colors.ORANGE_400,
    Priority.MEDIUM: ft.Colors.BLUE_400,
    Priority.NONE: ft.Colors.OUTLINE,
}

EMPTY_MESSAGES = {
    "today": ("Tudo em dia!", ft.Icons.TASK_ALT),
    "upcoming": ("Nada nos próximos dias", ft.Icons.EVENT_AVAILABLE),
    "overdue": ("Sem tarefas atrasadas 🎉", ft.Icons.CELEBRATION),
    "inbox": ("Inbox vazia", ft.Icons.INBOX),
    "completed": ("Ainda nada concluído", ft.Icons.HISTORY),
    "list": ("Lista vazia", ft.Icons.CHECKLIST),
    "search": ("Sem resultados", ft.Icons.SEARCH_OFF),
}

_PT_MONTHS = [
    "jan", "fev", "mar", "abr", "mai", "jun",
    "jul", "ago", "set", "out", "nov", "dez",
]
_PT_WEEKDAYS = [
    "segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo",
]


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

    # Círculo de conclusão (toca só aqui para concluir/reabrir).
    circle = ft.Container(
        ft.Icon(
            ft.Icons.CHECK_CIRCLE if done else ft.Icons.RADIO_BUTTON_UNCHECKED,
            color=ACCENT if done else PRIORITY_COLOR[task.priority],
            size=24,
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

    # Subtítulo: data + notas + lista (só os que existirem).
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

        self.list_view = ft.ListView(expand=True, spacing=2, padding=ft.Padding.only(top=4, bottom=8))
        self.empty = ft.Container(alignment=ft.Alignment.CENTER, expand=True, visible=False)
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
            icon=ft.Icons.EVENT_OUTLINED, tooltip="Data limite",
            on_click=lambda e: self._open_add_datepicker(),
        )
        self.drawer = ft.NavigationDrawer(controls=[])

    # --- construção do ecrã ---------------------------------------------------
    def build(self) -> None:
        page = self.page
        page.title = "Tick Up"
        page.theme = ft.Theme(color_scheme_seed=ACCENT)
        page.theme_mode = ft.ThemeMode.SYSTEM
        page.padding = 0
        page.drawer = self.drawer

        self.appbar = ft.AppBar(
            leading=ft.IconButton(ft.Icons.MENU, on_click=self._open_drawer),
            title=ft.Text(self.c.view_title(), weight=ft.FontWeight.BOLD),
            center_title=False,
            bgcolor=ft.Colors.SURFACE,
            actions=[
                ft.IconButton(ft.Icons.SEARCH, tooltip="Pesquisar", on_click=self._open_search),
            ],
        )
        page.appbar = self.appbar

        # IMPORTANTE: a NavigationBar tem de ter ≥2 destinos já no primeiro
        # render (o Flutter rebenta com a barra vazia → ecrã preto), por isso
        # construímos os destinos aqui e não só no refresh().
        self.nav = ft.NavigationBar(
            selected_index=0,
            on_change=self._on_nav,
            destinations=self._nav_destinations(),
        )
        page.navigation_bar = self.nav

        add_bar = ft.Container(
            ft.Row(
                [self.prio_btn, self.date_btn, self.add_field,
                 ft.IconButton(ft.Icons.ARROW_UPWARD, icon_color=ACCENT,
                               tooltip="Adicionar", on_click=lambda e: self._on_add())],
                vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=2,
            ),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            padding=ft.Padding.symmetric(horizontal=8, vertical=2),
        )
        self.add_bar = add_bar

        page.add(
            ft.SafeArea(
                ft.Column(
                    [ft.Stack([self.list_view, self.empty], expand=True), add_bar],
                    expand=True, spacing=0,
                ),
                expand=True,
            )
        )
        self._build_drawer()  # nunca deixar o drawer vazio antes do primeiro render
        self.refresh()

    # --- menu lateral ----------------------------------------------------------
    def _build_drawer(self) -> None:
        counts = self.c.counts()
        items: list[ft.Control] = [
            ft.Container(
                ft.Row([
                    ft.Icon(ft.Icons.CHECK_CIRCLE, color=ACCENT),
                    ft.Text("Tick Up", size=20, weight=ft.FontWeight.BOLD),
                ], spacing=10),
                padding=ft.Padding.only(left=20, top=20, bottom=8, right=20),
            ),
        ]

        def smart_tile(key: str) -> ft.Control:
            n = counts.get(key, 0)
            active = self.c.current_view == key
            trailing = (ft.Text(str(n), color=ft.Colors.ON_SURFACE_VARIANT)
                        if n and key != "completed" else None)
            return ft.ListTile(
                leading=ft.Icon(VIEW_ICONS[key],
                                color=ACCENT if active else ft.Colors.ON_SURFACE_VARIANT),
                title=ft.Text(SMART_VIEWS[key],
                              weight=ft.FontWeight.BOLD if active else ft.FontWeight.W_400),
                trailing=trailing,
                bgcolor=ft.Colors.with_opacity(0.08, ACCENT) if active else None,
                on_click=lambda e, k=key: self._go_smart(k),
            )

        for key in ("today", "upcoming", "overdue", "inbox", "completed"):
            items.append(smart_tile(key))

        items.append(ft.Divider())
        items.append(ft.Container(
            ft.Text("LISTAS", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE_VARIANT),
            padding=ft.Padding.only(left=20, top=4, bottom=4)))

        for lst in self.c.lists():
            active = self.c.current_view == "list" and self.c.list_id == lst.id
            items.append(ft.ListTile(
                leading=ft.Icon(ft.Icons.CIRCLE, color=lst.color, size=14),
                title=ft.Text(lst.name, weight=ft.FontWeight.BOLD if active else ft.FontWeight.W_400),
                bgcolor=ft.Colors.with_opacity(0.08, ACCENT) if active else None,
                on_click=lambda e, lid=lst.id: self._go_list(lid),
                trailing=ft.IconButton(ft.Icons.MORE_VERT, icon_size=18,
                                       on_click=lambda e, l=lst: self._open_list_menu(l)),
            ))

        items.append(ft.ListTile(
            leading=ft.Icon(ft.Icons.ADD, color=ACCENT),
            title=ft.Text("Nova lista", color=ACCENT),
            on_click=lambda e: self._open_new_list(),
        ))
        self.drawer.controls = items

    async def _open_drawer(self, e) -> None:
        self._build_drawer()
        await self.page.show_drawer()

    async def _go_smart(self, key: str) -> None:
        self.c.set_view(key)
        await self.page.close_drawer()
        self._sync_chrome()
        self.refresh()

    async def _go_list(self, list_id: str) -> None:
        self.c.set_list_view(list_id)
        await self.page.close_drawer()
        self._sync_chrome()
        self.refresh()

    # --- navegação inferior ----------------------------------------------------
    def _on_nav(self, e) -> None:
        key = list(VIEWS)[e.control.selected_index]
        self.c.set_view(key)
        self._sync_chrome()
        self.refresh()

    def _sync_chrome(self) -> None:
        """Atualiza título, ações e seleção da barra inferior conforme a vista."""
        self.appbar.title.value = self.c.view_title()
        view = self.c.current_view
        # Ação 'limpar concluídos' só na vista Concluídos.
        actions = [ft.IconButton(ft.Icons.SEARCH, tooltip="Pesquisar", on_click=self._open_search)]
        if view == "completed":
            actions.append(ft.IconButton(ft.Icons.DELETE_SWEEP_OUTLINED,
                                         tooltip="Limpar concluídos",
                                         on_click=lambda e: self._clear_completed()))
        self.appbar.actions = actions
        # Esconder a barra de adição em Concluídos/Pesquisa.
        self.add_bar.visible = view not in ("completed", "search")
        if view in VIEWS:
            self.nav.selected_index = list(VIEWS).index(view)

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
        render_due_initial = _fmt_date(task.due_date) if task.due_date else "Sem data"
        due_text.value = render_due_initial

        list_dd = ft.Dropdown(
            label="Lista",
            value=task.list_id or "",
            options=[ft.DropdownOption(key="", text="Inbox")]
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
                list_id=(list_dd.value or None),
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
                    ft.Text("Data limite", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                    due_row,
                    list_dd,
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
                             on_submit=lambda ev: do_search())

        def do_search():
            q = field.value.strip()
            self.page.pop_dialog()
            if q:
                self.c.set_search(q)
                self._sync_chrome()
                self.refresh()

        self.page.show_dialog(ft.AlertDialog(
            title=ft.Text("Pesquisar"),
            content=field,
            actions=[
                ft.TextButton("Cancelar", on_click=lambda ev: self.page.pop_dialog()),
                ft.FilledButton("Pesquisar", on_click=lambda ev: do_search()),
            ],
        ))

    # --- listas ----------------------------------------------------------------
    def _open_new_list(self) -> None:
        field = ft.TextField(label="Nome da lista", autofocus=True,
                             on_submit=lambda e: create())

        def create():
            name = field.value.strip()
            if not name:
                return
            self.c.add_list(name)
            self.page.pop_dialog()
            self._build_drawer()
            self.page.update()

        self.page.show_dialog(ft.AlertDialog(
            title=ft.Text("Nova lista"),
            content=field,
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.page.pop_dialog()),
                ft.FilledButton("Criar", on_click=lambda e: create()),
            ],
        ))

    def _open_list_menu(self, lst) -> None:
        def rename():
            self.page.pop_dialog()
            field = ft.TextField(label="Nome", value=lst.name, autofocus=True,
                                 on_submit=lambda e: do_rename())

            def do_rename():
                if field.value.strip():
                    self.c.rename_list(lst.id, field.value)
                self.page.pop_dialog()
                self._refresh_after_list_change()

            self.page.show_dialog(ft.AlertDialog(
                title=ft.Text("Renomear lista"), content=field,
                actions=[ft.TextButton("Cancelar", on_click=lambda e: self.page.pop_dialog()),
                         ft.FilledButton("Guardar", on_click=lambda e: do_rename())],
            ))

        def delete():
            self.c.delete_list(lst.id, delete_tasks=False)
            self.page.pop_dialog()
            self._refresh_after_list_change()

        self.page.show_dialog(ft.AlertDialog(
            title=ft.Text(lst.name),
            content=ft.Text("As tarefas voltam para a Inbox se apagares a lista."),
            actions=[
                ft.TextButton("Renomear", on_click=lambda e: rename()),
                ft.TextButton("Apagar", style=ft.ButtonStyle(color=ft.Colors.RED_400),
                              on_click=lambda e: delete()),
                ft.TextButton("Fechar", on_click=lambda e: self.page.pop_dialog()),
            ],
        ))

    def _refresh_after_list_change(self) -> None:
        self._build_drawer()
        self._sync_chrome()
        self.refresh()

    def _clear_completed(self) -> None:
        n = self.c.clear_completed()
        self.refresh()
        self.page.show_dialog(ft.SnackBar(
            content=ft.Text(f"{n} tarefa(s) removida(s)" if n else "Nada para limpar"),
            behavior=ft.SnackBarBehavior.FLOATING,
        ))

    # --- render ----------------------------------------------------------------
    def _nav_destinations(self) -> list[ft.Control]:
        counts = self.c.counts()
        dests = []
        for key, label in VIEWS.items():
            n = counts.get(key, 0)
            icon = ft.Icon(VIEW_ICONS[key])
            if n and key != "completed":
                icon.badge = ft.Badge(label=str(n))
            dests.append(ft.NavigationBarDestination(icon=icon, label=label))
        return dests

    def refresh(self) -> None:
        today = self.c.today()
        view = self.c.current_view
        self.nav.destinations = self._nav_destinations()

        rows: list[ft.Control] = []

        def add_rows(tasks, *, with_list_label=True):
            for t in tasks:
                lbl = None
                if with_list_label and t.list_id is not None and view != "list":
                    lbl = self.c.list_name(t.list_id)
                rows.append(make_task_row(
                    t, today, on_toggle=self._on_toggle, on_open=self._open_detail,
                    on_delete=self._on_delete, list_label=lbl,
                ))

        if view == "today":
            atrasadas, hoje = self.c.overdue_in_today()
            if atrasadas:
                rows.append(_section_header(f"Atrasadas · {len(atrasadas)}", color=ft.Colors.RED_400))
                add_rows(atrasadas)
            if hoje:
                rows.append(_section_header("Hoje"))
                add_rows(hoje)
        elif view == "upcoming":
            from tickup.views import group_by_due_date
            tasks = self.c.visible_tasks()
            groups = group_by_due_date(tasks)
            for d in sorted(k for k in groups if k is not None):
                delta = (d - today).days
                if delta == 1:
                    head = "Amanhã"
                elif delta < 7:
                    head = f"{_PT_WEEKDAYS[d.weekday()].capitalize()}, {_fmt_date(d)}"
                else:
                    head = _fmt_date(d)
                rows.append(_section_header(head))
                add_rows(groups[d])
        else:
            add_rows(self.c.visible_tasks())

        self.list_view.controls = rows
        has_rows = bool(rows)
        if not has_rows:
            msg, icon = EMPTY_MESSAGES.get(view, ("Vazio", ft.Icons.INBOX))
            self.empty.content = ft.Column(
                [ft.Icon(icon, size=56, color=ft.Colors.OUTLINE),
                 ft.Text(msg, size=18, color=ft.Colors.ON_SURFACE_VARIANT)],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8,
            )
        self.empty.visible = not has_rows
        self.list_view.visible = has_rows
        self.page.update()

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
