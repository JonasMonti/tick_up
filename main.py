"""Ponto de entrada para o empacotamento mobile/desktop (`flet build`).

O `flet build` procura um módulo `main.py` na raiz do diretório da app. Aqui
apenas reutilizamos a UI real em `app/main.py` — toda a lógica vive lá e no
núcleo (`src/tickup`). Para desenvolvimento continua a usar-se
`flet run app/main.py`.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Garante que o núcleo (`src/tickup`) e o pacote `app` são importáveis quando a
# app corre a partir do bundle empacotado.
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import flet as ft

from app.main import main

ft.app(main)
