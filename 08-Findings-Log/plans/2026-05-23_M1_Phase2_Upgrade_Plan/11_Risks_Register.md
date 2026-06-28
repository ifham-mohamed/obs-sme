---
tags: [m1, phase-2, risks, mitigations, register]
date: 2026-05-23
status: reference
---

# 11 — Consolidated Risk Register

> Single place to read every risk identified in the original plan (`05_Build_Sequence_and_Risks.md` §Risks) plus every new risk surfaced by the alignment audit and the upgraded slice plans.

## Risk grading

- **Likelihood:** L (low) / M (medium) / H (high) — how probable is this risk in the 8-week Phase-2 window?
- **Impact:** L / M / H — if it materialises, how much rework does it force?
- **Slice owner:** which slice's checks catch it.

## Risk table

| # | Risk | Likelihood | Impact | Slice owner | Mitigation |
|---|---|---|---|---|---|
| R-01 | Golden-set transcription disagreement (κ < 0.65 on any stratum) | M | H | 2 | Pilot 3 PDFs first; refine guidelines; re-pilot before expanding. Document single-source fallback. |
| R-02 | Wijesekara map insufficient for the actual fonts in `2468_44` | M | M | 7 | Task 7.3 instruments the corpus to find real font names before map expansion. |
| R-03 | Surya OCR too slow on CPU (> 15 s / page) | M | L | 7 | Gate-deferred: profile ships only if GPU available or CPU acceptable. Otherwise Phase 3. |
| R-04 | Statistical power (10 PDFs is too small for 2-pp CER claims) | H | M | 2, 7 | Honest reporting: CIs not point estimates; pre-registered hypotheses; expand to 100 PDFs in Phase 3. |
| R-05 | PyMuPDF AGPL licensing collision with future commercialisation | L | M | 7 | `pypdfium2` (Apache 2.0) introduced as drop-in replacement. Switch is single-file. |
| R-06 | Dataset version proliferation during slice-7 experimentation | M | L | 8 | Nightly retention Celery beat retires versions > 30 days old (unless `keep=TRUE`). |
| R-07 | Metric registry implementation drift | M | M | 1, 8 | Versioned metrics: every score row carries `metric_version`. Dashboard filters by version. |
| R-08 | `LegacyV1Profile` adapter API mismatch (would crash) | H (if uncorrected) | H | 4 | Corrected adapter shipped in this upgrade. Faithfulness regression test in slice 4. |
| R-09 | Alembic migration numbering breaks chain | H (if uncorrected) | H | 3 | Use the project's `YYYYMMDDNNNN` format; down-rev chains to current tip. |
| R-10 | Aiven 20-conn pool exhaustion on 400-PDF Celery group | H (if uncorrected) | H | 4 | Batches of 8 with Redis counter synchronisation, not one big group. |
| R-11 | Audit log rows missing on Phase-2 admin actions | M | M | 3, 4, 5, 6 | Every admin endpoint calls `audit_service.record()`. Linted in test. |
| R-12 | Excel upload as attack vector (unbounded size, formula evaluation, malicious macros) | M | H | 3 | 50 MB cap, MIME whitelist, `read_only=True, data_only=True`, ClamAV scan in slice 8. |
| R-13 | Concurrent re-upload corrupts a dataset | L | M | 3 | SHA-256 idempotency: 409 on duplicate, 423 on in-flight. |
| R-14 | Sinhala / Tamil text breaks the comparison UI layout (long strings, RTL bidi cases) | M | L | 6 | `whitespace-pre-wrap break-words` cells; Noto Sans Sinhala / Tamil preloaded via `next/font`. |
| R-15 | LaBSE / BERTScore models load slowly in CI | M | L | 1, 5 | Slow tests marked `@pytest.mark.slow`; CI runs fast suite only; slow suite runs nightly. |
| R-16 | Confidence-required calibration plot misleads when candidate is `legacy_v1` | M | M | 5, 6 | Plot conditional on confidence presence; placeholder card explains absence. |
| R-17 | `m1_pdf_resolver` fallback chain fails silently when web URL is dead | L | M | 4 | All three paths exhaust → `validation_warnings: ['pdf_unavailable']` + row counted as `missing`. |
| R-18 | Storage explosion from raw_text duplication across versions | L | L | 8 | Keep deduplication light; revisit only above 1 M rows. Retention policy is the primary control. |
| R-19 | The `legacy_v1` regression test is too strict and forces no-op edits to be branded as new profiles | L | L | 4 | The SHA-256 lock asserts byte-stability of the output, not the code path. Internal refactors are fine as long as outputs match. |
| R-20 | Celery `task_revoked` / `task_lost` leaves measurement runs orphaned in `running` state | M | L | 5 | Signal-handler patch in slice 8 sets `status='failed'` when these signals fire. |
| R-21 | Frontend ↔ backend contract drift (Zod ↔ Pydantic) | M | M | 3, 4, 5 | Cross-reviewed pair-by-pair in each slice. The repo-wide drift table in `AGENTS.md` is updated as new Phase-2 schemas land. |
| R-22 | i18n strings missed during PR review and shipped as `m1.measurements.foo` literal strings | M | L | 3, 4, 6 | i18n linter rule in CI checks every JSX string against the `next-intl` key namespace. (May defer to slice 8 if linter doesn't exist yet.) |
| R-23 | Operator runs `make thesis-artifacts` against a stale measurement run | L | L | 8 | Script emits a warning when the most-recent measurement run is > 14 days old. |
| R-24 | GitHub PAT leak (Session 55 known security issue) | already-materialised | H | independent | Tracked separately as security follow-up #12. Phase 2 does not introduce new PAT exposures. |

## Risks the original plan didn't surface

R-08 through R-13 and R-16 through R-23 are new in this upgrade. They were surfaced by the alignment audit ([01_Alignment_Audit](01_Alignment_Audit.md)) plus my reading of the actual codebase (`AGENTS.md` rule on `audit_log`, the Session-55 connection-pool note, the Session-57 vault-sync architecture).

## Risks the original plan flagged but I rated differently

- R-04 (statistical power): original called it "the fourth risk" with the mitigation "honest reporting." I agree but graded as **H likelihood** because it WILL materialise — 10 PDFs is genuinely too few. The mitigation is in slice 2's `STATISTICAL_POWER.md` and the honest-reporting convention in Chapter 4 prose.
- R-02 (Wijesekara map insufficient): original mentioned 1-2 days of inspection work. I bumped the slice-7 task 7.3 to a dedicated instrumentation step BEFORE map expansion so the work is empirically prioritised.

## How to use this register

- Each slice file references the risks it owns under "Risks specific to this slice".
- Before shipping a slice, re-read the relevant rows here and confirm mitigations landed in code.
- After Phase 2 ships, drop a `12_Risks_Outcome.md` capturing which risks materialised, how they were resolved, and which can be downgraded for Phase 3.

## Cross-references

- [01_Alignment_Audit](01_Alignment_Audit.md) — technical drift that produced R-08 → R-13 and R-16 → R-17.
- [10_Upgrades_Over_Original](10_Upgrades_Over_Original.md) — every Category B addition addresses a new risk.
- Each slice file's `## Risks specific to this slice` block.
