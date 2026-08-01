# Sealed-Baseline Evaluation Specification — M1 Gazette Pipeline

**Scope:** Accuracy measurement for the 4-stage pipeline (`ingested → extracted → preprocessed → classified`) against a sealed gold baseline.
**Baselines in use:**

- **Gold v1** — `C:\Reasearch\xyz\data\golden\structured_v1_batches_1_2_3_4_5_6_7_8_official.xlsx` (800 manually curated rows, gazette issues 2468–2486). Unmodified, and still the field-level reference for those 800 rows.
- **Gold v2 (combined, 2026-08-01)** — `C:\Reasearch\xyz\data\golden\structured_v2_combined_1508_official.xlsx` (**1508 rows, 52 columns**). Union of Gold v1 with the 1128-row classification gold standard; the two overlap on only 420 gazettes. Adds the frozen 8-class labels, sector sets and provenance columns.
  - **`field_truth_verified` is the column that matters.** TRUE on 800 rows, FALSE on the 708 appended ones. **Every field-level accuracy measurement must filter on it.**
  - `is_sme_relevant` was resolved **gold-wins** on the 151 rows where the two sources disagreed; both original values are retained and each conflict is flagged. Log: `documentation/m1/analysis/golden_workbook_gold_relevance_conflicts.csv`.
  - `change_category` / `domain_code` (workbook vocabulary) and `gold_change_category` (frozen 8-class) are **different label spaces** — 0 of 420 agreement. Never join or average them.
- **DB snapshot v2** — EGZ 2026-02-01..2026-02-28, ~204 rows, most at `status='preprocessed'`. Used for stage-coverage and regression checks.

Sealed = the baseline is frozen, checksummed, and never edited by the evaluator. The evaluator reads it read-only and compares predictions produced by a fresh pipeline run.

---

## A. Evaluation assumptions

1. **Join key.** Every predicted record joins to exactly one gold record on a stable natural key. Primary key = `(gazette_number, document_number)`. Fallback = `sha256` once extraction has run. `raw_pdf_path` is *not* a key (paths move).
2. **Status is the gate.** A record is scored only against columns valid for its **current** `status`. A record at `preprocessed` is never penalised for missing `domain_code` — those columns are out of scope for it.
3. **Gold is authoritative but may be null.** A gold null is a legitimate expected value (e.g. `amendment_type = NULL` for a non-amending gazette). Predicting null when gold is null is **correct**, not a miss.
4. **Status must itself be evaluated.** `status` is a first-class enumerated field: a record that should be `classified` but stopped at `preprocessed` is a *stage-progression* failure, tracked separately from field accuracy.
5. **Determinism where possible.** Machine-derived fields (`sha256`, `file_size_bytes`, `pdf_pages`) are expected to match exactly. Model-derived fields (`amendment_type`, `domain_code`, `classifier_confidence`) are expected to match within the tolerances defined per field.
6. **One record, one status per run.** Cumulative scoring assumes the record genuinely passed through all prior stages; upstream columns are re-scored at every stage (a corrupted `raw_text` should keep hurting the score at `classified`).
7. **Sealed baseline integrity.** Before every run, verify `sha256(baseline_file)` against a stored manifest. Abort if it differs.

---

## B. Status-based scoring logic

Each status defines a **field set**. Scoring uses two views:

- **Stage-only accuracy** — score *only* the fields introduced at that stage.
- **Cumulative-through-stage accuracy** — score *all* fields valid up to and including that stage.

```
FIELD_SETS = {
  ingested:     [m1_gazette_items, raw_pdf_path, gazette_number,
                 document_number, source_url, status],
  extracted:    [raw_text, extraction_method, extracted_at,
                 file_size_bytes, sha256, pdf_pages, language, status],
  preprocessed: [cleaned_text, classification_chunk, amendment_type,
                 metadata_confidence, m1_sub_documents,
                 m1_regulation_penalties, status],
  classified:   [domain_code, change_category, severity_level,
                 is_sme_relevant, classifier_confidence,
                 classified_at, status],
}

STAGE_ORDER = [ingested, extracted, preprocessed, classified]

def stage_only_fields(s):        return FIELD_SETS[s]
def cumulative_fields(s):        # union of all sets up to s
    return flatten(FIELD_SETS[k] for k in STAGE_ORDER[:index(s)+1])

def scorable_fields(record):
    return cumulative_fields(record.gold_status)   # cumulative is the default
```

**Selection rule (required):**

- `status = ingested` → score ingested fields only
- `status = extracted` → score ingested + extracted
- `status = preprocessed` → score ingested + extracted + preprocessed
- `status = classified` → score all four sets

`status` appears in every set; score it once per record (deduplicate on union).

---

## C. Field-by-field metric design

Each field is assigned exactly one **metric type**. The comparator returns a score in `[0,1]` plus an `error_code` (Section G).

| Field | Type | Comparator | Pass rule |
|---|---|---|---|
| `gazette_number` | identifier | exact (normalized) | `norm(p)==norm(g)` |
| `document_number` | identifier | exact (normalized) | `norm(p)==norm(g)` |
| `source_url` | identifier/URL | exact after URL-normalize | scheme+host+path lowercased, trailing `/` stripped |
| `raw_pdf_path` | path | basename exact | compare filename only, not directory |
| `m1_gazette_items` | count/int | exact | integer equality |
| `status` | enum | exact | `p==g` |
| `raw_text` | long text (OCR) | normalized similarity + CER | see §F |
| `extraction_method` | enum | exact | `{pdfplumber, ocr_tesseract, hybrid,...}` |
| `extracted_at` | timestamp | tolerance window | see below |
| `file_size_bytes` | int | exact (±0) or ±1% band | deterministic → exact |
| `sha256` | hash | exact | 64-hex equality |
| `pdf_pages` | int | exact | integer equality |
| `language` | enum | exact | ISO-639 code (`si`,`ta`,`en`) |
| `cleaned_text` | text | normalized similarity | token-level, §F |
| `classification_chunk` | text | normalized similarity | §F |
| `amendment_type` | enum (nullable) | exact + null-aware | §H enum handling |
| `metadata_confidence` | confidence [0,1] | calibration (separate) | not counted in correctness; see below |
| `m1_sub_documents` | list<obj> | set P/R/F1 | §G list scoring |
| `m1_regulation_penalties` | list<obj> | set P/R/F1 | §G list scoring |
| `domain_code` | enum | exact + P/R/F1 per class | §H classification |
| `change_category` | enum | exact + P/R/F1 | §H |
| `severity_level` | ordinal enum | exact + off-by-one credit | §H |
| `is_sme_relevant` | boolean | exact + P/R/F1 | §H |
| `classifier_confidence` | confidence [0,1] | calibration (separate) | ECE/Brier, not correctness |
| `classified_at` | timestamp | tolerance window | see below |

**Identifiers — normalization** (`norm`): trim, collapse internal whitespace, uppercase, strip leading zeros only where the domain guarantees numeric ids. Never fuzzy-match identifiers — a near-miss id is a **hard miss** (`ID_MISMATCH`).

**Timestamps — tolerance window.** `extracted_at`, `classified_at` are *process* timestamps; exact equality is meaningless across runs.

- Score = 1.0 if `|p − g| ≤ W`, else 0.0. Default `W = 24h` for process stamps.
- If the timestamp is a *content* date (extracted from the gazette body), tighten `W = 0` (must match the day exactly).
- Missing when required → `MISSING_TIMESTAMP` (score 0).

**Confidence fields** (`metadata_confidence`, `classifier_confidence`) are **not** scored for correctness — a confidence has no single "right" value. Evaluate them by **calibration** only (Section D, calibration block): Expected Calibration Error (ECE) and Brier score against the correctness of the field they accompany. Report separately so a poorly-calibrated confidence never inflates or deflates accuracy.

---

## D. Stage-level score formulas

### Notation

- `F(r)` = scorable field set for record `r` (Section B).
- `s(r,f) ∈ [0,1]` = comparator score for field `f` of record `r`.
- `w(f)` = field weight (weighted model) or `1` (non-weighted model).
- `V(r)` = fields with a valid gold value (exclude fields the gold marks *not-applicable*, distinct from gold-null which is scored).

### Field-level

```
field_accuracy(f) = mean( s(r,f)  for r in records where f ∈ V(r) )
```

### Record-level

**Non-weighted (macro over fields within a record):**
```
record_score(r) = ( Σ_{f∈V(r)} s(r,f) ) / |V(r)|
```

**Weighted:**
```
record_score_w(r) = ( Σ_{f∈V(r)} w(f)·s(r,f) ) / ( Σ_{f∈V(r)} w(f) )
```

### Stage-level

**Stage-only accuracy** (fields introduced at stage `S`, over records whose gold reached ≥ `S`):
```
stage_only(S) = mean( s(r,f)  for r with gold_status ≥ S, f ∈ stage_only_fields(S) ∩ V(r) )
```

**Cumulative-through-stage accuracy:**
```
cumulative(S) = mean( s(r,f)  for r with gold_status ≥ S, f ∈ cumulative_fields(S) ∩ V(r) )
```

**Stage-progression accuracy** (did the record reach the status it should?):
```
progression(S) = |{ r : pred_status ≥ S and gold_status ≥ S }| / |{ r : gold_status ≥ S }|
```

### Overall

```
overall_micro = Σ_r Σ_f s(r,f) / Σ_r |V(r)|          # every field equal weight
overall_macro = mean_r record_score(r)                # every record equal weight
overall_weighted = mean_r record_score_w(r)
```

Report micro, macro, and weighted side by side — micro is dominated by long field sets (classified rows), macro protects small-N stages.

### Recommended field weights (weighted model)

| Class | Fields | Weight |
|---|---|---|
| Hard identifiers | `gazette_number`, `document_number`, `sha256` | 3.0 |
| Structural | `status`, `pdf_pages`, `file_size_bytes`, `language`, `extraction_method` | 2.0 |
| Core NLP output | `domain_code`, `change_category`, `severity_level`, `is_sme_relevant` | 2.5 |
| List outputs | `m1_sub_documents`, `m1_regulation_penalties` | 2.0 |
| Bulk text | `raw_text`, `cleaned_text`, `classification_chunk` | 1.0 |
| Timestamps | `extracted_at`, `classified_at` | 0.5 |
| Confidence | `metadata_confidence`, `classifier_confidence` | 0.0 (calibration only) |

Rationale: a wrong id invalidates the whole record, so it is weighted heavily; bulk OCR text is high-volume and inherently noisy, so it does not dominate.

---

## E. Output report template

```
=== SEALED-BASELINE EVALUATION REPORT ===
run_id: <uuid>          pipeline_git_sha: <sha>
baseline: structured_v1_...official.xlsx  baseline_sha256: <hash>  [VERIFIED]
records evaluated: 800   snapshot: EGZ 2026-02..  date: 2026-07-26

1. STAGE SUMMARY
+--------------+-------+-------------+-------------+-------------+
| stage        | n     | stage_only  | cumulative  | progression |
+--------------+-------+-------------+-------------+-------------+
| ingested     | 800   | 0.994       | 0.994       | 1.000       |
| extracted    | 780   | 0.951       | 0.972       | 0.975       |
| preprocessed | 620   | 0.883       | 0.933       | 0.968       |
| classified   | 410   | 0.812       | 0.907       | 0.911       |
+--------------+-------+-------------+-------------+-------------+

2. OVERALL
micro=0.921  macro=0.905  weighted=0.913

3. FIELD LEADERBOARD (worst 10 by field_accuracy)
+------------------------+-------+----------+----------------+
| field                  | type  | accuracy | dominant_error |
+------------------------+-------+----------+----------------+
| amendment_type         | enum  | 0.71     | ENUM_MISMATCH  |
| severity_level         | ord   | 0.74     | OFF_BY_ONE     |
| m1_regulation_penalties| list  | 0.77     | FALSE_POSITIVE |
| ...                    |       |          |                |

4. CLASSIFICATION DETAIL (per enum field)
domain_code:  acc=0.84  macro-F1=0.79  worst class: TAX (F1 0.55)
is_sme_relevant: acc=0.88  P=0.86 R=0.90 F1=0.88

5. CALIBRATION (separate from accuracy)
classifier_confidence: ECE=0.061  Brier=0.112  (bins of 0.1)
metadata_confidence:   ECE=0.093  Brier=0.140

6. LIST-OUTPUT DETAIL
m1_sub_documents:      micro-P=0.90 R=0.86 F1=0.88
m1_regulation_penalties: micro-P=0.79 R=0.75 F1=0.77

7. ERROR TAXONOMY COUNTS
ID_MISMATCH 4 | MISSING_PRED 22 | EXTRA_PRED 9 | ENUM_MISMATCH 61 | ...

8. BAND VERDICT
overall weighted 0.913 -> ACCEPTABLE (upper). Blocker: amendment_type POOR.
```

Persist the same numbers to the SQL tables in Section H so the report is regenerable and trends are queryable.

---

## F. Scoring text fields (`raw_text`, `cleaned_text`, `classification_chunk`)

Text is never scored by exact equality. Pipeline:

1. **Normalize** both sides identically: Unicode NFC, collapse whitespace, strip control chars. For `raw_text` keep case and punctuation (OCR fidelity matters); for `cleaned_text`/`classification_chunk` apply the *same* cleaning the pipeline claims to apply, then compare.
2. **Primary metric — normalized similarity.** Use token-level similarity to avoid length bias:
   - `similarity = 1 − (levenshtein(tok_p, tok_g) / max(len(tok_p), len(tok_g)))` at token granularity, or Jaccard/ROUGE-L F1 over tokens. Report one consistently.
3. **OCR-sensitive fields (`raw_text`)** additionally get **CER** and **WER**:
   - `CER = edit_distance(chars_p, chars_g) / len(chars_g)`
   - `WER = edit_distance(words_p, words_g) / len(words_g)`
   - Field score for `raw_text` = `1 − CER` (clamped to `[0,1]`), with WER reported alongside.
4. **Pass bands for text:** similarity ≥ 0.95 excellent, ≥ 0.85 acceptable, < 0.85 poor. For multilingual (Sinhala/Tamil) content, compute per-language so a weak script doesn't hide in the average.
5. **Empty handling:** gold non-empty & pred empty → score 0, `EMPTY_TEXT`. Both empty (and gold expects empty) → 1.0.

---

## G. Scoring list outputs (`m1_sub_documents`, `m1_regulation_penalties`)

These are lists of structured objects. Score with **set-based precision / recall / F1** after element matching.

1. **Define an element key** per list:
   - `m1_sub_documents`: `(sub_doc_number | title_hash)` or normalized `title`.
   - `m1_regulation_penalties`: `(regulation_ref, penalty_type)`.
2. **Match** predicted elements to gold elements on the key (Hungarian / greedy on key equality; for fuzzy titles allow ≥0.9 similarity to count as the same element).
3. **Field-level partial credit within a matched pair:** each matched pair scores the mean of its attribute comparators (attributes scored by their own type from Section C). A matched pair with all attributes correct = 1.0.
4. **Counts:**
   - `TP` = matched pairs (weighted by their pair score for *soft* F1, or count only ≥0.5 pairs for *hard* F1).
   - `FP` = predicted elements with no gold match → `EXTRA_PRED` / `FALSE_POSITIVE`.
   - `FN` = gold elements with no predicted match → `MISSING_PRED` / `FALSE_NEGATIVE`.
5. **Metrics:**
   ```
   precision = TP / (TP + FP)
   recall    = TP / (TP + FN)
   f1        = 2PR / (P + R)
   ```
   The field's per-record score = its F1 for that record; the field's dataset score = **micro-F1** (pool TP/FP/FN across records) with **macro-F1** reported for balance.
6. **Empty lists:** gold empty & pred empty → 1.0 (define P=R=F1=1 by convention). Gold empty & pred non-empty → all FP. Gold non-empty & pred empty → all FN.

---

## H. Scoring classification outputs

`domain_code`, `change_category`, `severity_level`, `is_sme_relevant`.

**General:** per-field compute accuracy **and** per-class precision/recall/F1, plus a confusion matrix. Report **macro-F1** (treats rare classes fairly) and **micro-F1** (overall). Persist the confusion matrix — it drives the "worst class" callout.

**`domain_code`, `change_category` (nominal enums):**
- Score 1.0 iff `p == g` after canonicalization (upper-case, map synonyms via a fixed alias table). No partial credit.
- Unknown/unseen label predicted → `ENUM_UNKNOWN` (score 0).

**`severity_level` (ordinal enum, e.g. LOW<MEDIUM<HIGH<CRITICAL):**
- Exact match = 1.0.
- **Off-by-one credit:** adjacent level = 0.5 (`OFF_BY_ONE`); ≥2 apart = 0.0. Report both the strict accuracy (exact only) and the ordinal-credited score.
- Also report **MAE** over the integer-encoded levels.

**`is_sme_relevant` (boolean):**
- Treat as binary classification. Report accuracy, precision, recall, F1, and confusion counts (TP/TN/FP/FN).
- Because SME-relevance is the product-critical label, also report **recall at fixed precision** and flag if recall < band.

**Null-aware enum rule (all of the above + `amendment_type`):**
- gold null & pred null → 1.0 (correct abstention).
- gold null & pred value → `FALSE_POSITIVE` (0).
- gold value & pred null → `MISSING_PRED` (0).
- gold value & pred different value → `ENUM_MISMATCH` (0).

**Confidence, always separate:** `classifier_confidence` is evaluated by ECE + Brier against the correctness of `domain_code`/`is_sme_relevant`, never mixed into accuracy.

---

## Edge cases & failure handling (error taxonomy)

Every comparator emits one code. Fixed taxonomy:

| Code | Meaning | Field score |
|---|---|---|
| `OK` | matched within tolerance | 1.0 (or partial) |
| `NULL_MATCH` | both null, null expected | 1.0 |
| `MISSING_PRED` | gold has value, pred null/absent | 0.0 |
| `EXTRA_PRED` | pred has value, gold expects none | 0.0 (counts as FP) |
| `ID_MISMATCH` | identifier differs | 0.0 (hard) |
| `ENUM_MISMATCH` | wrong enum label | 0.0 |
| `ENUM_UNKNOWN` | label outside allowed set | 0.0 |
| `OFF_BY_ONE` | adjacent ordinal | 0.5 |
| `TEXT_LOW_SIM` | similarity below band | = similarity |
| `EMPTY_TEXT` | gold non-empty, pred empty | 0.0 |
| `TIMESTAMP_OOB` | outside tolerance window | 0.0 |
| `MALFORMED` | unparseable / type error / bad JSON | 0.0 + quarantine |
| `SCHEMA_VIOLATION` | field present but wrong type/shape | 0.0 |
| `UNJOINED` | pred record has no gold match | record excluded from field acc, counted in join report |
| `NOT_APPLICABLE` | field out of scope for status | excluded from V(r) |

Handling rules:

- **Nulls:** null is only a failure when gold is non-null. Distinguish gold-null (scored, expects null) from not-applicable (out of stage scope, excluded).
- **Missing predictions:** a whole missing predicted record → `UNJOINED`, reported in a join-coverage line; do not silently drop (that would inflate accuracy). A missing *field* on a joined record → `MISSING_PRED`.
- **Extra predictions:** predicted record with no gold → `UNJOINED_EXTRA`; predicted list element with no gold → `EXTRA_PRED` (hurts precision).
- **Malformed values:** never crash the evaluator. Wrap each comparator in try/except; on failure emit `MALFORMED`, score 0, and write the raw value to a quarantine table for manual review.
- **Status mismatch:** if `pred_status < gold_status`, score cumulative fields up to `pred_status` normally and mark all higher-stage fields `MISSING_PRED`; also increment the progression failure counter. If `pred_status > gold_status` (over-processed), score against gold's field set and flag `OVER_PROCESSED`.

---

## Threshold bands

Applied to `field_accuracy`, `stage cumulative`, and `overall` alike.

| Band | Score range | Action |
|---|---|---|
| Excellent | ≥ 0.95 | ship |
| Good | 0.90 – 0.949 | ship, monitor |
| Acceptable | 0.80 – 0.899 | ship with owner sign-off |
| Poor | 0.65 – 0.799 | block release of that field/stage |
| Critical | < 0.65 | pipeline defect, halt |

Overrides: any **hard identifier** field below 0.99 is automatically **Critical** regardless of the table. `is_sme_relevant` recall below 0.85 is **Poor** regardless of accuracy.

---

## SQL-friendly schema for storing results

```sql
-- One row per evaluation run
CREATE TABLE eval_run (
  run_id            UUID PRIMARY KEY,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  pipeline_git_sha  TEXT,
  baseline_file     TEXT NOT NULL,
  baseline_sha256   CHAR(64) NOT NULL,
  baseline_verified BOOLEAN NOT NULL,
  snapshot_label    TEXT,                 -- 'EGZ 2026-02'
  n_records         INT,
  scoring_model     TEXT CHECK (scoring_model IN ('weighted','non_weighted'))
);

-- One row per (record, field) comparison  -- the atomic fact table
CREATE TABLE eval_field_result (
  run_id        UUID REFERENCES eval_run(run_id),
  record_key    TEXT NOT NULL,            -- gazette_number|document_number
  gold_status   TEXT NOT NULL,
  pred_status   TEXT,
  stage         TEXT NOT NULL,            -- stage that introduced the field
  field_name    TEXT NOT NULL,
  field_type    TEXT NOT NULL,            -- identifier|text|enum|bool|timestamp|list|confidence
  gold_value    JSONB,
  pred_value    JSONB,
  score         NUMERIC(5,4) NOT NULL,    -- 0..1
  weight        NUMERIC(4,2) NOT NULL DEFAULT 1,
  error_code    TEXT NOT NULL,
  in_scope      BOOLEAN NOT NULL,         -- false = NOT_APPLICABLE
  PRIMARY KEY (run_id, record_key, field_name)
);

-- One row per (record) roll-up
CREATE TABLE eval_record_result (
  run_id         UUID REFERENCES eval_run(run_id),
  record_key     TEXT NOT NULL,
  gold_status    TEXT, pred_status TEXT,
  record_score   NUMERIC(5,4),
  record_score_w NUMERIC(5,4),
  n_fields       INT, n_missing INT, n_extra INT,
  progression_ok BOOLEAN,
  PRIMARY KEY (run_id, record_key)
);

-- One row per (stage) roll-up
CREATE TABLE eval_stage_result (
  run_id        UUID REFERENCES eval_run(run_id),
  stage         TEXT NOT NULL,
  n             INT,
  stage_only    NUMERIC(5,4),
  cumulative    NUMERIC(5,4),
  progression   NUMERIC(5,4),
  band          TEXT,
  PRIMARY KEY (run_id, stage)
);

-- Classification / list detail (per enum or list field)
CREATE TABLE eval_classification_detail (
  run_id UUID, field_name TEXT, class_label TEXT,
  tp INT, fp INT, fn INT,
  precision NUMERIC(5,4), recall NUMERIC(5,4), f1 NUMERIC(5,4),
  PRIMARY KEY (run_id, field_name, class_label)
);

-- Calibration detail (confidence fields)
CREATE TABLE eval_calibration (
  run_id UUID, field_name TEXT,
  ece NUMERIC(5,4), brier NUMERIC(5,4), bins INT,
  PRIMARY KEY (run_id, field_name)
);

-- Quarantine for MALFORMED / SCHEMA_VIOLATION
CREATE TABLE eval_quarantine (
  run_id UUID, record_key TEXT, field_name TEXT,
  raw_pred TEXT, reason TEXT, PRIMARY KEY (run_id, record_key, field_name)
);
```

`eval_field_result` is the single source of truth; every table above and every report number is a `GROUP BY` over it. Example — stage cumulative:

```sql
SELECT stage,
       AVG(score) FILTER (WHERE in_scope) AS cumulative
FROM eval_field_result
WHERE run_id = :run
GROUP BY stage;
```

---

## Example scoring table (single record, gold_status = classified)

| field | gold | pred | type | score | error |
|---|---|---|---|---|---|
| gazette_number | 2381/45 | 2381/45 | id | 1.00 | OK |
| document_number | D-118 | D-118 | id | 1.00 | OK |
| sha256 | a1b2… | a1b2… | hash | 1.00 | OK |
| pdf_pages | 12 | 12 | int | 1.00 | OK |
| language | si | si | enum | 1.00 | OK |
| raw_text | (4.1k chars) | (4.0k) | text | 0.96 | OK (CER 0.04) |
| cleaned_text | … | … | text | 0.93 | OK |
| amendment_type | AMEND | NULL | enum | 0.00 | MISSING_PRED |
| m1_sub_documents | 3 items | 3 items | list | 0.88 | OK (F1) |
| m1_regulation_penalties | 2 items | 3 items | list | 0.67 | EXTRA_PRED |
| domain_code | LABOUR | LABOUR | enum | 1.00 | OK |
| change_category | NEW | AMEND | enum | 0.00 | ENUM_MISMATCH |
| severity_level | HIGH | CRITICAL | ord | 0.50 | OFF_BY_ONE |
| is_sme_relevant | true | true | bool | 1.00 | OK |
| classified_at | 02-14 09:00 | 02-14 09:03 | ts | 1.00 | OK (≤24h) |
| classifier_confidence | — | 0.81 | conf | — | calibration only |

Non-weighted record_score = mean of scored fields (exclude confidence) = **0.812**.
Weighted record_score (§D weights) ≈ **0.86** (ids/structural lift it; text/timestamp low weight).

---

## Pseudocode — evaluator

```python
def evaluate(run, gold_rows, pred_rows):
    assert sha256(run.baseline_file) == run.manifest_sha, "sealed baseline changed"
    pred_by_key = index(pred_rows, key=natural_key)

    for g in gold_rows:
        p = pred_by_key.get(natural_key(g))
        if p is None:
            emit_unjoined(run, g); continue

        fields = cumulative_fields(g.status)          # §B, status gate
        for f in dedupe(fields):
            if not applicable(f, g):                  # NOT_APPLICABLE
                write_field(run, g, f, score=None, in_scope=False, err='NOT_APPLICABLE')
                continue
            try:
                score, err = COMPARATORS[type_of(f)](p.get(f), g.get(f), f)
            except Exception:
                score, err = 0.0, 'MALFORMED'
                quarantine(run, g, f, p.get(f))
            write_field(run, g, f, score, weight(f), err, in_scope=True)

        roll_up_record(run, g, p)

    for s in STAGE_ORDER: roll_up_stage(run, s)
    compute_classification_detail(run)   # P/R/F1 + confusion per enum/list field
    compute_calibration(run)             # ECE/Brier for confidence fields
    assign_bands(run)                    # §thresholds, with id/recall overrides

# comparator dispatch
COMPARATORS = {
  'identifier': cmp_exact_norm,      'text': cmp_text_sim,
  'enum':       cmp_enum_nullaware,  'bool': cmp_bool,
  'ordinal':    cmp_ordinal,         'timestamp': cmp_timestamp_window,
  'int':        cmp_int_exact,       'hash': cmp_exact,
  'list':       cmp_list_prf1,       'confidence': cmp_noop_calibration,
}

def cmp_enum_nullaware(p, g, f):
    if p is None and g is None: return 1.0, 'NULL_MATCH'
    if g is None and p is not None: return 0.0, 'FALSE_POSITIVE'
    if p is None: return 0.0, 'MISSING_PRED'
    if canon(p) not in ALLOWED[f]: return 0.0, 'ENUM_UNKNOWN'
    return (1.0,'OK') if canon(p)==canon(g) else (0.0,'ENUM_MISMATCH')

def cmp_list_prf1(p, g, f):
    tp, fp, fn = match_elements(p or [], g or [], key=LIST_KEY[f])
    if not g and not p: return 1.0, 'NULL_MATCH'
    P = tp/(tp+fp) if tp+fp else 0
    R = tp/(tp+fn) if tp+fn else 0
    f1 = 2*P*R/(P+R) if P+R else 0
    err = 'OK' if f1>=0.5 else ('EXTRA_PRED' if fp>fn else 'MISSING_PRED')
    return f1, err
```

---

## Final recommendation — production-ready design

Run **both** scoring models but gate releases on the **weighted** model, and report the **non-weighted micro + macro** alongside it for transparency.

1. **Weighted, cumulative-through-stage** is the release gate: it reflects that a wrong identifier or wrong SME-relevance label matters more than a few OCR characters, and cumulative scoring stops upstream corruption from being forgotten at the classifier.
2. **Non-weighted micro & macro** are the honesty check — publish them so weighting can never quietly hide a weak field. If weighted and non-weighted diverge sharply, investigate the weights, not the pipeline.
3. **Keep correctness and calibration strictly separate.** Confidence fields never touch the accuracy number; they get ECE/Brier only.
4. **The atomic `eval_field_result` table is the contract.** Every headline metric is a query over it, so results are reproducible, diffable across `run_id`, and trend-able over time.
5. **Enforce the sealed baseline** with a checksum gate on every run and treat identifier/SME-relevance thresholds as hard overrides that can fail an otherwise-passing run.
6. **Report at three granularities every run** — field, record, stage — plus the error-taxonomy histogram, because a single overall number cannot tell you *where* to fix the pipeline; the worst-field leaderboard can.

For your current data: score Gold v1 (~800 rows) as the field-accuracy authority, and use the v2 DB snapshot (204 preprocessed rows) for stage-progression and regression tracking, since most of it stops at `preprocessed` and cannot exercise the `classified` field set yet.
