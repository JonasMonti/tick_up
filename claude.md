# Tick Up

App de **lista de tarefas do dia-a-dia**, single-user e offline. Modelo
deliberadamente simples, com **dois ecrãs**:

- **Board (Tarefas):** um único sítio com todas as tarefas por fazer (grupo e data
  **opcionais**) + as concluídas de hoje. Ao virar o dia, as concluídas saem do
  board — **sem se apagarem** (ficam no histórico). Grupos são **chips de filtro**
  no topo (sem menu lateral).
- **Calendário:** que tarefas foram concluídas em cada dia do mês; tocar num dia
  mostra a lista desse dia.

Mantém prioridades P1–P4 (estilo Todoist) e data limite opcional por tarefa.

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
  views.py             #   Funções puras: board/completed_on/completed_by_day (+ today/overdue/… legadas)
app/                   # UI — Flet (mobile + web)
  main.py              #   ponto de entrada + widgets (board, chips, calendário, animações)
  controller.py        #   liga o TaskStore aos eventos da UI (board/calendar/grupo; sem widgets)
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
5. **Sem grupo = `list_id is None`** (não é uma `TaskList`). O filtro do board usa
   o sentinela `views.ALL_GROUPS` para "todos os grupos".
6. **Conclusão por dia local:** `Task.completed_date()` converte `completed_at`
   (UTC) para a data local — é por aí que o board ("feitas hoje") e o calendário
   agrupam as conclusões.
7. **Prioridade ao estilo Todoist:** `Priority.URGENT(1) … NONE(4)`; defeito = `NONE`.
8. **Português (pt-PT)** em toda a interface e mensagens de erro.
9. **Persistência atómica:** gravar via ficheiro temporário + `replace` (já em `store.save`).

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
- [x] UI Flet (mobile-first) **simplificada**: dois ecrãs (Board + Calendário),
      grupos como chips de filtro, "feitas hoje" no board, edição em sheet,
      prioridade/data opcionais, anular ao apagar, pesquisa, animações subtis.
- [x] Empacotamento mobile (apk) via GitHub Actions (`.github/workflows/release-apk.yml`).
- [x] Página de download (GitHub Pages, `docs/`).
- [ ] Assinatura para a Play Store (keystore).
- [ ] Site próprio (deploy da versão web do Flet).

## Versões

Semantic Versioning 2.0.0 (`MAJOR.MINOR.PATCH`). Versão atual: **0.3.0**.

- **0.3.0** — modelo simplificado **Board + Calendário**: remove o menu lateral e
  as vistas Inbox/Próximos/Atrasados/Concluídos; um único board com todas as
  tarefas (grupo/data opcionais) + "feitas hoje" (saem ao virar o dia, sem
  apagar); grupos como chips de filtro; calendário das concluídas por dia;
  animações subtis (troca de ecrã, navegação de mês, painel do dia).
- **0.2.1** — corrige ecrã preto no arranque (NavigationBar tem de ter destinos
  no primeiro render).
- **0.2.0** — UI remodelada + qualidade de vida (edição, listas, pesquisa, undo, badges).
- **0.1.0** — núcleo + primeira release APK.
