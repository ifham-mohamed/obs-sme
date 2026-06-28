# Research Ideas & Future Plans

Captures active research questions, dataset ideas, ML model candidates, and future feature plans for the Enigmatrix platform.

Last updated: 2026-05-22

---

## Data / Classifier (added Session 56)

### DATA-01 — Tariff-schedule-shape detector for gazette-2483-style customs days
**Hypothesis:** Gazette weeks with high one-day Customs Ordinance volume (e.g. 2483/17 through 2483/85 on 2026-04-10) currently leave 10–20% of rows generic because the per-PDF text is two header pages + a tariff schedule with no clear statute citation. A second-pass detector that looks for HS-code columns (`\d{4}\.\d{2}`) + cess-rate columns (`\d+%`) + "Section 10" near the page top should catch most of these. **Status:** 🔲 Not started — tracked as Session 56 open follow-up.

### DATA-02 — Body-date re-parse pass for PDFs that hit `PREFIX_FALLBACK`
**Hypothesis:** Several rows currently inherit the gazette-week-prefix fallback date (e.g. all 2483/* rows get `2026-04-06` regardless of actual publication day) because in-body date parsing fails on CID-encoded Sinhala dates. A pass that uses `pdftotext` output (which dodges the CID issue for many docs) and matches `2026 [මාර්තු|අප්‍රේල්] මස \d+ වැනි` should narrow most of these. **Status:** 🔲 Not started — tracked as Session 56 open follow-up.

### DATA-03 — Promote full multilingual + raw_text CSVs from Cowork outputs to user's csv folder
**Hypothesis:** The full multilingual + raw_text variants of `m1_regulations_next50_batch{5..11}.csv` currently only exist in the Cowork outputs dir (not in `C:\sme\03-Data-Sources\m1\raw\csv\`) because the file-tool single-call write budget can't fit a 60–86 KB multilingual CSV. A multi-call assembly path (split into 3–5 chunks, Read each, Write the concatenation) would land them. **Status:** 🔲 Not started — operator can `cp` from Cowork outputs manually for now.

### DATA-04 — Merge `v10` + `v11_addendum` + `v12_addendum` into single `m1_extraction_tracker_v12.csv`
**Hypothesis:** The 800-PDF tracker currently lives across three files (v10 + two addenda); BUILD_07 import job would benefit from a single canonical file. Same file-tool ceiling applies (~100 KB single-call), but the three files are pure ASCII and 98 KB combined — feasible with 3-chunk multi-call assembly. **Status:** 🔲 Not started.

---

## Deployment / Operations (added Session 55)

### OPS-01 — BuildKit secrets refactor for `GITHUB_TOKEN`
**Hypothesis:** Replacing `ARG GITHUB_TOKEN` + `RUN git config --global ...` in `enigmatrix-backend/Dockerfile` with `RUN --mount=type=secret,id=github_token` will keep the PAT out of build logs and out of the image's `/root/.gitconfig`. Railway supports BuildKit secrets via railway.toml — needs confirmation that the secret can be sourced from a service env var at build time.

**Status:** 🔲 Not started — tracked as part of task #12 (PAT rotation). Operator deferred during Session 55.

### OPS-02 — CI/CD pipeline via GitHub Actions
**Hypothesis:** Adding `.github/workflows/ci.yml` for `ruff` + `pytest` (backend) + `npx tsc --noEmit` + `npm test` (frontend) on every PR would have caught the `ForbiddenError` import bug confirmed in Session 55 Stage 4 audit. Pre-commit hooks for token-pattern detection would have caught the PAT leak before push.

**Status:** 🔲 Not started — no CI/CD in either repo today. Tracked as deploy-audit finding (Stage 4).

### OPS-03 — Bulk metadata backfill script for legacy `m1_regulations` rows
**Hypothesis:** Rows extracted before migration `202605280001` carry NULL on `file_size_bytes` / `sha256` / `pdf_pages` / `language`. A one-off `app/scripts/backfill_m1_pdf_metadata.py` could iterate over rows where these columns are NULL and `raw_pdf_path IS NOT NULL`, calling `compute_pdf_metadata(storage_root / raw_pdf_path, raw_text=row.raw_text)`. Avoids needing `/re-extract` per row.

**Status:** 🔲 Not started — per-row `/re-extract` is the opportunistic fallback today.

### OPS-04 — `sha256` dedup at spider insert time
**Hypothesis:** With `sha256` now indexed, the spider's `_insert_rows` could check for an existing hash before inserting a duplicate row. Useful for cases where documents.gov.lk republishes the same PDF under a different URL/gazette_number (rare but observed). Trade-off: requires hashing every PDF at download time, adds ~100-500ms per row depending on size.

**Status:** 🔲 Not started — current dedup uses `gazette_number` UNIQUE constraint only.

### OPS-05 — Celery signal handlers for `m1_extraction_runs` updates
**Hypothesis:** Today `m1_extraction_runs.celery_status` is updated lazily as a side-effect of `GET /status/{task_id}` polling. If no admin ever polls a finished task, the row stays at `PENDING` indefinitely. Wiring `task_success` / `task_failure` Celery signal handlers (in `app/celery_config.py`) would update the run row directly when the task transitions, removing the dependency on HTTP polling. Tracked as a Session 54 follow-up but not addressed in Session 55.

**Status:** 🔲 Not started.

### OPS-06 — WebSocket live feed for PDF Records page
**Hypothesis:** The Stage 3 PDF Records page (F-197) uses TanStack Query's standard fetch — no live updates. Wiring it to the existing WebSocket scaffold (`useExtractionLiveFeed`, Session 46 / F-173) would let newly-arriving rows appear without a full refetch. Trade-off: doubles the data path complexity for a page that's primarily a browse/audit view rather than a live monitoring view.

**Status:** 🔲 Not started.

---

## UX / Admin Interface (added Session 53)

### UX-01 — Admin pipeline usability study
**Hypothesis:** The 14 UX/UI findings identified in the Session 53 audit represent systemic patterns (missing loading states, destructive-action safety, status-badge semantics) that will recur as new pipeline admin pages are built (M2, M3, M4).

**Status:** 🔲 Not started — findings documented; no remediation sprint scoped yet.

**What to investigate:**
- Which of the 14 findings are duplicated on the M2/M3 admin pages (e.g. does the M2 scores table also load lazily only on search-box click)?
- Does the "Reconcile all raw folders" pattern (no confirmation on destructive action) appear elsewhere in the admin surface?
- Is the `dd/mm/yyyy` date format consistently wrong across all date pickers in the admin?

**Source:** [Plan: M1 pipeline admin UX audit](plans/2026-05-22_Plan%20M1%20pipeline%20admin%20UX%20audit%20—%2014%20findings%20report.md) — F-06, F-08, F-09, F-14.

---

### UX-02 — Recent Runs 503 root-cause investigation
**Hypothesis:** The HTTP 503 on `/admin/m1/pipeline/recent` (F-06) is caused by a missing or misconfigured backend service for the RSC data fetch; the same data renders correctly on the Trace page, so the issue is route-specific, not data-availability.

**Status:** 🔲 Not started — needs backend investigation.

**What to investigate:**
- Which FastAPI endpoint powers the RSC fetch for `/recent`?
- Is the 503 a missing route, a crashing handler, or a Celery/DB connection issue specific to that code path?
- Add `GET /api/v1/m1/recent-runs` integration test asserting HTTP 200 to CI.

**Source:** [Plan: M1 pipeline admin UX audit](plans/2026-05-22_Plan%20M1%20pipeline%20admin%20UX%20audit%20—%2014%20findings%20report.md) — F-06.

---

## 1. Active Research Questions

### RQ1 — Regulatory Awareness Gap
**Hypothesis:** Sri Lankan SMEs in labour-intensive sectors (retail, food & beverage, construction) have systematically lower awareness of EPF/ETF and SSCL changes than IT/services SMEs.

**Status:** 🟡 Survey instrument built (M0); needs ≥200 responses to validate.

**What to measure:**
- M0 question 4 ("Aware of April 2026 VAT change?") broken down by sector
- Channel awareness (Q1) correlated with knowledge score (M2 overall_pct)
- Time-to-awareness (Q11 — weeks to learn of a new regulation)

**Reference:** `research/Module_1_Regulatory_Change_Awareness_Gap.md.pdf`

---

### RQ2 — Knowledge-Gap ↔ Compliance-Risk Correlation
**Hypothesis:** M2 knowledge score < 50% is a significant predictor of M3 compliance risk (missed deadlines, penalties).

**Status:** 🔲 Needs M2 + M3 responses from the same SMEs (unified wizard data).

**What to measure:**
- Pearson correlation: `m2_knowledge_scores.overall_pct` × `m3_compliance_history.missed_deadline_24mo`
- Logistic regression: predict `penalty_received` from M2 domain scores + M3 behavioural signals
- Feature importance: which M2 domains (VAT, EPF, etc.) most predict M3 risk?

**Experiment design:** Minimum 100 SMEs completing both M2 + M3 via unified wizard before model training.

---

### RQ3 — Misinformation Prevalence
**Hypothesis:** ≥30% of SME-facing regulatory information circulating on social media (Facebook groups, WhatsApp) contains factual errors.

**Status:** 🔲 Data collection not started.

**What to collect:**
- Facebook Group posts from Sri Lankan SME communities (manual + API scraping)
- WhatsApp Business group forwards (volunteer SME participants)
- Comparison ground truth: official IRD / EPF / ETF publications

**Reference:** `research/module_4_data_collection.md`, `research/module_4_sri_lankan_sources.md`

---

### RQ4 — Multilingual Compliance Communication
**Hypothesis:** SMEs whose primary language is Sinhala or Tamil have significantly lower awareness scores than English-primary SMEs, controlling for sector.

**Status:** 🔲 Needs sufficient SI/TA survey completions.

**What to measure:**
- M0 score breakdown by `user.preferred_language`
- M2 score vs preferred_language (controlling for sector and business age)

---

## 2. Dataset Ideas

| Dataset | Source | Format | Priority | Status |
|---------|--------|--------|----------|--------|
| IRD gazette PDFs (2020–2026) | IRD website, National Archives | PDF | High | 🔲 |
| EPF/ETF circulars | EPF website | PDF | High | 🔲 |
| SME survey responses | Enigmatrix platform | PostgreSQL | High | 🟡 Collecting |
| Facebook regulatory posts | FB Graph API / manual | JSON/text | Medium | 🔲 |
| WhatsApp forward corpus | Volunteer SMEs | Text | Medium | 🔲 |
| IRD e-Tax returns data (anonymised) | IRD partnership | CSV | Low | 🔲 (needs MoU) |

---

## 3. ML Model Candidates

### Module 1 — Regulatory Change Classifier

**Goal:** Given a gazette PDF page, classify as: regulatory change / non-regulatory / SME-relevant change / non-SME-relevant change.

| Model | Approach | Notes |
|-------|----------|-------|
| Fine-tuned BERT (Sinhala + Tamil) | Transfer learning on SinBERT / TamilBERT | Primary candidate |
| Zero-shot GPT-4 (via Anthropic) | Prompt classification | Good baseline; expensive at scale |
| TF-IDF + logistic regression | Fast baseline | Low accuracy on mixed-language docs |
| LAYOUT-LM | PDF layout + text | Better for gazette table extraction |

**Training data needed:** ~500 labelled gazette pages (relevant / not relevant / SME-critical).  
**Reference:** `research/11_Module1_NLP_Classifier_Training.md`

---

### Module 3 — Compliance Risk Score

**Goal:** Predict a composite risk score (0–100) from M2 + M3 features.

| Model | Approach | Notes |
|-------|----------|-------|
| XGBoost / LightGBM | Tabular features from M2 scores + M3 signals | Primary candidate |
| Logistic regression | Predict `penalty_received` binary | Interpretable; good for regulatory reporting |
| Neural network | M2 per-domain breakdown as embeddings | Complex; needs larger dataset |

**Input features:**
- M2: `overall_pct`, `by_domain.VAT.pct`, `by_domain.EPF.pct`, ..., `instrument_breakdown.procedural.pct`
- M3: `missed_deadline_24mo`, `missed_count_band`, `penalty_received`, `filing_method`, `cash_flow_difficulty_1_5`, `barriers_json` (one-hot encoded)
- SME profile: `sector`, `employee_count_band`, `annual_turnover_band`, `business_age_years`

**Training data needed:** ≥200 SMEs with both M2 + M3 completed.  
**Reference:** `research/14_Module3_Risk_Architecture.md`

---

### Module 4 — Misinformation Detector

**Goal:** Given a text claim about Sri Lankan tax regulations, classify as: correct / incorrect / partially correct / uncertain.

| Model | Approach | Notes |
|-------|----------|-------|
| RAG + LLM verification | Retrieve regulation text → prompt GPT-4/Claude for verification | Primary MVP approach |
| DeBERTa NLI | Natural Language Inference against regulation corpus | Better offline/cost |
| Fact-checking pipeline | Claim decomposition → IR → verification | Research-grade; complex |

**Reference:** `research/15_Module4_Misinformation_Architecture.md`

---

## 4. Future Feature Ideas

### Near-term (next 3 sessions)

| Feature | What | Why |
|---------|------|-----|
| `survey_responses.linked_regulation_id` fix | Wire regulation ID into `_build_row` | Fixes dashboard pending-regulations; enables audit trail regulation_ids |
| Backend test suite | Fix CORS env issue in conftest; add missing test files | Unblocks CI |
| Risk score page | Wire `/risk` to M2+M3 composite | Completes SME journey |
| Gazette PDF ingest | Upload PDF → extract text → classify → create regulation draft | Key research pipeline piece |

### Medium-term

| Feature | What | Why |
|---------|------|-----|
| Q&A (RAG) | SME types question → answer grounded in regulation DB | High SME value |
| Annotator workflow | Highlight question/answer pairs for ML training data | Enables supervised training |
| Notification system | Email SME when a new relevant regulation is added | Closes the awareness gap |
| Export / reports | Admin exports M2 score breakdown as CSV/Excel | Research data collection |
| Multi-tenant / organisation | Group SMEs under a business registration | Needed for association partnerships |

### Long-term / Research

| Feature | What | Why |
|---------|------|-----|
| Active learning loop | Model flags uncertain SME answers for annotator review | Improves ML data quality |
| Longitudinal tracking | Track same SME over multiple survey rounds | Measures intervention effectiveness |
| Sector-specific question banks | Tailored M2/M3 questions per sector (retail vs IT vs construction) | Better risk signal precision |
| Regulatory change monitoring | Automated gazette scraper → alert pipeline | Keeps regulation DB fresh |
| Sinhala / Tamil NLP models | Fine-tune for local language regulatory text | Better SI/TA classification |

---

## 5. Academic Paper Checklist

For the interim/final report:

- [x] Research proposal submitted (`research/Enigmatrix_Research_Proposal_Upgraded.md`)
- [x] System architecture designed (`research/07_System_Architecture.md`)
- [x] Survey instrument designed — M0, M2, M3 (`research/08_SME_Questionnaire_Design.md`)
- [x] Technology stack justified (`research/04_Technology_Stack_Justification.md`)
- [ ] Literature review (minimum 20 references) — `research/05_Literature_Review_Guide.md` has the framework
- [ ] Data collection section — ethics, consent, sample size calculation
- [ ] Results chapter — M0 awareness analysis, M2 score distribution, M3 risk signals
- [ ] ML model training and evaluation chapter
- [ ] Discussion — limitations, threats to validity, future work
- [ ] Conclusion

**Target:** ≥200 SME responses before final submission.  
**IRB / Ethics approval:** Needed if collecting from human participants beyond internal testing.

---

## 6. Questions for Supervisor / Advisor

| Question | Status |
|----------|--------|
| Minimum sample size for M2 → M3 correlation (RQ2)? | Open |
| Should M4 use a labelled dataset approach or zero-shot RAG? | Open |
| IRD data partnership feasibility? | Open |
| Gazette PDF scraping: legal considerations in Sri Lanka? | Open |
| Should the risk score be validated against actual penalty records? | Open |


---

## Additions from Session 44-51 (2026-05-21)

### Per-language `raw_text` storage for gazettes

**Origin:** [[SESSIONS#2026-05-21 — Session 50: Completeness check + re-fetch + spider EN→SI→TA fallback]]

User explicitly chose fallback-only (EN→SI→TA) for the spider rather than per-language storage in F-177. The schema-migration approach (`raw_text_en` / `raw_text_si` / `raw_text_ta` columns or a child table) is genuinely valuable for cross-lingual NLP later — keeping it captured here.

**Status:** 🔲 deferred (no concrete trigger to revisit).

### Per-task_id WebSocket channel routing

**Origin:** [[SESSIONS#2026-05-21 — Session 46: Extraction running UX upgrade]]

Current WS feed (F-173) uses source-scoped Redis pub/sub channels (`m1:extraction:source:<source_id>`) — pragmatic scaffold. Concurrent runs against the same source would interleave their frames on the shared channel. True per-task routing requires plumbing the trigger task_id through the spider into every child `extract_gazette` call.

**Status:** 🔲 follow-up.

### `watchexec`-based dev loop instead of `uvicorn --reload`

**Origin:** [[SESSIONS#2026-05-21 — Session 48: Vault recovery]]

`uvicorn --reload` silently dies on module import errors during a reload cycle. `watchexec --restart --exts py -- uvicorn app.main:app` survives and restarts. Not yet adopted as the default for backend dev.

**Status:** 🔲 idea (low-risk drop-in if anyone wants to switch).
