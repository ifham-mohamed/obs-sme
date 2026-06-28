---
tags: [m1, phase-2, decisions, open-questions]
date: 2026-05-23
status: 4 of 8 resolved (2026-05-23) — slice 1 unblocked
---

# 12 — Open Questions That Need Your Decision

## Resolved decisions (2026-05-23 — operator accepted recommended defaults)

| # | Decision | Pick | Effect |
|---|---|---|---|
| Q1 | `m1_regulations` writes during Phase 2 | **C — Conditional flag**, defaults to OFF | Slice 4 trigger form gets an `update_canonical: bool = False` checkbox. Experimental safety wins. |
| Q2 | Manual Excel storage | **C — Vault canonical, repo synced copy** | Source of truth at `C:\sme\_Attachments\structured_v1.xlsx`. `data/golden/structured_v1.xlsx` is gitignored and synced from the vault. |
| Q3 | Surya GPU availability | **C — Defer to Phase 3** | Slice 7C ships as `NotImplementedError` stub; registry row stays `is_active=FALSE`. Slices 7A + 7B still ship. |
| Q4 | Second transcriber for slice 2 | **B — Pilot-first, recruit in parallel** | Slice 2 starts with a 1-PDF pilot to validate the protocol; full set proceeds when recruitment lands. Does not block slices 1 / 3 / 4. |
| Q5 | Ground-truth-switch label behaviour | A — Immutability (default accepted) | Measurement run baseline labels pinned to whatever was current at run time. UI shows demotion history. |
| Q6 | Frontend route name | A — `/admin/m1/measurements` (default accepted) | Matches the `m1_measurement_runs` table; concise. |
| Q7 | CSV upload in slice 3 | C — Defer to slice 8 polish (default accepted) | Excel-only in slice 3; parser is format-aware so CSV can drop in later without schema change. |
| Q8 | Chapter 4 prose location | C — `enigmatrix-docs/thesis/chapter_4_phase2.md` (default accepted) | Git history on the thesis chapter; vault carries supporting notes via Session-57 sync. |

**Slice 1 is unblocked. The remaining sections of this file are the original question text retained for reference / future revisions.**

---



> Eight decisions remain underspecified across the plan. Each one has 2–4 candidate answers; the upgrade defaults to one but flags the alternative so you can pick. None of these block reading the plan — but slice 1 / 3 / 7 cannot ship until they're resolved.
>
> Sorted by which slice is blocked.

## Q1 — `m1_regulations` writes during Phase 2 (blocks slice 4)

**Question.** When `run_extraction_with_profile(legacy_v1)` runs, should it ALSO update `m1_regulations` (the way the existing `extract_gazette` task does), or write only to `m1_dataset_rows`?

**Options.**

A. **Dual-write.** New rows land in both `m1_regulations` and `m1_dataset_rows`. Backward-compatible with every existing reader (the SME-facing `/regulations` page, the admin pipeline portal, all current dashboards). Cost: every Phase-2 extraction run has a side effect on the canonical table; you cannot run "100 experimental profile variants" without polluting it.

B. **Write-once-then-stop.** The existing `extract_gazette` Celery task keeps writing `m1_regulations` for spider-driven ingest (production behaviour unchanged). `run_extraction_with_profile` writes ONLY to `m1_dataset_rows`. Cost: the existing UI reads stale data; SME-facing pages don't reflect the new profile's output until slice 8's backfill runs.

C. **Conditional write.** A flag on the extraction-run trigger: `update_canonical=true|false`. Defaults to false (so experiments are safe); operator opts in for production-quality runs they want to surface immediately.

**Default in this upgrade plan:** **C.** Conditional write. Defaults to false. Production runs against `legacy_v1` (or any green-gated new profile) can opt in.

**Trade-off you're picking between:** experimental safety vs immediate UI freshness.

## Q2 — Manual Excel storage location (blocks slice 3)

**Question.** Where does the canonical `structured_v1.xlsx` live?

**Options.**

A. **Vault attachments** — `C:\sme\_Attachments\structured_v1.xlsx`. Syncs through the vault chain (Session 57). Visible in the `/admin/m1/knowledge` portal. Survives repo resets.

B. **Repo `data/golden/`** — `C:\Reasearch\xyz\data\golden\structured_v1.xlsx`. Source of truth for CI; loaded by `scripts/run_baseline_measurement.py` directly. Could leak into commits if `.gitignore` isn't careful.

C. **Both, with vault as canonical and `data/golden/` as a synced copy** — the script reads from `data/golden/`; the vault holds the source-of-truth blob with version history.

D. **Railway-deployed `storage/m1/datasets/golden/` volume** — uploaded once via the slice-3 UI; lives next to PDF storage. Survives container restarts. Not version-controlled.

**Default:** **C.** Vault canonical, `data/golden/` is the synced working copy. Add `data/golden/structured_v1.xlsx` to `.gitignore` since the source-of-truth lives in the vault.

**Trade-off:** vault-as-source-of-truth is consistent with Session-57's vault-sync philosophy and means thesis appendices reference the same file. The cost: a one-step sync (vault → repo) on every Excel update.

## Q3 — Surya GPU availability (blocks slice 7 task 7.4)

**Question.** Do you have GPU access on your Railway production env OR on a local dev box capable of running Surya at < 15 s / page?

**Options.**

A. **Yes — Railway GPU plugin available.** Slice 7C ships in Phase 2. The `requires_gpu` flag on the profile registry row gates dispatch.

B. **Yes — local laptop with CUDA-capable GPU.** Slice 7C ships, but only as a local-research toggle. Production extraction stays at `wijesekara_routing_v1`.

C. **No GPU available anywhere.** Slice 7C ships as a stub (`NotImplementedError`) and the registry row stays `is_active=FALSE`. Phase 3 picks this up.

D. **CPU-acceptable on laptop.** Run Surya on a sub-sample of pages (e.g. just `2468/44`'s body pages) and measure CER. Defer full Surya integration to Phase 3 but produce the empirical comparison number now.

**Default:** **C.** Defer to Phase 3 unless explicit GPU resource is available. The slice-7 outcome write-up will note which option you picked.

## Q4 — Second transcriber for slice 2 (blocks slice 2)

**Question.** Do you have a second bilingual person available to independently transcribe 10 PDFs across 4 page averages = ~40 pages each?

**Options.**

A. **Yes — known person committed.** Slice 2 ships with paired transcriptions + κ computation.

B. **Maybe — need to recruit.** Slice 2 starts with a 1-PDF pilot to validate the protocol; full set proceeds once recruitment lands.

C. **No.** Slice 2 ships with single-source gold. The CI for CER computations narrow to "single-transcriber, ±2 % CER" and the thesis claim is downgraded from "significant improvement" to "observed improvement, single-source baseline".

**Default:** **B.** Pilot-first, recruit in parallel.

## Q5 — Default behaviour of `is_ground_truth` switch when a measurement exists (informs slice 5 + 6)

**Question.** If a measurement run was scored against ground-truth-dataset-A, and the operator subsequently promotes dataset-B to ground truth, what happens to the existing measurement run's "baseline" label?

**Options.**

A. **The label stays pinned to dataset-A.** The measurement run is immutable; its baseline is whatever it was when it ran. New measurement runs default to dataset-B.

B. **The label updates retroactively** to show "dataset-A (was ground truth)" with a tooltip.

C. **The measurement run is auto-marked stale** with a banner suggesting a re-run.

**Default:** **A.** Immutability is a core value. Slice 6's UI shows "Manual ground truth — May 2026 v1 (was ground truth, demoted 2026-06-15)" so the label carries the demotion history.

## Q6 — Frontend route name for the measurement hub (informs slice 6)

**Question.** The existing convention is `/admin/m1/pipeline`, `/admin/m1/extractions`. The plan uses `/admin/m1/measurements`. Is this name fine, or do you prefer `/admin/m1/evaluation` or `/admin/m1/accuracy`?

**Options.**

A. `/admin/m1/measurements` — matches the table name (`m1_measurement_runs`). Concise.
B. `/admin/m1/evaluation` — broader semantic; could later host non-scoring evaluation tools.
C. `/admin/m1/accuracy` — emphasises the goal not the mechanism.

**Default:** **A.** Matches the schema; clear about what's happening.

## Q7 — Whether to ship a CSV alternative to the Excel upload in slice 3 (informs slice 3 scope)

**Question.** The original plan describes CSV upload as a parallel path with the same parser. Do you actually need it?

**Options.**

A. **Yes** — your manual Excel was authored in Excel but other contributors might prefer CSV.
B. **No** — Excel is the lingua franca for the manual Excel; CSV adds parser surface area without benefit.
C. **Yes, but deferred to slice 8** — ship the Excel path first; add CSV in polish if anyone actually asks.

**Default:** **C.** Defer CSV. Slice 3 ships Excel-only; the parser is structured to accept either format but the UI only exposes Excel.

## Q8 — Where to put the "Phase-2 complete" thesis chapter draft (informs slice 8)

**Question.** When slice 8 finishes, where does the draft Chapter 4 prose live?

**Options.**

A. `Interim/report/` — vault folder where the existing M1 chapter draft lives.
B. `10-Highlights/report/` — vault folder for highlights / final outputs.
C. `enigmatrix-docs/thesis/chapter_4_phase2.md` — repo-level, version-controlled.
D. `02-Research-Modules/1 Module-1-Awareness-Gap/findings/phase2_chapter_4.md` — module-scoped vault.

**Default:** **C.** Chapter 4 prose is a research artefact that benefits from git history. The vault carries the supporting notes + figures via Session-57's sync.

---

## How to answer

Reply with your picks (e.g. "Q1: A, Q3: C, Q5: A, defaults elsewhere"). Once these eight are resolved, this file gets a `## Resolved decisions` block at the bottom and slice 1 can start. Decisions can be revisited later but every revisit invalidates whatever was built on top of the previous choice — so it's worth getting them right before slice 1.

## Cross-references

- [00_INDEX](00_INDEX.md) — the headline status table that will turn green as decisions land.
- Each slice file's `Risks specific to this slice` block — picks from this file influence which risks apply.
