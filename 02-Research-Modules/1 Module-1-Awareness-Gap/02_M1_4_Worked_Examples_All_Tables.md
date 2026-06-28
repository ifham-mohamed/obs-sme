# 02_M1_4 — Worked Examples Across All 9 Tables

> Companion to [02_M1_Data_Requirements.md](02_M1_Data_Requirements.md) — three complete worked examples (multi-pin adapter, VAT amendment, EPF rate change), each showing rows in all 9 `m1_*` tables + the two analytical views.
> **Implementation status:** 🔲 Deferred (BUILD_07 — data only exists in the manual-CRUD admin slice today, with 5 demo regulations).

## Purpose

The parent doc has one worked end-to-end example (multi-pin adapter, §7). That's enough to explain the schema but insufficient to test it — readers can't see what edge cases look like. This companion adds two more examples that exercise the schema's harder corners: a multi-clause VAT amendment (19 changes from a single regulation) and an EPF rate change (cross-cutting impact on every employer in the country).

## Detailed process

Each example below populates every relevant table. Examples are anonymised but realistic — they're built from the seeded demo regulations (`VAT_2024_AMD`, `EPF_2024_RATE`, the `VAT_SSCL_MERGE_2026` Session-15 scenario, and the multi-pin adapter case from the parent doc).

### Example A — Multi-pin adapter regulation (carried over from parent doc §7)

The parent doc already populates 6 tables for this regulation. This sub-step doc adds the missing two: `m1_sme_awareness_responses` (survey responses) and the analytical view outputs.

**`m1_sme_awareness_responses` rows (n=5 sample SMEs):**

```json
[
  {"sme_profile_id":"sme_alpha", "regulation_id":"reg_2486_22",
   "awareness_date":"2026-05-12", "awareness_source":"news",
   "action_taken":"yes_in_progress", "response_date":"2026-05-20T09:14:00Z"},
  {"sme_profile_id":"sme_beta", "regulation_id":"reg_2486_22",
   "awareness_date":"2026-06-03", "awareness_source":"accountant",
   "action_taken":"yes_complied", "response_date":"2026-06-10T16:22:00Z"},
  {"sme_profile_id":"sme_gamma", "regulation_id":"reg_2486_22",
   "awareness_date":"2026-07-21", "awareness_source":"government_sms",
   "action_taken":"yes_complied", "response_date":"2026-07-30T11:00:00Z"},
  {"sme_profile_id":"sme_delta", "regulation_id":"reg_2486_22",
   "awareness_date":"2026-08-15", "awareness_source":"peer",
   "action_taken":"no_not_aware_of_deadline", "response_date":"2026-08-20T18:45:00Z"},
  {"sme_profile_id":"sme_epsilon", "regulation_id":"reg_2486_22",
   "awareness_date":null, "awareness_source":null,
   "action_taken":"no_not_applicable", "response_date":"2026-09-01T10:00:00Z"}
]
```

**View output — `v_m1_regulation_lag_summary` for this regulation:**

| Column | Value |
|---|---|
| `gazette_number` | 2486/22 |
| `gazette_published_date` | 2026-04-15 |
| `effective_date` | 2026-08-01 |
| `lag_to_official_portal` | 7.0 (days; SLSI portal posted on 2026-04-22) |
| `lag_to_news` | 23.0 (Daily FT covered 2026-05-08) |
| `smes_surveyed` | 5 |
| `smes_aware` | 4 (one `awareness_date IS NULL`) |
| `avg_sme_lag_days` | 53.5 |
| `median_sme_lag_days` | 50.0 |

### Example B — VAT Amendment Act, No. 8 of 2024 (`VAT_2024_AMD`)

A multi-clause amendment that touches 19 distinct clauses across the principal VAT Act. The full breakdown lives in [02_M1_Data_Requirements.md §7.1 (worked example)](02_M1_Data_Requirements.md) — this section shows two more tables it populates.

**`m1_regulations` row:**

```json
{
  "regulation_short_code":"VAT_2024_AMD",
  "gazette_number":"2369/14",
  "gazette_date":"2024-01-01",
  "gazette_type":"act",
  "title_en":"VAT Amendment Act No. 8 of 2024",
  "change_category":"TAX_RATE_CHANGE",
  "severity_level":"critical",
  "affected_sectors":["manufacturing","retail","services","agriculture","construction","it_bpo","hospitality","transport","healthcare","finance"],
  "primary_language":"en",
  "is_sme_relevant":true,
  "status":"alerted"
}
```

**`m1_regulation_sectors` rows (10 — one per sector):**

```sql
INSERT INTO m1_regulation_sectors (regulation_id, sector_code) VALUES
  ('reg_vat_2024_amd', 'manufacturing'),
  ('reg_vat_2024_amd', 'retail'),
  ('reg_vat_2024_amd', 'services'),
  -- ... 7 more
```

**`m1_regulation_changes` rows** — 19 total; 5 representative shown in [02_M1_Data_Requirements.md §7.1](02_M1_Data_Requirements.md). The pattern: each clause-level change is a separate row with `clause_reference`, `old_value`, `new_value`, `applies_to`, `real_world_impact`.

**`m1_regulation_penalties` rows (2 — one fine + one combined):**

```json
[
  {"violation_type":"Late filing of monthly VAT return", "penalty_type":"fine",
   "penalty_min_lkr":25000, "penalty_max_lkr":null,
   "additional_consequences":"1.5% per month of unpaid VAT",
   "legal_basis_section":"Section 66(3)"},
  {"violation_type":"Failure to register at the new threshold (LKR 80M turnover)",
   "penalty_type":"both",
   "penalty_min_lkr":100000, "penalty_max_lkr":1000000, "imprisonment_max_months":6,
   "legal_basis_section":"Section 22"}
]
```

**Cross-module wire-up.** Per the Session-15 unified-flow design, `VAT_2024_AMD` is the regulation triggered by M0/M1 awareness Q12 (a "yes" to the multi-pin adapter question). The chain continues: M1 surfaces → M2 RAG retrieves clause-level summaries → M3 projects to `m3_field_mapping` (per OQ32). See [13_M1_Folder_Structure_and_Implementation_Flow.md](13_M1_Folder_Structure_and_Implementation_Flow.md) §Inter-module connections for the full handoff.

### Example C — EPF Contribution Rate Change (`EPF_2024_RATE`)

EPF rate changes are cross-cutting — every employer is affected. The example illustrates the schema's all-10-sectors case + an analytical view that highlights this.

**`m1_regulations`:**

```json
{
  "regulation_short_code":"EPF_2024_RATE",
  "gazette_number":"2370/05",
  "gazette_date":"2024-02-01",
  "gazette_type":"supplement_1",
  "title_en":"Employees' Provident Fund (Contribution Rate Amendment) Order 2024",
  "change_category":"EPF_ETF_CHANGE",
  "severity_level":"high",
  "affected_sectors":["manufacturing","retail","services","agriculture","construction","it_bpo","hospitality","transport","healthcare","finance"],
  "primary_language":"en",
  "is_sme_relevant":true,
  "status":"alerted"
}
```

**`m1_regulation_changes` (3 rows):**

```json
[
  {"clause_reference":"Section 12(1)",
   "change_summary_en":"Employer EPF contribution rate raised from 12% to 13% of gross salary",
   "old_value":"12", "new_value":"13",
   "applies_to":"All employers of >5 employees",
   "real_world_impact":"~8.3% increase in employer-side payroll obligation"},
  {"clause_reference":"Section 12(2)",
   "change_summary_en":"Employee EPF contribution rate unchanged at 8% (clarification)",
   "old_value":"8", "new_value":"8",
   "applies_to":"All EPF members",
   "real_world_impact":"No change; clarification only"},
  {"clause_reference":"Schedule II",
   "change_summary_en":"Salary cap for EPF eligibility increased from LKR 75k to LKR 100k",
   "old_value":"75000", "new_value":"100000",
   "applies_to":"All employees earning above the threshold",
   "real_world_impact":"~14% more employees newly covered by EPF"}
]
```

**View output — `v_m1_channel_effectiveness` snapshot (across many regulations including this one):**

| `channel` | `sme_count` | `avg_lag_days` | `median_lag_days` |
|---|---|---|---|
| `government_sms` | 38 | 1.2 | 1.0 |
| `enigmatrix_alert_email` | 412 | 0.5 | 0.3 |
| `accountant` | 487 | 31.4 | 28.0 |
| `news` | 215 | 24.8 | 22.0 |
| `portal_epf` | 134 | 6.2 | 5.0 |
| `peer` | 89 | 48.3 | 42.0 |

This is the F4 finding (RQ4 — channel effectiveness) directly. Note the < 1-day lag for Enigmatrix alerts; the > 28-day lag for accountants. The dataset across all SMEs and all regulations produces a stable rank that informs the policy recommendation in the thesis.

## Technology choices

This is a worked-example doc — no software choice. The only craft decision is which regulations to use:

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| Seeded demo regulations only (chosen) | Anonymised + already known to readers | ✅ Uses `VAT_2024_AMD`, `EPF_2024_RATE`, `VAT_SSCL_MERGE_2026`, multi-pin adapter — all already in the project | If the demo seed changes, re-render. |
| Real scraped gazettes | Maximum realism | ❌ PII risk + commits us to keeping the examples current as gazettes are re-issued | If the project moves to a public docs site with clearance to publish real cases. |
| Synthetic templates | Easiest to generate | ❌ Loses the "this is what real Sri Lankan regulatory data looks like" flavour | If demo regulations are removed and we need stand-ins. |

## Worked example

The three worked examples above **are** this doc's example. The pattern they all share:

1. Insert into `m1_regulations` (one row).
2. Multi-row insert into `m1_regulation_sectors` (one per affected sector).
3. Multi-row insert into `m1_regulation_changes` (one per clause).
4. Optional `m1_real_world_examples` (one per illustrative SME scenario).
5. `m1_regulation_penalties` (one per distinct violation type).
6. `m1_court_cases` (zero or more — added post-enforcement).
7. `m1_propagation_events` (one per channel — `gazette`, `portal_*`, `news_*`, `alert_delivery`).
8. `m1_sme_awareness_responses` (one per surveyed SME — Q1–Q7 answers).
9. The two views (`v_m1_regulation_lag_summary` + `v_m1_channel_effectiveness`) compute lag from these rows.

A reader who can write each of those nine inserts for a *new* regulation has fully understood the schema.

## Failure modes & edge cases

- **Missing optional rows.** Not every regulation has court cases or real-world examples; the schema allows zero. The view computes lag from whatever propagation events exist.
- **Re-issue / supersession.** A gazette can be amended by a later gazette. The schema represents this via `m1_regulation_changes.supersedes_change_id` (FK to itself, NULL on first issuance). The view filters supersedeed rows when computing the current effective text.
- **Multi-language same regulation.** Sri Lankan acts are issued in EN + SI + TA simultaneously. The schema stores one `m1_regulations` row with all three title and summary fields populated, **not** three rows.
- **Cross-module overlap.** `VAT_2024_AMD` also seeds the M3 `m3_field_mapping` per OQ32 (the Session-15 unified flow). The M1 row is the source of truth; M3 references via `regulation_id`.

## Validation & acceptance criteria

- **Round-trip test.** For each of the three examples, a unit test in `tests/m1/test_worked_examples.py` inserts all rows, runs the two views, and asserts the expected lag values.
- **Constraint coverage.** Each example exercises at least one `CHECK` constraint from [02_M1_2_Database_Schema_Validation.md](02_M1_2_Database_Schema_Validation.md) (e.g. EPF example tests the `chk_category_when_classified` constraint).
- **Sector coverage.** Across the three examples, all 10 sectors and all 12 categories are exercised at least once.

## Cross-references

- Parent: [02_M1_Data_Requirements.md](02_M1_Data_Requirements.md) §7 (parent's worked example), §2 (schema)
- Related: [02_M1_2_Database_Schema_Validation.md](02_M1_2_Database_Schema_Validation.md), [08_M1_1_Research_Findings_Extraction.md](08_M1_1_Research_Findings_Extraction.md)
- BUILD phase: BUILD_07 (data ingestion fills these tables for real)
- Code (when shipped): `backend/app/scripts/seed_regulations.py` (currently seeds 5 demo rows — to be extended in BUILD_07)
