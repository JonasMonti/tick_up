"""Testes dos modelos de domínio (Task, TaskList, Priority)."""
from datetime import date, datetime, timezone

import pytest

from tickup.models import Priority, Task, TaskList


# --- Task: validação e normalização -------------------------------------------
def test_task_strips_title():
    assert Task(title="  Comprar pão  ").title == "Comprar pão"


def test_task_empty_title_raises():
    with pytest.raises(ValueError):
        Task(title="   ")


def test_task_defaults():
    t = Task(title="X")
    assert t.priority is Priority.NONE
    assert t.completed is False
    assert t.completed_at is None
    assert t.due_date is None
    assert t.list_id is None
    assert t.id  # gera um id único
    assert t.created_at.tzinfo is not None


def test_task_ids_are_unique():
    assert Task(title="A").id != Task(title="B").id


def test_priority_accepts_int():
    t = Task(title="X", priority=1)
    assert t.priority is Priority.URGENT


# --- Task: transições de estado -----------------------------------------------
def test_complete_sets_flag_and_timestamp():
    t = Task(title="X")
    when = datetime(2026, 6, 27, 10, 0, tzinfo=timezone.utc)
    t.complete(when=when)
    assert t.completed is True
    assert t.completed_at == when


def test_complete_is_idempotent():
    t = Task(title="X")
    first = datetime(2026, 6, 27, tzinfo=timezone.utc)
    t.complete(when=first)
    t.complete(when=datetime(2026, 6, 28, tzinfo=timezone.utc))
    assert t.completed_at == first  # não sobrescreve


def test_reopen_clears_state():
    t = Task(title="X")
    t.complete()
    t.reopen()
    assert t.completed is False
    assert t.completed_at is None


# --- Task: datas --------------------------------------------------------------
def test_is_overdue_true_for_past_due():
    t = Task(title="X", due_date=date(2026, 6, 20))
    assert t.is_overdue(date(2026, 6, 27)) is True


def test_is_overdue_false_when_completed():
    t = Task(title="X", due_date=date(2026, 6, 20))
    t.complete()
    assert t.is_overdue(date(2026, 6, 27)) is False


def test_is_overdue_false_without_due_date():
    assert Task(title="X").is_overdue(date(2026, 6, 27)) is False


def test_is_due_today():
    t = Task(title="X", due_date=date(2026, 6, 27))
    assert t.is_due_today(date(2026, 6, 27)) is True
    assert t.is_due_today(date(2026, 6, 28)) is False


# --- Task: serialização (round-trip) ------------------------------------------
def test_task_roundtrip():
    original = Task(
        title="Pagar renda",
        notes="via MB Way",
        due_date=date(2026, 7, 1),
        priority=Priority.URGENT,
        list_id="abc",
    )
    original.complete(when=datetime(2026, 6, 27, 9, 0, tzinfo=timezone.utc))
    restored = Task.from_dict(original.to_dict())
    assert restored == original


def test_task_roundtrip_minimal():
    original = Task(title="X")
    assert Task.from_dict(original.to_dict()) == original


# --- TaskList -----------------------------------------------------------------
def test_tasklist_validation_and_roundtrip():
    lst = TaskList(name="  Trabalho  ", color="#ff0000", order=2)
    assert lst.name == "Trabalho"
    assert TaskList.from_dict(lst.to_dict()) == lst


def test_tasklist_empty_name_raises():
    with pytest.raises(ValueError):
        TaskList(name="  ")


# --- Priority -----------------------------------------------------------------
def test_priority_labels():
    assert Priority.URGENT.label == "Urgente"
    assert Priority.NONE.label == "Sem prioridade"
