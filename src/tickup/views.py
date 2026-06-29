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

# Sentinela para "todos os grupos" nas vistas de board/calendário. Distingue-se
# de `None` (que significa "sem grupo") e de um `list_id` concreto.
ALL_GROUPS = object()


def _active(tasks: Iterable[Task]) -> list[Task]:
    return [t for t in tasks if not t.completed]


def _in_group(task: Task, list_id) -> bool:
    """True se a tarefa pertence ao filtro de grupo pedido.

    `list_id` pode ser `ALL_GROUPS` (qualquer grupo), `None` (sem grupo) ou um id.
    """
    return list_id is ALL_GROUPS or task.list_id == list_id


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


def board_sort_key(task: Task):
    """Ordena o board por data limite (cedo primeiro, sem data por último),
    depois prioridade, ordem manual e data de criação."""
    return (
        task.due_date or date.max,
        int(task.priority),
        task.order,
        task.created_at,
    )


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


def board(tasks: Iterable[Task], *, list_id=ALL_GROUPS) -> list[Task]:
    """Todas as tarefas ativas (por fazer) para o board principal.

    Mostra com e sem data, ordenadas por data (sem data por último). `list_id`
    filtra por grupo: `ALL_GROUPS` = todos, `None` = sem grupo, id = esse grupo.
    """
    return sorted(
        (t for t in _active(tasks) if _in_group(t, list_id)),
        key=board_sort_key,
    )


def completed_on(tasks: Iterable[Task], day: date, *, list_id=ALL_GROUPS) -> list[Task]:
    """Tarefas concluídas nesse dia (hora local), da mais recente para a mais antiga."""
    done = [
        t
        for t in tasks
        if t.completed and t.completed_date() == day and _in_group(t, list_id)
    ]
    return sorted(done, key=lambda t: t.completed_at or t.created_at, reverse=True)


def completed_by_day(
    tasks: Iterable[Task], year: int, month: int, *, list_id=ALL_GROUPS
) -> dict[date, list[Task]]:
    """Concluídas de um mês agrupadas pelo dia (local) em que foram feitas.

    Alimenta os indicadores e o detalhe do calendário. Cada lista vem ordenada
    da conclusão mais recente para a mais antiga.
    """
    groups: dict[date, list[Task]] = defaultdict(list)
    for task in tasks:
        if not task.completed or not _in_group(task, list_id):
            continue
        cd = task.completed_date()
        if cd is not None and cd.year == year and cd.month == month:
            groups[cd].append(task)
    return {
        day: sorted(items, key=lambda t: t.completed_at or t.created_at, reverse=True)
        for day, items in groups.items()
    }


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
