---
tags: [setup, frontend, local-dev, powershell]
source: synthesised
layer: meta
module: shared
---

# Frontend Local Development (PowerShell)

> **Prereqs**: complete [00_LOCAL_DEV_HANDBOOK §1.1](../../00_LOCAL_DEV_HANDBOOK.md) first (Node 20 + pnpm). This doc assumes you're in PowerShell 7+ with the repo at `C:\Reasearch\xyz\` (or the WSL-native + symlinked option per §2 of the handbook).

The frontend (`enigmatrix-frontend/`) is a Next.js 14 App Router app with TypeScript, Tailwind CSS, shadcn/ui primitives, React Hook Form + Zod, and next-intl (en/si/ta). It talks to the backend via the `lib/api/` typed client. Runs natively in PowerShell on Windows — no WSL needed.

---

## 1 · Pre-flight check

```powershell
pwsh --version              # 7.4+
node --version              # v20.x.x (LTS)
pnpm --version              # 9.x.x
git --version
docker info | Select-String "Server Version"   # Docker Desktop running (only needed for backend integration)
```

If any fail, see [00_LOCAL_DEV_HANDBOOK §1.1](../../00_LOCAL_DEV_HANDBOOK.md).

---

## 2 · Install deps (`pnpm install`)

```powershell
cd C:\Reasearch\xyz\enigmatrix-frontend
pnpm install
```

**Important:** the repo uses `pnpm-lock.yaml`. **Do NOT** run `npm install` — it would create a conflicting `package-lock.json`. If you see one accidentally, delete it.

First run takes ~1 minute. Subsequent runs use the pnpm content-addressable store (instant).

Verify:

```powershell
pnpm list next react   # expect next@14.x, react@18.x
```

---

## 3 · Environment configuration

```powershell
Copy-Item .env.example .env.local
notepad .env.local
```

Edit `.env.local` and set:

| Var | Local dev value | Notes |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | matches the backend's uvicorn dev port |
| `NEXTAUTH_URL` | `http://localhost:3000` | the frontend's own URL |
| `NEXT_PUBLIC_DEFAULT_LOCALE` | `en` | one of `en`/`si`/`ta` |

The frontend has its OWN cookie-handler routes at `/api/auth/establish` and `/api/auth/logout` that bridge between backend JWT auth and Next.js's session — see [07_Auth_and_Roles](../../backend/SETUP/07_Auth_and_Roles.md) on the backend side and `app/api/auth/` on the frontend.

---

## 4 · Run the dev server

```powershell
pnpm dev
```

Output:

```
ready - started server on 0.0.0.0:3000, url: http://localhost:3000
```

Open `http://localhost:3000` → should redirect to `/login` (assuming you haven't authenticated yet).

Sign in with the seed admin: `admin@enigmatrix.lk` / `admin12345678`. After successful auth → redirects to `/admin/regulations` (admin role) or `/dashboard` (SME role).

Press `Ctrl+C` to stop.

---

## 5 · Type-check + lint + build

```powershell
pnpm typecheck   # tsc --noEmit; ~10s for a clean codebase
pnpm lint        # eslint; warnings allowed, errors fail the build
pnpm build       # production build; ~30s; outputs .next/
pnpm start       # serve the production build on port 3000
```

CI runs `pnpm typecheck && pnpm lint && pnpm build` — keep these green before committing.

---

## 6 · Frontend project layout

```
enigmatrix-frontend/
├── app/                             (Next.js App Router routes)
│   ├── (admin)/admin/...           (admin-only routes; gated by middleware)
│   ├── (app)/...                   (authenticated user routes)
│   ├── (auth)/{login,register}/     (public auth pages — Session 29 split-panel UI)
│   ├── (app)/docs/m1/page.tsx       (M1 documentation portal — Session 29)
│   └── api/auth/                    (Next.js route handlers for cookie management)
├── components/
│   ├── admin/                       (admin-only components)
│   ├── docs/m1/                     (M1 portal components — Session 29)
│   ├── forms/                       (RHF + Zod forms)
│   ├── layout/                      (topbar, sidebar, theme toggle)
│   ├── surveys/                     (survey launcher, wizard, drawer)
│   ├── ui/                          (shadcn primitives + custom)
│   └── providers.tsx                (TanStack Query + next-themes)
├── lib/
│   ├── api/                         (typed API clients — admin-surveys, regulations, etc.)
│   ├── auth/                        (session, roles, server-side require helpers)
│   ├── i18n/                        (next-intl config + messages/{en,si,ta}.json)
│   ├── m1-docs.ts                   (M1 portal data — Session 29 consolidation)
│   ├── validators/                  (Zod schemas)
│   └── utils.ts                     (cn, formatters)
└── middleware.ts                    (auth redirect for protected routes)
```

---

## 7 · Frontend ↔ Backend wiring

The typed API clients in `lib/api/` call the backend via `NEXT_PUBLIC_API_BASE_URL`. Pattern:

```typescript
// lib/api/regulations.ts (example)
export const RegulationsApi = {
  list: (params?: ListParams) => apiGet<RegulationListOut>("/api/v1/regulations", params),
  ...
};
```

The cookie-handler at `app/api/auth/establish/route.ts` is the Next.js bridge:

1. Frontend POSTs credentials to backend `/api/v1/auth/login` → receives `access_token` + `refresh_token`.
2. Frontend POSTs both tokens to its own `/api/auth/establish` (Next.js route handler) → sets HTTP-only cookies.
3. Subsequent SSR requests read the cookie and call the backend with `Authorization: Bearer <access_token>`.

Backend's `CORS_ORIGINS=http://localhost:3000` is what allows this cross-origin chatter.

---

## 8 · Verifying changes after each edit

### Type-only or component change

1. Make the edit.
2. Watch `pnpm dev` hot-reload — the browser refreshes within ~1s.
3. If TypeScript fails: `pnpm typecheck` for the full error list (more detail than the in-browser overlay).

### Adding a new API client method

1. Add the function in `lib/api/<area>.ts`.
2. Add the matching backend route in `enigmatrix-backend/app/api/v1/<area>.py`.
3. Verify with `curl http://localhost:8000/api/v1/<route>` (or the API client from the dev server).
4. Add a test if the route mutates state.

### Adding a new admin page

1. New `app/(admin)/admin/<area>/page.tsx`.
2. Add to the sidebar nav at `components/layout/sidebar.tsx`.
3. Add a navigation key to all 3 `lib/i18n/messages/{en,si,ta}.json` files (next-intl will throw at runtime for missing keys).
4. Test with admin role; verify the route is gated for SME role.

### Adding a new SME-facing flow

1. New `app/(app)/<area>/page.tsx`.
2. Same sidebar + i18n steps as admin.
3. If it consumes survey data, wire to `lib/api/surveys.ts` or `survey-flow.ts`.

---

## 9 · Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `pnpm: cannot be loaded because running scripts is disabled` | PowerShell execution policy | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `pnpm: command not found` | Not on PATH | `npm install -g pnpm@9` + restart terminal |
| Port 3000 already in use | Prior `pnpm dev` still running | `netstat -ano \| findstr :3000` then `taskkill /PID <pid> /F` |
| `Error: Cannot find module 'next'` | `pnpm install` skipped or wrong directory | `pnpm install` from `enigmatrix-frontend/` |
| CORS error in browser console | Backend `CORS_ORIGINS` mismatch | Update backend `.env` `CORS_ORIGINS=http://localhost:3000` + restart uvicorn |
| 401 on /admin/regulations | Cookie expired or wrong base URL | Log out + log in; verify `NEXT_PUBLIC_API_BASE_URL` matches the running backend |
| Hot-reload doesn't update components | File saved on `/mnt/c/` from WSL (slow inotify) | Save from PowerShell side, or use `pnpm dev --turbo` (Turbopack is more reliable across WSL boundary) |
| Tailwind classes not applied | Tailwind didn't pick up the file | Restart `pnpm dev`; verify the file is included in `content` glob of `tailwind.config.ts` |
| i18n shows raw key (e.g. `surveys.hub.title`) | Missing translation key | Add to all 3 `lib/i18n/messages/{en,si,ta}.json` files; next-intl warns in dev console |
| Theme toggle stuck on light | localStorage caches the choice | Clear `localStorage.theme` in browser DevTools |

---

## 10 · Cross-references

- **Frontend dev guide** (feature-by-feature): [05_Frontend_Development](05_Frontend_Development.md)
- **UI screens inventory**: [12_UI_Screens_and_Loading](12_UI_Screens_and_Loading.md)
- **Unified survey config**: [13_Unified_Survey_Configuration](13_Unified_Survey_Configuration.md)
- **Architecture overview**: [../../shared/03_Architecture](../../shared/03_Architecture.md)
- **Backend WSL setup**: [../../backend/SETUP/00_LOCAL_DEV_WSL](../../backend/SETUP/00_LOCAL_DEV_WSL.md)
- **Top-level handbook**: [../../00_LOCAL_DEV_HANDBOOK](../../00_LOCAL_DEV_HANDBOOK.md)