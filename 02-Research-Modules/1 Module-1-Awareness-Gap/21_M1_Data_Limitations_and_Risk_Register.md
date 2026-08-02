# 21 — Module 1: Data Limitations and Risk Register

> Every limitation affecting the M1 classification data: where it occurred, why, whether it is resolved, what it does to evaluation, and the exact wording it needs in the lock manifest. Written so a reader can find any known weakness here rather than discovering it in a viva.
>
> Companion to [[18_M1_Dataset_And_Model_Lineage]] (what the data is), [[03_M1_Data_Collection]] (how it was collected), [[06_M1_Training_Evaluation]] (how it will be spent), and [[22_M1_Data_Usage_and_Row_Count_Register]] (how much of it there is).

> [!warning] Status — 2026-08-02
> Fresh Holdout v3 is **ready for lock validation, with declared limitations**. It is not ready for evaluation: Step 55A must pass first.
> The v1/v2 hard blocker (`general_retail`) is **resolved** at 29 positives against a minimum of 20. Two category shortfalls remain and are **source limitations, not annotation failures**.

---

## 1. Executive position

```text
Proceed to Step 55A — Fresh Holdout v3 lock validation.
Lock v3 with declared limitations.
Do not evaluate before the lock passes.
Do not rerun old Step 50.
Do not tune thresholds on the holdout.
```

The distinction that governs this whole document: a limitation that is **declared** is a scope statement, and a limitation that is **discovered afterwards** is a finding against the work. Everything below is written to be declared in advance.

Current v3 state:

```text
Rows                286
Structural checks   pass
Categories          all 8 populated · 6 of 8 targets met
Sector minimums     all 3 met (20 each)
Model runs          none
Evaluation          none
Promotion           blocked
```

Remaining open limitations:

```text
EPF_ETF_CHANGE       3 / 8
PENALTY_ENFORCEMENT  10 / 15  (all 10 sector-NONE)
Language             English only
Extraction           page 1 only
Sampling             targeted/stratified, not random or temporal
Row count            286, above the original 150–200 intake window
```

---

## 2. Severity register

| ID | Limitation | Severity | Status | What it does to evaluation |
|---|---|---|---|---|
| **L1** | `EPF_ETF_CHANGE` support = 3 (target 8) | High | **Open** | per-class F1 unstable; one flip moves it up to 0.33 |
| **L2** | `PENALTY_ENFORCEMENT` support = 10 (target 15) | Medium-High | **Open** | thin class metric |
| **L3** | all 10 `PENALTY_ENFORCEMENT` rows are sector-`NONE` | High for sector analysis | **Open** | SME-facing penalty *sectors* untested |
| **L4** | page-1-only extraction | Medium | **Open** | Schedules invisible to the model; some labels rest on context the model never sees |
| **L5** | English-only holdout | Medium | **Open** | no SI/TA claim can rest on this evaluation |
| **L6** | targeted/stratified source pool | Medium | **Open** | diagnostic metric, not a population estimate |
| **L7** | 286 rows vs the 150–200 intake window | Low-Medium | **Open** | spec deviation; declare, don't hide |
| **L8** | formulaic families over-represented | Medium | **Open** | macro metrics partly measure boilerplate recognition |
| **L9** | some sector labels use title/source context beyond model text | Medium | **Open** | those errors are evidence-limited, not purely model-limited |
| **L10** | `row_count_in_150_200: true` in the creation summary | Low but corrosive | **Fix in manifest** | a self-contradicting validation flag discredits the other checks |
| R1 | `IMPORT_EXPORT` = 0 in v1 | was High | **Resolved** (22) | — |
| R2 | `general_retail` below minimum in v1/v2 | was Blocking | **Resolved** (29) | — |
| R3 | SME-irrelevant majority in v2 | was Medium | **Resolved** (46.9 %) | — |
| R4 | training-source PDFs in the local cache | was Critical | **Mitigated** by the gazette-id gate | — |

---

## 3. Open limitations

### L1 — `EPF_ETF_CHANGE` is under-supported at 3 / 8

**Where:** v1, v2 and v3 alike. The count never moved: 3 → 3 → 3.

**Why.** Three independent searches across all 39,649 indexed extraordinary gazette items returned **zero** genuine EPF or ETF instruments. This is not a search-quality problem. EPF and ETF rules are published through Department of Labour circulars, Central Bank notices and ETF Board notices — not extraordinary gazettes. The three rows carried here are provincial Co-operative Employees' Pension Scheme instruments: contributory employee-fund rules, but not EPF or ETF proper.

**Effect.** With support 3, per-class F1 has three possible denominators and one prediction flip moves it by up to 0.33 — which propagates to roughly 0.04 on an 8-class macro average. That is over three times the 0.0117 margin that failed the Step 50 sector gate. A macro-F1 that includes this class is not wrong, but it is fragile, and any reader who checks will notice.

**Declare:**

> `EPF_ETF_CHANGE` is under-supported at 3/8. This is a source limitation, not an annotation shortcut. Repeated searches of the indexed extraordinary Gazette source pool produced no additional genuine EPF/ETF instruments. Full evaluation of this class requires Department of Labour EPF circulars, Central Bank notices, ETF Board notices, or another non-Gazette source.

**Do not** fabricate rows, and do not stretch adjacent pension instruments into the class to make the count. The honest alternatives are to source the other channels or to declare the class out of scope for this holdout.

### L2 / L3 — `PENALTY_ENFORCEMENT` is 10 / 15, and all 10 carry no sector

**Where:** v1 (2) → v2 (10) → v3 (10).

**Why.** What surfaces from gazette titles is property forfeitures, provincial court-fines statutes, a prosecution-jurisdiction regulation and sports-offence investigation units. None imposes an offence, fine or inspection duty on a grocery, food-service or general-retail business. The SME-facing offence provisions genuinely exist — inside the Schedules of Pradeshiya Sabha and Municipal Council trade by-laws, several of which are already in this set — but those Schedules sit on page 2 and later, and the extraction is page-1 only (**L4**). Reaching them means changing the extraction scope for one instrument family, which would make those rows structurally unlike the other 280.

**Effect.** The category is testable as a *category*. Sector attribution within it is not testable at all: with every row `NONE`, the sector head can score perfectly on these rows by predicting nothing.

**Declare:**

> `PENALTY_ENFORCEMENT` is under-supported at 10/15, and all 10 rows are `affected_sectors=NONE`. The holdout tests category recognition for penalty/enforcement instruments but does not test SME-facing penalty or inspection duties, because those provisions sit in later by-law schedules outside the page-1 extraction scope.

### L4 — page-1-only extraction

**Recipe:** `pdftotext -layout -f 1 -l 1`, whitespace collapsed, five boilerplate strings stripped.

**Why it matters.** Sri Lankan gazette instruments routinely carry the operative content in a Schedule beyond page 1. Special Commodity Levy orders say only "the commodities specified in Column I of the Schedule"; Imports and Exports (Control) regulations carry their controlled-goods lists past page 1; by-law offence clauses sit in later Schedules.

**Effect.** For some rows the text the model sees does **not** contain the information the annotator used. 23 levy rows never name their commodity; 21 of 22 `IMPORT_EXPORT` rows carry `NONE`. Sector errors on those rows are partly an evidence limitation, not purely a model limitation — see **L9**.

**Declare:**

> The holdout uses page-1-only extraction for structural consistency with the intake recipe. Some instruments place goods schedules or offence clauses on later pages; sector labels for those rows are weaker, and some enforcement provisions are not observable in the model input text.

Do not change the extraction scope after lock. A mid-stream change produces a set whose rows are not comparable to each other; if the scope needs to change, that is a new holdout version.

### L5 — English-only

`language_counts: { en: 286 }`. Only `_E.pdf` editions were collected; Sinhala and Tamil editions were not downloaded.

**Effect.** RQ2 asks whether multilingual models handle EN/SI/TA without per-language pipelines. **This holdout cannot answer it.** XLM-R's multilingual capability is untested here.

**Declare:**

> Fresh Holdout v3 is English-only. Metrics from this holdout cannot be used as evidence of Sinhala or Tamil performance.

A separate SI/TA holdout is required before any trilingual claim. See [[10_M1_Sinhala_Tamil_NLP]].

### L6 — targeted / stratified source pool

The pool was assembled by keyword-targeted mining of gazette listing titles to close specific category and sector gaps. It is not random, not temporal and not proportional to publication volume.

**Effect.** Rare categories are over-represented relative to deployment traffic. The resulting metrics are **promotion-gate diagnostics**, not an estimate of field performance.

**Declare:**

> This holdout is targeted/stratified to test known weak categories and SME sectors. It is not a random sample of Gazette publications, so reported metrics are diagnostic and gate-specific rather than a population estimate of deployment performance.

This one matters for the thesis framing more than for the gate. A deployment-performance claim needs a random or temporal sample; this set was never built to support one.

### L7 — 286 rows against a 150–200 window

The intake spec named 150–200 rows. v3 has 286, because closing `IMPORT_EXPORT`, `PRODUCT_STANDARD`, `BUSINESS_REGISTRATION`, `SECTOR_SPECIFIC` and `general_retail` with real source-backed rows took two top-up rounds.

More evaluation data is not a statistical problem. The deviation from spec still gets declared, and the manifest should mark the size requirement **relaxed**, not **passed**.

**Optional mitigation, and only before evaluation:** subsampling the two formulaic families (**L8**) would restore the count and raise every other class's relative weight without touching category coverage or the sector minimums. This is a research-design decision, not a cleanup task — the full 286 is a reproducible base either way.

### L8 — formulaic over-representation

`LABOUR_LAW` (88) and `TAX_RATE_CHANGE` (58) are internally repetitive: 25 near-identical cocoa/cardamom/pepper cost-of-living allowance notices, 42 single-employer industrial dispute and collective agreement notices, 54 Special Commodity Levy orders.

**Effect.** A model can score well on these by recognising boilerplate. Macro metrics are then partly a measure of template recognition rather than semantic classification.

**Declare, and mitigate in reporting:**

> The holdout contains formulaic legal-notice families, especially in LABOUR_LAW and TAX_RATE_CHANGE. Per-class support and family-level error analysis are reported alongside macro metrics.

Family-level error analysis is the cheap fix: if the 25 cocoa/cardamom notices are all correct and all near-identical, they are approximately one test case, and the report should say so.

### L9 — some labels rest on context beyond the model's input

Most visible in the Special Commodity Levy rows and the import/export control rows. The annotator had the official title, the enabling Act and the provenance record; the model gets page-1 text that references a Schedule it cannot see.

**Effect.** Sector errors on those rows are partly evidence-limited. Counting them purely as model errors understates the model and misdirects any error analysis that follows.

**Declare:**

> Some sector labels rely partly on official title/source context because the page-1 extracted text references schedules without naming commodities. These rows are flagged in `annotation_notes` and `reason_for_sector` and may be excluded from sector-only sensitivity checks.

The flags already exist per row, so a sensitivity analysis with and without them is available at reporting time and costs nothing.

### L10 — the metadata flag that contradicts itself

`fresh_holdout_creation_summary.json` reports `row_count: 286` and `validation.row_count_in_150_200: true` in the same object. 286 is not in 150–200.

Small, and worth fixing before anyone else finds it. A validation block that passes a check it demonstrably fails invites the question of which other checks were asserted rather than computed. Correct the flag or override it in the lock manifest as **"original size window relaxed, not passed"** (**L7**).

---

## 4. Resolved limitations, kept for the record

These are retained because the *process* by which each was caught is part of the methodology.

### R1 — `IMPORT_EXPORT` was zero in v1

193 labelled rows and not one import/export licence, control, restriction or prohibition. The nearest candidate — a Customs Ordinance Revenue Protection Order fixing import duty rates — belongs to `TAX_RATE_CHANGE`.

Had v1 been locked, `IMPORT_EXPORT` F1 would have been undefined and the macro average would have silently dropped a category. **Resolved:** 0 → 17 (v2) → **22** (v3), target met.

### R2 — `general_retail` below the sector minimum

10 (v1) → 11 (v2) → **29** (v3), against a minimum of 20. The blocker held for two rounds because title matching does not work for sector attribution: searching descriptions for "textile", "electronics" or "hardware" returned council prorogations and wage-board appointments.

The fix came from Consumer Affairs Authority instruments on non-food goods — cement maximum-retail-price orders, LPG cylinder pricing and weight marking, paint and varnish labelling with lead declarations, skin-cream heavy-metal limits, marking and shop-registration rules for incense and monastic requisites. **Resolved.**

### R3 — SME-irrelevant rows became the majority in v2

49.2 % (v1) → **53.3 %** (v2) → 46.9 % (v3). The v2 top-up added 32 rows of which 25 were `NONE`, because import-control page-1 text does not identify goods (**L4**).

Worth keeping in the write-up: a top-up that closed the category gaps it targeted while degrading the sector and relevance balance, because extraction scope — not sampling — determined what the new rows could carry. **Resolved** by round 2.

### R4 — the local cache would have leaked training data

The repository holds 372 cached gazette PDFs. 193 are the intake holdout rows. Of the remaining 202 — the ones that *look* available — **128 are source PDFs for the V6 train, validation and test splits.**

> **A candidate being unused by the holdout is not the same as a candidate being unused.**

Selecting on "not already in the holdout" would have scored the model against its own training data and produced excellent, meaningless numbers. The gazette-id gate caught all 128; 60 gap-closing candidates were rejected by it.

**Mitigated, and now a permanent rule:** never select top-up rows by absence from the holdout. Always gate on gazette id against every consumed split, plus exact-text hash and near-duplicate Jaccard. Full gate: [[03_M1_Data_Collection]] §∞ Step 54A.

---

## 5. Failure modes that were avoided

Recorded because their absence is only credible if it was deliberate.

| Risk | Status | Evidence |
|---|---|---|
| Synthetic or rewritten gazette text | **avoided** | every row is verbatim `pdftotext` output from a source PDF, provenance recorded per row |
| Labels influenced by model predictions | **avoided** | no model was loaded, run or evaluated during any collection round |
| Reusing the consumed old Step 50 test | **avoided** | recorded as consumed; `old_step50_do_not_rerun: true` in the candidate registry |
| Training leakage from the local cache | **mitigated** | four-part leakage gate; 128 training-source PDFs excluded |
| Quietly dropping hard rows | **avoided** | 3 rows dropped at annotation, each with a written reason, before any model contact |

The three dropped rows: two Local Authorities Elections Ordinance notices about a councillor forfeiting a nomination-paper place (matched the target list on "forfeited", but not business regulation and fitting none of the eight categories), and one North Central Province draft standard by-law whose page-1 text is publishing preamble and never states its subject. Labelling that last one from its listing title would have reproduced exactly the failure mode the exercise guards against.

---

## 6. Lock manifest declaration — use verbatim

```text
Fresh Holdout v3 is locked with declared limitations.

The dataset contains 286 real, source-backed, English Gazette rows. Structural
checks pass, all 8 categories are populated, and all 3 SME sector minimums are
met: grocery_retail=136, food_service=88, general_retail=29.

Six of eight category targets are met. EPF_ETF_CHANGE remains under-supported at
3/8 because genuine EPF/ETF instruments were not found in the indexed
extraordinary Gazette source pool after repeated searches; full evaluation of
this class requires Department of Labour, Central Bank, ETF Board, or other
non-Gazette sources.

PENALTY_ENFORCEMENT remains under-supported at 10/15, and all 10 rows are
affected_sectors=NONE. The available Gazette-title instruments do not contain
SME-facing offence or inspection duties on page 1; such provisions generally
appear in later by-law schedules outside the page-1 extraction scope.

The holdout is English-only and targeted/stratified rather than random. Metrics
should be interpreted as promotion-gate diagnostic metrics, not as an unbiased
estimate of field performance across all languages or Gazette publications.

The row count is 286, above the original 150-200 intake window. This size was
accepted to satisfy category and sector coverage. Any metadata flag claiming
row_count_in_150_200=true must be corrected or overridden as a relaxed
requirement.
```

---

## 7. Reporting rules carried into evaluation

When the seed13 candidate is evaluated on locked v3, the report must carry:

```text
category macro-F1, weighted-F1, accuracy
category per-class precision / recall / F1 / SUPPORT
sector macro-F1, micro-F1, exact match, Hamming loss
sector per-label precision / recall / F1 / SUPPORT
relevance derived from sectors: F1 and accuracy
auxiliary relevance head, labelled diagnostic
confusion matrix, error table, error-overlap counts
family-level error analysis for the formulaic notice families
every limitation in this register, attached to the metrics
```

Explicitly stated in the results, not the appendix:

```text
EPF_ETF_CHANGE support = 3
PENALTY_ENFORCEMENT support = 10 (all sector-NONE)
English-only
page-1 extraction
targeted/stratified source pool
row count 286
old Step 50 not reused
thresholds frozen from validation: grocery 0.45 / food 0.45 / general 0.75
```

**Report macro-F1 both with and without L1/L2 classes**, labelled. Do not tune thresholds on v3.

---

## 8. Current status

```text
Fresh Holdout v3
  usable for lock validation           YES
  usable for evaluation before lock    NO
  usable for the promotion gate        YES, with declared limitations

Open       L1 L2 L3 L4 L5 L6 L7 L8 L9
Fix now    L10 (manifest wording)
Resolved   R1 R2 R3 R4

Next       Step 55A — lock validation
```

---

## 9. Cross-references

- Holdout contents, distributions and leakage status: [[18_M1_Dataset_And_Model_Lineage]] §∞ Fresh locked holdout v3
- Candidate lineage and the failed strict gate: [[18_M1_Dataset_And_Model_Lineage]] §∞ V7-M multitask line · [[20_M1_Multitask_Classifier_Upgrade]] §∞ V7-M line
- Collection method, leakage gates, version progression: [[03_M1_Data_Collection]] §∞ Step 54A
- Lock checklist and one-shot evaluation protocol: [[06_M1_Training_Evaluation]] §∞ Step 55A/55B
- Row counts and usage rules: [[22_M1_Data_Usage_and_Row_Count_Register]]
- Label taxonomy and sector definitions: [[09_M1_Annotation_Guidelines]]
- Language coverage: [[10_M1_Sinhala_Tamil_NLP]]
