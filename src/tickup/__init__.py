"""Tick Up — app de lista de tarefas do dia-a-dia.

O subpacote `tickup` contém o núcleo de domínio (modelos, armazenamento e
vistas), totalmente independente da interface gráfica (Flet).
"""
from .models import DEFAULT_LIST_COLOR, Priority, Task, TaskList
from .store import TaskStore
from . import views

__version__ = "0.1.0"

__all__ = [
    "Priority",
    "Task",
    "TaskList",
    "TaskStore",
    "DEFAULT_LIST_COLOR",
    "views",
    "__version__",
]
