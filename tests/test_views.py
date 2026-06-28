"""Testes das vistas inteligentes (Hoje, Próximos, Atrasados, etc.)."""
from datetime import date

import pytest

from tickup import views
from tickup.models import Priority, Task

TODAY = date(2026, 6, 27)


def make(title, *, due=None, prio=Priority.NONE, list_id=None, done=False, order=0):
    t = Task(title=title, due_date=due, priority=prio, list_id=list_id, order=order)
    if done:
        t.complete()
    return t


# --- ordenação ----------------------------------------------------------------
def test_sorted_by_priority_first():
    low = make("low", prio=Priority.NONE)
    high = make("high", prio=Priority.URGENT)
    assert views.sorted_tasks([low, high]) == [high, low]


def test_sorted_by_due_date_when_same_priority():
    later = make("later", due=date(2026, 7, 10))
    sooner = make("sooner", due=date(2026, 7, 1))
    no_date = make("no_date")
    result = views.sorted_tasks([no_date, later, sooner])
    assert result == [sooner, later, no_date]  # sem data fica por último


# --- inbox --------------------------------------------------------------------
def test_inbox_only_unlisted_active():
    a = make("inbox")
    b = make("listed", list_id="L1")
    c = make("done", done=True)
    assert views.inbox([a, b, c]) == [a]


# --- hoje ---------------------------------------------------------------------
def test_today_includes_overdue_and_due_today():
    overdue = make("atrasada", due=date(2026, 6, 20))
    due_today = make("hoje", due=TODAY)
    future = make("futuro", due=date(2026, 6, 30))
    none = make("sem data")
    result = views.today([overdue, due_today, future, none], TODAY)
    assert overdue in result and due_today in result
    assert future not in result and none not in result


def test_today_excludes_completed():
    done = make("feita", due=TODAY, done=True)
    assert views.today([done], TODAY) == []


# --- atrasados ----------------------------------------------------------------
def test_overdue_only_past_active():
    past = make("passado", due=date(2026, 6, 1))
    today_task = make("hoje", due=TODAY)
    assert views.overdue([past, today_task], TODAY) == [past]


# --- próximos -----------------------------------------------------------------
def test_upcoming_window():
    tomorrow = make("amanhã", due=date(2026, 6, 28))
    in_a_week = make("daqui a 7d", due=date(2026, 7, 4))
    too_far = make("longe", due=date(2026, 7, 5))
    today_task = make("hoje", due=TODAY)
    result = views.upcoming([tomorrow, in_a_week, too_far, today_task], TODAY, days=7)
    assert tomorrow in result and in_a_week in result
    assert too_far not in result  # fora da janela
    assert today_task not in result  # hoje não é "próximo"


# --- por lista ----------------------------------------------------------------
def test_by_list_filters():
    a = make("a", list_id="L1")
    b = make("b", list_id="L2")
    inbox = make("c")
    assert views.by_list([a, b, inbox], "L1") == [a]
    assert views.by_list([a, b, inbox], None) == [inbox]


# --- concluídos ---------------------------------------------------------------
def test_completed_most_recent_first():
    from datetime import datetime, timezone

    first = make("primeira")
    first.complete(when=datetime(2026, 6, 1, tzinfo=timezone.utc))
    second = make("segunda")
    second.complete(when=datetime(2026, 6, 20, tzinfo=timezone.utc))
    active = make("ativa")
    result = views.completed([first, second, active])
    assert result == [second, first]


# --- pesquisa -----------------------------------------------------------------
def test_search_matches_title_and_notes():
    t1 = Task(title="Comprar PÃO")
    t2 = Task(title="Reunião", notes="trazer o pão de forma")
    t3 = Task(title="Outra")
    assert set(views.search([t1, t2, t3], "pão")) == {t1, t2}


def test_search_empty_query_returns_nothing():
    assert views.search([Task(title="X")], "  ") == []


def test_search_ignores_completed():
    done = make("pão", done=True)
    assert views.search([done], "pão") == []


# --- agrupamento e contagens --------------------------------------------------
def test_group_by_due_date():
    a = make("a", due=date(2026, 7, 1))
    b = make("b", due=date(2026, 7, 1))
    c = make("c")  # sem data
    groups = views.group_by_due_date([a, b, c])
    assert set(groups[date(2026, 7, 1)]) == {a, b}
    assert groups[None] == [c]


def test_counts():
    # As tarefas com data estão numa lista, por isso só "inbox" conta para a Inbox.
    tasks = [
        make("inbox"),
        make("hoje", due=TODAY, list_id="L1"),
        make("atrasada", due=date(2026, 6, 1), list_id="L1"),
        make("proxima", due=date(2026, 6, 28), list_id="L1"),
        make("feita", done=True),
    ]
    c = views.counts(tasks, TODAY)
    assert c["inbox"] == 1
    assert c["today"] == 2  # hoje + atrasada
    assert c["overdue"] == 1
    assert c["upcoming"] == 1
    assert c["completed"] == 1
