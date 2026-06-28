# Plan: Frontend perf overhaul — dashboard streaming, login handoff, bundle + query tuning

## Context

User reported >10 second delay between login submission and the dashboard rendering. Investigation in chat traced three compounding causes:

1. Login handler makes **four sequential** network calls — `AuthApi.login()` → `/api/auth/establish` → `/api/auth/me` → `router.replace()` triggers SSR → `router.refresh()` throws away the just-rendered tree and re-renders.
2. Dashboard server component awaits `Promise.all` of **five backend fetches** before returning any HTML — blank screen on cold backend start.
3. React-query defaults `refetchOnWindowFocus: true`, `refetchOnReconnect: true`, `refetchOnMount: true` cause redundant fetches on every navigation.

Planning questions confirmed: full overhaul, OK to move slow queries server-side.

## Goal

Cut the >10s symptom to a perceived sub-second shell paint; apply broader perf wins where they don't add churn.

## Scope

- **In:** Dashboard Suspense streaming, login flow shortening, Next.js prod config, QueryClient defaults, code-splitting of heavy admin charts.
- **Out:** Full route-by-route audit, bundle-analyzer wiring, RSC conversion of admin routes.

## Steps

1. **Dashboard streaming** — rewrite `app/(app)/dashboard/page.tsx` so the page shell + welcome banner are synchronous, and each data-bound section is its own async server component wrapped in `<Suspense fallback={<Skeleton/>}>`: `StatCardsSection`, `PendingRegulationsSection`, `LowerSection`. Each section's `Promise.all` is independent — slow upstream calls only delay their own section.
2. **`/api/auth/establish` returns role** — add a base64url JWT-payload decoder server-side that pulls `role` from the access token's claims and returns `{ ok: true, role }`. No verification (the token is already signed by the backend; we only need to peek for routing).
3. **Login page slimming** — read `role` from `establish` response, drop the `/api/auth/me` fetch, drop `router.refresh()` (the `router.replace()` already triggers a fresh SSR for the new route).
4. **`next.config.mjs`** — add `productionBrowserSourceMaps: false`, `swcMinify: true`, `compress: true`, `output: "standalone"`, `poweredByHeader: false`. Expand `experimental.optimizePackageImports` to cover `lucide-react`, `date-fns`, `recharts`, `framer-motion`, six `@radix-ui/*` packages. Add `images` config with AVIF/WebP and `documents.gov.lk` + `enigmatrix-backend.vercel.app` `remotePatterns`.
5. **`providers.tsx`** — tune QueryClient: `staleTime: 60_000`, `gcTime: 10 * 60_000`, `refetchOnWindowFocus: false`, `refetchOnReconnect: false`, `refetchOnMount: false`, `retry: 1`, `retryDelay: 1_000`. Mutations: `retry: 0`.
6. **Code-split recharts** — `next/dynamic({ ssr: false, loading: () => <Skeleton /> })` for `ThroughputChart`, `StatusDistribution`, `FunnelChart` in `app/(admin)/admin/m1/pipeline/page.tsx`. Note the route-segment-config / `next/dynamic` name collision; alias the import as `nextDynamic`.

## Decisions taken

- Streaming Suspense over RSC + fetch deduplication is the biggest single perceived-perf win — shell paints in 50–200ms while sections fill in.
- QueryClient defaults tuned for "data is fine for 60s without refetch" — live polling stays opt-in per query (e.g. the new `summaryForResume` keeps its own 5s `refetchInterval`).
- `output: "standalone"` enables smaller Docker / Fly.io deploys without breaking Vercel.

## Open questions / risks

- Streaming requires the reverse proxy NOT buffer responses. Vercel default is fine. Nginx in front of a custom deploy would need `proxy_buffering off`.
- `output: "standalone"` may need Dockerfile adjustments for non-Vercel deploys.

## Acceptance criteria

- Login → dashboard shell paint < 1 second.
- Login network sequence reduced from 4 calls to 2.
- Back-navigation pops instantly from cache (no refetch on mount).
- M1 pipeline page initial JS bundle smaller; recharts deferred until after first paint.

## Linked trackers

- [CHANGES.md](../CHANGES.md)
- [FEATURES.md](../FEATURES.md) — F-174
- [SESSIONS.md](../SESSIONS.md) — Session 47
