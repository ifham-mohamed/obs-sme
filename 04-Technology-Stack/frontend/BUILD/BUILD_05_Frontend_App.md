# BUILD 05 — Frontend (Next.js 14, App Router)

> **Goal:** a runnable Next.js 14 app with TypeScript, Tailwind, i18n (EN/SI/TA), an authenticated layout, an API client, a design system, and stub pages for every module.

---

## 1. Initialize

```bash
# RUN
cd frontend
pnpm create next-app@14 . --typescript --tailwind --eslint --app --src-dir=false \
  --import-alias "@/*" --use-pnpm
pnpm add next-intl @tanstack/react-query zod react-hook-form @hookform/resolvers \
        lucide-react clsx class-variance-authority tailwind-merge \
        recharts date-fns @radix-ui/react-dialog @radix-ui/react-dropdown-menu \
        @radix-ui/react-tabs @radix-ui/react-tooltip @radix-ui/react-slot
pnpm add -D @types/node prettier prettier-plugin-tailwindcss \
            @playwright/test vitest @testing-library/react @testing-library/jest-dom
```

### `package.json` scripts

```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "format": "prettier -w .",
    "test": "vitest",
    "e2e": "playwright test"
  }
}
```

---

## 2. Tailwind + Design Tokens

```ts
// FILE: frontend/tailwind.config.ts
import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg:      "hsl(var(--bg))",
        fg:      "hsl(var(--fg))",
        muted:   "hsl(var(--muted))",
        border:  "hsl(var(--border))",
        primary: { DEFAULT: "hsl(var(--primary))", fg: "hsl(var(--primary-fg))" },
        success: "hsl(var(--success))",
        warning: "hsl(var(--warning))",
        danger:  "hsl(var(--danger))",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        si:   ["var(--font-si)", "system-ui", "sans-serif"],
        ta:   ["var(--font-ta)", "system-ui", "sans-serif"],
      },
      borderRadius: { lg: "var(--radius)", md: "calc(var(--radius) - 2px)" },
    },
  },
} satisfies Config;
```

```css
/* FILE: frontend/styles/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --bg: 0 0% 100%;
  --fg: 224 71% 4%;
  --muted: 220 14% 96%;
  --border: 220 13% 91%;
  --primary: 212 95% 42%;
  --primary-fg: 0 0% 100%;
  --success: 142 71% 45%;
  --warning: 38 92% 50%;
  --danger: 0 72% 51%;
  --radius: 0.5rem;
}
.dark { --bg: 224 71% 4%; --fg: 210 20% 98%; --muted: 215 28% 17%;
        --border: 215 28% 25%; --primary: 212 95% 60%; }
```

---

## 3. Multilingual Fonts (Sinhala / Tamil)

Use `next/font` for self-hosting. Edit `app/layout.tsx`:

```tsx
// FILE: frontend/app/layout.tsx
import "@/styles/globals.css";
import { Inter, Noto_Sans_Sinhala, Noto_Sans_Tamil } from "next/font/google";
import { Providers } from "@/components/providers";

const sans = Inter({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const si   = Noto_Sans_Sinhala({ subsets: ["sinhala"], variable: "--font-si", display: "swap" });
const ta   = Noto_Sans_Tamil({ subsets: ["tamil"], variable: "--font-ta", display: "swap" });

export const metadata = { title: "Enigmatrix", description: "SME Regulatory Intelligence" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${sans.variable} ${si.variable} ${ta.variable}`}>
      <body className="bg-bg text-fg antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

---

## 4. i18n with `next-intl`

```ts
// FILE: frontend/lib/i18n/config.ts
export const locales = ["en", "si", "ta"] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = "en";
```

```ts
// FILE: frontend/i18n.ts (project root, used by next-intl)
import { getRequestConfig } from "next-intl/server";
import { locales, type Locale } from "@/lib/i18n/config";

export default getRequestConfig(async ({ locale }) => {
  if (!locales.includes(locale as Locale)) locale = "en";
  return { messages: (await import(`./lib/i18n/messages/${locale}.json`)).default };
});
```

```json
// FILE: frontend/lib/i18n/messages/en.json
{
  "nav": { "dashboard": "Dashboard", "regulations": "Regulations",
           "qa": "Ask", "verify": "Verify", "risk": "Risk" },
  "common": { "loading": "Loading...", "error": "Something went wrong",
              "save": "Save", "cancel": "Cancel" },
  "auth": { "login": "Sign in", "register": "Sign up", "logout": "Sign out" }
}
```

> Mirror the structure for `si.json` and `ta.json`. Use the workflow from research file `Enigmatrix_Research_Proposal_Upgraded.md` §7.4 (back-translation review by NL speakers).

---

## 5. API Client

```ts
// FILE: frontend/lib/api/client.ts
const BASE = process.env.NEXT_PUBLIC_API_BASE_URL!;

class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}, accessToken?: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...(init.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ code: "unknown", message: res.statusText }));
    throw new ApiError(res.status, body.code, body.message);
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

export const api = {
  get:  <T>(p: string, t?: string) => request<T>(p, { method: "GET" }, t),
  post: <T>(p: string, body: unknown, t?: string) =>
    request<T>(p, { method: "POST", body: JSON.stringify(body) }, t),
};
export { ApiError };
```

```ts
// FILE: frontend/lib/api/regulations.ts
import { api } from "./client";
import type { Regulation, Page } from "@/lib/types";

export const RegulationsApi = {
  list: (params: Record<string, string | number | undefined>, token?: string) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined) as [string, string][]
    ).toString();
    return api.get<Page<Regulation>>(`/api/v1/regulations?${qs}`, token);
  },
  get: (id: string, token?: string) => api.get<Regulation>(`/api/v1/regulations/${id}`, token),
};
```

---

## 6. Shared Types (Mirror Pydantic Schemas)

```ts
// FILE: frontend/lib/types/index.ts
export type Page<T> = { items: T[]; page: number; size: number; total: number };

export type Regulation = {
  regulation_id: string;
  gazette_number: string;
  gazette_date: string;          // ISO
  title: string | null;
  issuing_agency: string | null;
  predicted_category: string | null;
  confidence: number | null;
  summary_en: string | null;
  summary_si: string | null;
  summary_ta: string | null;
  effective_date: string | null;
  source_url: string;
  created_at: string;
};

export type RiskScore = { score: number; band: "low" | "medium" | "high" };
export type ShapAttribution = { feature: string; value: number };
```

> **Tip:** generate these from FastAPI's OpenAPI spec to stay in sync — see Claude Prompt 3 below.

---

## 7. Layouts and Route Groups

```tsx
// FILE: frontend/app/(app)/layout.tsx
import { Sidebar } from "@/components/layout/sidebar";
import { TopBar } from "@/components/layout/topbar";
import { requireUser } from "@/lib/auth/session";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const user = await requireUser();   // redirects to /login if not authed
  return (
    <div className="flex min-h-screen">
      <Sidebar role={user.role} />
      <div className="flex flex-1 flex-col">
        <TopBar user={user} />
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
```

```tsx
// FILE: frontend/app/(app)/dashboard/page.tsx
import { RiskGauge } from "@/components/module3/risk-gauge";
import { RecentRegulations } from "@/components/module1/recent-regulations";

export default async function DashboardPage() {
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <section className="lg:col-span-1"><RiskGauge /></section>
      <section className="lg:col-span-2"><RecentRegulations /></section>
    </div>
  );
}
```

---

## 8. UI Primitives — `components/ui/`

Lift small pieces from `shadcn/ui` (or write your own). Minimum set:

```
components/ui/
├── button.tsx
├── input.tsx
├── textarea.tsx
├── select.tsx
├── label.tsx
├── card.tsx
├── dialog.tsx
├── dropdown.tsx
├── tabs.tsx
├── toast.tsx
├── badge.tsx
├── skeleton.tsx
├── alert.tsx
└── pagination.tsx
```

Pattern (Button):

```tsx
// FILE: frontend/components/ui/button.tsx
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const button = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary: "bg-primary text-primary-fg hover:bg-primary/90",
        ghost:   "hover:bg-muted",
        danger:  "bg-danger text-white hover:bg-danger/90",
        outline: "border border-border hover:bg-muted",
      },
      size: { sm: "h-8 px-3", md: "h-10 px-4", lg: "h-12 px-6" },
    },
    defaultVariants: { variant: "primary", size: "md" },
  }
);
type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof button>;
export function Button({ className, variant, size, ...rest }: Props) {
  return <button className={cn(button({ variant, size }), className)} {...rest} />;
}
```

---

## 9. State / Data Fetching — TanStack Query

```tsx
// FILE: frontend/components/providers.tsx
"use client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(() => new QueryClient({
    defaultOptions: { queries: { staleTime: 30_000, refetchOnWindowFocus: false } },
  }));
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
```

```tsx
// FILE: frontend/components/module1/regulation-list.tsx
"use client";
import { useQuery } from "@tanstack/react-query";
import { RegulationsApi } from "@/lib/api/regulations";
import { useSession } from "@/lib/auth/use-session";
import { RegulationCard } from "./regulation-card";

export function RegulationList({ page, category }: { page: number; category?: string }) {
  const { token } = useSession();
  const { data, isLoading } = useQuery({
    queryKey: ["regulations", page, category],
    queryFn: () => RegulationsApi.list({ page, size: 20, category }, token),
  });
  if (isLoading) return <div>Loading…</div>;
  return (
    <div className="grid gap-3">
      {data?.items.map(r => <RegulationCard key={r.regulation_id} reg={r} />)}
    </div>
  );
}
```

---

## 10. Page Inventory (Stubs in Week 3)

| Path | What it shows | Status by week 3 |
|------|---------------|------------------|
| `/login` | Email/password form | working |
| `/register` | User + SME profile form | working |
| `/dashboard` | Risk + recent regulations | stub w/ static |
| `/regulations` | Paginated list, filters | working (M1 backed) |
| `/regulations/[id]` | Detail w/ EN/SI/TA tabs | working |
| `/qa` | Chat UI (Module 2) | stub |
| `/verify` | Paste claim → verdict (Module 4) | stub |
| `/risk` | Risk score + SHAP (Module 3) | stub |
| `/surveys/awareness` | Module 1 survey | working (forms backed) |
| `/surveys/knowledge` | Module 2 survey | working |
| `/surveys/vulnerability` | Module 3 survey | working |
| `/surveys/misinformation` | Module 4 survey | working |
| `/admin/annotation` | Annotator queue | stub |
| `/admin/training` | Training run dashboard | stub |
| `/admin/models` | Model registry | stub |
| `/admin/datasets` | Untrained vs trained counts | stub |
| `/admin/lag` | Researcher lag dashboard | stub |

---

## 11. Forms — Reusable Survey Pattern

```tsx
// FILE: frontend/components/forms/survey-form.tsx
"use client";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";

export type Question =
  | { id: string; type: "text"; label: string; required?: boolean }
  | { id: string; type: "single"; label: string; options: string[] }
  | { id: string; type: "multi"; label: string; options: string[] }
  | { id: string; type: "scale"; label: string; min: number; max: number };

export function SurveyForm({ instrument, questions, onSubmit }: {
  instrument: string;
  questions: Question[];
  onSubmit: (values: Record<string, any>) => Promise<void>;
}) {
  const schema = z.object(Object.fromEntries(questions.map(q => [q.id, z.any()])));
  const { register, handleSubmit, formState } = useForm({ resolver: zodResolver(schema) });
  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {/* Render fields based on q.type */}
      {questions.map(q => <div key={q.id} className="space-y-2">{/* … */}</div>)}
      <Button disabled={formState.isSubmitting}>Submit</Button>
    </form>
  );
}
```

---

## 12. Accessibility, RTL, and Locale Switching

- Every interactive element keyboard-accessible (`tabindex`, `aria-*`)
- Run `pnpm lint` with `eslint-plugin-jsx-a11y`
- `<html lang="...">` switches per locale
- For Tamil and Sinhala, ensure font fallbacks via `font-si` / `font-ta` utility classes on text-heavy areas
- Provide a locale switcher in the topbar that writes a `NEXT_LOCALE` cookie and reloads

---

## 13. Acceptance Criteria

- [ ] `pnpm dev` serves `http://localhost:3000` and the home page loads in all three locales
- [ ] Sinhala and Tamil text renders with correct fonts (no boxes or fallback Latin)
- [ ] `/regulations` makes a real call to `http://localhost:8000/api/v1/regulations` and renders rows
- [ ] Auth-guarded layout redirects unauthenticated users to `/login`
- [ ] Dark mode toggles via a class on `<html>`
- [ ] Lighthouse a11y score ≥ 90 on home + dashboard
- [ ] All pages from §10 exist (stubs are fine where marked)

---

## 14. Claude Prompts for This Section

### Prompt 1 — Generate UI primitives

```
Generate these UI primitive components for a Next.js 14 + TypeScript + Tailwind app
using class-variance-authority and Radix UI primitives:
button, input, textarea, select, label, card, dialog, dropdown,
tabs, toast (with provider), badge, skeleton, alert, pagination.

Each as `# FILE: frontend/components/ui/<name>.tsx`. Use the design tokens from
BUILD_05 §2 (--bg, --fg, --primary, --muted, etc.). No prose.
```

### Prompt 2 — Generate localized survey

```
Build a complete `/surveys/awareness` page (Next.js 14 app router) that:
- Loads the question set from `lib/surveys/awareness.ts` (12 questions matching
  research file 08_SME_Questionnaire_Design.md §3)
- Uses react-hook-form + zod for validation
- Supports en/si/ta question text via next-intl
- Submits to POST /api/v1/surveys/awareness/submit with the access token
- Shows a thank-you screen on success

Output: page.tsx, the question set file, and a thank-you component.
```

### Prompt 3 — Sync TS types from OpenAPI

```
Set up automatic generation of TypeScript types in frontend/lib/types/api.ts
from the FastAPI OpenAPI schema at http://localhost:8000/openapi.json
using openapi-typescript. Include:
- The pnpm script `gen:types`
- A pre-commit hook so types regenerate on backend schema changes
- A README block explaining the workflow
```

---

> **Note on admin routes:** the role-based access middleware defined here is the foundation that `BUILD_13_Admin_and_Annotation.md` builds upon. Admin/annotator routes inherit the RBAC guards specified in §6 (route groups + middleware) — they are not re-implemented in BUILD_13.

**Prev:** `BUILD_04_Database_and_Storage.md` &nbsp;·&nbsp; **Next:** `BUILD_06_Auth_and_Users.md`
