---
tags: [meta, findings, tracker, index]
source: synthesised + tracker/README.md
layer: meta
module: shared
---

# 08 — Findings Log (Index)

> Append-only engineering + research log. This is the working memory of the project: what was built, what changed, what was tried, what was discovered.

## Live trackers

| File | What it is | Update rhythm |
|---|---|---|
| [SESSIONS](SESSIONS.md) | Chronological diary — what was done, what's next, what's blocking | Every working session |
| [CHANGES](CHANGES.md) | Code-change log, semver-ish, keyed to feature IDs | Every PR / commit batch |
| [FEATURES](FEATURES.md) | Living checklist of features (🔲 not started · 🟡 in progress · 🟢 done · 🔴 blocked · ⚪ dropped) | Weekly |
| [RESEARCH_IDEAS](RESEARCH_IDEAS.md) | Half-baked research ideas, hypotheses, experiments to try | Whenever |
| [RESEARCH_BUILD_TRACKER](RESEARCH_BUILD_TRACKER.md) | Research-side build progress | Weekly |
| [BUILD_PLAN_COVERAGE](BUILD_PLAN_COVERAGE.md) | Delivered work vs the BUILD spec | At each milestone |
| [SETUP_COVERAGE](SETUP_COVERAGE.md) | Onboarding-doc completeness audit | When SETUP docs change |

## Conventions

See [_Tracker_Conventions](_Tracker_Conventions.md) for the original `tracker/README.md` — status legend, feature-ID format, how to add a session entry.

Template for a new findings entry: [_Templates/Findings-Entry-Template](../_Templates/Findings-Entry-Template.md).

## Where to go next

- [Timeline](../06-Timeline/00_Timeline_Overview.md) — what was planned
- [BUILD_Master_Index](../00-Meta/BUILD_Master_Index.md) — what is being built
- [Project-Overview](../01-Project-Overview/Project-Overview.md) — why it is being built


## Session 56 plans (2026-05-22)

- [Plan: M1 raw PDF bulk extraction and classification — 800 PDFs across 11 batches](plans/2026-05-22_Plan%20M1%20raw%20PDF%20bulk%20extraction%20and%20classification%20—%20800%20PDFs%20across%2011%20batches.md)

## Session 55 plans (2026-05-22)

- [Plan: Railway production deployment — backend deploy chain and PAT leak](plans/2026-05-22_Plan%20Railway%20production%20deployment%20—%20backend%20deploy%20chain%20and%20PAT%20leak.md)
- [Plan: M1 cancel + rollback endpoint and frontend button](plans/2026-05-22_Plan%20M1%20cancel%20+%20rollback%20endpoint%20and%20frontend%20button.md)
- [Plan: Per-PDF metadata schema and population](plans/2026-05-22_Plan%20Per-PDF%20metadata%20schema%20and%20population.md)
- [Plan: PDF Records browse-all admin page](plans/2026-05-22_Plan%20PDF%20Records%20browse-all%20admin%20page.md)
- [Plan: Cross-repo code quality audit — Stage 4](plans/2026-05-22_Plan%20Cross-repo%20code%20quality%20audit%20—%20Stage%204.md)

## Session 54 plans (2026-05-22)

- [Plan: M1 extraction page UX improvements — sticky sidebar, resume/restart, history table, auto-scroll](plans/2026-05-22_Plan%20M1%20extraction%20page%20UX%20improvements%20—%20sticky%20sidebar%20resume%20restart%20history%20auto-scroll.md)
- [Plan: M1 extraction run history — server-side persistence and pool fix](plans/2026-05-22_Plan%20M1%20extraction%20run%20history%20—%20server-side%20persistence%20and%20pool%20fix.md)

## Session 53 plans (2026-05-22)

- [Plan: M1 pipeline admin UX audit — 14 findings report](plans/2026-05-22_Plan%20M1%20pipeline%20admin%20UX%20audit%20—%2014%20findings%20report.md)

## Session 52 plans (2026-05-22)

- [Plan: AnimatedList + FuzzyText UI component suite](plans/2026-05-22_Plan%20AnimatedList%20+%20FuzzyText%20UI%20component%20suite.md)
- [Plan: Theme polish — view-transition animation + disable system tracking](plans/2026-05-21_Plan%20Theme%20polish%20%E2%80%94%20view-transition%20animation%20+%20disable%20system%20tracking.md) *(appended Session 52 update — theme toggle dropdown → button)*

## Session 44-51 plans (2026-05-21)

- [Plan: Theme polish — view-transition animation + disable system tracking](plans/2026-05-21_Plan%20Theme%20polish%20—%20view-transition%20animation%20+%20disable%20system%20tracking.md)
- [Plan: M1 pipeline page responsiveness v2 — funnel, sticky sidebar, collapsed footer](plans/2026-05-21_Plan%20M1%20pipeline%20page%20responsiveness%20v2%20—%20funnel,%20sticky%20sidebar,%20collapsed%20footer.md)
- [Plan: Extraction running UX upgrade — PipelineRunStatusCard + WS scaffold + ML progress](plans/2026-05-21_Plan%20Extraction%20running%20UX%20upgrade%20—%20PipelineRunStatusCard%20+%20WS%20scaffold%20+%20ML%20progress.md)
- [Plan: Frontend perf overhaul — dashboard streaming, login handoff, bundle tuning](plans/2026-05-21_Plan%20Frontend%20perf%20overhaul%20—%20dashboard%20streaming,%20login%20handoff,%20bundle%20tuning.md)
- [Plan: Vault recovery from Write-tool truncation (incident)](plans/2026-05-21_Plan%20Vault%20recovery%20from%20Write-tool%20truncation%20(incident).md)
- [Plan: Live count polling for summaryForResume + SpiderResultCard polish](plans/2026-05-21_Plan%20Live%20count%20polling%20for%20summaryForResume%20+%20SpiderResultCard%20polish.md)
- [Plan: Completeness check + re-fetch + spider EN-SI-TA fallback](plans/2026-05-21_Plan%20Completeness%20check%20+%20re-fetch%20+%20spider%20EN-SI-TA%20fallback.md)
- [Plan: Completeness ver