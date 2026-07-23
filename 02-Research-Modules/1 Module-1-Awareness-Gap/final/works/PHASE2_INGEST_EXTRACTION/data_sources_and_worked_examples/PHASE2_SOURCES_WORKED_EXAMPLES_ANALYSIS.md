# Phase 2 · Data Requirements — Source Catalogue + Worked Examples: Analysis

> Group: `PHASE2_INGEST_EXTRACTION / data_sources_and_worked_examples`. Companion: [[PHASE2_SOURCES_WORKED_EXAMPLES_PLAN]].
> Builds [[02_M1_1_Data_Sources_Catalogue]] + [[02_M1_4_Worked_Examples_All_Tables]] into code. Sibling build: [[PHASE2_DATA_VALIDATION_GOVERNANCE_ANALYSIS]] (02_2 + 02_3). **Status: implemented 2026-07-23 (verification deferred — sandbox VHDX down).**

## 1. 02_M1_1 — what already existed vs the real gap

The doc reads as "build the source registry + per-source ops + health tracking." Reading the code showed **most of that already shipped** in Phase-4 gap 4a:

- `m1_sources` table (migration `202607210006`, 15 rows seeded) — identity + `active` + health columns (`last_checked_at`, `last_ok_at`, `consecutive_failures`, `last_error`).
- `secondary_sources.load_sources()` (registry read, static-tuple fallback) and `mark_source_result()` (per-pass health update) — **already wired into both `portal_watcher` and `rss_watcher`**.

So re-implementing "health tracking" would have duplicated working code. The genuine gap was the **operational catalogue** the doc's table describes — scrape cadence, auth, URL pattern, failure mode, fallback — which lived nowhere in code, plus the doc's monitoring asks (per-source uptime alert, "≥3 consecutive cycles" empty-response signal) which nothing surfaced.

**Real vs idealized ids:** the doc's `SRC_GOV_EGZ`/`SRC_IRD`/`SRC_NEWS_FT` handles don't exist; the live ids are `IRD`, `EPF`, …, `NEWS_FT`. The primary gazette sources are Scrapy spiders, not `m1_sources` rows. The catalogue is keyed by the real secondary-source ids; primary spider ops are reference-only.

## 2. 02_M1_4 — the schema is smaller than the doc

The doc walks "all 9 tables," but only a subset was ever tabled:

| Doc table | Reality |
|---|---|
| `m1_regulations`, `m1_regulation_sectors`, `m1_regulation_penalties`, `m1_propagation_events` | exist |
| `m1_sme_awareness_responses` | responses live in `survey_responses` (keyed `sme_id`, `answer_date`) |
| `m1_regulation_changes` (clause-level), `m1_court_cases`, `m1_real_world_examples` | **no such tables** — clause changes were never tabled; the real-world example is a column on `m1_regulations` |
| `v_m1_regulation_lag_summary`, `v_m1_channel_effectiveness` | exist (migration `202606300004`) |

So the worked-example seed can populate `regulation → sectors → penalties → propagation → awareness` and let the two views compute — but not the three non-existent tables. The seed documents that honestly rather than inventing tables.

## 3. Enum reality (shared with the 02_2 build)

The seed had to use the **real** enums or trip the new Layer-1 CHECK constraints from [[PHASE2_DATA_VALIDATION_GOVERNANCE_PLAN]]: `change_category` from the 12-value set (not `TAX_RATE_CHANGE`), integer `severity_level` (not `critical`), `penalty_type` from the 7-value set, `channel IN ('official_portal','news_rss')`, `match_method IN ('exact_gazette','fuzzy_title')`, and — critically — `status='alerted'` requires a non-null `change_category` (`ck_m1_reg_category_when_classified`). All examples set a category, so they satisfy their own validation layer.

## 4. Risk posture (sandbox down)

No migrate/seed/pytest run was possible. The seed is therefore **defensive**: idempotent on `regulation_short_code`; it queries the existing `sectors` / `m1_sources` / `sme_profiles` keys up front and links only those that exist, so a fresh or partially-seeded DB produces fewer linked rows instead of a `ForeignKeyViolation`; each example commits in its own transaction inside a try/except. Worst case on first run is "some examples seed fewer child rows," never a crash or partial-corrupt state. The catalogue + health-report additions are read-only over `m1_sources`.
