---
tags: [tracker, findings, m1]
source: synthesised
layer: tracker
module: m1
---

# 2026-05-17 — M1 docs portal data consolidation

> **Owner:** mohamedifham
> **Module:** m1
> **Type:** decision + session log

## What I did

- Appended **11 portal-derived constants** to `enigmatrix-frontend/lib/m1-docs.ts` under a clearly delimited banner. These are the curated visual data the `/docs/m1` portal renders (hero metrics, pipeline rail, T0–T9 timeline, F1–F6 findings table, tech-choice table, stats counter, inter-module connections, architecture layers, happy-path timeline, DB entities, RQs with methods).
- Updated four consumer files to import from `@/lib/m1-docs` instead of the duplicate `@/lib/m1-docs-data`: `components/docs/m1/m1-pipeline.tsx`, `components/docs/m1/m1-timeline.tsx`, `components/docs/m1/m1-stats-counter.tsx`, `app/(app)/docs/m1/page.tsx` (merged into the existing single `from "@/lib/m1-docs"` import block).
- **Deleted** `enigmatrix-frontend/lib/m1-docs-data.ts` — the duplicate is gone.

## What I found

- **11** typed constants moved · **4** consumer files updated · **1** file deleted · **0** remaining references to `m1-docs-data` after `grep -r "m1-docs-data" enigmatrix-frontend`.
- `M1_SECTIONS` was the one obsolete export — replaced by `M1_NON_TRACKING_SECTIONS` already in use by `m1-section-grid.tsx`, so it was dropped rather than ported.
- The hero band's status grid was already reading `overview?.metrics.slice(0, 5)` from generated JSON and only falling back to `M1_META.status_targets` — no change needed there.

## What changed in the repo

| File | Change |
|---|---|
| `enigmatrix-frontend/lib/m1-docs.ts` | +11 portal-derived constants appended under `// Portal-derived constants —` banner |
| `enigmatrix-frontend/lib/m1-docs-data.ts` | **DELETED** (duplicate eliminated) |
| `enigmatrix-frontend/components/docs/m1/m1-pipeline.tsx` | Import changed: `@/lib/m1-docs-data` → `@/lib/m1-docs` |
| `enigmatrix-frontend/components/docs/m1/m1-timeline.tsx` | Import changed: `@/lib/m1-docs-data` → `@/lib/m1-docs` |
| `enigmatrix-frontend/components/docs/m1/m1-stats-counter.tsx` | Import changed: `@/lib/m1-docs-data` → `@/lib/m1-docs` |
| `enigmatrix-frontend/app/(app)/docs/m1/page.tsx` | 8 named imports merged into the existing `from "@/lib/m1-docs"` import block |

## What's next

- [ ] No follow-up required for the portal itself — it renders identically to before.
- [ ] When the generated-JSON pipeline gains a cross-section synthesis layer in the future (e.g. auto-derives pipeline stages from doc 04 + doc 05 + doc 07 tables), the typed constants can be replaced — but that's a separate research-grade exercise, not a hygiene cleanup.

## Blockers

None.

## Cross-references

- Related session: [Session 29 — 2026-05-17](../../../08-Findings-Log/SESSIONS.md)
- Related feature: F-151 in [FEATURES](../../../08-Findings-Log/FEATURES.md)
- Related research doc: [16_M1_Development_Roadmap](../16_M1_Development_Roadmap.md)