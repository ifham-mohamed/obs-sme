---
tags: [m1, phase-3, risks, open-questions]
date: 2026-06-28
status: reference
---

# Phase 3 — Risks & Open Questions

## Risks (with mitigations)

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| R1 | **Silver taxonomy ≠ canonical 12.** Silver uses 6 ad-hoc labels; `procedural_change`/`other` dominate and don't cleanly map. | Pre-annotations mislead annotators; wasted relabeling. | Treat silver as a *hint only* for `rate_change`/`registration_change`; force human decision on `procedural_change`/`other`/`new_obligation`/`structural_change` (Slice 2 §2b). |
| R2 | **Severe class imbalance + missing classes.** 500 rows are 67% `procedural`; canonical classes like `ENVIRONMENTAL`, `EPF_ETF_CHANGE`, `PRODUCT_STANDARD` may have ~0 examples. | Can't hit ≥50/category; model never learns rare classes. | Targeted sourcing: crawl more gazettes from the missing domains; oversample + back-translation (train only); accept lower per-class support with reported CIs. |
| R3 | **Sinhala/Tamil text is `(cid:…)`-garbled** in `raw_text`. | SI/TA training text is corrupt → SI/TA F1 collapses, RQ2 fails. | Re-extract SI/TA via the OCR + Wijesekara path (`enigmatrix-ml/m1/extraction`) before building the gold text; verify CER on a sample. **Do this before Slice 2 scaling.** |
| R4 | **Gold set > silver set.** Need ≥ 800 gold; only 500 silver gazettes + 300 uncovered PDFs exist. | Short of the 800 bar. | Label the 300 uncovered + re-crawl additional gazette days (the spider supports date-range); the corpus is not capped at 800 PDFs. |
| R5 | **GPU access** for training/Surya. | Slow/blocked training. | Colab/Kaggle/Fly A10 for the 3-seed run; CPU only for unit tests + inference (ONNX INT8). |
| R6 | **F1-gate inconsistency** — BUILD_11 enforces ≥ 0.80, RQ1 publishes ≥ 0.92. | Model "passes" code gate but misses thesis bar. | Reconcile to **0.92** across BUILD_11 + roadmap + code (P0). |
| R7 | **Vault ↔ code drift.** Vault stops at Session 56; code at 58. | Plan references may not match live code symbols. | Sync vault (flip slice statuses, add S57/58 notes) + `graphify update .` (P0). |

## Open questions (decide with supervisor before Slice 2 scales)

1. **Canonical mapping for bulk `lands` procedural gazettes** — most are land-settlement notices. `NO_SME_IMPACT` (recommended) vs `SECTOR_SPECIFIC`? This decision moves ~250 rows.
2. **Gold-only vs weak-supervision.** Recommend the headline F1 ≥ 0.92 be **gold-only**; use silver solely for pre-annotation + active-learning acquisition, not as training labels.
3. **Sector multi-label at MVP?** Category single-label is the RQ1 core; sector multi-label can land in the same model or a fast-follow. Recommend same dual-head model (cheap) but gate the thesis claim on category F1.
4. **Annotation capacity.** 800 gold with 2 annotators + 15% overlap ≈ how many weeks? Size the timeline before committing; consider 500 gold as a v1 milestone if needed (report power honestly via `data/golden/raw_text/STATISTICAL_POWER.md`).
5. **Sinhala/Tamil scope.** If SI/TA clean-text volume is too low for ≥ 0.88, is an EN-first model with SI/TA as a reported limitation acceptable for the interim → final progression?

## Cross-refs
[00_INDEX](00_INDEX.md) · status report [STATUS_2026-06-28](../../../02-Research-Modules/1%20Module-1-Awareness-Gap/STATUS_2026-06-28_Module1_Analysis_and_Next_Level_Roadmap.md) · predecessor risks [2026-05-23_M1_Phase2_Upgrade_Plan/11_Risks_Register](../2026-05-23_M1_Phase2_Upgrade_Plan/11_Risks_Register.md)
