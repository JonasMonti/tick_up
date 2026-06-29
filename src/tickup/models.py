"""Modelos de domínio do Tick Up.

Tudo aqui é Python puro (sem Flet, sem I/O), por isso é trivial de testar.
Inspirado no Todoist: tarefas com prioridade P1–P4, opcionalmente com data
limite, organizadas em listas. A lista `None` representa a *Inbox*.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import IntEnum


def _now() -> datetime:
    """Instante atual em UTC. Isolado numa função para ser fácil de simular."""
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex


class Priority(IntEnum):
    """Níveis de prioridade ao estilo Todoist (P1 = mais urgente)."""

    URGENT = 1  # P1
    HIGH = 2    # P2
    MEDIUM = 3  # P3
    NONE = 4    # P4 — sem prioridade (valor por defeito)

    @property
    def label(self) -> str:
        return {1: "Urgente", 2: "Alta", 3: "Média", 4: "Sem prioridade"}[self.value]


# Cores por defeito para listas, ao estilo das apps populares.
DEFAULT_LIST_COLOR = "#0F7B66"  # esmeralda


@dataclass
class TaskList:
    """Uma lista/projeto que agrupa tarefas (ex.: 'Trabalho', 'Compras')."""

    name: str
    id: str = field(default_factory=_new_id)
    color: str = DEFAULT_LIST_COLOR
    order: int = 0

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("O nome da lista não pode estar vazio.")

    def __hash__(self) -> int:
        return hash(self.id)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "color": self.color, "order": self.order}

    @classmethod
    def from_dict(cls, data: dict) -> "TaskList":
        return cls(
            id=data["id"],
            name=data["name"],
            color=data.get("color", DEFAULT_LIST_COLOR),
            order=data.get("order", 0),
        )


@dataclass
class Task:
    """Uma tarefa do dia-a-dia.

    `list_id` a `None` significa que a tarefa está na *Inbox*.
    `due_date` a `None` significa que não tem data limite.
    """

    title: str
    id: str = field(default_factory=_new_id)
    notes: str = ""
    due_date: date | None = None
    priority: Priority = Priority.NONE
    completed: bool = False
    completed_at: datetime | None = None
    created_at: datetime = field(default_factory=_now)
    list_id: str | None = None
    order: int = 0

    def __post_init__(self) -> None:
        self.title = self.title.strip()
        if not self.title:
            raise ValueError("O título da tarefa não pode estar vazio.")
        # Aceita um int (ex.: vindo de JSON) e converte para Priority.
        if not isinstance(self.priority, Priority):
            self.priority = Priority(int(self.priority))

    def __hash__(self) -> int:
        # Hash pelo id: tarefas com campos iguais têm o mesmo id (o id é um
        # campo), por isso o contrato hash/eq mantém-se.
        return hash(self.id)

    # --- transições de estado -------------------------------------------------
    def complete(self, *, when: datetime | None = None) -> None:
        """Marca a tarefa como concluída (idempotente)."""
        if not self.completed:
            self.completed = True
            self.completed_at = when or _now()

    def reopen(self) -> None:
        """Reabre uma tarefa concluída (idempotente)."""
        self.completed = False
        self.completed_at = None

    def is_overdue(self, today: date) -> bool:
        """True se a tarefa tem data limite no passado e ainda não está feita."""
        return (
            not self.completed
            and self.due_date is not None
            and self.due_date < today
        )

    def is_due_today(self, today: date) -> bool:
        return not self.completed and self.due_date == today

    def completed_date(self) -> date | None:
        """Dia (na hora local) em que a tarefa foi concluída, ou None se ativa.

        `completed_at` é guardado em UTC; aqui converte-se para a hora local para
        que o board e o calendário agrupem as conclusões pelo dia "do utilizador".
        """
        if self.completed_at is None:
            return None
        return self.completed_at.astimezone().date()

    # --- serialização ---------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "notes": self.notes,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "priority": int(self.priority),
            "completed": self.completed,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat(),
            "list_id": self.list_id,
            "order": self.order,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(
            id=data["id"],
            title=data["title"],
            notes=data.get("notes", ""),
            due_date=date.fromisoformat(data["due_date"]) if data.get("due_date") else None,
            priority=Priority(data.get("priority", Priority.NONE)),
            completed=data.get("completed", False),
            completed_at=(
                datetime.fromisoformat(data["completed_at"])
                if data.get("completed_at")
                else None
            ),
            created_at=datetime.fromisoformat(data["created_at"]),
            list_id=data.get("list_id"),
            order=data.get("order", 0),
        )
