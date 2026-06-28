# Plan: AnimatedList + FuzzyText UI component suite

## Context

The enigmatrix-frontend codebase had plain static lists, card grids, and tables with no entrance animation and no visual feedback when items entered the viewport. Tables also lacked sticky headers, making it hard to read column labels while scrolling long data sets. Separately, the platform-map stats, the research-log metrics, the 404 page, and the "Coming Soon" placeholder component all rendered text as plain HTML — no visual identity.

User asked to:
1. Integrate the AnimatedList component from React Bits across all list and card pages — scroll-triggered entrance animations.
2. Make all table headers sticky with scrollable bodies (responsive upgrade).
3. Integrate the FuzzyText component from React Bits "correctly and beautifully" across the codebase.
4. Explicitly NOT change the global PageHeader `h1` style after an initial attempt was rejected.

## Goal

Ship two reusable UI primitives (`AnimatedList` / `FuzzyText`) and apply them site-wide to every eligible list, card grid, table, and high-impact text surface.

## Scope

- **In:** `components/ui/animated-list.tsx`, `components/ui/animated-list.css`, `components/ui/fuzzy-text.tsx`, `components/ui/fuzzy-not-found-hero.tsx`, 6 list/card pages, 13 table files, `app/not-found.tsx`, `components/coming-soon.tsx`, `app/(app)/docs/platform-map/page.tsx`, `app/(admin)/admin/research-log/page.tsx`.
- **Out:** Global page `h1` / `PageHeader` (user explicitly rejected FuzzyText on `components/layout/page-header.tsx` — reverted).

## Steps

### AnimatedList (F-179)

1. Create `components/ui/animated-list.tsx` — three exports:
   - `AnimatedItem` — wraps any `ReactNode` in a `motion.div` with `useInView({ amount: 0.15, once: false })`; entrance: `scale 0.95→1`, `opacity 0→1`, `y 8→0`, 220ms easeOut; accepts `delay`, `index`, `className`, `onMouseEnter`, `onClick`.
   - `AnimatedListScrollable` — scrollable container with `.al-top-gradient` + `.al-bottom-gradient` overlays.
   - Default `AnimatedList` — string array with keyboard arrow navigation (original React Bits pattern).
2. Create `components/ui/animated-list.css` — theme-aware via `hsl(var(--background))`, `hsl(var(--card))`, `hsl(var(--border))`, `hsl(var(--muted))`; scrollbar styled with `hsl(var(--border))` + `hsl(var(--muted-foreground) / 0.5)`; `.sticky-thead` helper class.
3. Apply `AnimatedItem` wrappers to 6 list/card pages:
   - `app/(admin)/admin/m1/pipeline/steps/page.tsx` — StepTile grid, `delay={index * 0.05}`
   - `app/(admin)/admin/m1/pipeline/sources/page.tsx` — SourceCard grid
   - `app/(admin)/admin/research-log/page.tsx` — MetricTile grid (6 items, `delay={index * 0.05}`) + SessionCard list (`delay={index * 0.06}`)
   - `app/(app)/docs/page.tsx` — docs cards, `delay={index * 0.06}`
   - `app/(app)/surveys/page.tsx` — module cards + recent sessions
   - `app/(app)/dashboard/page.tsx` — regulation cards, `delay={index * 0.05}`
4. Apply sticky table headers to 13 table files — wrapper changed from `overflow-hidden` to `overflow-auto rounded-lg border bg-background max-h-[520px]`; `<TableHeader className="sticky top-0 z-10 bg-background">`:
   - `app/(app)/surveys/history/page.tsx`
   - `app/(admin)/admin/activity-log/page.tsx`
   - `app/(admin)/admin/m3/risk-signals/page.tsx`
   - `app/(admin)/admin/m2/scores/page.tsx`
   - `app/(admin)/admin/m2/questions/page.tsx`
   - `app/(admin)/admin/m1/pdf-records/page.tsx`
   - `app/(admin)/admin/questions/questions-client.tsx`
   - `app/(admin)/admin/surveys/surveys-client.tsx`
   - `app/(admin)/admin/surveys/awareness/responses/page.tsx`
   - `app/(admin)/admin/regulations/regulations-client.tsx`
   - `app/(admin)/admin/users/users-client.tsx`
   - `app/(app)/admin/survey/questions/page.tsx`
   - `app/(app)/docs/m1/page.tsx`

### FuzzyText (F-181 / F-182)

1. Create `components/ui/fuzzy-text.tsx` — full TypeScript port of React Bits FuzzyText:
   - Canvas-based per-row pixel displacement; `requestAnimationFrame` render loop.
   - Key adaptation: `color` defaults to `"currentColor"`, resolved at runtime via `window.getComputedStyle(canvas).color` so it automatically tracks CSS colour inheritance in both light and dark mode.
   - Full prop interface: `fontSize` (default `"clamp(2rem, 10vw, 10rem)"`), `fontWeight` (900), `fontFamily` (inherit), `color` (currentColor), `enableHover` (true), `baseIntensity` (0.18), `hoverIntensity` (0.5), `fuzzRange` (30), `fps` (60), `direction` (horizontal/vertical/both), `transitionDuration` (0), `clickEffect` (false), `glitchMode` (false), `glitchInterval` (2000), `glitchDuration` (200), `gradient` (null), `letterSpacing` (0), `className` ("").
2. Create `components/ui/fuzzy-not-found-hero.tsx` — thin `"use client"` island:
   - Renders "404" at `fontSize="clamp(5rem, 20vw, 14rem)"`, `fontWeight=900`, `glitchMode`, `glitchInterval=3500`, `glitchDuration=180`, `clickEffect`, `transitionDuration=8`, `direction="horizontal"`.
   - Wrapper: `<div className="text-foreground select-none" aria-label="404" role="img">`.
3. Modify `app/not-found.tsx` — import `FuzzyNotFoundHero`, replace `FileQuestion` icon + plain h1 with the hero component + "Page not found" heading.
4. Modify `components/coming-soon.tsx` — add `"use client"`, import FuzzyText, render title with `fontSize="1.125rem"`, `fontWeight=600`, `baseIntensity=0.06`, `hoverIntensity=0.32`, `fuzzRange=16`, `fps=45`, `transitionDuration=6`, `enableHover`. Wrapper: `<div aria-label={title} role="heading" aria-level={2}>`.
5. Modify `app/(app)/docs/platform-map/page.tsx`:
   - Stat numbers (hero bar): `FuzzyText fontSize="1.375rem"`, `fontWeight=700`, `baseIntensity=0.09`, `hoverIntensity=0.45`, `fuzzRange=14`, `fps=50`, `glitchMode`, `glitchInterval=3600`, `glitchDuration=140`, `transitionDuration=6`. Wrapped in `<div className={cls} aria-label={String(value)}>` — inherits section colour via `getComputedStyle`.
   - Section headers (timeline explorer): `FuzzyText fontSize="1rem"`, `fontWeight=700`, `baseIntensity=0.05`, `hoverIntensity=0.28`, `fuzzRange=10`, `fps=45`, `transitionDuration=5`, `enableHover`. Placed inside `<h2>` with colour class — inherits violet/blue/orange etc.
6. Modify `app/(admin)/admin/research-log/page.tsx` — MetricTile metric number: `FuzzyText fontSize="1.25rem"`, `fontWeight=600`, `baseIntensity=0.07`, `hoverIntensity=0.38`, `fuzzRange=10`, `fps=45`, `glitchMode`, `glitchInterval=4800`, `glitchDuration=120`, `transitionDuration=4`. Colour inherited from parent `toneClass` div (success/warning/foreground).

### PageHeader revert (no net change)

- `components/layout/page-header.tsx` was temporarily changed to use FuzzyText for the `h1` title.
- User rejected: "i dont anto change the above style of header n h1 of them."
- Reverted to original exact implementation — plain `<h1 className="truncate text-2xl font-semibold tracking-tight">{title}</h1>`.

## Decisions taken

- **`"currentColor"` as the FuzzyText default** — instead of hardcoding hex colours (the original React Bits component uses `#fff`/`#120F17`), `color="currentColor"` + `getComputedStyle` reads the CSS `color` from the parent div. FuzzyText colour is therefore automatic in both light and dark mode and inherits per-section colour classes (violet, blue, orange) on the platform-map page.
- **`AnimatedItem` as a separate export** from the string-array `AnimatedList` — the original React Bits component only handles `string[]`. Exporting `AnimatedItem` lets any `ReactNode` be wrapped for scroll-triggered entrance.
- **Sticky table headers require `overflow-auto` on the wrapper** — `overflow-hidden` creates a clipping context that disables `position:sticky` on descendants. Changed to `overflow-auto max-h-[520px]`.
- **FuzzyText on `"use client"` islands only** — `not-found.tsx` is a server component; `FuzzyNotFoundHero` is a thin client island. `coming-soon.tsx` added `"use client"` directive.
- **No FuzzyText on PageHeader `h1`** — user explicitly rejected; reverted completely.

## Open questions

- None outstanding. All user requests addressed.

## Acceptance criteria

- `AnimatedItem` wrappers: items on all 6 list pages animate in on scroll entrance (scale + fade from y=8px). Scrolling away and back re-triggers the animation.
- Table headers: on all 13 table pages the `<thead>` stays fixed at the top as the body scrolls; max height 520px.
- FuzzyText on 404: "404" canvas renders with glitch mode, click-burst effect, no FOUC.
- FuzzyText on ComingSoon: title has gentle base fuzz; on hover the fuzz intensifies.
- FuzzyText on platform-map stats: stat numbers fuzz + glitch, colour matches section accent.
- FuzzyText on research-log metrics: metric numbers fuzz + glitch, colour inherits tone class.
- `components/layout/page-header.tsx` is bit-for-bit identical to its pre-session state.

## Linked trackers

- [CHANGES.md](../CHANGES.md)
- [FEATURES.md](../FEATURES.md) — F-179, F-180, F-181, F-182
- [SESSIONS.md](../SESSIONS.md) — Session 52
