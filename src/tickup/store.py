"""Armazenamento e operações CRUD do Tick Up.

`TaskStore` guarda listas e tarefas em memória e persiste em JSON num ficheiro
local. Esta escolha funciona offline (ideal para mobile, single-user) e mantém
a lógica testável sem precisar de uma base de dados.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .models import Priority, Task, TaskList


class TaskStore:
    """Guarda o estado da aplicação: listas e tarefas.

    A *Inbox* não é uma `TaskList` — é simplesmente `list_id is None`.
    """

    def __init__(self) -> None:
        self._lists: dict[str, TaskList] = {}
        self._tasks: dict[str, Task] = {}

    # --- listas ---------------------------------------------------------------
    def add_list(self, name: str, *, color: str | None = None) -> TaskList:
        order = self._next_list_order()
        lst = TaskList(name=name, order=order)
        if color:
            lst.color = color
        self._lists[lst.id] = lst
        return lst

    def get_list(self, list_id: str) -> TaskList | None:
        return self._lists.get(list_id)

    def lists(self) -> list[TaskList]:
        """Listas ordenadas pelo campo `order` e depois pelo nome."""
        return sorted(self._lists.values(), key=lambda l: (l.order, l.name.lower()))

    def rename_list(self, list_id: str, name: str) -> TaskList:
        lst = self._require_list(list_id)
        new_name = name.strip()
        if not new_name:
            raise ValueError("O nome da lista não pode estar vazio.")
        lst.name = new_name
        return lst

    def delete_list(self, list_id: str, *, delete_tasks: bool = False) -> None:
        """Apaga uma lista. Por defeito move as tarefas para a Inbox.

        Com `delete_tasks=True`, apaga também as tarefas dessa lista.
        """
        self._require_list(list_id)
        for task in list(self._tasks.values()):
            if task.list_id == list_id:
                if delete_tasks:
                    del self._tasks[task.id]
                else:
                    task.list_id = None  # volta para a Inbox
        del self._lists[list_id]

    # --- tarefas --------------------------------------------------------------
    def add_task(
        self,
        title: str,
        *,
        notes: str = "",
        due_date=None,
        priority: Priority = Priority.NONE,
        list_id: str | None = None,
    ) -> Task:
        if list_id is not None and list_id not in self._lists:
            raise KeyError(f"Lista inexistente: {list_id}")
        task = Task(
            title=title,
            notes=notes,
            due_date=due_date,
            priority=priority,
            list_id=list_id,
            order=self._next_task_order(list_id),
        )
        self._tasks[task.id] = task
        return task

    def get_task(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def tasks(self) -> list[Task]:
        """Todas as tarefas (ordem não garantida; usar `views` para ordenar)."""
        return list(self._tasks.values())

    def update_task(self, task_id: str, **changes) -> Task:
        """Atualiza campos de uma tarefa (title, notes, due_date, priority, list_id)."""
        task = self._require_task(task_id)
        allowed = {"title", "notes", "due_date", "priority", "list_id", "order"}
        unknown = set(changes) - allowed
        if unknown:
            raise ValueError(f"Campos desconhecidos: {sorted(unknown)}")
        if "list_id" in changes and changes["list_id"] is not None:
            if changes["list_id"] not in self._lists:
                raise KeyError(f"Lista inexistente: {changes['list_id']}")
        if "title" in changes:
            new_title = str(changes["title"]).strip()
            if not new_title:
                raise ValueError("O título da tarefa não pode estar vazio.")
            changes["title"] = new_title
        if "priority" in changes:
            changes["priority"] = Priority(int(changes["priority"]))
        for key, value in changes.items():
            setattr(task, key, value)
        return task

    def complete_task(self, task_id: str, *, when=None) -> Task:
        task = self._require_task(task_id)
        task.complete(when=when)
        return task

    def reopen_task(self, task_id: str) -> Task:
        task = self._require_task(task_id)
        task.reopen()
        return task

    def delete_task(self, task_id: str) -> None:
        self._require_task(task_id)
        del self._tasks[task_id]

    def clear_completed(self) -> int:
        """Remove todas as tarefas concluídas. Devolve quantas foram removidas."""
        done = [t.id for t in self._tasks.values() if t.completed]
        for task_id in done:
            del self._tasks[task_id]
        return len(done)

    # --- persistência ---------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "version": 1,
            "lists": [l.to_dict() for l in self.lists()],
            "tasks": [t.to_dict() for t in self._tasks.values()],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TaskStore":
        store = cls()
        for raw in data.get("lists", []):
            lst = TaskList.from_dict(raw)
            store._lists[lst.id] = lst
        for raw in data.get("tasks", []):
            task = Task.from_dict(raw)
            store._tasks[task.id] = task
        return store

    def save(self, path: str | Path) -> None:
        """Grava em JSON de forma atómica (escreve para tmp e renomeia)."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with open(fd, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
            Path(tmp).replace(path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    @classmethod
    def load(cls, path: str | Path) -> "TaskStore":
        """Carrega de JSON. Se o ficheiro não existir, devolve um store vazio."""
        path = Path(path)
        if not path.exists():
            return cls()
        with open(path, encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    # --- helpers internos -----------------------------------------------------
    def _require_list(self, list_id: str) -> TaskList:
        lst = self._lists.get(list_id)
        if lst is None:
            raise KeyError(f"Lista inexistente: {list_id}")
        return lst

    def _require_task(self, task_id: str) -> Task:
        task = self._tasks.get(task_id)
        if task is None:
            raise KeyError(f"Tarefa inexistente: {task_id}")
        return task

    def _next_list_order(self) -> int:
        return (max((l.order for l in self._lists.values()), default=-1)) + 1

    def _next_task_order(self, list_id: str | None) -> int:
        same = [t.order for t in self._tasks.values() if t.list_id == list_id]
        return (max(same, default=-1)) + 1
