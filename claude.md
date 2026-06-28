# Tick Up

App de **lista de tarefas do dia-a-dia**, single-user e offline. Inspirada nas
apps de referência (Todoist, Things 3, Microsoft To Do): tarefas com prioridade
P1–P4, data limite opcional, organizadas em listas, com vistas inteligentes
(**Hoje**, **Próximos**, **Atrasados**, **Inbox**, **Concluídos**).

Objetivo: **app nativa de mobile primeiro** (Android/iOS) e, mais tarde, um
**site próprio** — ambos a partir da mesma base de código Python (Flet).

## Stack

- **Linguagem:** Python (3.11+; desenvolvido em 3.14)
- **UI:** [Flet](https://flet.dev) — Python puro sobre Flutter. A mesma base de
  código corre em **Android, iOS, Web e Desktop**.
- **Persistência:** JSON local no dispositivo (offline, sem servidor). Ver
  `src/tickup/store.py`.
- **Testes:** pytest.

## Arquitetura — regra de ouro

> **O núcleo (`src/tickup/`) NÃO importa Flet.** É Python puro e testável.
> A UI (`app/`) depende do núcleo, nunca o contrário.

```
src/tickup/            # NÚCLEO — domínio puro, sem UI, 100% testável
  models.py            #   Task, TaskList, Priority (dataclasses + serialização)
  store.py             #   TaskStore: CRUD, regras de negócio, persistência JSON (atómica)
  views.py             #   Vistas inteligentes: funções puras (today/upcoming/overdue/…)
app/                   # UI — Flet (mobile + web)
  main.py              #   ponto de entrada: ft.app(...)
  controller.py        #   liga o TaskStore aos eventos da UI (sem widgets)
  ui_*.py              #   ecrãs/componentes Flet
tests/                 # pytest (espelha src/tickup/)
  test_models.py
  test_store.py
  test_views.py
pyproject.toml         # config do projeto + pytest (pythonpath=src)
requirements.txt
```

## Convenções

1. **Núcleo sem UI.** Nada de `import flet` dentro de `src/tickup/`.
2. **Lógica de dados no núcleo**, não nos widgets. A UI chama `TaskStore`/`views`.
3. **Determinismo nos testes:** as funções de `views.py` recebem o "hoje" como
   argumento (`ref: date`) — nunca chamam `date.today()` lá dentro.
4. **Datas vs. instantes:** `due_date` é `date` (dia). `created_at`/`completed_at`
   são `datetime` em **UTC**.
5. **Inbox = `list_id is None`** (não é uma `TaskList`).
6. **Prioridade ao estilo Todoist:** `Priority.URGENT(1) … NONE(4)`; defeito = `NONE`.
7. **Português (pt-PT)** em toda a interface e mensagens de erro.
8. **Persistência atómica:** gravar via ficheiro temporário + `replace` (já em `store.save`).

## Comandos

```bash
# Ambiente (uma vez)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Testes (rápido; o núcleo não precisa de Flet)
pytest

# Correr a app
flet run app/main.py            # desktop (dev)
flet run --web app/main.py      # no browser (preview do futuro site)

# Empacotar para mobile (fase seguinte)
flet build apk                  # Android
flet build ipa                  # iOS (só em macOS + Xcode)
```

## Estado atual

- [x] Núcleo de domínio (`models`, `store`, `views`) + testes a passar.
- [x] UI Flet (mobile-first): vistas com secções, edição em sheet, prioridade/data
      na criação, anular ao apagar, menu lateral de listas, pesquisa, badges.
- [x] Empacotamento mobile (apk) via GitHub Actions (`.github/workflows/release-apk.yml`).
- [x] Página de download (GitHub Pages, `docs/`).
- [ ] Assinatura para a Play Store (keystore).
- [ ] Site próprio (deploy da versão web do Flet).

## Versões

Semantic Versioning 2.0.0 (`MAJOR.MINOR.PATCH`). Versão atual: **0.2.0**.

- **0.2.0** — UI remodelada + qualidade de vida (edição, listas, pesquisa, undo, badges).
- **0.1.0** — núcleo + primeira release APK.
