"""Testes do TaskStore: CRUD, regras de negócio e persistência."""
from datetime import date

import pytest

from tickup.models import Priority
from tickup.store import TaskStore


@pytest.fixture
def store() -> TaskStore:
    return TaskStore()


# --- listas -------------------------------------------------------------------
def test_add_and_get_list(store):
    lst = store.add_list("Trabalho")
    assert store.get_list(lst.id) is lst
    assert store.lists() == [lst]


def test_lists_ordered_by_creation(store):
    a = store.add_list("A")
    b = store.add_list("B")
    assert [l.id for l in store.lists()] == [a.id, b.id]


def test_rename_list(store):
    lst = store.add_list("Antigo")
    store.rename_list(lst.id, "Novo")
    assert store.get_list(lst.id).name == "Novo"


def test_rename_list_empty_raises(store):
    lst = store.add_list("X")
    with pytest.raises(ValueError):
        store.rename_list(lst.id, "  ")


def test_delete_list_moves_tasks_to_inbox(store):
    lst = store.add_list("Trabalho")
    task = store.add_task("Tarefa", list_id=lst.id)
    store.delete_list(lst.id)
    assert store.get_list(lst.id) is None
    assert store.get_task(task.id).list_id is None  # voltou à Inbox


def test_delete_list_with_tasks(store):
    lst = store.add_list("Trabalho")
    task = store.add_task("Tarefa", list_id=lst.id)
    store.delete_list(lst.id, delete_tasks=True)
    assert store.get_task(task.id) is None


def test_delete_missing_list_raises(store):
    with pytest.raises(KeyError):
        store.delete_list("nao-existe")


def test_restore_task_reinserts_exact_task(store):
    t = store.add_task("Recuperar", priority=Priority.HIGH)
    store.complete_task(t.id)
    store.delete_task(t.id)
    assert store.get_task(t.id) is None
    restored = store.restore_task(t)
    assert restored is t
    again = store.get_task(t.id)
    assert again is t and again.completed and again.priority == Priority.HIGH


def test_restore_task_is_idempotent(store):
    t = store.add_task("X")
    assert store.restore_task(t) is t  # já existe -> devolve o atual sem duplicar
    assert len(store.tasks()) == 1


# --- tarefas: criação ---------------------------------------------------------
def test_add_task_defaults_to_inbox(store):
    t = store.add_task("Comprar leite")
    assert t.list_id is None
    assert store.get_task(t.id) is t


def test_add_task_with_list(store):
    lst = store.add_list("Casa")
    t = store.add_task("Aspirar", list_id=lst.id)
    assert t.list_id == lst.id


def test_add_task_invalid_list_raises(store):
    with pytest.raises(KeyError):
        store.add_task("X", list_id="nao-existe")


def test_add_task_assigns_incrementing_order(store):
    a = store.add_task("A")
    b = store.add_task("B")
    assert a.order == 0 and b.order == 1


def test_order_is_per_list(store):
    lst = store.add_list("L")
    inbox_task = store.add_task("inbox")
    list_task = store.add_task("lista", list_id=lst.id)
    assert inbox_task.order == 0
    assert list_task.order == 0  # ordem independente por lista


# --- tarefas: atualização -----------------------------------------------------
def test_update_task_fields(store):
    t = store.add_task("X")
    store.update_task(t.id, title="Y", notes="nota", priority=Priority.HIGH)
    updated = store.get_task(t.id)
    assert updated.title == "Y"
    assert updated.notes == "nota"
    assert updated.priority is Priority.HIGH


def test_update_task_unknown_field_raises(store):
    t = store.add_task("X")
    with pytest.raises(ValueError):
        store.update_task(t.id, bogus=1)


def test_update_task_empty_title_raises(store):
    t = store.add_task("X")
    with pytest.raises(ValueError):
        store.update_task(t.id, title="   ")


def test_update_task_invalid_list_raises(store):
    t = store.add_task("X")
    with pytest.raises(KeyError):
        store.update_task(t.id, list_id="nao-existe")


def test_move_task_to_inbox(store):
    lst = store.add_list("L")
    t = store.add_task("X", list_id=lst.id)
    store.update_task(t.id, list_id=None)
    assert store.get_task(t.id).list_id is None


# --- tarefas: conclusão/remoção -----------------------------------------------
def test_complete_and_reopen(store):
    t = store.add_task("X")
    store.complete_task(t.id)
    assert store.get_task(t.id).completed is True
    store.reopen_task(t.id)
    assert store.get_task(t.id).completed is False


def test_delete_task(store):
    t = store.add_task("X")
    store.delete_task(t.id)
    assert store.get_task(t.id) is None


def test_delete_missing_task_raises(store):
    with pytest.raises(KeyError):
        store.delete_task("nao-existe")


def test_clear_completed(store):
    a = store.add_task("A")
    store.add_task("B")
    store.complete_task(a.id)
    removed = store.clear_completed()
    assert removed == 1
    assert store.get_task(a.id) is None
    assert len(store.tasks()) == 1


# --- persistência -------------------------------------------------------------
def test_save_and_load_roundtrip(tmp_path, store):
    lst = store.add_list("Trabalho", color="#123456")
    store.add_task("Tarefa", due_date=date(2026, 7, 1), priority=Priority.URGENT, list_id=lst.id)
    done = store.add_task("Feita")
    store.complete_task(done.id)

    path = tmp_path / "data" / "tickup.json"
    store.save(path)
    assert path.exists()

    loaded = TaskStore.load(path)
    assert len(loaded.lists()) == 1
    assert len(loaded.tasks()) == 2
    assert loaded.lists()[0].color == "#123456"


def test_load_missing_file_returns_empty(tmp_path):
    loaded = TaskStore.load(tmp_path / "nope.json")
    assert loaded.lists() == []
    assert loaded.tasks() == []


def test_save_is_atomic_no_leftover_tmp(tmp_path, store):
    store.add_task("X")
    path = tmp_path / "tickup.json"
    store.save(path)
    leftovers = list(tmp_path.glob("*.tmp"))
    assert leftovers == []
