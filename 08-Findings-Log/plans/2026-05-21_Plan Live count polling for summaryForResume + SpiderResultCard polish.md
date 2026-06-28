# Plan: Live count polling for summaryForResume + SpiderResultCard polish

## Context

Two related extraction-page UX issues:

1. **Polling stalls at Celery SUCCESS.** The page-level `summaryForResume` react-query had `staleTime: 8_000` but no `refetchInterval`. Once the spider's Celery task hit SUCCESS the existing status query stopped polling — but downstream `extract_gazette` + `preprocess_gazette` were still processing 100+ PDFs. Counts on the screen stayed frozen at "100 extracted · 0 preprocessed" until a manual reload.
2. **Raw JSON dump for spider result.** The Celery task's return payload was rendered as `<pre>{JSON.stringify(status.data.result, null, 2)}</pre>` — ugly and inconsistent with the rest of the UI.

User asked for both fixed.

## Goal

Keep `summaryForResume` polling until every in-scope row has truly settled; replace the raw JSON dump with a polished card that works for every source (EGZ/GZ/BILL/ACT).

## Scope

- **In:** `app/(admin)/admin/m1/pipeline/sources/[sourceId]/extraction/page.tsx`, new `components/m1-extraction/spider-result-card.tsx`.
- **Out:** Re-architecting the existing polling. No new dependency or schema change.

## Steps

1. Add `refetchInterval` callback to the `summaryForResume` query:
   ```ts
   refetchInterval: (q) => {
     const c = q.state.data?.status_counts;
     if (!c) return 5_000;
     const settled =
       c.ingested === 0 &&
       c.extracted === 0 &&
       c.preprocessed + c.extraction_failed >= c.in_scope;
     return settled ? false : 5_000;
   },
   refetchIntervalInBackground: false,
   ```
   5-second interval matches the existing status query. Stops automatically when everything has reached `preprocessed` (or `extraction_failed`).
2. Create `components/m1-extraction/spider-result-card.tsx` (~196 lines):
   - Header: status pill (Success / Failed) driven by `status === "ok" && returncode === "0"`.
   - 2×2 grid: Source (mono chip), Spider (mono), Scope (parsed `YYYY-MM-DD..YYYY-MM-DD` → `Date.toLocaleDateString` per locale), Return code.
   - "Other fields" fallthrough for any unknown keys (forward-compatible).
3. Wire the new card into `page.tsx` via python-atomic-write — import line + replace the `<pre>` JSON block with `<SpiderResultCard result={status.data.result as Record<string, unknown>} />`.

## Decisions taken

- Polling lives on the page-level query rather than per-component so the `PipelineRunStatusCard` and `MissingGazettesPanel` both benefit automatically.
- "Settled" condition explicitly includes `extraction_failed` so genuinely-failed rows don't keep the panel polling forever.
- Spider result card works for every source because the route is shared (`KnownSourceExtractionWorkspace` already handles EGZ/GZ/BILL/ACT).

## Open questions

- None.

## Acceptance criteria

- After Celery SUCCESS, counts on the page continue to update every 5s without manual reload.
- Polling stops once `ingested + extracted == 0` and `preprocessed + failed >= in_scope`.
- Spider result card replaces the JSON `<pre>` block; renders on all four source pages.

## Linked trackers

- [CHANGES.md](../CHANGES.md)
- [FEATURES.md](../FEATURES.md) — F-175 (polling), F-176 (card)
- [SESSIONS.md](../SESSIONS.md) — Session 49
