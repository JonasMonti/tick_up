"""Testes do AppController (lógica de UI, sem Flet) — modelo Board + Calendário."""
from datetime import date, datetime

import pytest

from app.controller import ALL_GROUPS, AppController
from tickup.models import Priority

TODAY = date(2026, 6, 27)


@pytest.fixture
def ctrl(tmp_path):
    return AppController(tmp_path / "tickup.json", today_provider=lambda: TODAY)


def _complete_on(ctrl, task_id, day: date) -> None:
    """Conclui uma tarefa e fixa o dia (local) da conclusão, para testes deterministas."""
    ctrl.toggle(task_id)
    ctrl.store.get_task(task_id).completed_at = datetime(day.year, day.month, day.day, 12).astimezone()


# --- arranque / board ---------------------------------------------------------
def test_starts_on_board_view(ctrl):
    assert ctrl.current_view == "board"
    assert ctrl.view_title() == "Tarefas"
    assert ctrl.group_filter is ALL_GROUPS


def test_add_has_no_due_date_by_default(ctrl):
    task = ctrl.add_quick("Comprar pão")
    assert task is not None
    assert task.due_date is None
    assert task in ctrl.visible_tasks()


def test_add_with_explicit_date(ctrl):
    task = ctrl.add_quick("Dentista", due_date=date(2026, 7, 3))
    assert task.due_date == date(2026, 7, 3)
    assert task in ctrl.visible_tasks()  # board mostra todas as ativas


def test_add_empty_returns_none(ctrl):
    assert ctrl.add_quick("   ") is None


def test_board_shows_active_not_completed(ctrl):
    t = ctrl.add_quick("X")
    assert t in ctrl.visible_tasks()
    ctrl.toggle(t.id)
    assert t not in ctrl.visible_tasks()


# --- grupos (chips de filtro) -------------------------------------------------
def test_add_in_group_filter_assigns_group(ctrl):
    lst = ctrl.add_list("Trabalho")
    ctrl.set_group(lst.id)
    t = ctrl.add_quick("reunião")
    assert t.list_id == lst.id
    assert t in ctrl.visible_tasks()


def test_group_filter_scopes_board(ctrl):
    lst = ctrl.add_list("Trabalho")
    grouped = ctrl.add_quick("nada")  # ainda em ALL → sem grupo
    ctrl.set_group(lst.id)
    work = ctrl.add_quick("reunião")
    assert ctrl.visible_tasks() == [work]
    ctrl.set_group(ALL_GROUPS)
    assert set(ctrl.visible_tasks()) == {grouped, work}


def test_set_group_none_shows_ungrouped(ctrl):
    lst = ctrl.add_list("L")
    ctrl.set_group(lst.id)
    work = ctrl.add_quick("reunião")
    ctrl.set_group(None)  # sem grupo
    loose = ctrl.add_quick("solta")
    titles = {t.title for t in ctrl.visible_tasks()}
    assert titles == {"solta"} and work.title not in titles


def test_set_invalid_group_raises(ctrl):
    with pytest.raises(KeyError):
        ctrl.set_group("nao-existe")


# --- concluídas hoje / fim do dia ---------------------------------------------
def test_completed_today_shows_done_today_only(ctrl):
    today_done = ctrl.add_quick("hoje")
    _complete_on(ctrl, today_done.id, TODAY)
    old_done = ctrl.add_quick("ontem")
    _complete_on(ctrl, old_done.id, date(2026, 6, 26))
    done_today = ctrl.completed_today()
    assert today_done in done_today
    assert old_done not in done_today  # saiu do board ao virar o dia


def test_completed_today_respects_group_filter(ctrl):
    lst = ctrl.add_list("Trabalho")
    ctrl.set_group(lst.id)
    t = ctrl.add_quick("reunião")
    _complete_on(ctrl, t.id, TODAY)
    assert t in ctrl.completed_today()
    ctrl.set_group(None)
    assert t not in ctrl.completed_today()


# --- calendário ---------------------------------------------------------------
def test_calendar_defaults_to_current_month(ctrl):
    assert ctrl.calendar_year == 2026 and ctrl.calendar_month == 6


def test_calendar_month_navigation_wraps(ctrl):
    ctrl.calendar_month = 1
    ctrl.calendar_prev_month()
    assert (ctrl.calendar_year, ctrl.calendar_month) == (2025, 12)
    ctrl.calendar_next_month()
    assert (ctrl.calendar_year, ctrl.calendar_month) == (2026, 1)


def test_calendar_days_and_completed_on(ctrl):
    t = ctrl.add_quick("X")
    _complete_on(ctrl, t.id, TODAY)
    by_day = ctrl.calendar_days()
    assert by_day[TODAY] == [t]
    assert ctrl.completed_on(TODAY) == [t]
    assert ctrl.completed_on(date(2026, 6, 1)) == []


# --- navegação de ecrã --------------------------------------------------------
def test_set_calendar_and_board(ctrl):
    ctrl.set_calendar()
    assert ctrl.current_view == "calendar" and ctrl.view_title() == "Calendário"
    ctrl.set_board()
    assert ctrl.current_view == "board"


def test_set_invalid_view_raises(ctrl):
    with pytest.raises(ValueError):
        ctrl.set_view("nao-existe")


# --- pesquisa (filtra o board) ------------------------------------------------
def test_search_filters_board(ctrl):
    ctrl.add_quick("Comprar pão")
    ctrl.add_quick("Ligar à Ana")
    ctrl.set_search("pão")
    assert [t.title for t in ctrl.visible_tasks()] == ["Comprar pão"]
    ctrl.clear_search()
    assert len(ctrl.visible_tasks()) == 2


# --- mutação / persistência / undo --------------------------------------------
def test_toggle_completes_and_reopens(ctrl):
    task = ctrl.add_quick("X")
    ctrl.toggle(task.id)
    assert ctrl.store.get_task(task.id).completed is True
    ctrl.toggle(task.id)
    assert ctrl.store.get_task(task.id).completed is False


def test_delete_removes_task(ctrl):
    task = ctrl.add_quick("X")
    ctrl.delete(task.id)
    assert ctrl.store.get_task(task.id) is None


def test_changes_are_persisted(tmp_path):
    path = tmp_path / "tickup.json"
    c1 = AppController(path, today_provider=lambda: TODAY)
    c1.add_quick("Persistir isto")
    c2 = AppController(path, today_provider=lambda: TODAY)
    assert any(t.title == "Persistir isto" for t in c2.store.tasks())


def test_clear_completed(ctrl):
    a = ctrl.add_quick("a")
    ctrl.add_quick("b")
    ctrl.toggle(a.id)
    assert ctrl.clear_completed() == 1


def test_update_changes_and_persists(tmp_path):
    path = tmp_path / "tickup.json"
    c1 = AppController(path, today_provider=lambda: TODAY)
    t = c1.add_quick("rascunho")
    c1.update(t.id, title="Final", priority=Priority.URGENT, notes="detalhes")
    c2 = AppController(path, today_provider=lambda: TODAY)
    saved = c2.store.get_task(t.id)
    assert saved.title == "Final" and saved.priority == Priority.URGENT and saved.notes == "detalhes"


def test_delete_group_resets_filter_to_all(ctrl):
    lst = ctrl.add_list("Temp")
    ctrl.set_group(lst.id)
    ctrl.delete_list(lst.id)
    assert ctrl.group_filter is ALL_GROUPS


def test_undo_delete_restores_task(ctrl):
    t = ctrl.add_quick("apagar-me")
    ctrl.delete(t.id)
    assert ctrl.store.get_task(t.id) is None
    restored = ctrl.undo_delete()
    assert restored is not None and ctrl.store.get_task(t.id) is not None


def test_undo_delete_without_deletion_returns_none(ctrl):
    assert ctrl.undo_delete() is None
