# Plan: Multi-source documents.gov.lk extraction (Acts + Bills + Weekly Gazettes) — Sources hub UI

  

## Context

  

The M1 pipeline currently ingests only **Extra-Gazettes** from `documents.gov.lk/view/egz/`, even though `02_M1_1_Data_Sources_Catalogue.md` registers four primary sources on the same portal (EGZ, GZ, BILL, ACT) and the live site exposes additional categories (Forms, Notices, Calendar). The current `GazetteSpider` hardcodes the EGZ start-URL template and the pipeline hardcodes `document_type="extraordinary_gazette"`, so anything other than Extra-Gazettes silently disappears.

  

The user wants three new sources covered, a "Sources hub" admin page that surfaces them as the new primary navigation, and the existing extraction page repurposed as a per-source sub-page. Forms is deferred (no date scope; different UX), Notices and Calendar are deferred (the public pages 404), and gazettes.lk is deferred (HTTP 403 to scrapers).

  

Outcome: one parameterised spider class, four concrete subclasses, one polymorphic Celery task, a `GET /sources` catalogue endpoint, and a `/admin/m1/pipeline/sources` hub that lets the operator pick which source to run.

  

## Row categorization story (each row knows its source + its storage folder)

  

Each `m1_regulations` row already carries two fields that together pin down "what is this and where does it live":

  

- **`document_type`** (existing `Literal` enum) — the explicit category: `extraordinary_gazette` / `weekly_gazette` / `bill` / `act`. The spiders set this at ingest time so every row knows which source it came from. This is the single source of truth for "category" — no separate `source_id` column added per the user's "no schema change" decision.

- **`raw_pdf_path`** (existing column) — the on-disk location, now partitioned by source: `m1/raw/EGZ/<slug>.pdf`, `m1/raw/ACT/<slug>.pdf`, etc. Reading the row tells you exactly which folder under `storage/m1/` holds the PDF.

  

A fixed mapping `_DOCTYPE_BY_SOURCE_ID` lives in `app/services/m1_sources_catalogue.py` and is the only place where source-id ↔ document-type ↔ storage-folder coupling lives, so the spiders, pipeline, reconcile, and API all read the same map.

  

**Un-categorizable PDFs (manual drops, legacy strays)** get `document_type="unknown"` (new value added to the `DocumentType` Literal — code-only change, no DB migration since the column is `VARCHAR`). The file is moved to `m1/raw/UNKNOWN/<slug>.pdf`. These rows surface as a dedicated "Needs categorization" tile on the Sources hub; the operator picks the correct type via a dropdown, the row's `document_type` flips, and the PDF moves to the right source folder. Implemented via a new `POST /api/v1/admin/m1/extraction/regulations/{id}/categorize` endpoint that:

  

1. Validates the new document_type against the known catalogue.

2. Renames the file from `m1/raw/UNKNOWN/<slug>.pdf` to `m1/raw/<NEW_SOURCE>/<slug>.pdf` atomically.

3. Updates `raw_pdf_path` and `document_type` on the row in one transaction.

4. Returns `RegulationActionOut` with `action="categorize"` (extend the existing Literal).

  

## Out of scope (explicit)

  

- Forms / Notices / Calendar — defer; flag as follow-up.

- gazettes.lk — defer; 403 needs Playwright/UA-rotation work that's its own PR.

- `m1_sources` DB table + per-source admin CRUD — defer; the catalogue lives in code (Python literal) for now.

- Adding a new `source_id` column on `m1_regulations` — defer; reuse the existing `document_type` enum (`extraordinary_gazette`, `weekly_gazette`, `bill`, `act`) as the source discriminator.

- Multi-part / multi-language drill-down inside one weekly-gazette issue (Part I/II/III × EN/SI/TA = 18 PDFs per issue). Phase-1 weekly spider grabs every PDF the year-listing surfaces but does not navigate into the per-issue 6-part page tree. Encoding part/language disambiguation goes into a follow-up.

  

## Backend changes

  

### Phase 1 — Spider refactor + storage partitioning + idempotent migration

  

**New base spider** `scraper/spiders/_base.py` — `BaseDocumentsGovLkSpider(scrapy.Spider)`:

  

```python

class BaseDocumentsGovLkSpider(scrapy.Spider):

    # Per-subclass overrides:

    source_id: ClassVar[str]              # 'EGZ' | 'ACT' | 'BILL' | 'GZ'

    document_type: ClassVar[str]          # matches M1Regulation.document_type Literal

    year_listing_template: ClassVar[str]  # e.g. 'https://documents.gov.lk/view/act/acts_{year}.html'

    short_code_prefix: ClassVar[str]      # 'GZT_' | 'ACT_' | 'BILL_' | 'WGZ_'

    document_number_regex: ClassVar[re.Pattern]   # e.g. r'\b(\d{1,3}/\d{4})\b' for acts, r'\b(\d{4}/\d{1,3})\b' for gazettes

  

    allowed_domains = ["documents.gov.lk"]

    custom_settings = {"ITEM_PIPELINES": {...}}  # shared with EGZ

  

    def __init__(self, date_from=None, date_to=None, start_url=None, **kw):

        # Shared init: validate, derive start_urls from year_listing_template

    def _in_scope(self, parsed_date):

        # Lexicographic ISO compare — unchanged from existing

    def parse(self, response):

        # Common: walk a[href$='.pdf'], pull document_number + date, yield RegulatoryDocumentItem(document_type=self.document_type, source_id=self.source_id, ...)

        # Subclasses override _extract_row_metadata() if their row markup diverges

    def _extract_row_metadata(self, anchor, response):

        # Template method: returns (document_number, document_date) — base impl works for EGZ/ACT/BILL year pages

```

  

**Existing `scraper/spiders/gazette_spider.py`** → rename to `extraordinary_gazette_spider.py`; class becomes:

  

```python

class ExtraordinaryGazetteSpider(BaseDocumentsGovLkSpider):

    name = "extraordinary_gazette_spider"  # back-compat alias 'gazette_spider' kept

    source_id = "EGZ"

    document_type = "extraordinary_gazette"

    year_listing_template = "https://documents.gov.lk/view/egz/egz_{year}.html"

    short_code_prefix = "GZT_"

    document_number_regex = re.compile(r"\b(\d{4}/\d{1,3})\b")

```

  

`name="gazette_spider"` is preserved as a class-level alias so the existing Celery subprocess invocation `scrapy crawl gazette_spider` still works during transition.

  

**Item rename** `scraper/items.py`: `GazetteItem` → `RegulatoryDocumentItem` with new fields `document_type` and `source_id`. Keep `GazetteItem = RegulatoryDocumentItem` alias for back-compat.

  

**`M1RegulationsInsertPipeline`** (`scraper/pipelines.py:142-243`):

- Read `item["document_type"]` instead of hardcoding `"extraordinary_gazette"` (line 181).

- Build short_code as `f"{item['short_code_prefix']}{_slug(item['document_number'])}"`.

- Build raw_pdf_path as `f"m1/raw/{item['source_id']}/{slug}.pdf"` (partitioned by source).

- The existing IntegrityError catch (line 203-209) already covers per-source uniqueness because each source has its own number-space.

  

**Storage partitioning** — new layout:

```

storage/m1/raw/

  EGZ/      # extraordinary gazettes (was the flat root)

  ACT/

  BILL/

  GZ/       # weekly gazettes

```

  

**One-off migration task** `app/tasks/m1/migrate_raw_layout.py` (Celery + admin button at `POST /api/v1/admin/m1/extraction/migrate-raw-layout`):

1. Scan `storage/m1/raw/*.pdf` (root level, the legacy flat layout).

2. For each file: move to `storage/m1/raw/EGZ/<file>` (every legacy file is an Extra-Gazette).

3. Update each affected `m1_regulations.raw_pdf_path` from `m1/raw/<slug>.pdf` to `m1/raw/EGZ/<slug>.pdf` in one batch UPDATE.

4. Idempotent: if root-level `*.pdf` count is 0, return `{moved: 0, already_migrated: True}`.

  

**`DocumentType` Literal** (`app/models/regulation.py:31`) gains `"unknown"`:

```python

DocumentType = Literal[

    "bill", "act", "extraordinary_gazette", "weekly_gazette",

    "circular", "order", "notification",

    "unknown",  # NEW — reconcile inserts here when source can't be inferred

]

```

No DB migration needed (column is `VARCHAR`, no CHECK constraint on this enum).

  

### Phase 2 — Three new spiders

  

**`scraper/spiders/acts_spider.py`** — `ActsSpider(BaseDocumentsGovLkSpider)`:

- `source_id="ACT"`, `document_type="act"`, `short_code_prefix="ACT_"`.

- `year_listing_template="https://documents.gov.lk/view/act/acts_{year}.html"`.

- `document_number_regex=re.compile(r"\b(\d{1,3}\s+of\s+\d{4})\b", re.I)` — pattern observed in the live table (e.g. "14 of 2024").

- 4-column table — same as EGZ. Reuse base `parse()`; override `_extract_row_metadata()` only if the row layout diverges.

  

**`scraper/spiders/bills_spider.py`** — `BillsSpider`:

- `source_id="BILL"`, `document_type="bill"`, `short_code_prefix="BILL_"`.

- `year_listing_template="https://documents.gov.lk/view/bill/bl_{year}.html"`.

- Same number-regex as Acts.

  

**`scraper/spiders/weekly_gazette_spider.py`** — `WeeklyGazetteSpider`:

- `source_id="GZ"`, `document_type="weekly_gazette"`, `short_code_prefix="WGZ_"`.

- `year_listing_template="https://documents.gov.lk/view/gz/{year}.html"`.

- Phase-1 behaviour: walk every `a[href$='.pdf']` the year page surfaces (which includes the per-date issue links). For each PDF found, yield one item. We do **not** drill into the 6-part date subpage in this PR (that's the follow-up).

- `document_number` derivation: parse `\b(\d{4}/\d{1,3})\b` from the link text or surrounding row text (same shape as EGZ).

  

All three spiders inherit `_in_scope()`, scope-exhaustion early-exit, and `from_crawler` from the base. Each test fixture (under `app/tests/integration/`) drops a recorded HTML snapshot of the year page into `app/tests/fixtures/documents_gov_lk/{source_id}_{year}.html`.

  

### Phase 3 — Polymorphic Celery task + API extension + source catalogue

  

**New Celery task** `app/tasks/m1/run_scraper.py`:

```python

_SPIDERS_BY_SOURCE_ID: Final[dict[str, str]] = {

    "EGZ": "extraordinary_gazette_spider",

    "ACT": "acts_spider",

    "BILL": "bills_spider",

    "GZ": "weekly_gazette_spider",

}

  

@celery_app.task(name="app.tasks.m1.run_scraper.run_scraper", bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3}, acks_late=True)

def run_scraper(self, source_id: str, date_from: str | None = None, date_to: str | None = None) -> dict[str, str]:

    spider_name = _SPIDERS_BY_SOURCE_ID[source_id]

    # Same subprocess + scope validation as run_gazette_spider, parameterised on spider_name

```

  

`run_gazette_spider` becomes a back-compat shim: `run_scraper("EGZ", date_from, date_to)`. The existing periodic beat schedule (if any) keeps working.

  

**New source catalogue** `app/services/m1_sources_catalogue.py` — pure-Python registry, no DB:

```python

SOURCES: Final[list[SourceMeta]] = [

    SourceMeta(source_id="EGZ", display_name="Extra-Gazettes", document_type="extraordinary_gazette", landing_url="https://documents.gov.lk/view/egz/egz.html", supports_date_range=True, cadence="daily", description_en="Time-sensitive extraordinary gazettes (~3–5/week)."),

    SourceMeta(source_id="GZ",  display_name="Weekly Gazettes", document_type="weekly_gazette",     landing_url="https://documents.gov.lk/view/gz/find_gazette.html", supports_date_range=True, cadence="weekly", description_en="Regular weekly Friday gazettes (Part I–III)."),

    SourceMeta(source_id="BILL", display_name="Bills", document_type="bill", landing_url="https://documents.gov.lk/view/bill/bills.html", supports_date_range=True, cadence="weekly", description_en="Draft legislation before parliament."),

    SourceMeta(source_id="ACT",  display_name="Acts", document_type="act",  landing_url="https://documents.gov.lk/view/act/acts.html", supports_date_range=True, cadence="weekly", description_en="Certified acts of parliament."),

]

```

Plus helper `get_source_stats(session, source_id)` returning `{total, status_counts, last_extracted_at}` for the hub tiles.

  

**API extensions** (`app/api/v1/m1_gazette_extraction.py`):

  

- `GET /sources` → `list[SourceWithStatsOut]` — catalogue + per-source counts.

- `GET /sources/{source_id}` → `SourceWithStatsOut` — single source.

- `POST /trigger` — `GazetteExtractionTriggerIn` gains `source_id: str = "EGZ"` (default = back-compat). Dispatches `run_scraper.delay(source_id, ...)` instead of `run_gazette_spider.delay(...)`.

- `GET /progress` — optional `?source_id=...` filter; existing `_extraction_scope_filter` extended with `M1Regulation.document_type == _DOCTYPE_BY_SOURCE_ID[source_id]` when present.

- `GET /summary` — same.

- `POST /reconcile` — `ReconcileRequestIn` with optional `source_id`. Reconcile walks `storage/m1/raw/{source_id}/` if given; otherwise walks every known source subdir **plus** the legacy root and any unknown subdir. The slug regex needs source-aware extraction (acts/bills use `<num>_<year>` slug, gazettes use `<gz_num>_<part>` slug). Use a per-source `recover_document_number(source_id, stem)` helper next to `slug_gazette_number`. PDFs that don't match any known slug pattern (or live outside a known source folder) get inserted with `document_type="unknown"`, moved to `m1/raw/UNKNOWN/`, and surface on the "Needs categorization" tile.

  

- `POST /regulations/{id}/categorize` — body `CategorizeIn { document_type: DocumentType }`. Validates the new type against the catalogue (rejects `unknown` — only "real" categories accepted), atomically renames the file from its current `raw_pdf_path` to `m1/raw/<NEW_SOURCE>/<basename>`, updates `raw_pdf_path` + `document_type` in one transaction, returns `RegulationActionOut` with `action="categorize"`. The `RegulationActionOut.action` Literal grows to include `"categorize"` alongside `"retry" | "re-extract" | "re-preprocess"`.

  

**Schema changes** `app/schemas/m1_pipeline.py`:

- New `SourceMeta` and `SourceWithStatsOut` Pydantic models matching the catalogue.

- `GazetteExtractionTriggerIn`: `source_id: Literal["EGZ", "GZ", "BILL", "ACT"] = "EGZ"`.

- `ExtractionProgressRow`: add `source_id: str | None` derived from `document_type`.

  

**`unslug_to_gazette_number`** in `app/services/m1_pipeline_service.py` needs a sibling `recover_document_number(source_id, stem)` that handles the per-source slug shapes (`14_2024` → "14 of 2024" for acts; `2486_22` → "2486/22" for gazettes).

  

## Frontend changes

  

### Phase 4 — Sources hub + per-source extraction sub-page

  

**New page** `app/(admin)/admin/m1/pipeline/sources/page.tsx` — Sources hub:

- Server component, fetches `GET /sources` once.

- Renders a 2×2 grid of source cards (one per `SourceMeta`). Each card shows:

  - Icon (lucide: `FileText` for acts, `FileEdit` for bills, `CalendarDays` for weekly, `FileWarning` for extra-gazettes).

  - Display name + cadence chip.

  - Stats triple: total ingested, last extracted relative time, status pill (success if last_extracted_at < 24h, warning if 1–7d, neutral if older, error if any `extraction_failed` in the last 24h).

  - Description (en).

  - "Open extraction →" link to `/admin/m1/pipeline/sources/{source_id}/extraction`.

  

- **5th "Needs categorization" tile** rendered when `GET /sources` reports any row with `document_type="unknown"`. Tile shows the count, a `FileQuestion` icon, and a "Categorize →" link to `/admin/m1/pipeline/sources/UNKNOWN`. That page lists each uncategorized row with the existing `RegulationProgressCard` plus a `<Select>` of the four real source types; on change → `POST /regulations/{id}/categorize` → row vanishes from this list once the API returns 200 (React Query invalidation). The tile disappears automatically when the count hits 0.

  

**New dynamic route** `app/(admin)/admin/m1/pipeline/sources/[sourceId]/extraction/page.tsx`:

- Moves the body of the existing `app/(admin)/admin/m1/pipeline/extraction/page.tsx` here, parameterised on `params.sourceId`.

- All API calls include `source_id` in the payload / query string.

- `ExtractionProgressPanel`, `ExtractionSummaryCard`, `RegulationProgressCard` all accept an optional `sourceId` prop and pass through.

- Page header shows the source's display name + cadence chip + landing-URL link out.

  

**Old route** `app/(admin)/admin/m1/pipeline/extraction/page.tsx`:

- Replace body with a `redirect("/admin/m1/pipeline/sources/EGZ/extraction")` Next.js server-side redirect (no client flash). Preserves any bookmarks pointing at the old URL.

  

**Sidebar** (`components/layout/sidebar.tsx`):

- Add "Sources" entry under "M1 Pipeline" pointing at `/admin/m1/pipeline/sources`. The old "Extraction" entry either stays (links straight to EGZ for muscle-memory) or gets removed in favour of "Sources" — recommend **remove** for cleanliness.

  

**API client extensions** (`lib/api/m1-gazette-extraction.ts`):

```typescript

export type SourceId = "EGZ" | "GZ" | "BILL" | "ACT";

  

export interface SourceMeta {

  source_id: SourceId;

  display_name: string;

  document_type: string;

  landing_url: string;

  supports_date_range: boolean;

  cadence: "daily" | "weekly";

  description_en: string;

}

  

export interface SourceWithStatsOut extends SourceMeta {

  total: number;

  status_counts: { ingested: number; extracted: number; preprocessed: number; extraction_failed: number };

  last_extracted_at: string | null;

}

  

M1GazetteExtractionApi = {

  ...existing,

  listSources: (token) => api.get<SourceWithStatsOut[]>(...),

  getSource:   (token, sid) => api.get<SourceWithStatsOut>(...),

  trigger:     (token, { source_id?, date_from, date_to }) => ...,   // source_id added

  reconcile:   (token, { source_id? }) => ...,                       // source_id added

  categorize:  (token, regulationId, document_type) => ...,           // NEW — for the "Needs categorization" flow

};

```

  

## Reuse — existing code that should NOT be re-implemented

  

- `scraper/spiders/gazette_spider.py` `_in_scope`, `_DATE_RE`, `parse_pdf_listing` — extract into the base class.

- `scraper/pipelines.py` `_SLUG_RE`, `_slug`, `PDFDownloadPipeline` (idempotent disk-skip), `M1RegulationsInsertPipeline` (IntegrityError handling) — keep, only swap the hardcoded `document_type` and prefix.

- `app/tasks/m1/gazette_scraper.py` `_validate_scope`, subprocess wiring — base of the new `run_scraper.py`.

- `app/services/m1_pipeline_service.py` `_extraction_scope_filter`, `get_extraction_progress`, `get_extraction_summary` — add an optional `document_type` filter, do not rewrite.

- `app/api/v1/m1_gazette_extraction.py` retry / re-extract / re-preprocess / reconcile endpoints from the just-shipped recovery layer — already source-agnostic (operate on a `regulation_id`); no changes needed.

- Frontend `DateRangePicker`, `RegulationProgressCard`, `ExtractionProgressPanel`, `ExtractionSummaryCard`, `RecentTriggersBar` — reused verbatim by the dynamic `[sourceId]/extraction` page; only the API-call payloads thread `source_id` through.

  

## Critical files

  

**Backend (new):**

- `scraper/spiders/_base.py` — `BaseDocumentsGovLkSpider`

- `scraper/spiders/acts_spider.py`

- `scraper/spiders/bills_spider.py`

- `scraper/spiders/weekly_gazette_spider.py`

- `app/tasks/m1/run_scraper.py`

- `app/tasks/m1/migrate_raw_layout.py`

- `app/services/m1_sources_catalogue.py`

  

**Backend (modified):**

- `scraper/spiders/gazette_spider.py` → rename to `extraordinary_gazette_spider.py`; subclass base

- `scraper/items.py` — `GazetteItem` → `RegulatoryDocumentItem` + alias

- `scraper/pipelines.py` — read `document_type` + partitioned raw_pdf_path

- `app/tasks/m1/__init__.py` — export `run_scraper`, `migrate_raw_layout`

- `app/tasks/m1/gazette_scraper.py` — make `run_gazette_spider` a shim calling `run_scraper("EGZ", ...)`

- `app/tasks/m1/reconcile_raw.py` — walk per-source subdirs; per-source slug recovery

- `app/services/m1_pipeline_service.py` — `recover_document_number` helper; optional `document_type` filter on progress/summary

- `app/schemas/m1_pipeline.py` — `SourceMeta` / `SourceWithStatsOut`; `source_id` on trigger + progress row

- `app/api/v1/m1_gazette_extraction.py` — `/sources`, `/sources/{id}`; thread `source_id` through trigger / progress / summary / reconcile

  

**Frontend (new):**

- `app/(admin)/admin/m1/pipeline/sources/page.tsx` — Sources hub (4 source tiles + conditional "Needs categorization" tile)

- `app/(admin)/admin/m1/pipeline/sources/[sourceId]/extraction/page.tsx` — per-source extraction sub-page (moves the existing extraction page body); when `sourceId === "UNKNOWN"`, render the "Needs categorization" list view with the categorize dropdown instead

  

**Frontend (modified):**

- `app/(admin)/admin/m1/pipeline/extraction/page.tsx` — server-side redirect to `/sources/EGZ/extraction`

- `components/layout/sidebar.tsx` — add "Sources" entry; remove or repoint "Extraction"

- `lib/api/m1-gazette-extraction.ts` — `SourceMeta` / `SourceWithStatsOut`; new methods; thread `source_id` through existing methods

- `components/m1-extraction/extraction-progress-panel.tsx` — accept + forward `sourceId`

- `components/m1-extraction/extraction-summary-card.tsx` — same

- `components/m1-extraction/regulation-progress-card.tsx` — source badge derived from `document_type`

  

## Verification

  

**Backend (run from `enigmatrix-backend/`):**

```

uv run pytest app/tests/integration/test_spiders_documents_gov_lk.py -v

uv run pytest app/tests/unit/test_sources_catalogue.py -v

uv run alembic upgrade head     # no migration this PR, but verify no drift

```

  

**Spider smoke:**

1. `scrapy crawl acts_spider -a date_from=2026-01-01 -a date_to=2026-05-01` — confirm PDFs land in `storage/m1/raw/ACT/`.

2. Same for `bills_spider` and `weekly_gazette_spider`.

3. `POST /api/v1/admin/m1/extraction/migrate-raw-layout` once on a dev DB seeded with legacy flat files; confirm files moved to `m1/raw/EGZ/` and DB `raw_pdf_path` values updated.

  

**End-to-end:**

1. Visit `/admin/m1/pipeline/sources` — see 4 tiles with correct counts pulled from the existing 452 EGZ rows.

2. Click "Acts" tile → land on `/sources/ACT/extraction` with empty progress feed.

3. Pick a date range, click "Start extraction" — see new ACT rows appear with `document_type='act'` and `raw_pdf_path` starting `m1/raw/ACT/`.

4. Hit the EGZ tile — confirm the existing 452 rows + the recovery actions (retry / re-extract / re-preprocess / reconcile) still work after the rename and migration.

5. `GET /api/v1/admin/m1/extraction/progress?source_id=ACT&date_from=...&date_to=...&since=...` — only ACT rows return.

6. Drop a random PDF into `storage/m1/raw/` root (no source folder), click "Reconcile raw folder" — file moves to `m1/raw/UNKNOWN/`, row appears with `document_type='unknown'`. Sources hub shows a 5th "Needs categorization (1)" tile. Open it, pick "Acts" from the dropdown → row's `document_type` flips to `'act'`, PDF moves to `m1/raw/ACT/`, tile count drops to 0 and disappears.

  

## Post-run vault sync

  

After implementation, append a Session entry to `C:\sme\08-Findings-Log\SESSIONS.md` and add F-### rows to `CHANGES.md` / `FEATURES.md` covering the four sub-features:

- F-### Multi-source spider base + Acts spider

- F-### Bills + Weekly Gazettes spiders

- F-### `/sources` API + source catalogue

- F-### Sources hub UI + per-source extraction sub-page

  

Then run `/graphify --update` on both `C:\Reasearch\xyz\graphify-out\` and `C:\sme\graphify-out\`.