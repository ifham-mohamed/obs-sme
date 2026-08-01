# 12 — Trilingual Translation Pipeline (NLLB-200, EN → SI/TA)

> The program-level record of the machine-translation pipeline shipped 2026-07-31: why the backend never calls the GPU, what the queue table guarantees, the three failures that would have been silent, and what must not be claimed from this data before it is measured.
>
> Supersedes the MarianMT plan that Stage E of [[00_INDEX]] carried until this shipped.
>
> Evidence: `AI_WORK_LOG.md` Session 102 · `enigmatrix-docs/m1/10_M1_3_NLLB_Translation_Pipeline.md` (full engineering spec) · vault §10 of [[10_M1_Sinhala_Tamil_NLP]] · migration `202607310001`.

---

## 0. The one-paragraph truth

`m1_regulations` has carried `title_si` / `title_ta` / `summary_si` / `summary_ta` / `real_world_example_si` / `real_world_example_ta` since the initial schema, and until this shipped they were filled **only by hand**. At ~180 gazettes per ingest window that is not a workable path, so the trilingual promise in the research design was in practice an English-only product. This pipeline fills those columns with NLLB-200 running on a free Colab GPU, at ingest time, **without making translation a dependency of extraction**. The architecture is inverted from the obvious one — the backend never calls the GPU; it writes queue rows and the notebook leases them — and every property that makes the design survive a reclaimed Colab session follows from that inversion. Translation quality is **unmeasured**; treat SI/TA as draft-until-reviewed in any claim made from this data.

---

## 1. Why this is a research point, not a feature

The awareness gap this module measures is **not evenly distributed across languages**. An SME owner who reads only Sinhala or Tamil cannot act on a gazette published in English — and that is part of the barrier under study (RQ2, and the channel analysis behind RQ4).

A platform that surfaces regulatory change in English only would be **measuring the gap while reproducing it**. That is the argument for spending engineering effort here rather than treating translation as polish.

---

## 2. The design decision that shaped everything

NLLB-200 runs in Google Colab. Colab is free GPU capacity, and it is also: no stable public URL, disconnects on idle, sessions reclaimed without warning.

So the direction is **inverted**. The backend does not push text to Colab; it writes rows to a queue table and Colab **pulls** them.

```text
extract_gazette  ──enqueue──▶  m1_translation_jobs (pending)
                                       │
Colab notebook   ──POST /worker/lease──┤   claims a batch, receives a lease token
Colab notebook   ──NLLB-200 on T4──────┤
Colab notebook   ──POST /worker/submit─┘
backend          ──write-back──▶  m1_regulations.title_si / title_ta / …
```

Four consequences, each of which was the actual reason rather than a happy accident:

| Property | Because |
|---|---|
| No tunnel, ngrok, or inbound port | The dev backend is not publicly addressable; a push design needs a Colab URL re-pasted into settings every session. |
| A reclaimed session loses nothing | **A lease is a visibility timeout, not a lock.** Jobs return to `pending` after `M1_TRANSLATION_LEASE_SECONDS` and are re-handed out. |
| Translation can never fail an extraction | The pipeline's only interaction is an `INSERT`, **after** the extraction has committed, inside its own `try`. |
| Two Colab sessions can run concurrently | `SELECT … FOR UPDATE SKIP LOCKED` — each transaction claims a disjoint set, with no coordination. |

**The failure mode this design accepts:** with no worker attached, nothing is translated. Extraction still succeeds. That is precisely why the UI treats *pending > 0 with zero online workers* as a **warning state** rather than a number among numbers (§5.3).

---

## 3. The idempotency contract

`m1_translation_jobs` holds one row per **(regulation, field, target language)**, with:

```sql
UNIQUE (regulation_id, field, target_lang)
```

That single constraint is what let the translate flag be threaded through **both** extract and preprocess with no special-casing:

- `extract_gazette` queues whatever English exists at that moment;
- `preprocess_gazette` tops up anything that became non-empty since;
- re-queuing unchanged text costs nothing.

"Enqueue this regulation" is therefore safe to call any number of times. Only genuinely new or drifted English creates work.

**`source_sha256` is the drift detector.** The job stores a snapshot of the English at enqueue time plus its hash. If a re-extraction improves `title_en`, the stored translation is stale *by definition* and the job re-opens — rather than leaving a Sinhala title that describes a superseded English one.

| Column | Role |
|---|---|
| `field` | `title` \| `summary` \| `real_world_example` — the *logical* field; the column written is `f"{field}_{target_lang}"`, so the naming convention **is** the mapping |
| `target_lang` | `si` \| `ta` — the app locale, **not** the NLLB code (§4.1) |
| `status` | `pending` → `leased` → `done` \| `failed` |
| `attempts` | Capped by `M1_TRANSLATION_MAX_ATTEMPTS` — stops an input that reliably OOMs the GPU from cycling forever |
| `lease_token` / `lease_expires_at` | The visibility timeout; submit must present the live token, so a zombie session cannot overwrite a newer result |
| `origin` | `pipeline` (checkbox) \| `manual` (Retranslate button) — decides write-back policy (§4.2) |
| `worker_id`, `model_name`, `device`, `latency_ms` | Provenance, kept for the quality write-up that has not been done yet (§6.1) |

`m1_translation_workers` is a heartbeat registry and is **purely observational** — nothing in the lease path reads it. It answers exactly one operator question: *is a GPU actually listening right now, or is this queue going to sit at 47 pending forever?*

---

## 4. Three failures that would have been silent

### 4.1 NLLB does not take ISO-639-1

It takes FLORES-200 codes carrying the script:

| App locale | FLORES-200 |
|---|---|
| `si` | `sin_Sinh` |
| `ta` | `tam_Taml` |
| (source) | `eng_Latn` |

Given a wrong `forced_bos_token_id`, **the model does not error — it produces fluent output in the wrong language.** So the mapping lives in exactly one place server-side (`translation_service.NLLB_LANG`) and the server ships `nllb_target_code` to the worker on every job. The notebook never guesses.

This is the same class of error as the Wijesekara-before-detection ordering constraint in [[10_M1_Sinhala_Tamil_NLP]] §5: **a confident wrong answer with nothing downstream to flag it.** Both are handled by removing the opportunity to guess rather than by validating afterwards.

### 4.2 Machine translation clobbering human review

- `origin='pipeline'` jobs write **only into an empty column**. A Sinhala title a reviewer has already typed survives every later automatic run; the machine's output is recorded on the job row only.
- `origin='manual'` jobs — the explicit *Retranslate* button — **overwrite**. There the human is the one asking for the machine's version.

That one rule is why this queue and the pre-existing Session-12 manual queue at `/admin/translations` never fight: the manual `PATCH` wins **by construction**, with no coordination between the two surfaces.

The admin page's **MT / Human** badge is *inferred* by comparing the column against the completed job's output, rather than stored in a provenance column — deliberately, so that it also reads correctly for SI/TA values hand-entered long before this queue existed.

### 4.3 Ticking the box with no GPU attached

Extraction succeeds, the queue grows, and nothing says otherwise. So `pending > 0 && online_workers == 0` is surfaced as a warning in **two** places — an inline hint under the checkbox itself, and the console banner.

Related: `M1_TRANSLATION_WORKER_KEY` is **empty by default on purpose**. With no key set, the worker endpoints return 503 for every request, so a backend deployed without anyone thinking about this **cannot expose an unauthenticated write path into `m1_regulations`**.

---

## 5. Operating it

### 5.1 One-time backend setup

```dotenv
M1_TRANSLATION_ENABLED=true
M1_TRANSLATION_WORKER_KEY=<openssl rand -hex 32>
# Optional:
# M1_TRANSLATION_MODEL=facebook/nllb-200-distilled-600M
# M1_TRANSLATION_LEASE_SECONDS=300
# M1_TRANSLATION_MAX_BATCH=32
```

```bash
make migrate   # applies 202607310001
```

### 5.2 Start the worker

Colab → **Runtime → Change runtime type → T4 GPU** → paste `enigmatrix-backend/app/m1/colab/nllb_translation_worker.py` → set `BACKEND_URL` (must be reachable from Google's network) and `WORKER_KEY` → run, leave the tab open. The worker prints its `worker_id` and appears on the admin page within seconds.

The worker is kept in-repo as a reviewable `.py` rather than an `.ipynb` JSON blob, and it handles the `lang_code_to_id` → `convert_tokens_to_ids` transformers API move so a Colab image refresh does not break it.

### 5.3 Run and review

Extraction run page → **Batch pipeline control** → tick *"Translate title/summary → සිංහල / தமிழ்"* → Extract all / Run all steps as normal. Then `/admin/m1/translation` for queue health, backfill, job list, and the per-regulation EN / SI / TA panel.

| Signal | Healthy | Action if not |
|---|---|---|
| `online_workers` | ≥ 1 | 0 with `pending > 0` → start the Colab notebook |
| `worker_key_configured` | true | false → set `M1_TRANSLATION_WORKER_KEY` |
| `failed` | 0 | inspect `error` on the job — usually an over-long input or a GPU OOM |
| `leased` | small, moving | stuck high → a session died; jobs self-recover after the lease expires |

---

## 6. Limits worth stating before the viva

1. **MT quality is unmeasured.** There is no BLEU/chrF reference set. Per-job `model_name`, `device` and `latency_ms` are stored so a sampled human evaluation can be attributed later, but that evaluation has not been done. **Treat SI/TA as draft-until-reviewed in any claim made from this data.**
2. **Domain terminology is generic.** NLLB carries no Sri Lankan legal-register signal, so statutory terms come back literal rather than in established Sinhala/Tamil legal usage. Glossary-constrained decoding is the natural next step, and is the honest answer if asked.
3. **Summary translation now has live data.** The 2026-08-01 Stage-E backend slice writes conservative `summary_en` values and enqueues `summary` jobs for SI/TA. First verification found 380 generated summaries, 11 review-required rows, 388 Sinhala summary jobs done, 388 Tamil summary jobs done, and 0 generated summaries missing SI/TA. These are still machine-generated draft translations pending human review.
4. **`MAX_SOURCE_CHARS = 8000`.** Longer text is skipped with a warning rather than half-translated; NLLB's ~512-token window means long inputs are sentence-chunked by the worker.
5. **Execution has now been verified, but quality is still unmeasured.** The migration has been applied, the Colab/NLLB worker path has completed jobs, and the summary queue drained for generated summaries. This closes the "does it run" question for the first slice; it does **not** close MT quality, domain-terminology, or numeric-preservation evidence.

---

## 7. Why the worker uses a shared secret, not a JWT

A Colab session is long-lived and unattended. Asking an operator to paste a refreshing admin token into a notebook every hour is **how credentials end up committed in a shared notebook**.

The key grants exactly three narrow operations — lease, submit, heartbeat — and cannot read gazette text or touch any other table.

| Method | Path | Auth |
|---|---|---|
| POST | `/api/v1/m1/translation/worker/lease` | `X-Translation-Worker-Key` |
| POST | `/api/v1/m1/translation/worker/submit` | same |
| POST | `/api/v1/m1/translation/worker/heartbeat` | same |
| GET | `/api/v1/m1/translation/status` | admin JWT |
| GET | `/api/v1/m1/translation/jobs` | admin JWT |
| GET | `/api/v1/m1/translation/regulations/{id}` | admin JWT |
| POST | `/api/v1/m1/translation/enqueue` | admin JWT |
| POST | `/api/v1/m1/translation/regulations/{id}/retranslate` | admin JWT |
| PUT | `/api/v1/m1/translation/regulations/{id}/manual` | admin JWT |

---

## 8. What shipped

**Backend** — migration `202607310001` (`m1_translation_jobs` + `m1_translation_workers`, partial index on claimable rows); `app/m1/models/translation_job.py`; `app/m1/services/translation_service.py` (enqueue / lease / submit / reap); `app/m1/api/translation.py` (worker + admin routers); `app/m1/colab/nllb_translation_worker.py`. Hooks in `extract_gazette`, `preprocess_gazette`, `admin_pipeline`.

**Frontend** — `/admin/m1/translation` page; `translation-health` and `regulation-translation-panel` components; `lib/api/m1-translation.ts`; checkbox in `batch-stage-control.tsx`; sidebar entry with en/si/ta nav labels.

**Docs** — `enigmatrix-docs/m1/10_M1_3_NLLB_Translation_Pipeline.md` (engineering spec); vault synced as §10 of [[10_M1_Sinhala_Tamil_NLP]] per the consolidation convention; the index's Stage-E row corrected, since it still described MarianMT.

---

## 9. Next actions

| # | Action | Why it is next |
|---|---|---|
| 1 | Run the first end-to-end translation: `make migrate` → single-row `/advance?translate=true` | Nothing in this workstream has been executed (§6.5) |
| 2 | Build a sampled human-evaluation set (≥ 100 title pairs per language, rated by a fluent reader) | Turns "unmeasured" into a number the viva can be given |
| 3 | Decide whether SI/TA appear in the SME-facing survey before evaluation, and label them as machine-translated if so | An unlabelled draft translation in front of a research respondent is a validity problem, not just a UX one |
| 4 | Review summary translations now that the Stage-E summariser has shipped | Summaries are the field this pipeline was actually built for; the next evidence task is sampled SI/TA quality and numeric-preservation review |

---

## 10. Cross-references

- **Trilingual NLP background, detection, OCR, and §10 pipeline summary:** [[10_M1_Sinhala_Tamil_NLP]]
- **Full engineering spec (schema, API, file list):** `enigmatrix-docs/m1/10_M1_3_NLLB_Translation_Pipeline.md`
- **Migration applied alongside the classifier migration:** [[11_CLASSIFIER_FREEZE_AND_INTEGRATION]] §6.3
- **Stage-E summarisation implementation and remaining gates:** [[19_M1_Regulation_Summarization]] · `PROGRAM_READINESS/M1_SUMMARIZATION_TRANSLATION_READINESS_PLAN.md`
- **Pipeline stage map (Stage E / E2):** [[00_INDEX]] · [[10_PIPELINE_STAGING_AND_MANUAL_STEPPING]]
- **Status ledger:** [[03_FEATURE_CHECKLIST]]
