"""Controlador da aplicação — a ponte entre o núcleo e a UI.

Não importa Flet: contém apenas estado e lógica de apresentação, por isso é
testável sem interface gráfica. A UI (`main.py`) cria um `AppController`, lê
`visible_tasks()`/`completed_today()`/`calendar_days()` e chama os métodos de
mutação (que persistem automaticamente).

Modelo (v0.3.0): dois ecrãs apenas —
  • **Board** (`current_view == "board"`): todas as tarefas por fazer + as feitas
    hoje, opcionalmente filtradas por grupo (`group_filter`).
  • **Calendário** (`current_view == "calendar"`): histórico das concluídas por dia.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from tickup import views
from tickup.models import Priority, Task, TaskList
from tickup.store import TaskStore

# Sentinela "todos os grupos" para o filtro do board (ver tickup.views.ALL_GROUPS).
ALL_GROUPS = views.ALL_GROUPS

# Sentinela para distinguir "não passou data" de "passou data = None".
_UNSET = object()

# Os dois ecrãs da app.
VIEWS = ("board", "calendar")


class AppController:
    def __init__(self, data_path: str | Path, *, today_provider=date.today) -> None:
        self.data_path = Path(data_path)
        self._today_provider = today_provider
        self.store = TaskStore.load(self.data_path)
        self.current_view = "board"
        # Filtro de grupo do board: ALL_GROUPS | None (sem grupo) | list_id.
        self.group_filter = ALL_GROUPS
        self.query: str = ""  # pesquisa não-intrusiva no board
        self._last_deleted: Task | None = None
        # Mês visível no calendário (default: mês de hoje).
        ref = self.today()
        self.calendar_year = ref.year
        self.calendar_month = ref.month

    # --- consulta -------------------------------------------------------------
    def today(self) -> date:
        return self._today_provider()

    def visible_tasks(self) -> list[Task]:
        """Tarefas por fazer do board (filtradas por grupo e, se houver, pesquisa)."""
        tasks = views.board(self.store.tasks(), list_id=self.group_filter)
        q = self.query.strip().lower()
        if q:
            tasks = [t for t in tasks if q in t.title.lower() or q in t.notes.lower()]
        return tasks

    def completed_today(self) -> list[Task]:
        """Concluídas hoje (secção 'Feitas hoje' do board). Saem ao virar o dia."""
        return views.completed_on(
            self.store.tasks(), self.today(), list_id=self.group_filter
        )

    def calendar_days(self) -> dict[date, list[Task]]:
        """Concluídas do mês visível, agrupadas por dia (para o calendário)."""
        return views.completed_by_day(
            self.store.tasks(),
            self.calendar_year,
            self.calendar_month,
            list_id=self.group_filter,
        )

    def completed_on(self, day: date) -> list[Task]:
        """Concluídas num dia específico (detalhe ao tocar no calendário)."""
        return views.completed_on(self.store.tasks(), day, list_id=self.group_filter)

    def view_title(self) -> str:
        return "Tarefas" if self.current_view == "board" else "Calendário"

    def is_empty(self) -> bool:
        return not self.visible_tasks() and not self.completed_today()

    def get(self, task_id: str) -> Task | None:
        return self.store.get_task(task_id)

    def lists(self) -> list[TaskList]:
        return self.store.lists()

    def list_name(self, list_id: str | None) -> str:
        if list_id is None:
            return "Sem grupo"
        lst = self.store.get_list(list_id)
        return lst.name if lst else "Sem grupo"

    def active_group(self) -> TaskList | None:
        """Grupo selecionado no filtro, ou None (Todos / Sem grupo)."""
        if self.group_filter is ALL_GROUPS or self.group_filter is None:
            return None
        return self.store.get_list(self.group_filter)

    # --- navegação ------------------------------------------------------------
    def set_board(self) -> None:
        self.current_view = "board"

    def set_calendar(self) -> None:
        self.current_view = "calendar"

    def set_view(self, view: str) -> None:
        if view not in VIEWS:
            raise ValueError(f"Vista desconhecida: {view}")
        self.current_view = view

    def set_group(self, value) -> None:
        """Filtra o board por grupo: ALL_GROUPS, None (sem grupo) ou um list_id."""
        if value is not ALL_GROUPS and value is not None:
            self.store._require_list(value)  # valida; KeyError se não existir
        self.group_filter = value

    def set_search(self, query: str) -> None:
        self.query = query

    def clear_search(self) -> None:
        self.query = ""

    def calendar_prev_month(self) -> None:
        y, m = self.calendar_year, self.calendar_month
        self.calendar_year, self.calendar_month = (y - 1, 12) if m == 1 else (y, m - 1)

    def calendar_next_month(self) -> None:
        y, m = self.calendar_year, self.calendar_month
        self.calendar_year, self.calendar_month = (y + 1, 1) if m == 12 else (y, m + 1)

    # --- mutação de tarefas (persistem sempre) --------------------------------
    def add_quick(
        self,
        title: str,
        *,
        priority: Priority = Priority.NONE,
        due_date=_UNSET,
    ) -> Task | None:
        """Adiciona uma tarefa rápida. Devolve None se o título for vazio.

        A data é **opcional** (sem data por defeito). Se o board estiver filtrado
        por um grupo concreto, a tarefa é criada nesse grupo; caso contrário, sem
        grupo.
        """
        title = title.strip()
        if not title:
            return None
        due = None if due_date is _UNSET else due_date
        list_id = (
            self.group_filter
            if self.group_filter is not ALL_GROUPS and self.group_filter is not None
            else None
        )
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
        """Remove definitivamente as concluídas (não exposto na UI; apaga histórico)."""
        removed = self.store.clear_completed()
        if removed:
            self._persist()
        return removed

    # --- mutação de grupos ----------------------------------------------------
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
        # Se estávamos a filtrar por esse grupo, volta a "Todos".
        if self.group_filter == list_id:
            self.group_filter = ALL_GROUPS
        self._persist()

    # --- interno --------------------------------------------------------------
    def _persist(self) -> None:
        self.store.save(self.data_path)
