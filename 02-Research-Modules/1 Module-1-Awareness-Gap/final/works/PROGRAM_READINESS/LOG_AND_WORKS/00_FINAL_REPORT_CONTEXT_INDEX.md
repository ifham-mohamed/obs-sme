# Enigmatrix Final Report — Context Index

Updated: 2026-08-01 (fourth pass - V6 dataset and frozen LinearSVC evidence added)
Project: Enigmatrix — SME Regulatory Intelligence Platform
Group: G28
Module 1 owner: Mohomed M.R.I (215075J) — working name Ifham Mohamed

The group title page spells the name **Mohomed M.R.I**; confirm against the university student record before submission.

## Single Source of Truth

The full report now lives in **one markdown file** and is compiled to `.docx` by a script. Edit the markdown, re-run the build, never hand-edit the `.docx`.

| File | Role |
|---|---|
| `…\Understanding Information Barriers…\Enigmatrix_Final_Report_Master.md` | Full report text, all 9 chapters + 2 appendices |
| `…\Understanding Information Barriers…\build_final_report_docx.py` | Markdown → Word builder (headings, tables, captions, images, TOC/LOF/LOT fields) |
| `…\Understanding Information Barriers…\Build_Final_Report_DOCX.bat` | Double-click to rebuild the `.docx` |
| `…\Understanding Information Barriers…\G28 - Enigmatrix - Final Report (Module 1 - Ifham Mohamed).docx` | Generated deliverable |

Deliverable folder: `C:\Users\Administrator\Documents\Claude\Projects\Understanding Information Barriers to Regulatory Compliance Among Sri Lankan SMEs`

## Official Template Structure (B21 FYP)

The report follows the faculty template exactly. Deviations would cost marks.

| Section | Status |
|---|---|
| Title page (Level 04) | Drafted; needs supervisor names, month, degree name |
| Dissertation submission page | Drafted; needs degree name |
| DECLARATION | Drafted; needs signatures and date |
| ACKNOWLEDGMENT | Draft text supplied; adapt and sign off |
| ABSTRACT | Written (~330 words) |
| TABLE OF CONTENT | Word field, auto-populates |
| LIST OF FIGURES | Word field, auto-populates from the `FigureCaption` style |
| LIST OF TABLES | Word field, auto-populates from the `TableCaption` style |
| Chapter 1 — Introduction | Complete for the common part and Module 1; M2/M3/M4 placeholders |
| Chapter 2 — Related Work | Complete; 55 references reused from the interim report |
| Chapter 3 — Technology Adapted | Complete (3.2 languages/libraries, 3.3 Colab + Kaggle, 3.4 other tools) |
| Chapter 4 — Approach | Module 1 Input/Process/Output complete; M2/M3/M4 I-P-O placeholders |
| Chapter 5 — Analysis and Design | Complete; interim diagrams embedded as Figures 5.1, 5.3–5.8, 5.13–5.15 |
| Chapter 6 — Implementation | Complete for Module 1 with 4 real code listings and 8 screenshot slots |
| Chapter 7 — Evaluation | Metrics defined; Module 1 results tables populated where evidence exists |
| Chapter 8 — Conclusion | Complete |
| Chapter 9 — References | 55 entries, IEEE numbered |
| Appendix A — Individual Contribution | A.1 written in full; A.2–A.4 placeholders |
| Appendix B — Additional Implementation Details | Artefact inventory, annotation guideline, evaluation assumptions, checklists |

## Historical V1 Numbers Verified Against Artefacts

These are still valid for the original 800-row V1 annotation/training milestone, but they are no longer the latest classifier evidence. Do not use them as the final model-selection result.

| Fact | Value | Source artefact |
|---|---|---|
| Gold dataset rows | 800 | `research\data\labeling\gold_standard_v1_800.csv` |
| Category Cohen's kappa | 0.871534 | `research\data\labeling\iaa_report_v1_800.json` |
| Category raw agreement | 0.960000 | same |
| Mean sector kappa | 0.863776 | same |
| Sector-set agreement | 0.952500 | same |
| SME-relevance kappa | 0.723518 | same |
| Disagreement rows | 40 | same |
| TF-IDF LogReg test macro-F1 | 0.498039 | `storage\models\m1\baselines_v1\baselines.json` |
| TF-IDF LinearSVC test macro-F1 | 0.616745 | same |
| Smoke-test test macro-F1 / gate_pass | 0.0 / `false` | `storage\models\m1\xlmr_lora_smoke\model_registry.json` |
| Split | 560 / 120 / 120 | `enigmatrix-ml\datasets\m1_regulations` |
| Taxonomy | 8 categories, 3 sectors | `enigmatrix-ml\m1\model\labels.py` |

## Latest Module 1 Evidence Addendum

The earlier report pack records the 800-row V1 dataset, the 1128-row rare-domain V3 baseline, and the Kaggle LoRA diagnostics. The latest classifier-evidence dataset is now **V6**:

| Fact | Value | Source artefact |
|---|---:|---|
| Current classifier dataset | `m1_regulations_v6_1110_clean_fixedsplit` | `C:\Reasearch\xyz\datasets\m1_regulations_v6_1110_clean_fixedsplit` |
| Current split | 777 / 166 / 167 | `dataset_manifest_v6.json` |
| V6 total rows | 1110 | same |
| V6 label correction | 4 EPF/ETF incidental-mention rows relabelled to `SECTOR_SPECIFIC`; all in train | `applied_label_changes_v6.csv` |
| Cross-split key leakage | 0 | `dataset_manifest_v6.json` |
| Frozen primary model | `m1_linearsvc_v6_primary` | `C:\Reasearch\xyz\models\m1\linearsvc_v6_primary` |
| Validation macro-F1 | 0.924476 | `validation_summary.json` |
| Temporal test macro-F1 | 0.947220 | `test_summary.json` |
| Test accuracy | 0.958084, 160/167 correct | `test_summary.json` |
| Gate result | passed, threshold 0.92 | `model_registry.json` |
| Reproduced on Windows | 0.9472199858964565 macro-F1, exact match to Kaggle | `local_windows_verification.json` |
| XLM-R V6 comparison | test macro-F1 0.743563, not promoted | `model_registry.json` |
| Dataset ZIP SHA256 | `66EF4CF6FB187146641173BBB71628AD711C635FCEADE34CAB01AADDD99F35F0` | `C:\Reasearch\xyz\kaggle_bundle\m1_regulations_v6_1110_clean_fixedsplit.zip` |
| Model bundle SHA256 | `2F80BEFE494F1275DCB14FCB5352902A8BF98C1CC3FA86F919D53B7958C5F11B` | `C:\Reasearch\xyz\models\m1\linearsvc_v6_primary_bundle.zip` |

Use [[18_M1_Dataset_And_Model_Lineage]] for the active dataset/model lineage, hashes, Kaggle paths, and recovery commands. Use [[05_M1_RARE_DOMAIN_TOPUP_AND_V3_BASELINE]] as the predecessor evidence that explains why V3 was insufficient (`LinearSVC` macro-F1 0.908012). Keep [[04_M1_KAGGLE_TRAINING_RESULTS_V1]] as historical evidence that the 800-row V1 LoRA checkpoint was not promotable.

## Standing Corrections

1. Current taxonomy is **8 categories and 3 sectors**, not the older 12/10 planning figures. The stale comments in `config.py` and `architecture.py` were corrected on 2026-07-30.
2. `gold_standard_v1_800.csv` has no usable `gazette_published_date`, so the split is **deterministic on `regulation_key`, not temporal**. Do not describe it as temporal until dates are backfilled.
3. The local XLM-R LoRA run is a **CPU smoke test**. It proves the pipeline runs; it is not model-quality evidence.
4. The F1 ≈ 6.8 d / F2 ≈ 21.8 d / F6 ≈ −19.9 d figures are **synthetic demo output** from the notebooks, not empirical findings.
5. `EPF_ETF_CHANGE` is still sparse after V6: 4 train, 2 validation, 1 test. The reported EPF/ETF test F1 of 1.000 is one correctly classified test document, not stable per-class evidence.
6. The production classifier is category-only. Sectors remain in the expert/manual sector ledger; do not claim that the frozen LinearSVC predicts sectors.
7. The frozen classifier exposes margins, not probabilities. `classifier_confidence` is nullable and margins must not be displayed or written as percentages.
8. Summarisation and Sinhala/Tamil translation exist at schema, queue, worker, and review-surface level. Final report claims still need completed backfill screenshots and human review evidence.

## Figures Already Embedded

Pulled from `Interim\report\Attachments\` and embedded automatically by the builder.

| Figure | Image |
|---|---|
| 5.1 Four-layer architecture | `SMEs Interim.png` |
| 5.3 Level 0 DFD | `SMEs Interim 4.jpeg` |
| 5.4 Level 1 DFD | `SMEs Interim 5.jpeg` |
| 5.5 Domain class diagram | `SMEs Interim 6.jpeg` |
| 5.6 Sequence diagram | `SMEs Interim 7.jpeg` |
| 5.7 Database ER design | `SMEs Interim 8.jpeg` |
| 5.8 Module 1 pipeline | `SMEs Interim.jpeg` |
| 5.13 / 5.14 / 5.15 M2 / M3 / M4 pipelines | `SMEs Interim 1/2/3.jpeg` |

Figures 1.1, 4.1, 5.2, 5.9–5.12 and 6.6 are Mermaid source with a grey insert box. Render at `https://mermaid.live`, export PNG, drop it into the box.

## Screenshots Still Needed

Label Studio · admin pipeline console · measurement dashboard · Kaggle/Colab GPU session · alerts feed · translation review queue · trilingual SME dashboard · confusion matrix.

Each has a yellow `[ SCREENSHOT ]` box in Chapter 6 describing exactly what to capture.

## Placeholder Markers To Clear

`[M2 PLACEHOLDER]` · `[M3 PLACEHOLDER]` · `[M4 PLACEHOLDER]` · `[ADD FINAL GPU RESULT]` · `[ADD MEASUREMENT RESULT]` · `[ADD FINDINGS RESULT]` · `[ADD TRANSLATION RESULT]` · `[ADD INTEGRATION RESULT]` · `[ADD LOCAL …]` · `[ADD GPU …]` · `[VERIFY OFFICIAL NAME]` · `[VERIFY TEAM DETAILS]` · `[ADD SUPERVISOR NAME]` · `[ADD DEGREE NAME]` · `[ADD MONTH]`

All are highlighted yellow in the Word document. Table B.5 lists where each value comes from.

## Related Notes

- [[04_OFFICIAL_TEMPLATE_STRUCTURE_MAP]] — section map and open items
- [[03_M1_EVIDENCE_EVALUATION_AND_COMMANDS]] — evidence pack, formulas, reproducibility commands
- [[05_M1_RARE_DOMAIN_TOPUP_AND_V3_BASELINE]] — latest rare-domain Batch 06/07 evidence and v3 baseline
- [[06_M1_FULL_WORK_SESSION_CHRONOLOGY_2026-07-31]] — full chat/workflow chronology from calibration through v3 baseline
- [[18_M1_Dataset_And_Model_Lineage]] — active V6 dataset, frozen LinearSVC model, hashes, and Kaggle/local recovery commands
- [[01_CHAPTER_1_INTRODUCTION_DRAFT]] — superseded first-pass draft
- [[02_CHAPTER_2_RELATED_WORK_DRAFT]] — superseded first-pass draft
