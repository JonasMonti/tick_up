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
from tickup.models import Priority, Task, TaskList
from tickup.store import TaskStore

# Vistas inteligentes (chave interna -> rótulo em pt-PT).
SMART_VIEWS = {
    "today": "Hoje",
    "upcoming": "Próximos",
    "overdue": "Atrasadas",
    "inbox": "Inbox",
    "completed": "Concluídos",
}

# Subconjunto mostrado na barra de navegação inferior (as restantes vistas e as
# listas do utilizador são acedidas pelo menu lateral).
VIEWS = {key: SMART_VIEWS[key] for key in ("today", "upcoming", "inbox", "completed")}

# Sentinela para distinguir "não passou data" de "passou data = None".
_UNSET = object()


class AppController:
    def __init__(self, data_path: str | Path, *, today_provider=date.today) -> None:
        self.data_path = Path(data_path)
        self._today_provider = today_provider
        self.store = TaskStore.load(self.data_path)
        self.current_view = "today"
        self.list_id: str | None = None  # lista ativa quando current_view == "list"
        self.query: str = ""             # termo ativo quando current_view == "search"
        self._last_deleted: Task | None = None

    # --- consulta -------------------------------------------------------------
    def today(self) -> date:
        return self._today_provider()

    def visible_tasks(self) -> list[Task]:
        tasks = self.store.tasks()
        ref = self.today()
        view = self.current_view
        if view == "today":
            return views.today(tasks, ref)
        if view == "upcoming":
            return views.upcoming(tasks, ref)
        if view == "overdue":
            return views.overdue(tasks, ref)
        if view == "inbox":
            return views.inbox(tasks)
        if view == "completed":
            return views.completed(tasks)
        if view == "list":
            return views.by_list(tasks, self.list_id)
        if view == "search":
            return views.search(tasks, self.query)
        raise ValueError(f"Vista desconhecida: {view}")

    def overdue_in_today(self) -> tuple[list[Task], list[Task]]:
        """Divide a vista 'Hoje' em (atrasadas, mesmo-dia) para mostrar secções."""
        ref = self.today()
        atrasadas = [t for t in self.visible_tasks() if t.due_date and t.due_date < ref]
        hoje = [t for t in self.visible_tasks() if t.due_date == ref]
        return atrasadas, hoje

    def counts(self) -> dict[str, int]:
        return views.counts(self.store.tasks(), self.today())

    def view_title(self) -> str:
        if self.current_view == "list":
            lst = self.store.get_list(self.list_id) if self.list_id else None
            return lst.name if lst else "Lista"
        if self.current_view == "search":
            return f"“{self.query}”" if self.query else "Pesquisa"
        return SMART_VIEWS[self.current_view]

    def is_empty(self) -> bool:
        return not self.visible_tasks()

    def get(self, task_id: str) -> Task | None:
        return self.store.get_task(task_id)

    def lists(self) -> list[TaskList]:
        return self.store.lists()

    def list_name(self, list_id: str | None) -> str:
        if list_id is None:
            return "Inbox"
        lst = self.store.get_list(list_id)
        return lst.name if lst else "Inbox"

    # --- navegação ------------------------------------------------------------
    def set_view(self, view: str) -> None:
        if view not in SMART_VIEWS:
            raise ValueError(f"Vista desconhecida: {view}")
        self.current_view = view
        self.list_id = None
        self.query = ""

    def set_list_view(self, list_id: str) -> None:
        self.store._require_list(list_id)  # valida; levanta KeyError se não existir
        self.current_view = "list"
        self.list_id = list_id
        self.query = ""

    def set_search(self, query: str) -> None:
        self.current_view = "search"
        self.query = query
        self.list_id = None

    # --- mutação de tarefas (persistem sempre) --------------------------------
    def add_quick(
        self,
        title: str,
        *,
        priority: Priority = Priority.NONE,
        due_date=_UNSET,
    ) -> Task | None:
        """Adiciona uma tarefa rápida. Devolve None se o título for vazio.

        Sem data explícita: na vista 'Hoje' a tarefa fica com data limite = hoje
        (como em 'O Meu Dia' do Microsoft To Do); nas outras, sem data. Numa
        vista de lista, a tarefa é criada nessa lista.
        """
        title = title.strip()
        if not title:
            return None
        if due_date is _UNSET:
            due = self.today() if self.current_view == "today" else None
        else:
            due = due_date
        list_id = self.list_id if self.current_view == "list" else None
        task = self.store.add_task(
            title, due_date=due, priority=priority, list_id=list_id
        )
        self._persist()
        return task

    def update(self, task_id: str, **changes) -> Task:
        """Atualiza campos de uma tarefa (title, notes, due_date, priority, list_id)."""
        task = self.store.update_task(task_id, **changes)
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
        task = self.store.get_task(task_id)
        if task is not None:
            self._last_deleted = task
            self.store.delete_task(task_id)
            self._persist()

    def undo_delete(self) -> Task | None:
        """Repõe a última tarefa apagada (suporta o 'Anular'). Devolve-a ou None."""
        if self._last_deleted is None:
            return None
        task = self.store.restore_task(self._last_deleted)
        self._last_deleted = None
        self._persist()
        return task

    def clear_completed(self) -> int:
        removed = self.store.clear_completed()
        if removed:
            self._persist()
        return removed

    # --- mutação de listas ----------------------------------------------------
    def add_list(self, name: str, *, color: str | None = None) -> TaskList:
        lst = self.store.add_list(name, color=color)
        self._persist()
        return lst

    def rename_list(self, list_id: str, name: str) -> TaskList:
        lst = self.store.rename_list(list_id, name)
        self._persist()
        return lst

    def delete_list(self, list_id: str, *, delete_tasks: bool = False) -> None:
        self.store.delete_list(list_id, delete_tasks=delete_tasks)
        # Se estávamos a ver essa lista, volta para a Inbox.
        if self.current_view == "list" and self.list_id == list_id:
            self.set_view("inbox")
        self._persist()

    # --- interno --------------------------------------------------------------
    def _persist(self) -> None:
        self.store.save(self.data_path)
