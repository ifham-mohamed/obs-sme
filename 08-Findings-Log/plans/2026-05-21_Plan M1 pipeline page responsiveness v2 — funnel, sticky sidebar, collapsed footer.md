# Plan: M1 pipeline page responsiveness v2 — funnel, sticky sidebar, collapsed footer

## Context

User reported four UI issues on `/admin/m1/pipeline` via screenshots:

1. Pipeline funnel chart bars overflow the card by orders of magnitude.
2. Sidebar shows a chunky native scrollbar that should be hidden.
3. Sidebar scrolls with the page instead of pinning to the top.
4. Collapsed sidebar's user/locale footer is cramped.

Root causes traced in the chat:

- **Funnel:** `widthPct = (value / counts[TIERS[0].key]) * 100` divides by the *ingested* tier. Once rows drain downstream (`ingested=1, extracted=101, preprocessed=102`), the math produces 10,100% / 10,200% widths.
- **Scrollbar:** an earlier fix scoped `* { scrollbar: none }` to `html, body` only, exposing the sidebar's `overflow-y-auto` native scrollbar.
- **Sticky breakage:** the earlier responsiveness fix used `overflow-x-hidden` on the admin layout's flex containers. `overflow: hidden` on *any* axis establishes a containing block that disables `position: sticky` on descendants.
- **Collapsed footer:** UserRow's expanded layout (avatar + email + role + logout side-by-side) crammed into 64px width.

## Goal

Constrain the funnel bars to the card; restore native scrollbar visibility scope while keeping the sidebar's inner scrollbar hidden; restore sticky positioning; polish the collapsed footer.

## Scope

- **In:** `components/m1-pipeline/funnel-chart.tsx`, `components/layout/sidebar.tsx`, `app/(admin)/layout.tsx`.
- **Out:** Mobile-specific sidebar drawer behaviour.

## Steps

1. `funnel-chart.tsx` — replace `topValue = counts[TIERS[0].key]` with `maxAcrossTiers = Math.max(1, ...TIERS.map(t => counts[t.key] ?? 0))`. Clamp `widthPct` to `[0, 100]`. Add `overflow-hidden` + `bg-muted/30` on the track parent as belt-and-braces.
2. `sidebar.tsx` — add `scrollbar-hide` class to the inner `<nav>`. Tighten `mx-1.5` inner card margin when collapsed; bottom-section padding `p-1.5` when collapsed. Rewrite `UserRow` to branch on `collapsed`: stack avatar above logout pill with `<Tooltip>`-wrapped triggers when collapsed; horizontal row with hover bg when expanded. Avatar gets `ring-1 ring-border/60`.
3. `admin/layout.tsx` — switch `overflow-x-hidden` → `overflow-x-clip` on both the shell `<div>` and the main column. `overflow-x-clip` clips overflow without establishing a containing block, so `md:sticky md:top-0 md:h-screen` works again.

## Decisions taken

- Use max-across-tiers as the funnel denominator (rather than max of the canonical "top tier") so the chart stays sane even when the pipeline drains downstream.
- `overflow-x-clip` is the right primitive when you need clipping without breaking sticky.

## Open questions

- None.

## Acceptance criteria

- Funnel bars stay inside the card regardless of count distribution.
- Sidebar sits still when the page scrolls.
- No native scrollbar visible in the sidebar.
- Collapsed sidebar avatar + logout stacked vertically with hover tooltips.

## Linked trackers

- [CHANGES.md](../CHANGES.md)
- [FEATURES.md](../FEATURES.md) — F-172
- [SESSIONS.md](../SESSIONS.md) — Session 45
