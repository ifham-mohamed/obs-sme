---
title: "Module 1 — Report vs Vault Gap Analysis"
date: 2026-08-02
report: "28_Enigmatrix _Final_Draft_Report.pdf + G28 - Enigmatrix - Final Report (Module 1 - Ifham Mohamed).docx"
vault: "E:\\Obsidian\\sme\\02-Research-Modules\\1 Module-1-Awareness-Gap\\"
---

# Module 1 — how far the submitted report is behind the vault

**Verdict: roughly three weeks and one architecture decision.**

The report was written against the state of the module in mid-July 2026, when XLM-RoBERTa with LoRA adapters was still the intended production classifier and the gold set stood at 800 rows. Between 2026-07-26 and 2026-08-02 the module changed in five ways the report has no account of:

1. a four-model bake-off **rejected the transformer** and froze a lexical classifier instead;
2. the confidence contract changed from probability to **uncalibrated margin**, which cascaded into the schema, the API and the review queue;
3. the gold set grew from 800 to **1,128 adjudicated rows** and the reporting split moved to 777 / 166 / 167;
4. three subsystems shipped that the report never describes — **tier-weighted EQS**, **manual stage stepping**, and the **inverted NLLB lease-queue**;
5. two headline capabilities were **measured for the first time and failed** — SI/TA numeric preservation at 6.58%, and SME survey recruitment at zero.

Nothing here is a difference of opinion. Every row below is a claim in the report contradicted by a dated artefact in the vault.

---

## 1. Severity classes

| Class | Meaning | Count |
|---|---|---:|
| **A — factually wrong** | The report asserts something the vault disproves. Must change before submission. | 12 |
| **B — materially incomplete** | The report is not wrong but omits a subsystem or constraint that changes how a result should be read. | 11 |
| **C — presentational** | Numbering, table provenance, wording. | 5 |

---

## 2. Class A — factually wrong

| # | Report claim | Where in the report | Vault truth | Evidence |
|---|---|---|---|---|
| A1 | Production classifier is XLM-R + LoRA dual head served through ONNX | I §4.2.2, §5.3.1, Fig 2, Fig 10, Fig 13; II §4.2, §5.3.1 | TF-IDF + `LinearSVC(class_weight="balanced")`, frozen at `models/m1/linearsvc_v6_primary/` | `final/works/11_CLASSIFIER_FREEZE_AND_INTEGRATION.md` §0, §4 |
| A2 | Headline classifier result is test macro-F1 0.6415 with `gate_pass false` | I Fig 21; II §7.2 | Temporal test **0.947220**, validation 0.924476, accuracy 0.958084 (160/167), gate ≥ 0.92 passed | same, §4 |
| A3 | ONNX artefact is exported, INT8-quantised and serving | I §3.2.7, §5.3.1; II §5.3.1, §6.3.1 | **Never exported.** `storage/models/m1/onnx/v1` is empty; the ONNX backend is dormant | same, §5.2 |
| A4 | `classifier_confidence` is a calibrated probability | I §5.3.1, Fig 11, Fig 13; II §5.3.1 | Uncalibrated signed margin. Adapter returns `confidence: null`, `confidence_type: "not_available_uncalibrated_linearsvc"` | same, §7 |
| A5 | Review threshold is 0.55, calibrated in Chapter 7 | I Table 5.3, §7.1.8; II Table 5.3 | **0.40, provisional.** Recorded as `provisional_no_review_outcomes` — zero completed review outcomes exist | `evidence/M1_OPERATING_EVIDENCE_2026-08-02.json` |
| A6 | A 3-label sigmoid sector head is served | I Fig 13, Table 3.5; II Fig 5.11 | **No sector model in production.** Frozen classifier is category-only, returns `sectors: []` | `20_M1_Multitask_Classifier_Upgrade.md` |
| A7 | Gold dataset is 800 rows | I §6.2.2, Table 7.3; II §6.2.2 | **1,128 adjudicated rows** across batches 01–07, 2,256 annotations; 1,110 in the ML branch | `18_M1_Dataset_And_Model_Lineage.md` §1 |
| A8 | Split is 560 / 120 / 120 | I Table 7.4; II Table 7.x | **777 / 166 / 167**, fixed since V5 and byte-identical through V6 | same |
| A9 | IAA is κ 0.8715 / 0.8638 / 0.7235 | I §7.2, Table 7.5; II §7.2 | **κ 0.947215 / 0.965567 / 0.914637** at v3 | `00_INDEX.md` |
| A10 | Status machine has five states | I Fig 11; II Fig 5.9 | Seven: `ingested → extracted → preprocessed → classified → summarized → alerted → archived`, plus `extraction_failed` | `final/works/10_PIPELINE_STAGING_AND_MANUAL_STEPPING.md` §1 |
| A11 | NLLB-200 is called inline between summarisation and publication | I Fig 22, §3.12; II Fig 6.6 | **Inverted lease-queue.** Backend enqueues to `m1_translation_jobs`; Colab pulls via `/worker/lease` and `/worker/submit`; `SELECT … FOR UPDATE SKIP LOCKED` | `final/works/12_TRILINGUAL_TRANSLATION_PIPELINE.md` §2–§3 |
| A12 | Migration state is `202606300001` | I §6.3.1; II §6.3.1 | **`202608010001`** applied live to Supabase; 53 migrations, single head | `final/works/11_…` §6 |

---

## 3. Class B — materially incomplete

| # | Omission | Why it changes the reading | Evidence |
|---|---|---|---|
| B1 | The **bake-off** is not described at all | Without it, the reader cannot tell that the transformer was tested rather than skipped. The negative result is a contribution, not an embarrassment | `11_…` §3 |
| B2 | The **review-queue defect** is unreported | `WHERE classifier_confidence < 0.55` matched nothing on the LinearSVC backend — an empty queue indistinguishable from a clean bill of health. A failure with no error message belongs in the evaluation chapter | `11_…` §6.1 |
| B3 | **Tier-weighted EQS** and the field contract are absent | The report implies an unweighted per-field mean. As built, tiers A/B/C/D/S carry weights 3.0 / 2.0 / 1.0 / 0.0 / 0.0, EQS = Σ(w·m)/Σ(w), gates Tier-A ≥ 0.95 and EQS ≥ 0.90, with classification labels phase-separated out | `final/works/09_PHASE2_MEASUREMENT_EQS_UPGRADE.md` §1.1–1.2 |
| B4 | **Golden truth v2** and its mandatory filter are absent | `structured_v2_combined_1508_official.xlsx` holds 1,508 rows / 52 columns, but only **800 carry field-level truth**. Measuring without `field_truth_verified = TRUE` scores the extractor against blank cells | same, header + §6 |
| B5 | **Measured extraction accuracy is never reported** | 14 completed runs; latest pair score 0.852 (15 fields) and 0.942 (11 fields) over 51 regulations. This is the module's strongest evidence and it is missing from Chapter 7 | report Fig 20 + vault measurement records |
| B6 | **Manual stage stepping** is absent | `auto_advance` parameter, `POST /advance`, `POST /run-all`, `StageStepper` UI — shipped 2026-07-26 | `10_…` §2 |
| B7 | **`classification_source`** tagging is absent | Every row is tagged `heuristic \| model \| expert`. F6 and any category-reading finding **must** facet on it — the 800 F-199 rows are heuristic seed data, not model output | `PHASE5_RESEARCH_FINDINGS_ANALYSIS.md` §0 note 1 |
| B8 | **Matching-precision publish gate** is absent | A false secondary-source match biases the headline lag *downward*. ≥ 0.90 hand-audit is a gate on F1/F2, not a nicety | same, §0 note 2 |
| B9 | **Source registry** understated | 15 DB-backed sources with per-source health and admin API, not 4 portals + 5 feeds. Seed URLs are unconfirmed defaults | `PHASE4_SCHEDULERS_ALERTS_ANALYSIS.md` §1 |
| B10 | **Retraining and canary promotion** absent | `promotion.decide()` (promote/hold/rollback, 0.92 gate, 1 pp regression tolerance), `m1_retraining_runs`, quarterly Beat + drift trigger | `PHASE5_…` §5c |
| B11 | **Reproducibility evidence** absent | Model SHA256, bundle SHA256, and a second-machine re-score returning `0.9472199858964565` to the last digit | `11_…` §4 |

---

## 4. Class C — presentational

| # | Item | Fix |
|---|---|---|
| C1 | Tables 7.3 / 7.4 describe the legacy L1 800-row branch | Label as provenance; the reporting dataset is V6 at n = 1,110 |
| C2 | Figure 13 caption presents V7 as shipped | Re-caption as the design that was executed and rejected |
| C3 | Figure 11 state machine omits three states | Redraw from the Mermaid source in Part II |
| C4 | "800-row gold dataset" appears in the abstract, conclusion and contribution statement | Update all four occurrences consistently |
| C5 | SMS listed as a delivered channel without qualification | Note that the phone column landed only in Session 71 |

---

## 5. Claims in the report that the vault shows to be unmeasured or failed

These are the ones that matter most in a viva, because each is stated or implied as a success.

| Claim as presented | Measured reality | Evidence |
|---|---|---|
| A trilingual product delivering Sinhala and Tamil alerts | English summary generation passes 80/80. **SI/TA numeric preservation passes 10/152 = 6.58%** — gazette identifiers are dropped in translation. 72 summaries reopened, 144 jobs pending. *"No translation-quality success is claimed."* | `final/works/13_OPERATING_EVIDENCE_AND_FIELDWORK.md` |
| An SME awareness survey answering RQ4 | Portal built and browser-verified. **0 of 100** completed unique SMEs; 0 sessions. RQ4 has no primary respondent data | same |
| Findings F1 ≈ 6.8 d, F2 ≈ 21.8 d, F6 ≈ −19.9 d | **Synthetic demo outputs** produced when `DATABASE_URL` is unset. Real inputs are empty | `PHASE5_…` §0 |
| Drift-triggered retraining | Coded, Beat-wired, and **dormant by construction** — the KL check reads `classifier_confidence`, always NULL on the live backend | `03_FEATURE_CHECKLIST.md` |
| Propagation and lag analytics operating | Watchers have never run at scale with a working classifier; `m1_propagation_events` and both lag views effectively empty | `PHASE4_…` §0 |
| A dual-head multitask classifier | V7 executed and rejected. Weighted recovery reached validation category macro-F1 0.899862 but never touched the test split; output records `claim_eligible=false` | `evidence/M1_V7_WEIGHTED_SEED42_VALIDATION_2026-08-02.json` |

---

## 6. The root cause of the sector failure

Worth isolating, because it is the one gap that no amount of engineering closes.

| Pattern | Share of gold rows |
|---|---:|
| No sector at all | **73.2%** |
| All three sectors (of those carrying any) | **84%** |
| Genuinely partial (one or two) | **48 rows = 4.3%** |

A sigmoid head trained on that distribution learns "predict nothing" or "predict everything" — both locally optimal. The V7 collapse to one-or-zero sector predictions is the expected consequence, not a tuning failure. The fix is an annotation round designed to yield partial sector sets, then a re-measure of the distribution, *before* any head is retrained.

---

## 7. Recommended order of repair

| Priority | Action | Closes |
|---|---|---|
| 1 | Replace the classifier narrative in Chapters 4, 5, 6, 7 of both parts | A1–A6, B1, B2 |
| 2 | Replace all dataset figures and Tables 7.3 / 7.4 | A7–A9, C1, C4 |
| 3 | Add the EQS / field-contract section and the 0.852 / 0.942 results to Chapter 7 | B3, B4, B5 |
| 4 | Redraw Figures 11 and 13 from the Part II Mermaid source | A10, C2, C3 |
| 5 | Replace the translation section with the lease-queue architecture and the 6.58% result | A11, §5 |
| 6 | Rewrite the limitations section against measured evidence | §5 entire |
| 7 | Add `classification_source` and the matching-precision gate to the findings method | B7, B8 |

Items 1–3 are non-optional: without them the report's central technical claim is untrue.

---

## 8. What the module can defend as it stands

Stated plainly, because the gap list above is long enough to read as though nothing works.

1. A trilingual ingestion and extraction pipeline measured at **EQS 0.852–0.942** over 51 regulations, 14 runs, zero failures.
2. A **1,128-row dual-annotated gold dataset** at category κ **0.947215**, fully adjudicated, zero lead-annotator fallbacks.
3. A **frozen, hashed, independently reproduced classifier** at temporal-test macro-F1 **0.947220**, clearing the 0.92 gate, wired into the backend with its migration applied live.
4. A documented **negative result**: a transformer trained to convergence and rejected on generalisation, with the corpus-size reasoning stated rather than hidden.
5. An **honest confidence contract** that refuses to render an uncalibrated margin as a percentage, and a review queue that reports `disabled` rather than pretending to be empty.

Items 4 and 5 are contributions. A dissertation that reports a rejected architecture with its evidence, and names a failure mode that produces no error message, is doing something a dissertation that reports only its successes is not.
