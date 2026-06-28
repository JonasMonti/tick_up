"""Tick Up — interface Flet (mobile-first; corre também na web e desktop).

Layout inspirado nas apps populares:
  • barra de navegação inferior: Hoje / Próximos / Inbox / Concluídos
  • lista de tarefas com checkbox (tocar = concluir) e swipe para apagar
  • campo de adição rápida fixo em baixo (estilo Microsoft To Do)

Toda a lógica vive no núcleo (`tickup`) via `AppController`. Aqui só há widgets.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Permite `flet run app/main.py` encontrar o pacote `tickup` em ../src.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import flet as ft

from app.controller import VIEWS, AppController
from tickup.models import Priority, Task

ACCENT = ft.Colors.INDIGO

# Ícone de cada vista na barra inferior.
VIEW_ICONS = {
    "today": ft.Icons.TODAY,
    "upcoming": ft.Icons.UPCOMING,
    "inbox": ft.Icons.INBOX,
    "completed": ft.Icons.CHECK_CIRCLE_OUTLINE,
}

# Cor da bolinha de prioridade (P1–P3 destacam-se; P4 é neutra).
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


def _data_path() -> Path:
    """Onde guardar os dados. No mobile, Flet define FLET_APP_STORAGE_DATA."""
    base = os.environ.get("FLET_APP_STORAGE_DATA")
    if base:
        return Path(base) / "tickup.json"
    return Path(__file__).resolve().parent.parent / "storage" / "tickup.json"


def _due_label(task: Task, today) -> tuple[str, str] | None:
    """Devolve (texto, cor) para a etiqueta de data, ou None se não houver data."""
    if task.due_date is None:
        return None
    if task.due_date < today:
        return ("Atrasada", ft.Colors.RED_400)
    if task.due_date == today:
        return ("Hoje", ACCENT)
    delta = (task.due_date - today).days
    if delta == 1:
        return ("Amanhã", ft.Colors.ON_SURFACE_VARIANT)
    text = f"{task.due_date.day} {_PT_MONTHS[task.due_date.month - 1]}"
    return (text, ft.Colors.ON_SURFACE_VARIANT)


def make_task_row(task: Task, today, *, on_toggle, on_delete) -> ft.Control:
    """Constrói a linha de uma tarefa (checkbox + título + etiqueta de data).

    Função separada para ser fácil de testar a construção dos widgets.
    """
    done = task.completed
    title = ft.Text(
        task.title,
        size=16,
        weight=ft.FontWeight.W_400,
        color=ft.Colors.ON_SURFACE_VARIANT if done else None,
        # tachado quando concluída
        style=ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH) if done else None,
        expand=True,
    )

    row_items = [
        ft.Icon(
            ft.Icons.CHECK_CIRCLE if done else ft.Icons.RADIO_BUTTON_UNCHECKED,
            color=ACCENT if done else PRIORITY_COLOR[task.priority],
        ),
        title,
    ]

    label = _due_label(task, today)
    if label and not done:
        text, color = label
        row_items.append(
            ft.Container(
                ft.Text(text, size=12, color=color),
                padding=ft.Padding.symmetric(horizontal=8, vertical=2),
            )
        )

    content = ft.Container(
        ft.Row(row_items, spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.Padding.symmetric(horizontal=16, vertical=14),
        on_click=lambda e: on_toggle(task.id),
        ink=True,
    )

    # Swipe da direita para a esquerda apaga a tarefa.
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
        ),
        data=task.id,
    )


class TickUpApp:
    def __init__(self, page: ft.Page, controller: AppController) -> None:
        self.page = page
        self.c = controller
        self.list_view = ft.ListView(expand=True, spacing=2, padding=ft.Padding.only(top=4))
        self.empty = ft.Container(
            ft.Column(
                [
                    ft.Icon(ft.Icons.TASK_ALT, size=56, color=ft.Colors.OUTLINE),
                    ft.Text("Tudo em dia!", size=18, color=ft.Colors.ON_SURFACE_VARIANT),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
            alignment=ft.Alignment.CENTER,
            expand=True,
            visible=False,
        )
        self.add_field = ft.TextField(
            hint_text="Adicionar tarefa…",
            border=ft.InputBorder.NONE,
            expand=True,
            on_submit=self._on_add,
            text_size=16,
        )

    # --- construção do ecrã ---------------------------------------------------
    def build(self) -> None:
        page = self.page
        page.title = "Tick Up"
        page.theme = ft.Theme(color_scheme_seed=ACCENT)
        page.theme_mode = ft.ThemeMode.SYSTEM
        page.padding = 0

        page.appbar = ft.AppBar(
            title=ft.Text(self.c.view_title(), weight=ft.FontWeight.BOLD),
            center_title=False,
            bgcolor=ft.Colors.SURFACE,
        )

        page.navigation_bar = ft.NavigationBar(
            selected_index=list(VIEWS).index(self.c.current_view),
            on_change=self._on_nav,
            destinations=[
                ft.NavigationBarDestination(icon=VIEW_ICONS[key], label=label)
                for key, label in VIEWS.items()
            ],
        )

        add_bar = ft.Container(
            ft.Row(
                [
                    ft.Icon(ft.Icons.ADD, color=ACCENT),
                    self.add_field,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            padding=ft.Padding.symmetric(horizontal=16, vertical=4),
        )

        page.add(
            ft.SafeArea(
                ft.Column(
                    [
                        ft.Stack([self.list_view, self.empty], expand=True),
                        add_bar,
                    ],
                    expand=True,
                    spacing=0,
                ),
                expand=True,
            )
        )
        self.refresh()

    # --- eventos ---------------------------------------------------------------
    def _on_nav(self, e) -> None:
        key = list(VIEWS)[e.control.selected_index]
        self.c.set_view(key)
        self.page.appbar.title.value = self.c.view_title()
        # Esconder o campo de adição na vista de concluídos.
        self.add_field.disabled = key == "completed"
        self.refresh()

    def _on_add(self, e) -> None:
        if self.c.add_quick(self.add_field.value):
            self.add_field.value = ""
            self.add_field.focus()
            self.refresh()

    def _on_toggle(self, task_id: str) -> None:
        self.c.toggle(task_id)
        self.refresh()

    def _on_delete(self, task_id: str) -> None:
        self.c.delete(task_id)
        self.refresh()

    # --- render ----------------------------------------------------------------
    def refresh(self) -> None:
        today = self.c.today()
        tasks = self.c.visible_tasks()
        self.list_view.controls = [
            make_task_row(t, today, on_toggle=self._on_toggle, on_delete=self._on_delete)
            for t in tasks
        ]
        self.empty.visible = not tasks
        self.list_view.visible = bool(tasks)
        self.page.update()


def main(page: ft.Page) -> None:
    controller = AppController(_data_path())
    TickUpApp(page, controller).build()


if __name__ == "__main__":
    ft.app(main)
