# M1 Summarization And NLLB Translation Readiness Plan

> Updated: 2026-07-30 · **method superseded 2026-08-01**  
> Repo: `C:\Reasearch\xyz`  
> Purpose: define the next implementation slice for SME-facing regulation summaries in English, Sinhala, and Tamil.
>
> **Read [[19_M1_Regulation_Summarization]] first.** This plan's §5 and §7 propose a template-based summariser filled from the extracted fields. That approach was tested and **fails**: running the production extractors over all 167 V6 test rows returns a *wrong* `gazette_number` on **31.1%** of them — scored 0.95 by `metadata_confidence` with `needs_review=False` — and finds an `effective_date` in **0 of the 11 rows that state one**. A template built on those fields would cite the wrong gazette in fluent prose. Doc 19 supplies the corrected method (field-grounded constrained generation with anchor binding) and moves steps 1–3 of the work upstream into field extraction. The operational content below — eligibility rules, output fields, CLI surface, review workflow, acceptance list — still stands.

## 1. Current Status

This feature is not production-complete yet.

What already exists:

- DB/model/schema fields for `title_en`, `title_si`, `title_ta`, `summary_en`, `summary_si`, and `summary_ta`.
- Admin translation queue for missing regulation translations: `enigmatrix-backend\app\api\v1\admin_translations.py`.
- NLLB helper for English-to-Sinhala/Tamil title translation: `scripts\lib\nllb_translate.py`.
- Gazette listing title scraper: `scripts\lib\title_scraper.py`.
- Evaluation support for title/summary fields in `enigmatrix-ml\m1\evaluation\field_metrics.py` and `xlsx_reader.py`.
- Snapshot service includes title/summary fields for dataset measurement.

What is missing:

- A production summarizer that reads classified/extracted regulation text and writes `summary_en`.
- A backfill command that translates `title_en` and `summary_en` into `title_si`, `title_ta`, `summary_si`, and `summary_ta`.
- Quality gates for numbers, dates, legal references, and hallucination.
- Admin review workflow for low-quality summaries/translations.

Current implementation decision:

Build the first production slice as a conservative regulated-summary pipeline:

```text
raw_text / cleaned_text
  -> category + sector + SME relevance context
  -> controlled English summary
  -> NLLB Sinhala/Tamil translation
  -> DB storage
  -> translation/admin review
  -> dataset snapshot and measurement
```

Do not summarize from raw OCR text alone. The summary must use the classifier or gold/adjudicated fields:

```text
change_category
affected_sectors
is_sme_relevant
confidence / review status
```

This prevents a non-SME land-title, appointment, public-security, or public-service notice from being summarized as if it creates an SME action.

## 2. Why This Feature Comes After Classification

The summary should be generated only after the regulation has:

- extracted raw/cleaned text.
- a stable `classification_chunk`.
- predicted or adjudicated `change_category`.
- affected sectors.
- `is_sme_relevant`.
- confidence/review status.

Why:

- The summary must explain the regulation in the context of SME relevance.
- A tax notice, product-standard notice, and land-title notice need different summary language.
- The summary should not imply SME impact when `is_sme_relevant=False`.

## 3. Inputs

Use these fields as summarization input:

| Input | Why it is needed |
|---|---|
| `title_en` | Gives the official/public title when available |
| `raw_text` or `cleaned_text` | Source evidence for the summary |
| `classification_chunk` | Compact, classifier-safe text window |
| `change_category` | Tells the summarizer the regulation domain |
| `affected_sectors` | Tells the summarizer who may be affected |
| `is_sme_relevant` | Prevents false SME-facing claims |
| `effective_date` | Required for actionable summaries when present |
| `gazette_number` and `published_date` | Used for citation/provenance |
| `principal_act` and penalties | Preserve legal basis and penalty amounts |

Recommended source priority:

```text
1. cleaned_text, when available and long enough
2. classification_chunk, when cleaned_text is missing or too long for the first slice
3. raw_text excerpt, only if cleaned_text and classification_chunk are missing
```

Recommended classifier context priority:

```text
1. gold/adjudicated label, for training/evaluation datasets
2. expert-verified DB label, for production records
3. model-predicted label, only when confidence is high enough
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
- mention affected SME sectors only when justified.
- avoid legal advice.
- avoid adding obligations that are not in the text.
- say "not SME-facing" or avoid SME action wording when `is_sme_relevant=False`.

Suggested structure:

```text
[What changed]. [Who/which sectors are affected]. [Effective date/action/penalty if available].
```

Example for SME-relevant tax:

```text
This notice changes a tax or duty rule that may affect pricing, invoicing, or import cost. Grocery retail, food service, and general retail SMEs should check the effective date and update their compliance records if the rule applies to them.
```

Example for non-SME land title:

```text
This notice concerns land-title claims or administrative title settlement. It does not create a direct operating, tax, labour, import, product-standard, or penalty obligation for the study SME sectors.
```

Recommended summary templates for the first implementation:

| Condition | Summary behavior |
|---|---|
| `is_sme_relevant=False` | State the administrative/legal nature and explicitly avoid SME action wording. |
| `TAX_RATE_CHANGE` and SME relevant | Mention tax/levy/duty effect, affected sectors, effective date/rate if present. |
| `IMPORT_EXPORT` and SME relevant | Mention customs/import/export rule, valuation/permit/proceeds effect, and affected sectors. |
| `LABOUR_LAW` and SME relevant | Mention employer/employee obligation, wage/hours/leave/EPF/ETF issue, and sector scope. |
| `PRODUCT_STANDARD` and SME relevant | Mention product, standard/labelling/certification obligation, and sector scope. |
| `BUSINESS_REGISTRATION` and SME relevant | Mention registration/filing/licence duty and affected business sectors. |
| Low confidence or OCR damaged | Generate a cautious draft and set review flag, or skip automatic summary. |

## 6. Translation Approach

Use English as the controlled source text, then translate to Sinhala and Tamil with NLLB.

Existing smoke test:

```powershell
cd C:\Reasearch\xyz

uv run python scripts\lib\nllb_translate.py "Value Added Tax (Amendment) Order"
```

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
status in ("preprocessed", "classified", "verified")
summary_en is null or force_refresh is true
raw_text/cleaned_text exists
```

### Stage 2 - Build Summary Prompt/Input

Input should include:

```text
title_en
gazette_number
change_category
affected_sectors
is_sme_relevant
effective_date
principal_act
classification_chunk
cleaned_text excerpt
```

### Stage 3 - Generate `summary_en`

Implementation options:

| Option | Use when |
|---|---|
| Rule/template summary | Fast baseline for clear categories and non-SME notices |
| Local summarization model | If GPU/CPU budget is acceptable and output can be checked |
| Admin-written summary | For high-risk, low-OCR-quality, or thesis examples |

For the first production slice, use a conservative hybrid:

1. Template non-SME obvious notices.
2. Template common tax/import/labour/product categories where fields are clear.
3. Send ambiguous rows to admin review instead of generating confident prose.

### Stage 4 - Quality Check English

Reject or flag a summary if:

- it drops a number/date/rate found in the title or chunk.
- it invents a sector not in `affected_sectors`.
- it says SMEs are affected while `is_sme_relevant=False`.
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

- Reuse `scripts\lib\nllb_translate.py` for the first local NLLB path.
- Translate from controlled English, not directly from noisy Sinhala/Tamil OCR.
- Preserve gazette numbers, act names, dates, percentages, currency amounts, and section references.
- Add a review flag when NLLB output drops numbers or leaves untranslated legal fragments.
- For titles, keep the existing `title_en -> title_si/title_ta` approach and extend it to summaries.

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

uv run python scripts\backfill_summary_translations_nllb.py `
  --source summary_en `
  --targets si,ta `
  --limit 200 `
  --write
```

Those two scripts do not yet exist as production commands. Build them before claiming the summarization feature is complete.

Minimum implementation files to add:

| File | Purpose |
|---|---|
| `scripts\generate_regulation_summaries.py` | Backfill `summary_en` for eligible classified/verified regulations. |
| `scripts\backfill_summary_translations_nllb.py` | Translate `summary_en` into `summary_si` and `summary_ta`; optionally translate missing titles. |
| `enigmatrix-backend\app\m1\services\summary_service.py` | Shared service for summary templates, quality checks, and DB writes. |
| Alembic migration if needed | Add metadata fields such as `summary_status`, `summary_model_version`, and quality flags. |
| Backend tests | Check non-SME wording, date/number preservation, sector consistency, and translation queue behavior. |

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
