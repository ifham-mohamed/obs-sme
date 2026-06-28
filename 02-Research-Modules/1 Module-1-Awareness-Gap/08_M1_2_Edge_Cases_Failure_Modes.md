# 08_M1_2 — Edge Cases & Failure Modes (extended catalogue)

> Companion to [08_M1_Full_System_Architecture.md](08_M1_Full_System_Architecture.md) — 20+ edge cases beyond the parent doc's table, with detection, resolution, and monitoring metric for each.
> **Implementation status:** 🟡 Partial — edge-case handling is wired up alongside the code that produces the failure mode; many entries below are deferred to BUILD_07/11/12.

## Purpose

Parent doc §13 has 9 edge cases. This companion extends to 23 — every failure mode the system has been *anticipated* to encounter, with the specific monitoring metric or code path that detects each. It's the runbook for "the on-call has just been paged, what does this mean?"

## Detailed process

The catalogue below is sorted by pipeline stage. For each: trigger (how it appears), detection (the metric/log that catches it), resolution (manual + automated paths), monitoring (where the dashboard surfaces it).

### Stage A — Ingestion

| # | Edge case | Trigger | Detection | Resolution | Monitoring |
|---|---|---|---|---|---|
| 1 | `gazette.lk` down | HTTP 5xx | Scrapy retry middleware fails 5×; Celery task marked failed | Wait for portal recovery; manual re-trigger after | `m1_sources.uptime_30d_pct` alert |
| 2 | Source URL silently changed | Scraper returns empty list when there should be new items | `m1_sources.last_check_status='empty_response'` for 3 cycles | Admin updates URL override table | Dashboard alert |
| 3 | PDF download timeout > 30 s | `asyncio.TimeoutError` | Celery retry once; if still fails → `status='extraction_failed'` | Admin re-runs `POST /admin/m1/regulations/{id}/redownload` | `m1_pipeline_errors` table |
| 4 | Duplicate gazette URL | Pre-check matches | Skip silently | None needed | Debug log |
| 5 | Cabinet leak — news before gazette | News article arrives, no `m1_regulations` row | Tier-3 review queue with `pre_gazette_leak=true` | Admin links to regulation once gazetted | Review queue dashboard |

### Stage B — Extraction

| # | Edge case | Trigger | Detection | Resolution | Monitoring |
|---|---|---|---|---|---|
| 6 | PDF password-protected | `fitz.PasswordError` | Caught in extractor; status=`extraction_failed`, reason='encrypted' | Admin manually decrypts or marks `is_active=false` | Daily failure-reason summary |
| 7 | PDF is a TIFF wrapper (no text) | OCR returns < 10 chars on all pages | `chars_per_page < 5` across all pages | Auto-mark `is_active=false`; flag for manual review | Pipeline failure-rate metric |
| 8 | Wijesekara font detected | Glyph-fingerprint heuristic in `ocr.py` | `is_wijesekara_encoded=True` | Apply Wijesekara→Unicode conversion before classification | OCR conversion-rate metric |
| 9 | Multi-language interleaved at line level | High `mixed` rate from lang router | `language='mixed'` for > 30 % of lines | Pipeline still runs; thesis flags as data-quality limitation | `mixed` rate dashboard |
| 10 | OCR Tesseract version mismatch | Tesseract calls fail on missing lang pack | `subprocess.CalledProcessError` | Admin alert; pipeline halts for this gazette | Stage-B failure-rate alert |

### Stage C — Preprocessing

| # | Edge case | Trigger | Detection | Resolution | Monitoring |
|---|---|---|---|---|---|
| 11 | Metadata extraction returns 0 fields | All 4 regex patterns miss | `extracted_metadata={}` | Auto-set `needs_review=true`; admin fills manually | `needs_review` rate |
| 12 | Multi-penalty regulation | `finditer` returns > 1 fine match | Multiple `m1_regulation_penalties` rows inserted | None needed (handled by design) | Per-regulation penalty count |
| 13 | Future-dated effective date beyond 5 years | `effective_date > published + 5y` | Pydantic validator rejects | Admin reviews; usually a regex misfire | `m1_pipeline_errors` |
| 14 | Repeal regulation | `amendment_type='repeal'` | Detected by verb regex | Special UI treatment; SME alert mentions "repealed" | Repeal count per quarter |

### Stage D — Classification

| # | Edge case | Trigger | Detection | Resolution | Monitoring |
|---|---|---|---|---|---|
| 15 | Classifier confidence < 0.30 | Confidence floor in `classify_gazette.py` | Auto-`needs_review=true`; alert NOT dispatched | Admin manually reclassifies in dashboard | `needs_review` count + low-confidence histogram |
| 16 | Long PDF — category in tail (chunk N) | Classifier picked chunk 0, mis-classified | Caught only by admin verification (manual signal) | Open ticket; logit-aggregation rollout per [06_M1_2_Slice_Analysis_Framework.md](06_M1_2_Slice_Analysis_Framework.md) | Length-cliff dashboard |
| 17 | Category drift — new gazette type | > 5 `needs_review=true` rows with same keyword | Per-week pattern detector in `analytics.py` | Admin triggers retraining + taxonomy update | Drift alert |

### Stage E — Summarisation

| # | Edge case | Trigger | Detection | Resolution | Monitoring |
|---|---|---|---|---|---|
| 18 | MarianMT returns truncated summary | Output is just `[EOS]` token | Empty `summary_en` after dispatch | Re-run with shorter chunks; if still fails, mark `summary_en=NULL`, flag | Summary-empty rate |
| 19 | Translated summary diverges from English semantics | Cosine sim between back-translated `summary_si` and `summary_en` < 0.65 | Per-batch QC sample (1 % of summaries hand-checked) | Mark translation low-confidence; SME UI shows EN alongside | Quarterly QC summary |

### Stage F — Alerting

| # | Edge case | Trigger | Detection | Resolution | Monitoring |
|---|---|---|---|---|---|
| 20 | High-fan-out gazette (> 500 matched SMEs) | Per-gazette `matched_smes` count | Detected at dispatch time | Chunked dispatch (100/s) — handled by `alert_dispatch.py` | Per-gazette dispatch duration |
| 21 | SendGrid rate limit (429) | API error | Exponential backoff in alert task; rejoin queue | Auto-recover; SLA shifts to 1 h | `alert_delivery` p99 latency |
| 22 | SME unsubscribed mid-dispatch | `sme_profiles.is_subscribed=false` set after match | Dispatch task re-checks subscribed status before sending | Skip silently | Unsubscribe count |
| 23 | Duplicate alert for same (regulation, sme) | Idempotency-key check fails | Caught by `uq_alerts_reg_sme` index | Drop second send | Zero duplicate alerts (alert on > 0) |

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| Per-stage failure taxonomy (chosen) | Localised resolution paths | ✅ Each failure has a clear owner (Stage A vs B vs F) | Never. |
| Centralized failure registry | One table to query | ❌ Loses the stage context | Only if observability tooling unifies the data. |
| Auto-recovery vs admin-triggered | Mix per row | ✅ Auto for transient infra; admin for semantic | Re-evaluated quarterly. |

## Worked example

A real failure resolution trace for case #6 (encrypted PDF):

```
[Day 0 14:23:11] Scrapy spider downloads gazette_2491_07.pdf (3.2 MB)
[Day 0 14:23:12] extract_gazette task starts
[Day 0 14:23:13] fitz.open() raises mupdf.MuPDFError: "encrypted"
[Day 0 14:23:13] Celery task catches; writes:
                   m1_pipeline_errors row: stage='extract', reason='encrypted_pdf'
                   m1_regulations.status = 'extraction_failed'
                   m1_regulations.error_detail = '{"library":"pymupdf","error":"encrypted"}'
[Day 0 14:23:13] Slack message to #enigmatrix-info (severity: info)

[Day 1 09:00 — admin in office]
Dashboard /admin/m1/failed-extractions shows 1 row
Admin clicks → 'gazette_2491_07.pdf' → 'Download Raw PDF'
Inspects: file requires no password but has DRM
Decision: mark is_active=false with reason='drm_unreadable'
Adds an entry to research/data/excluded_gazettes.csv (thesis limitations)

Resolution time: 18 hours (within 24h SLA for `info`)
```

## Failure modes & edge cases

This *is* the failure-modes doc — the table above is the body. One meta-edge case: **case not on this list**. Mitigation: every uncaught exception in any Celery task logs to `m1_pipeline_errors` with the *stack trace*; admin reviews weekly; new patterns get added to this doc.

## Validation & acceptance criteria

- **Every row in the table is detectable.** Either by a Prometheus metric, a `m1_pipeline_errors` reason code, or an admin dashboard view.
- **Every row in the table has a resolution path.** Either automated or with a documented admin action.
- **Unit tests cover the *resolution path* for every automated case.** Smoke test runs the failure scenario through the pipeline and asserts the expected DB state.
- **Quarterly review.** Each quarter, audit the last 90 days of `m1_pipeline_errors` reasons; add any new ones to this doc.

## Cross-references

- Parent: [08_M1_Full_System_Architecture.md](08_M1_Full_System_Architecture.md) §13, §14 (Definition of Done)
- Related: [12_M1_Monitoring_Maintenance.md](12_M1_Monitoring_Maintenance.md) (alerting), [03_M1_Data_Collection.md §6](03_M1_Data_Collection.md) (Stage A/B errors)
- BUILD phase: BUILD_07 §error handling, BUILD_12 §monitoring
- Code (when shipped): `backend/app/tasks/m1/*.py`, `m1_pipeline_errors` table
