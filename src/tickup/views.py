"""Vistas inteligentes sobre uma coleção de tarefas.

Funções puras (sem estado, sem I/O) que filtram, ordenam e agrupam tarefas para
alimentar a interface. Os nomes seguem as vistas conhecidas das apps populares:
Inbox, Hoje, Próximos, Atrasados, Concluídos.

Todas recebem o "hoje" como argumento (`today: date`) em vez de o calcular,
para que os testes sejam deterministas.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Iterable

from .models import Task


def _active(tasks: Iterable[Task]) -> list[Task]:
    return [t for t in tasks if not t.completed]


def sort_key(task: Task):
    """Ordena por: prioridade (P1 primeiro), depois data limite (cedo primeiro,
    sem data por último), depois ordem manual e por fim data de criação."""
    return (
        int(task.priority),
        task.due_date or date.max,
        task.order,
        task.created_at,
    )


def sorted_tasks(tasks: Iterable[Task]) -> list[Task]:
    return sorted(tasks, key=sort_key)


# --- vistas -------------------------------------------------------------------
def inbox(tasks: Iterable[Task]) -> list[Task]:
    """Tarefas ativas sem lista atribuída."""
    return sorted_tasks(t for t in _active(tasks) if t.list_id is None)


def today(tasks: Iterable[Task], ref: date) -> list[Task]:
    """Tarefas para hoje: vencidas (atrasadas) + as que vencem hoje.

    É a vista central das apps populares ('O Meu Dia', 'Today').
    `ref` é a data de referência ("hoje").
    """
    return sorted_tasks(
        t for t in _active(tasks) if t.due_date is not None and t.due_date <= ref
    )


def overdue(tasks: Iterable[Task], ref: date) -> list[Task]:
    """Tarefas ativas com data limite no passado."""
    return sorted_tasks(t for t in _active(tasks) if t.is_overdue(ref))


def upcoming(tasks: Iterable[Task], ref: date, *, days: int = 7) -> list[Task]:
    """Tarefas que vencem entre amanhã e `days` dias à frente (inclusive)."""
    horizon = ref + timedelta(days=days)
    return sorted_tasks(
        t
        for t in _active(tasks)
        if t.due_date is not None and ref < t.due_date <= horizon
    )


def by_list(tasks: Iterable[Task], list_id: str | None) -> list[Task]:
    """Tarefas ativas de uma lista (ou da Inbox se `list_id is None`)."""
    return sorted_tasks(t for t in _active(tasks) if t.list_id == list_id)


def completed(tasks: Iterable[Task]) -> list[Task]:
    """Tarefas concluídas, da mais recente para a mais antiga."""
    done = [t for t in tasks if t.completed]
    return sorted(done, key=lambda t: t.completed_at or t.created_at, reverse=True)


def search(tasks: Iterable[Task], query: str) -> list[Task]:
    """Procura (case-insensitive) no título e nas notas das tarefas ativas."""
    q = query.strip().lower()
    if not q:
        return []
    return sorted_tasks(
        t for t in _active(tasks) if q in t.title.lower() or q in t.notes.lower()
    )


# --- agrupamento ---------------------------------------------------------------
def group_by_due_date(tasks: Iterable[Task]) -> dict[date | None, list[Task]]:
    """Agrupa tarefas pela data limite (à la Things 3). `None` = sem data."""
    groups: dict[date | None, list[Task]] = defaultdict(list)
    for task in tasks:
        groups[task.due_date].append(task)
    return {key: sorted_tasks(value) for key, value in groups.items()}


def counts(tasks: Iterable[Task], ref: date) -> dict[str, int]:
    """Contagens para os 'badges' das vistas na barra lateral."""
    tasks = list(tasks)
    return {
        "inbox": len(inbox(tasks)),
        "today": len(today(tasks, ref)),
        "overdue": len(overdue(tasks, ref)),
        "upcoming": len(upcoming(tasks, ref)),
        "completed": len(completed(tasks)),
    }
