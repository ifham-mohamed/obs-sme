# Plan: register the new M1 Celery tasks with the worker

  

## Context

  

Live worker log shows:

  

```

KeyError: 'app.tasks.m1.reconcile_raw.reconcile_raw_pdfs'

KeyError: 'app.tasks.m1.run_scraper.run_scraper'

```

  

…and the BILL extraction trigger lands in `FAILURE` immediately. The

producer side (FastAPI) is calling `.delay()` correctly — the messages

reach Redis — but the worker process **doesn't have these task names in

its registry**, so it rejects every message with `Received unregistered

task of type …`.

  

Why: `app/celery_config.py` registers tasks via an explicit

`include=[...]` list (not `autodiscover_tasks`). When the multi-source

work shipped, three new modules landed under `app/tasks/m1/` —

`reconcile_raw.py`, `run_scraper.py`, `migrate_raw_layout.py` — but the

`include` list was never updated, so a fresh worker boot still imports

only the three legacy modules (`gazette_scraper`, `extract_gazette`,

`preprocess_gazette`). The web API works because it imports the new

modules on demand at request time; the worker only loads what's in

`include` at boot, so the new task names never reach its task registry.

  

Outcome: the BILL extraction trigger (and any future `/reconcile`,

`/migrate-raw-layout` call) fails with `KeyError`. Fix is a one-line

edit + worker restart.

  

## The fix (one file)

  

**`C:\Reasearch\xyz\enigmatrix-backend\app\celery_config.py`** — extend

the `include` list passed to `Celery(...)`:

  

```python

celery_app = Celery(

    "enigmatrix-m1",

    broker=settings.CELERY_BROKER_URL,

    backend=settings.CELERY_BROKER_URL,

    include=[

        "app.tasks.m1.gazette_scraper",

        "app.tasks.m1.extract_gazette",

        "app.tasks.m1.preprocess_gazette",

        "app.tasks.m1.reconcile_raw",        # NEW

        "app.tasks.m1.run_scraper",          # NEW

        "app.tasks.m1.migrate_raw_layout",   # NEW

    ],

)

```

  

Nothing else has to change. The task definitions, `@celery_app.task`

decorators, names, and `app/tasks/m1/__init__.py` re-exports are all

already correct — they were verified during exploration. The web API

side already imports each module at request time, so this addition only

affects worker-boot behaviour.

  

## Why we're not switching to `autodiscover_tasks`

  

`autodiscover_tasks(['app.tasks.m1'])` would also work and would prevent

this class of bug for the next module too. But it changes how every task

module gets imported on worker boot, has subtle ordering effects with

respect to the Celery app construction, and is a behaviour change beyond

the scope of "fix the FAILURE on BILL extraction". Leaving the explicit

`include` list in place keeps the diff to three lines and is reversible

in one revert. A switch to autodiscovery is a sensible follow-up.

  

## Operator step (post-edit)

  

Restart the running Celery worker so it imports the newly-listed

modules. From the backend project root, typical dev invocation:

  

```bash

# Stop the existing worker (Ctrl+C in its terminal, or kill the pid).

# Then re-launch:

uv run celery -A app.celery_config:celery_app worker --loglevel=info

```

  

On boot, the worker log should show `[tasks]` listing the three new

task names (plus the existing three). The next BILL trigger from the UI

will route to a healthy worker and progress past `KeyError` into the

normal `STARTED → SUCCESS` flow.

  

## Critical files

  

- `C:\Reasearch\xyz\enigmatrix-backend\app\celery_config.py` — the only

  file edited.

  

## Reuse (no new code)

  

- `app/tasks/m1/reconcile_raw.py`, `run_scraper.py`,

  `migrate_raw_layout.py` — already exist, decorated, named, and

  re-exported via `app/tasks/m1/__init__.py`. No edits needed.

- `app/api/v1/m1_gazette_extraction.py` — already imports and `.delay()`s

  the new tasks via `from app.tasks.m1.run_scraper import run_scraper`

  and friends. No edits needed.

  

## Verification

  

1. Inspect the diff: `app/celery_config.py` shows only three new lines

   inside the `include` list.

2. Restart the worker. Confirm the boot banner lists all six task

   names under `[tasks]`:

   - `app.tasks.m1.extract_gazette.extract_gazette`

   - `app.tasks.m1.gazette_scraper.run_gazette_spider`

   - `app.tasks.m1.migrate_raw_layout.migrate_raw_layout`

   - `app.tasks.m1.preprocess_gazette.preprocess_gazette_task`

   - `app.tasks.m1.reconcile_raw.reconcile_raw_pdfs`

   - `app.tasks.m1.run_scraper.run_scraper`

3. From the Sources hub, open `BILL → Start Bills extraction` with the

   same `2026-01-01 → 2026-01-31` scope. The status pill should

   transition `Queued → Running → Completed` instead of immediately

   `Failed`.

4. From the Sources hub, click `Reconcile all raw folders`. The toast

   should report the per-source counts (not crash with `KeyError`).

5. Worker log should show **no** `Received unregistered task of type …`

   lines after the restart.

  

## Post-run vault sync

  

After the edit lands and the worker is restarted, append a one-line

entry to `C:\sme\08-Findings-Log\CHANGES.md` (next F-### row) noting:

"Register reconcile_raw / run_scraper / migrate_raw_layout in

celery_config.include — worker was rejecting them with KeyError after

the multi-source ship." No SESSIONS / FEATURES update needed (this is a

hotfix, not a feature).