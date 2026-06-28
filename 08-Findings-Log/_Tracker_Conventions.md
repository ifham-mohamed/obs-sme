# `docs/tracker/` — Engineering progress log for the MVP build

This folder is the **engineering-side** progress log for the Enigmatrix data-management MVP (the vertical slice described in [`README.md`](../../README.md)). Update it at the end of every coding session.

It is deliberately **separate** from [`docs/progress/`](../progress/), which is reserved for the four formal trackers defined in [`BUILD_PLAN/BUILD_16_Progress_Tracker_Template.md`](../shared/BUILD_PLAN/BUILD_16_Progress_Tracker_Template.md) — those serve thesis-progress reporting and supervisor reviews, not day-to-day engineering.

## Files

| File | Purpose | Update cadence |
|------|---------|----------------|
| [`FEATURES.md`](FEATURES.md) | Single living checklist of every MVP feature with the `BUILD_16` status legend (🔲 🟡 🟢 🔴 ⚪). | After every PR / session |
| [`SESSIONS.md`](SESSIONS.md) | Chronological diary — one entry per work session: what was done, what's next, blockers. | One entry per session |
| [`CHANGES.md`](CHANGES.md) | Code-change log keyed to feature ids — semver-ish, append-only. | One entry per logical change |
| [`BUILD_PLAN_COVERAGE.md`](BUILD_PLAN_COVERAGE.md) | Snapshot audit of delivered work (`FEATURES.md`) vs the spec under [`docs/BUILD_PLAN/`](../BUILD_PLAN/). One row per BUILD with status + delivered F-IDs + open work. | Snapshot per session, or every 5 new F-IDs |
| [`SETUP_COVERAGE.md`](SETUP_COVERAGE.md) | Snapshot audit of the 12 onboarding docs under [`docs/SETUP/`](../SETUP/) — accurate vs minor-stale vs broken — plus cross-doc consistency checks. | Snapshot when any SETUP file changes |

## Status legend (verbatim from BUILD_00)

| Char | Meaning |
|------|---------|
| 🔲 | Not started |
| 🟡 | In progress |
| 🟢 | Done & accepted |
| 🔴 | Blocked |
| ⚪ | Out of scope / dropped |

The status-generation prompts in [`BUILD_16 §7`](../shared/BUILD_PLAN/BUILD_16_Progress_Tracker_Template.md) grep for these chars; do not substitute lookalikes.

## Conventions

- Feature ids are `F-NN` (zero-padded, e.g. `F-01`). Reuse ids; never re-number.
- Every `CHANGES.md` row references the feature id(s) it touches.
- A `FEATURES.md` row only flips to 🟢 when its acceptance criteria — defined in the source `BUILD_NN` file or inline in `FEATURES.md` — are all met **and** the smoke test from the plan's "Verification" section passes.
- Blockers (🔴) carry a single-line "next action" so the next session can pick them up cold.
