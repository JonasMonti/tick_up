"""Controlador da aplicação — a ponte entre o núcleo e a UI.

Não importa Flet: contém apenas estado e lógica de apresentação, por isso é
testável sem interface gráfica. A UI (`main.py`) cria um `AppController`, lê
`visible_tasks()`/`counts()` e chama os métodos de mutação (que persistem
automaticamente).
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from tickup import views
from tickup.models import Priority, Task
from tickup.store import TaskStore

# Vistas disponíveis na navegação (chave interna -> rótulo em pt-PT).
VIEWS = {
    "today": "Hoje",
    "upcoming": "Próximos",
    "inbox": "Inbox",
    "completed": "Concluídos",
}


class AppController:
    def __init__(self, data_path: str | Path, *, today_provider=date.today) -> None:
        self.data_path = Path(data_path)
        self._today_provider = today_provider
        self.store = TaskStore.load(self.data_path)
        self.current_view = "today"

    # --- consulta -------------------------------------------------------------
    def today(self) -> date:
        return self._today_provider()

    def visible_tasks(self) -> list[Task]:
        tasks = self.store.tasks()
        ref = self.today()
        if self.current_view == "today":
            return views.today(tasks, ref)
        if self.current_view == "upcoming":
            return views.upcoming(tasks, ref)
        if self.current_view == "inbox":
            return views.inbox(tasks)
        if self.current_view == "completed":
            return views.completed(tasks)
        raise ValueError(f"Vista desconhecida: {self.current_view}")

    def counts(self) -> dict[str, int]:
        return views.counts(self.store.tasks(), self.today())

    def view_title(self) -> str:
        return VIEWS[self.current_view]

    def is_empty(self) -> bool:
        return not self.visible_tasks()

    # --- mutação (persistem sempre) ------------------------------------------
    def set_view(self, view: str) -> None:
        if view not in VIEWS:
            raise ValueError(f"Vista desconhecida: {view}")
        self.current_view = view

    def add_quick(self, title: str, *, priority: Priority = Priority.NONE) -> Task | None:
        """Adiciona uma tarefa rápida. Devolve None se o título for vazio.

        Na vista 'Hoje', a nova tarefa fica com data limite = hoje (como em
        'O Meu Dia' do Microsoft To Do).
        """
        title = title.strip()
        if not title:
            return None
        due = self.today() if self.current_view == "today" else None
        task = self.store.add_task(title, due_date=due, priority=priority)
        self._persist()
        return task

    def toggle(self, task_id: str) -> None:
        task = self.store.get_task(task_id)
        if task is None:
            return
        if task.completed:
            self.store.reopen_task(task_id)
        else:
            self.store.complete_task(task_id)
        self._persist()

    def delete(self, task_id: str) -> None:
        if self.store.get_task(task_id) is not None:
            self.store.delete_task(task_id)
            self._persist()

    def clear_completed(self) -> int:
        removed = self.store.clear_completed()
        if removed:
            self._persist()
        return removed

    # --- interno --------------------------------------------------------------
    def _persist(self) -> None:
        self.store.save(self.data_path)
