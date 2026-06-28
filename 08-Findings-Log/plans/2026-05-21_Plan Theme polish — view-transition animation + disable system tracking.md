# Plan: Theme polish — view-transition animation + disable system tracking

## Context

Two unrelated theme issues surfaced in the same chat segment:

1. The theme-switch view-transition reveal felt twitchy — easing was `ease-in-out` over 420ms and the universal `* { transition: ... }` colour transitions in `globals.css` were running underneath the view-transition snapshot, producing two parallel animations.
2. The app was auto-changing themes when the operating system flipped colour scheme (macOS / Windows auto-appearance schedules).

User asked for a smoother animation and an end to the OS auto-follow behaviour.

## Goal

Replace the current view-transition reveal with a single cohesive motion; pin the theme to a user-chosen value and stop tracking OS preference.

## Scope

- **In:** `components/layout/theme-toggle.tsx`, `app/globals.css`, `components/providers.tsx`.
- **Out:** Per-route theme overrides, system-aware fallback for first-time visitors (replaced with fixed `defaultTheme="light"`).

## Steps

1. `theme-toggle.tsx` — easing → `cubic-bezier(0.22, 1, 0.36, 1)` (easeOutQuint); duration 420ms → 600ms; subtle scale (1.015 → 1) + opacity (0.92 → 1) on new layer; scale (1 → 0.985) + opacity (1 → 0.6) on old layer; flip a `theme-transitioning` class on `<html>` for the transition's lifetime; sync Sun/Moon icon transitions to 500ms with the same bezier.
2. `globals.css` — add GPU promotion (`will-change: clip-path, transform, opacity`, `backface-visibility: hidden`, `transform-origin: center center`) on the view-transition pseudo-elements; add `html.theme-transitioning *` rule suppressing the universal colour transitions during the view-transition.
3. `providers.tsx` — `ThemeProvider` props: `defaultTheme="light"`, `enableSystem={false}`, `storageKey="enigmatrix-theme"`. Confirm `setTheme` is only invoked from `theme-toggle.tsx` (single click handler) — no other programmatic callers in the codebase.

## Decisions taken

- Disabling the universal transitions only during the view-transition (via the `theme-transitioning` class) avoids two animations competing; outside the transition window the universal hover/focus transitions still run.
- `defaultTheme="light"` rather than `"dark"` because the brand's identity palette reads warmer on light first.
- `storageKey="enigmatrix-theme"` namespaces the persisted preference so it can't be clobbered by a generic key collision.

## Open questions

- Should first-time visitors with a strongly-set `prefers-color-scheme: dark` get dark by default? Current decision: no, fixed `light` default.

## Acceptance criteria

- Click toggle → reveal animates smoothly, ~600ms, no flicker.
- OS auto-flips colour scheme → app theme does not change.
- Refresh → theme preference persists in localStorage under `enigmatrix-theme`.

## Linked trackers

- [CHANGES.md](../CHANGES.md)
- [FEATURES.md](../FEATURES.md) — F-171, F-183
- [SESSIONS.md](../SESSIONS.md) — Session 44, Session 52

---

## Update — 2026-05-22 (Session 52 — Theme toggle: dropdown to single-click toggle button)

### Additional context

The `ThemeToggle` component in `components/layout/theme-toggle.tsx` was still rendered as a shadcn dropdown menu (three options: Light / Dark / System). User asked to convert it to a single click-to-toggle button with a beautiful animated transition.

### Additional goal

Replace the dropdown control with a minimal icon button that cycles `light <-> dark` on click, using the View Transitions API for a full-screen circular clip-path reveal expanding outward from the click origin.

### Additional scope

- **In:** `components/layout/theme-toggle.tsx` (full rewrite to toggle pattern), `components/providers.tsx` (remove `disableTransitionOnChange`), `app/globals.css` (view-transition rules + universal colour token transitions).
- **Out:** System theme support (dropped — user confirmed fixed `light` default is acceptable).

### Steps taken (Session 52)

1. `theme-toggle.tsx` full rewrite:
   - Removed dropdown menu entirely.
   - Single `<Button variant="ghost" size="icon">` with `onClick={handleToggle}`.
   - Sun icon visible when `isDark=true` (click goes to light); Moon visible when `isDark=false` (click goes to dark). Each in an `<span className="absolute">` with `transition-all duration-500 ease-[cubic-bezier(0.22,1,0.36,1)]`; toggled via `rotate-0 scale-100 opacity-100` and `rotate-90 scale-0 opacity-0`.
   - `handleToggle` computes click coordinates `(x, y)` and `endRadius = Math.hypot(max(x, W-x), max(y, H-y))`.
   - Feature-detected `"startViewTransition" in document` — graceful fallback to instant `setTheme` if unavailable.
   - Flips `document.documentElement.classList.add("theme-transitioning")` before `startViewTransition` and removes it in `transition.finished.finally(...)`.
   - New layer (`::view-transition-new(root)`): `clip-path circle(0->endRadius)` + `scale(1.015->1)` + `opacity(0.92->1)`, 600ms `cubic-bezier(0.22, 1, 0.36, 1)` (easeOutQuint), `fill:"both"`.
   - Old layer (`::view-transition-old(root)`): `opacity(1->0.6)` + `scale(1->0.985)`, same easing + duration.

2. `providers.tsx` — removed `disableTransitionOnChange` attribute from `<ThemeProvider>` so CSS colour-token transitions run during the switch.

3. `app/globals.css` — added:
   - `::view-transition-old/new(root) { animation: none; mix-blend-mode: normal; }` + z-index layering (`new` at 9999, `old` at 1).
   - `html.theme-transitioning * { transition: none !important; }` — suppresses competing universal colour transitions only during the view-transition window; outside it, normal hover/focus transitions are unaffected.
   - `will-change: clip-path, transform, opacity; backface-visibility: hidden; transform-origin: center center` on `::view-transition-new/old(root)` — GPU-promotes the animated layers.
   - `@media (prefers-reduced-motion: reduce)` — both pseudo-elements get `animation: none` for accessibility.
   - Universal colour token transition block: `transition-property: background-color, border-color, color, fill, stroke, box-shadow; transition-duration: 200ms` on `*,*::before,*::after`; overridden to 150ms for interactive elements (`a, button, [role="button"], input, textarea, select`).

### Feature ID

F-183

### Acceptance criteria

- Click toggle reveals circular expand from exact click coordinates, ~600ms easeOutQuint, no flicker.
- Old snapshot gently scales down + fades underneath.
- Sun and Moon icons swap with rotate+scale+fade over 500ms with easeOutQuint.
- `html.theme-transitioning` is present only during the ~600ms window; absent at all other times.
- `prefers-reduced-motion: reduce` results in instant swap, no clip-path animation.
- `providers.tsx` has no `disableTransitionOnChange` attribute.
