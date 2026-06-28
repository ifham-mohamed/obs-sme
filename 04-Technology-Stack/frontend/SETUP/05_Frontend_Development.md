# 05 — Frontend Development

> **Goal:** add a new page, locale string, theme token, or shadcn primitive without inventing a pattern. Every convention here is already followed by `(auth)`, `(app)`, and `(admin)` route groups.
>
> **Prerequisite:** [`02_Quickstart.md`](02_Quickstart.md) ran to completion; `make dev-frontend` shows the landing page.

---

## 1. Day-to-day commands

All run from the `frontend/` directory. Source: [`frontend/package.json`](../../frontend/package.json).

| Command | What it does |
|---------|--------------|
| `pnpm install` | Install dependencies. Re-run when `package.json` changes. |
| `pnpm dev` | Next.js dev server with hot reload on `:3000`. (Or `make dev-frontend`.) |
| `pnpm build` | Production build (validates types and routes). |
| `pnpm start` | Run the production build locally. |
| `pnpm lint` | ESLint via `next lint`. |
| `pnpm typecheck` | `tsc --noEmit` — catches type errors without emitting JS. |
| `pnpm format` | Prettier on the whole tree. |
| `pnpm test` | Vitest. |
| `pnpm e2e` | Playwright. Both dev servers must be running. |
| `pnpm exec playwright install chromium` | One-time browser install for E2E. |

---

## 2. Directory map

```
frontend/
├── app/                                  ← App Router root
│   ├── layout.tsx                        ← root: fonts, providers, Toaster
│   ├── globals.css                       ← shadcn HSL token contract (light + dark)
│   ├── page.tsx                          ← public landing
│   │
│   ├── (auth)/                           ← unauth'd shell
│   │   ├── layout.tsx
│   │   ├── login/page.tsx
│   │   └── register/page.tsx
│   │
│   ├── (app)/                            ← auth'd shell
│   │   ├── layout.tsx                    ← await requireUser()
│   │   ├── dashboard/page.tsx
│   │   ├── surveys/
│   │   │   ├── page.tsx                  ← unified hub (By Regulation / By Module tabs)
│   │   │   ├── awareness/{page,thank-you/page}.tsx
│   │   │   ├── knowledge/{page,thank-you/page}.tsx
│   │   │   ├── vulnerability/{page,thank-you/page}.tsx
│   │   │   ├── regulation/[id]/page.tsx  ← regulation-scoped session survey
│   │   │   ├── module/[id]/page.tsx      ← per-module session survey
│   │   │   ├── unified/page.tsx          ← cross-module unified session survey
│   │   │   └── history/page.tsx          ← SME completed session list
│   │   ├── risk/page.tsx             ← M2+M3 risk dashboard (fully implemented: knowledge score + compliance/behavioural signals)
│   │   └── regulations/qa/verify/page.tsx   ← stub pages (ComingSoon — BUILD_07/08/10)
│   │
│   ├── (admin)/                          ← admin shell
│   │   ├── layout.tsx                    ← await requireRole("admin")
│   │   ├── questions/{page,new/page,[code]/edit/page}.tsx ← unified question bank
│   │   ├── regulations/{page,new/page,[id]/edit/page,[id]/flow/page,[id]/authoring/page}.tsx
│   │   ├── surveys/awareness/page.tsx    ← response list
│   │   ├── m2/scores/page.tsx            ← per-SME knowledge scores
│   │   ├── m3/risk-signals/page.tsx      ← combined M2+M3 risk view
│   │   ├── activity-log/page.tsx         ← audit log viewer
│   │   ├── settings/page.tsx             ← survey submission limits (survey_limits singleton)
│   │   ├── translations/page.tsx
│   │   └── users/page.tsx
│   │
│   └── api/auth/                         ← Node-runtime cookie handlers
│       └── establish/token/logout/route.ts
│
├── components/
│   ├── ui/                               ← shadcn-pattern primitives (incl. AnimatedLoadingSkeleton, Pagination, Skeleton from Session 13)
│   ├── layout/                           ← Sidebar, Topbar, ThemeToggle, LocaleSwitcher
│   ├── surveys/
│   │   └── survey-launcher.tsx           ← start/resume session; localStorage-backed draft
│   ├── forms/
│   │   ├── survey-wizard.tsx             ← one-question renderer; module accent CSS swap; back-nav; progress bar
│   │   ├── flow-canvas.tsx               ← CSS-grid visual branching editor (M1/M2/M3 columns)
│   │   ├── authoring-wizard.tsx          ← 3-step regulation authoring wizard
│   │   ├── question-form.tsx             ← 5-card admin question form
│   │   ├── branching-rules-editor.tsx    ← Visual + JSON tabs for next_question_rules
│   │   ├── linked-questions-panel.tsx    ← M1/M2/M3 grouped question list on regulation edit
│   │   ├── flow-question-drawer.tsx      ← Radix Sheet for authoring child questions in canvas
│   │   ├── vulnerability-form.tsx        ← M3 client shell — owns submit fan-out to M3Api.submitHistory + M3Api.submitBehavioural
│   │   └── question-renderer.tsx         ← per-format renderer (single/multi/likert/numeric/date/text)
│   ├── coming-soon.tsx                   ← stub component used by deferred pages (/qa, /verify)
│   └── providers.tsx                     ← ThemeProvider + QueryClientProvider
│
├── lib/
│   ├── api/                              ← typed clients per resource (survey-sessions.ts, admin-survey-questions.ts, …)
│   ├── auth/                              ← session.ts, roles.ts
│   ├── i18n/                             ← config.ts + messages/{en,si,ta}.json
│   ├── surveys/                          ← question-code.ts (MODULE_INSTRUMENT map); legacy bank files
│   ├── types/index.ts                    ← TS mirrors of Pydantic schemas
│   ├── utils.ts                          ← cn() helper
│   └── validators/                       ← auth.ts / survey-question.ts (zod schemas)
│
├── middleware.ts                         ← cookie-presence redirect for protected paths
├── i18n.ts                               ← next-intl request config
└── tailwind.config.ts                    ← maps Tailwind utilities to HSL CSS vars
```

Why this split → [`docs/BUILD_PLAN/BUILD_02_Folder_Structure.md`](../../infra/BUILD_PLAN/BUILD_02_Folder_Structure.md) §3.

---

## 3. Route groups & RBAC

Three route groups, each with its own layout:

| Group | Layout | Who can reach pages inside |
|-------|--------|----------------------------|
| `app/(auth)/` | none beyond a thin shell | Anyone, even unauth'd. |
| `app/(app)/` | `await requireUser()` | Any authenticated user (sme / annotator / admin). |
| `app/(admin)/` | `await requireRole("admin")` | Admin only — others redirect to `/dashboard`. |

`requireUser()` and `requireRole()` live in [`frontend/lib/auth/session.ts`](../../frontend/lib/auth/session.ts). They:

1. Read the `access` cookie via `next/headers`.
2. Call `AuthApi.me(token)` → `GET /api/v1/users/me`.
3. Redirect to `/login?next=<original>` if missing/invalid; redirect to `/dashboard` if role insufficient.

[`frontend/middleware.ts`](../../frontend/middleware.ts) provides a fast cookie-presence rejection — it doesn't validate the token, just confirms a cookie exists. The actual user/role check happens in the layouts.

---

## 4. Add a new page that calls a backend endpoint — the canonical 4 steps

Worked example: `/admin/sectors` listing sector counts (matches the backend example in [`04_Backend_Development.md`](04_Backend_Development.md)).

### Step 1 — Add the TS type

```ts
// FILE: frontend/lib/types/index.ts
export type Sector = { name: string; sme_count: number };
```

### Step 2 — Add the typed API client

```ts
// FILE: frontend/lib/api/sectors.ts
import { api } from "./client";
import type { Sector } from "@/lib/types";

export const SectorsApi = {
  list: (token: string) => api.get<Sector[]>("/api/v1/sectors", token),
};
```

### Step 3 — Server-component page

Server components are async and have access to `requireRole()` + `getAccessToken()` — no client-side useEffect required.

```tsx
// FILE: frontend/app/(admin)/sectors/page.tsx
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { SectorsApi } from "@/lib/api/sectors";
import { getAccessToken } from "@/lib/auth/session";

export const dynamic = "force-dynamic";

export default async function AdminSectorsPage() {
  const token = (await getAccessToken()) ?? "";
  const sectors = await SectorsApi.list(token).catch(() => []);

  return (
    <Card>
      <CardHeader><CardTitle>Sectors</CardTitle></CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow><TableHead>Sector</TableHead><TableHead className="text-right">SMEs</TableHead></TableRow>
          </TableHeader>
          <TableBody>
            {sectors.map((s) => (
              <TableRow key={s.name}>
                <TableCell>{s.name}</TableCell>
                <TableCell className="text-right">{s.sme_count}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
```

The `(admin)` layout already calls `requireRole("admin")`, so this page is admin-only without any extra check.

### Step 4 — Sidebar link (optional)

```tsx
// FILE: frontend/components/layout/sidebar.tsx — inside ADMIN_ITEMS
{ href: "/admin/sectors", labelKey: "nav.adminSectors", icon: BarChart3, admin: true },
```

Then add the i18n key (Step 5 below) and you're done.

For client-side data (mutations, optimistic updates), wrap your page in a client component and use TanStack Query — see [`frontend/components/forms/survey-form.tsx`](../../frontend/components/forms/survey-form.tsx) for a full example.

---

## 5. Add a new locale message key

Every UI string is keyed in three message files. They must all have the same shape.

```json
// frontend/lib/i18n/messages/en.json
{ "nav": { "adminSectors": "Sectors" } }

// frontend/lib/i18n/messages/si.json
{ "nav": { "adminSectors": "අංශ" } }

// frontend/lib/i18n/messages/ta.json
{ "nav": { "adminSectors": "துறைகள்" } }
```

Then use it from any component:

```tsx
import { useTranslations } from "next-intl";
const t = useTranslations();
return <span>{t("nav.adminSectors")}</span>;
```

For server components that don't have access to the `useTranslations` hook, use `getTranslations()` from `next-intl/server`.

The locale resolves from the `NEXT_LOCALE` cookie set by the topbar's `LocaleSwitcher`. Fonts auto-fall back via the three CSS variables `--font-sans`, `--font-si`, `--font-ta` set in [`app/layout.tsx`](../../frontend/app/layout.tsx).

---

## 6. Theme tokens — light + dark

The shadcn token contract — **HSL values without `hsl(...)` and space-separated** — is defined in [`frontend/app/globals.css`](../../frontend/app/globals.css). Tailwind utilities then map via `hsl(var(--token))` in [`frontend/tailwind.config.ts`](../../frontend/tailwind.config.ts).

Today's domain-tuned palette:

| Token | Light | Dark |
|-------|-------|------|
| `--background` | `0 0% 100%` | `222 47% 6%` |
| `--foreground` | `222 47% 11%` | `210 40% 98%` |
| `--primary` (trust blue) | `217 91% 50%` | `217 91% 60%` |
| `--accent` (amber) | `38 92% 50%` | `38 92% 56%` |
| `--muted` | `210 40% 96%` | `217 32% 17%` |
| `--border` | `214 32% 91%` | `217 32% 22%` |
| `--success` | `142 71% 45%` | same |
| `--warning` | `38 92% 50%` | `38 92% 56%` |
| `--destructive` | `0 72% 51%` | same |

**To add a new semantic token:** edit `globals.css` to add it to both `:root` and `.dark`, then map it in `tailwind.config.ts` under `theme.extend.colors`. Always define the dark value — leaving it out makes dark mode look broken.

Theme switching uses [`next-themes`](https://github.com/pacocoursey/next-themes); the toggle UI is in [`components/layout/theme-toggle.tsx`](../../frontend/components/layout/theme-toggle.tsx).

---

## 7. Add a new shadcn primitive

The 21 primitives in [`frontend/components/ui/`](../../frontend/components/ui/) are written directly in the repo (not installed via `pnpm dlx shadcn add`). Recent additions: `tabs.tsx` (Session 7 — `@radix-ui/react-tabs`, used by the regulations admin form's EN/SI/TA panels); `avatar.tsx` / `breadcrumb.tsx` / `tooltip.tsx` (Session 8 — used by the new app shell); `sheet.tsx` (Session 10 — `@radix-ui/react-dialog` styled as a left-edge slide-in panel; used by the mobile sidebar drawer); `combobox.tsx` (Session 10 — searchable single + multi select with chips, no popover dep); `dialog.tsx` (Session 10 — `@radix-ui/react-dialog` for centered modals, used by the Create-user flow). Two ways to add the 22nd:

**Option A — install via the shadcn CLI:**

```bash
cd frontend
pnpm dlx shadcn@latest add tooltip
```

This writes `components/ui/tooltip.tsx` using the same HSL-token contract the existing primitives follow. The CLI reads [`frontend/components.json`](../../frontend/components.json) for paths and aliases.

**Option B — copy a similar primitive:**

If you want to customise heavily, copy one of the existing files (e.g. `dropdown-menu.tsx`) and rename. They all follow the same patterns: forwardRef, `cva` for variants, `cn()` for class merging.

Either way, the new primitive uses `hsl(var(--primary))` etc. — *never* hard-coded colours — so light/dark continues to work.

---

## 8. Reusable patterns

### `SurveyForm` + `QuestionRenderer`

Six question kinds are supported out of the box: `single`, `multi`, `likert`, `date`, `numeric`, `short_text`. Adding a new instrument doesn't require a new component:

```ts
// FILE: frontend/lib/surveys/knowledge.ts
import type { Question } from "@/lib/surveys/awareness";

export const knowledgeQuestions: Question[] = [
  { id: "knowledge.v1.q01", type: "single", label: "...", options: [...], required: true },
  ...
];
```

Then a 4-line page:

```tsx
import { SurveyForm } from "@/components/forms/survey-form";
import { knowledgeQuestions } from "@/lib/surveys/knowledge";
// ... pass instrument="knowledge" once the backend allow-list adds it
```

The backend allow-list is `SupportedInstrument` in [`backend/app/schemas/survey.py`](../../backend/app/schemas/survey.py) — extend it together with the frontend, otherwise submission 404s.

### Forms

Every form follows the same recipe: `react-hook-form` + `zod` resolver + shadcn `Input`/`Select`/`RadioGroup` + an optional `<Alert variant="destructive">` for the submit-time error message. See [`app/(auth)/login/page.tsx`](../../frontend/app/(auth)/login/page.tsx) for the smallest example, [`app/(auth)/register/page.tsx`](../../frontend/app/(auth)/register/page.tsx) for the most complete.

### Toasts

Use `toast({ title, description, variant })` from [`components/ui/toaster.tsx`](../../frontend/components/ui/toaster.tsx). The MVP toaster is intentionally minimal; richer notifications come with [`BUILD_13`](../BUILD_PLAN/BUILD_13_Admin_and_Annotation.md).

---

## 9. Common pitfalls

- **"useTranslations is not a function" in a server component** — server components must use `getTranslations()` from `next-intl/server`, not the `useTranslations` hook. The hook works only inside client components.
- **Cookie not visible to a server component** — you must `await cookies()` (Next 14) or import from `next/headers`. Server components run before route handlers; the cookie set by `/api/auth/establish` is visible on the *next* navigation, not the current response.
- **`Module not found: '@/lib/...'`** — confirm `tsconfig.json` has the `@/*` path alias and you're running from the `frontend/` directory. Restart `pnpm dev` after changing aliases.
- **shadcn primitive looks fine in light mode but ugly in dark** — you used a Tailwind colour utility (`bg-blue-500`) instead of a token (`bg-primary`). Replace it with the token.
- **Hydration mismatch warning involving the theme** — make sure `app/layout.tsx` has `suppressHydrationWarning` on `<html>`. It already does; don't remove it.

## 10. Loading states

Two tools, picked by scope:

- **`<Skeleton>`** (`components/ui/skeleton.tsx`) — a bare `animate-pulse bg-muted` box. For *inline* placeholders: one value, an avatar, a single field loading inside an otherwise-rendered page.
- **`<AnimatedLoadingSkeleton>`** (`components/ui/animated-loading-skeleton.tsx`, framer-motion) — a search icon sweeping a shuffling 6-card grid; theme-aware (`bg-card` / `text-primary` / `hsl(var(--primary))` glow), inherits the per-module accent, takes an optional `className`. For a *whole* table / grid / page loading.

And the streaming pattern: drop a `loading.tsx` into a route segment and Next wraps that segment's `page.tsx` in a Suspense boundary using `loading.tsx` as the fallback — so a server component that `await`s data streams the skeleton first. Client components that fetch via React Query render `<AnimatedLoadingSkeleton>` directly while `isLoading`.

Full screen-by-screen rationale, the component catalog, and the decision table → [`12_UI_Screens_and_Loading.md`](12_UI_Screens_and_Loading.md) §4, §6–§7.

---

**Prev:** [`04_Backend_Development.md`](04_Backend_Development.md) &nbsp;·&nbsp; **Next:** [`06_Database_and_Migrations.md`](06_Database_and_Migrations.md)
