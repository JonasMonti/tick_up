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


# --- vistas adicionais --------------------------------------------------------
def test_overdue_view(ctrl):
    ctrl.set_view("inbox")
    t = ctrl.add_quick("velha", due_date=date(2026, 6, 1))  # antes de TODAY
    ctrl.set_view("overdue")
    assert t in ctrl.visible_tasks()


def test_overdue_in_today_splits_sections(ctrl):
    late = ctrl.add_quick("atrasada", due_date=date(2026, 6, 1))
    hoje = ctrl.add_quick("hoje")  # due = TODAY na vista Hoje
    atrasadas, today_tasks = ctrl.overdue_in_today()
    assert late in atrasadas and hoje in today_tasks


# --- listas / vista de lista --------------------------------------------------
def test_list_view_filters_and_add_assigns_list(ctrl):
    lst = ctrl.add_list("Trabalho")
    ctrl.set_list_view(lst.id)
    assert ctrl.current_view == "list" and ctrl.view_title() == "Trabalho"
    t = ctrl.add_quick("reunião")
    assert t.list_id == lst.id
    assert t in ctrl.visible_tasks()


def test_delete_list_resets_view_to_inbox(ctrl):
    lst = ctrl.add_list("Temp")
    ctrl.set_list_view(lst.id)
    ctrl.delete_list(lst.id)
    assert ctrl.current_view == "inbox"


def test_set_view_clears_list_and_query(ctrl):
    lst = ctrl.add_list("L")
    ctrl.set_list_view(lst.id)
    ctrl.set_view("today")
    assert ctrl.list_id is None and ctrl.query == ""


# --- edição -------------------------------------------------------------------
def test_update_changes_and_persists(tmp_path):
    path = tmp_path / "tickup.json"
    c1 = AppController(path, today_provider=lambda: TODAY)
    t = c1.add_quick("rascunho")
    c1.update(t.id, title="Final", priority=Priority.URGENT, notes="detalhes")
    c2 = AppController(path, today_provider=lambda: TODAY)
    saved = c2.store.get_task(t.id)
    assert saved.title == "Final" and saved.priority == Priority.URGENT and saved.notes == "detalhes"


# --- pesquisa -----------------------------------------------------------------
def test_search_view(ctrl):
    ctrl.add_quick("Comprar pão")
    ctrl.add_quick("Ligar à Ana")
    ctrl.set_search("pão")
    titles = [t.title for t in ctrl.visible_tasks()]
    assert titles == ["Comprar pão"]


# --- anular apagar ------------------------------------------------------------
def test_undo_delete_restores_task(ctrl):
    t = ctrl.add_quick("apagar-me")
    ctrl.delete(t.id)
    assert ctrl.store.get_task(t.id) is None
    restored = ctrl.undo_delete()
    assert restored is not None and ctrl.store.get_task(t.id) is not None


def test_undo_delete_without_deletion_returns_none(ctrl):
    assert ctrl.undo_delete() is None
