"""Testes do AppController (lógica de UI, sem Flet)."""
from datetime import date

import pytest

from app.controller import AppController
from tickup.models import Priority

TODAY = date(2026, 6, 27)


@pytest.fixture
def ctrl(tmp_path):
    return AppController(tmp_path / "tickup.json", today_provider=lambda: TODAY)


def test_starts_on_today_view(ctrl):
    assert ctrl.current_view == "today"
    assert ctrl.view_title() == "Hoje"


def test_add_in_today_view_sets_due_today(ctrl):
    task = ctrl.add_quick("Comprar pão")
    assert task is not None
    assert task.due_date == TODAY
    assert task in ctrl.visible_tasks()


def test_add_in_inbox_has_no_due_date(ctrl):
    ctrl.set_view("inbox")
    task = ctrl.add_quick("Ideia solta")
    assert task.due_date is None


def test_add_empty_returns_none(ctrl):
    assert ctrl.add_quick("   ") is None


def test_toggle_completes_and_reopens(ctrl):
    task = ctrl.add_quick("X")
    ctrl.toggle(task.id)
    assert ctrl.store.get_task(task.id).completed is True
    ctrl.toggle(task.id)
    assert ctrl.store.get_task(task.id).completed is False


def test_completed_view_shows_done_tasks(ctrl):
    task = ctrl.add_quick("X")
    ctrl.toggle(task.id)
    ctrl.set_view("completed")
    assert task in ctrl.visible_tasks()


def test_delete_removes_task(ctrl):
    task = ctrl.add_quick("X")
    ctrl.delete(task.id)
    assert ctrl.store.get_task(task.id) is None


def test_changes_are_persisted(tmp_path):
    path = tmp_path / "tickup.json"
    c1 = AppController(path, today_provider=lambda: TODAY)
    c1.add_quick("Persistir isto")
    # Uma nova instância lê do disco o que a primeira gravou.
    c2 = AppController(path, today_provider=lambda: TODAY)
    assert any(t.title == "Persistir isto" for t in c2.store.tasks())


def test_set_invalid_view_raises(ctrl):
    with pytest.raises(ValueError):
        ctrl.set_view("nao-existe")


def test_counts_reflect_state(ctrl):
    ctrl.add_quick("hoje")  # due = TODAY
    ctrl.set_view("inbox")
    ctrl.add_quick("inbox", priority=Priority.HIGH)
    counts = ctrl.counts()
    assert counts["today"] == 1
    # Ambas estão sem lista, por isso ambas contam para a Inbox (semântica Todoist).
    assert counts["inbox"] == 2


def test_clear_completed(ctrl):
    a = ctrl.add_quick("a")
    ctrl.add_quick("b")
    ctrl.toggle(a.id)
    assert ctrl.clear_completed() == 1
