# M1 Summarization And NLLB Translation Readiness Plan

> Updated: 2026-07-30 · **method superseded 2026-08-01**  
> Repo: `C:\Reasearch\xyz`  
> Purpose: define the next implementation slice for SME-facing regulation summaries in English, Sinhala, and Tamil.
>
> **Read [[19_M1_Regulation_Summarization]] first.** This plan's §5 and §7 propose a template-based summariser filled from the extracted fields. That approach was tested and **fails**: running the production extractors over all 167 V6 test rows returns a *wrong* `gazette_number` on **31.1%** of them — scored 0.95 by `metadata_confidence` with `needs_review=False` — and finds an `effective_date` in **0 of the 11 rows that state one**. A template built on those fields would cite the wrong gazette in fluent prose. Doc 19 supplies the corrected method (field-grounded constrained generation with anchor binding) and moves steps 1–3 of the work upstream into field extraction. The operational content below — eligibility rules, output fields, CLI surface, review workflow, acceptance list — still stands.

> **Implementation update — 2026-08-01:** first conservative backend slice is now built in `enigmatrix-backend`. It adds `app/m1/services/summary_service.py`, `app/m1/tasks/summarise_gazette.py`, `scripts/generate_regulation_summaries.py`, `scripts/enqueue_missing_m1_translations.py`, Alembic migration `202608010002_m1_summary_metadata.py`, and focused unit tests. This is not a final summarisation claim yet: it is the safe Stage-E backfill path that either writes a short anchored English evidence summary or stores `summary_status='review_required'` with named flags.

## 1. Current Status

This feature is not production-complete yet.

What already exists:

- DB/model/schema fields for `title_en`, `title_si`, `title_ta`, `summary_en`, `summary_si`, and `summary_ta`.
- DB/model/schema fields for summary provenance: `summary_source`, `summary_model_version`, `summary_status`, `summary_generated_at`, `summary_reviewed_by`, `summary_quality_flags`, and `summary_source_sha256`.
- Conservative Stage-E summary service: `enigmatrix-backend\app\m1\services\summary_service.py`.
- Per-row Celery task: `enigmatrix-backend\app\m1\tasks\summarise_gazette.py`.
- Backfill command: `enigmatrix-backend\scripts\generate_regulation_summaries.py`.
- Translation enqueue command: `enigmatrix-backend\scripts\enqueue_missing_m1_translations.py`.
- Admin translation queue for missing regulation translations: `enigmatrix-backend\app\api\v1\admin_translations.py`.
- NLLB-200 pull queue for title/summary translation: `m1_translation_jobs`, `m1_translation_workers`, `/api/v1/m1/translation/*`, and the Colab worker at `enigmatrix-backend\app\m1\colab\nllb_translation_worker.py`.
- Gazette listing title scraper: `scripts\lib\title_scraper.py`.
- Evaluation support for title/summary fields in `enigmatrix-ml\m1\evaluation\field_metrics.py` and `xlsx_reader.py`.
- Snapshot service includes title/summary fields for dataset measurement.

What is missing:

- Full production evidence for summaries. The first backend summarizer exists, but it is intentionally conservative and must still be evaluated against live `cleaned_text`.
- Broader anchor-bound extraction for rates, levies, duties, thresholds, effective date roles, identity gazette vs cross-referenced gazette, and other summary-critical facts.
- Quality gates for numbers, dates, legal references, sector claims, relevance claims, and hallucination.
- Admin review workflow for rejected summaries and low-quality translations.

Current implementation decision:

Build the first production slice as a conservative regulated-summary pipeline:

```text
raw_text / cleaned_text
  -> section_chunks + extracted metadata
  -> category + sector-ledger + SME relevance context
  -> anchor-bound slots
  -> controlled English evidence summary
  -> verifier
  -> NLLB Sinhala/Tamil translation queue
  -> DB storage
  -> summary/translation admin review
  -> dataset snapshot and measurement
```

Do not summarize from raw OCR text alone. The summary must use the source text plus the classifier or gold/adjudicated category fields and the sector ledger:

```text
change_category
sector ledger / expert routing
is_sme_relevant
classification_source
classifier_decision_margin as a review rank, not as a probability
```

This prevents a non-SME land-title, appointment, public-security, or public-service notice from being summarized as if it creates an SME action.

## 2. Why This Feature Comes After Classification

The summary should be generated only after the regulation has:

- extracted raw/cleaned text.
- a stable `classification_chunk`.
- persisted `section_chunks` / sub-document text for full-document summary evidence.
- predicted or adjudicated `change_category`.
- sector applicability from the expert/manual sector ledger.
- `is_sme_relevant`.
- `classification_source` and `classifier_decision_margin` review rank.

Why:

- The summary must explain the regulation in the context of SME relevance.
- A tax notice, product-standard notice, and land-title notice need different summary language.
- The summary should not imply SME impact when `is_sme_relevant=False`.

## 3. Inputs

Use these fields as summarization input:

| Input | Why it is needed |
|---|---|
| `title_en` | Gives the official/public title when available |
| `section_chunks` | Full-document, section-aware evidence; primary Stage-E input |
| `cleaned_text` | Source evidence fallback when chunks are unavailable |
| `classification_chunk` | Classifier-safe head window; fallback only for short notices |
| `change_category` | Tells the summarizer the regulation domain |
| sector ledger / expert routing | Tells the summarizer who may be affected; not emitted by the frozen LinearSVC classifier |
| `is_sme_relevant` | Prevents false SME-facing claims |
| `effective_date` | Required for actionable summaries when present |
| `gazette_number` and `published_date` | Used for citation/provenance |
| `principal_act` and penalties | Preserve legal basis and penalty amounts |
| rate/levy/duty/threshold slots | Must be added before production summaries; current extractor does not capture them |

Recommended source priority:

```text
1. section_chunks, when available
2. cleaned_text, when chunks are unavailable
3. classification_chunk, only for short notices or fallback
4. raw_text excerpt, only if cleaned_text and classification_chunk are missing
```

Recommended classifier context priority:

```text
1. gold/adjudicated label, for training/evaluation datasets
2. expert-verified DB label, for production records
3. model-predicted label, with `classifier_decision_margin` used as a review rank, not a probability
4. otherwise send to admin review before summary generation
```

## 4. Outputs

Use existing fields first:

```text
title_en
title_si
title_ta
summary_en
summary_si
summary_ta
```

Recommended future metadata fields:

```text
summary_source
summary_model_version
summary_status
summary_generated_at
summary_reviewed_by
summary_quality_flags
translation_model_version
translation_status
```

If new metadata fields are added, create an Alembic migration. Do not alter the DB manually.

## 5. English Summary Rules

A good `summary_en` should:

- be 1-3 short sentences.
- say what changed.
- say who is affected.
- mention dates, amounts, rates, thresholds, penalties, or deadlines exactly when present.
- mention SME sectors only when they are present in the sector ledger or manually verified.
- avoid legal advice.
- avoid adding obligations that are not in the text.
- say "not SME-facing" or avoid SME action wording when `is_sme_relevant=False`.

Suggested structure:

```text
[What changed]. [Who/which sectors are affected]. [Effective date/action/penalty if available].
```

Example for SME-relevant tax:

```text
This notice changes a tax or duty rule. State the verified rate, levy, threshold or effective date only when the value is anchored in the source; otherwise omit that clause and flag the summary for review.
```

Example for non-SME land title:

```text
This notice concerns land-title claims or administrative title settlement. It does not create a direct operating, tax, labour, import, product-standard, or penalty obligation for the study SME sectors.
```

Recommended category frames for the first implementation:

| Condition | Summary behavior |
|---|---|
| `is_sme_relevant=False` | State the administrative/legal nature and explicitly avoid SME action wording. |
| `TAX_RATE_CHANGE` and SME relevant | Mention tax/levy/duty effect, sector ledger scope, effective date/rate only if anchor-verified. |
| `IMPORT_EXPORT` and SME relevant | Mention customs/import/export rule, valuation/permit/proceeds effect, and sector ledger scope only if anchor-verified. |
| `LABOUR_LAW` and SME relevant | Mention employer/employee obligation, wage/hours/leave/EPF/ETF issue, and sector scope. |
| `PRODUCT_STANDARD` and SME relevant | Mention product, standard/labelling/certification obligation, and sector scope. |
| `BUSINESS_REGISTRATION` and SME relevant | Mention registration/filing/licence duty and affected business sectors. |
| Low margin, missing anchor, or OCR damaged | Skip automatic summary or write `summary_status='review_required'`; do not generate cautious-but-unsupported prose. |

## 6. Translation Approach

Use English as the controlled source text, then translate to Sinhala and Tamil with NLLB.

Current operational path: enqueue translation jobs through `/api/v1/m1/translation/*` and drain them with the Colab NLLB worker. The old local helper can remain useful for isolated experiments, but it is not the production path.

Why NLLB:

- It supports Sinhala (`sin_Sinh`) and Tamil (`tam_Taml`).
- It can run locally without API keys.
- It is suitable for batch title/summary translation at research scale.

Translation rules:

- Preserve numbers, dates, percentages, and legal citations.
- Do not translate gazette numbers.
- Keep named acts recognizable.
- Prefer conservative translation over fluent but legally loose wording.
- Flag rows with OCR damage, very long source text, or missing dates for admin review.

## 7. Proposed Pipeline

### Stage 1 - Select Candidate Rows

Rows should be eligible when:

```text
status in ("classified", "summarized", "alerted")
summary_en is null or force_refresh is true
raw_text/cleaned_text exists
classification_source is expert/manual/model with review policy satisfied
```

### Stage 2 - Build Summary Prompt/Input

Input should include:

```text
title_en
gazette_number
change_category
sector ledger / expert routing
is_sme_relevant
effective_date
principal_act
section_chunks
cleaned_text
classification_chunk fallback
```

### Stage 3 - Generate `summary_en`

Implementation options:

| Option | Use when |
|---|---|
| Anchor-bound evidence summary | **First production version.** Extract verified slots, assemble controlled English, reject unsafe output |
| Rule/template summary from current fields | Baseline only; do not ship because current fields return wrong gazette identities and miss rates/dates |
| Local summarization model | Optional rewrite only after verifier exists |
| Admin-written summary | For high-risk, low-OCR-quality, or thesis examples |

For the first production slice, use the doc-19 conservative path:

1. Extract anchor-bound slots from `section_chunks`.
2. Compose a controlled English evidence summary from verified slots only.
3. Omit unverified slots and record named quality flags.
4. Send ambiguous rows to admin review instead of generating confident prose.

### Stage 4 - Quality Check English

Reject or flag a summary if:

- it drops a number/date/rate found in the title or chunk.
- it invents a sector not in the sector ledger.
- it says SMEs are affected while `is_sme_relevant=False`.
- it uses an identity gazette number that is only anchored as a cross-reference.
- it uses a rate, levy, duty, threshold, date, section number or penalty amount without a source span and role anchor.
- it exceeds the length limit.
- source OCR is too damaged.

### Stage 5 - Translate With NLLB

Translate:

```text
title_en -> title_si
title_en -> title_ta
summary_en -> summary_si
summary_en -> summary_ta
```

Implementation notes:

- Reuse the shipped `m1_translation_jobs` pull queue and Colab worker. Do not create a second summary-translation path.
- Translate from controlled English, not directly from noisy Sinhala/Tamil OCR.
- Preserve gazette numbers, act names, dates, percentages, currency amounts, and section references.
- Add a review flag when NLLB output drops numbers or leaves untranslated legal fragments.
- For titles and summaries, use the same no-clobber/manual-retranslate policy already implemented in the M1 translation queue.

### Stage 6 - Store And Review

Persist into `m1_regulations` through the service/API layer, not direct SQL.

Rows needing review should appear in the admin translation queue until:

- `title_si` and `title_ta` exist.
- `summary_si` and `summary_ta` exist when `summary_en` exists.
- quality flags are cleared or accepted.

## 8. Commands To Build Next

These commands are the intended workflow after the missing scripts are implemented:

```powershell
cd C:\Reasearch\xyz

uv run python scripts\generate_regulation_summaries.py `
  --status preprocessed,classified,verified `
  --limit 200 `
  --write

uv run python scripts\enqueue_missing_m1_translations.py `
  --fields summary `
  --targets si,ta `
  --limit 200
```

These commands now exist in `enigmatrix-backend\scripts`. They are dry-run by default; add `--write` only after the migration is applied and the dry-run output has been inspected. The translation command calls the existing `m1_translation_jobs` queue; it does not run NLLB locally.

Minimum implementation files to add:

| File | Purpose |
|---|---|
| `scripts\generate_regulation_summaries.py` | **Added.** Backfills `summary_en` for eligible classified/verified regulations; dry-run unless `--write` is supplied. |
| `scripts\enqueue_missing_m1_translations.py` | **Added.** Enqueues `summary_en -> summary_si/summary_ta` jobs through the existing M1 translation queue. |
| `enigmatrix-backend\app\m1\services\summary_service.py` | **Added.** Shared service for conservative slots, summary frames, verifier, quality flags, and ORM write helpers. |
| `enigmatrix-backend\app\m1\tasks\summarise_gazette.py` | **Added.** Per-row Celery Stage-E summarization task. |
| Slot extractors for rates/levies/duties/thresholds/effective dates/gazette-role binding | **Partial.** First regex-backed figure/date/gazette/provenance slice exists; full extractor evaluation is still required. |
| Alembic migration if needed | **Added.** `202608010002_m1_summary_metadata.py`. |
| Backend tests | **Added partial.** `test_m1_summary_service.py` covers grounded rate/date, unanchored date omission, low-margin review, non-SME wording, and missing-source rejection. |

## 9. Dataset And Measurement Impact

Once summaries/translations are stored:

- DB snapshots should include `summary_en`, `summary_si`, and `summary_ta`.
- Excel ground-truth sheets can include human-written summary fields.
- Extraction measurement can score title/summary completeness and quality.
- SME-facing discovery and alerts can show trilingual summaries instead of raw gazette chunks.

This connects summarization to:

- `14_M1_Tracking_Workflows.md` (`S1 SME Regulation Discovery`)
- `07_M1_Deployment_Integration.md` (latency budget includes summarization)
- `12_M1_Monitoring_Maintenance.md` (monitor summary/translation completeness)
- `M1_EXTRACTION_ACCURACY_AND_DATASET_MANAGEMENT_MANUAL.md` (measure title/summary fields)

Parent documentation sections to update after implementation:

| Parent doc | What to add |
|---|---|
| `02_M1_Data_Requirements.md` | Final storage contract for `summary_en`, `summary_si`, `summary_ta`, status, review flags, and model/version provenance. |
| `04_M1_Preprocessing_Pipeline.md` | Which cleaned/chunked text is passed into the summarizer and how OCR quality affects review routing. |
| `07_M1_Deployment_Integration.md` | Runtime placement: batch backfill first, then optional async Celery stage after classification. |
| `10_M1_Sinhala_Tamil_NLP.md` | NLLB model choice, language codes, number/date preservation, and manual review fallback. |
| `11_M1_API_Reference.md` | Admin/API fields for summaries, translations, review status, and re-generation actions. |
| `14_M1_Tracking_Workflows.md` | SME-facing regulation cards and survey prompts using localized summaries. |

## 10. Acceptance Checklist

Mark this feature ready only when:

- [ ] `summary_en` is generated for classified/verified rows.
- [ ] `title_si` and `title_ta` are backfilled from `title_en`.
- [ ] `summary_si` and `summary_ta` are backfilled from `summary_en`.
- [ ] numbers/dates/rates are preserved across translations.
- [ ] non-SME notices do not get SME action wording.
- [ ] admin review queue shows low-quality/missing translations.
- [ ] DB snapshots include summary/title fields.
- [ ] extraction measurement can score title/summary fields.
- [ ] SME-facing pages/alerts display the correct language.
- [ ] screenshots and sample outputs are added to the vault.
