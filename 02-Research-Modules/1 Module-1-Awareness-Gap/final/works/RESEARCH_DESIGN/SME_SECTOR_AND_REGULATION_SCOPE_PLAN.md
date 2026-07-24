# Research Design — CONFIRMED SME Sector & Regulation-Domain Scope

> Group: `RESEARCH_DESIGN`. Status: **CONFIRMED / FINAL (2026-07-24, rev. 2 — full taxonomy replacement)** by the researcher. Supersedes the draft AND rev. 1 (which treated the 7 priority domains as a *prioritisation* over the old 12-category / 12-sector vocabulary). Feeds doc 01 (scope), 09 (annotation), the Label Studio config, `m1/model/labels.py`, the seeded `sectors` / `regulatory_domains` tables, and the golden set `structured_v1.xlsx`.

## 1. Confirmed SME sectors (survey units + classifier labels) — exactly three

The three study sectors ARE the sector vocabulary now — survey units, DB `sectors` table, frontend pick-list, and classifier multi-label heads all use the same three codes. No `universal` sentinel: economy-wide regulations are tagged with all three sectors.

| # | SME type (survey unit) | Sector code | Notes |
|---|---|---|---|
| 1 | **Grocery / food retail** — neighbourhood kade, mini-marts, small supermarkets | `grocery_retail` | densest, most data-rich |
| 2 | **Food service** — restaurants, cafés, bakeries, take-aways | `food_service` | food-safety + tax + EPF/ETF |
| 3 | **General-goods retail** — textile/apparel, electronics/mobile, hardware | `general_retail` | import duty/CESS + VAT + SLSI |

All other sectors (agriculture, manufacturing, construction, it, transport, finance, healthcare, education, tourism, services) are **removed from the vocabulary** — out of survey scope AND out of the classifier label set. Gazettes aimed only at removed sectors carry `is_sme_relevant = FALSE` + empty `affected_sectors`. Shop sub-type (kade vs mini-mart; textile vs electronics vs hardware) is recorded as a survey field (`sub_sector`), not a separate classifier sector.

## 2. Confirmed regulation domains — exactly eight

Ordered by SME-shop relevance × gazette volume. These 8 replace the previous 12-category `change_category` set (this IS a taxonomy edit — rev. 2):

1. **`TAX_RATE_CHANGE`** — anchor; VAT/SVAT/income/excise. (Tax deadline extensions fold in here.)
2. **`IMPORT_EXPORT`** — duty/CESS/SCL, import controls.
3. **`SECTOR_SPECIFIC`** — CAA maximum-retail-price, Food Act, NMRA (biggest shop-relevant stream).
4. **`EPF_ETF_CHANGE`** — employer obligations (paired stream with 5).
5. **`LABOUR_LAW`** — wages-board/minimum-wage.
6. **`PRODUCT_STANDARD`** — SLSI standards, labelling.
7. **`BUSINESS_REGISTRATION`** — trade licences, registration.
8. **`PENALTY_ENFORCEMENT`** — fines/enforcement (the "cost of not knowing").

**Retired (rev. 2):** `FINANCIAL_REGULATION`, `ENVIRONMENTAL`, `DEADLINE_EXTENSION`, `NO_SME_IMPACT`. There is no reject *domain*; out-of-scope/regulatory-noise gazettes are handled by the `NOT_REGULATORY` pre-filter + the `is_sme_relevant = FALSE` flag. Existing labeled data remapped: FINANCIAL_REGULATION/ENVIRONMENTAL → SECTOR_SPECIFIC, DEADLINE_EXTENSION → TAX_RATE_CHANGE (tax-schedule) with per-row notes, NO_SME_IMPACT rows dropped (cal_016 retired).

## 3. Golden set alignment (`structured_v1.xlsx`)

Canonical source: `C:\sme\_Attachments\structured_v1.xlsx` (working copy `data/golden/`, git-ignored, versioned-immutable). It carries a **21-field metadata schema** — note it uses `domain_code` (e.g. `tax`) as the topical domain and `change_category = amendment|repeal|new_act` (i.e. *amendment type*, a **different** field from the classifier's 8-domain `change_category`). Any "sync" must not conflate these two `change_category` meanings.

## 4. ✅ Taxonomy reconciliation — RESOLVED 2026-07-24 (rev. 2 supersedes rev. 1)

Rev. 1 resolved the four disagreeing sector vocabularies by conforming ML/annotation to the 12-sector frontend/DB list (universal…transport). **Rev. 2 replaces that entirely**: the canonical vocabulary everywhere (DB `sectors` seed, frontend `lib/constants/sectors.ts`, `labels.py::SECTORS`, `samplers.py::SECTORS_3`, Label Studio config, calibration set) is now the three study sectors — `grocery_retail`, `food_service`, `general_retail` — and the canonical `regulatory_domains` seed is the 8-domain list above (replacing the old VAT/INCOME_TAX/WHT/SSCL/EPF/ETF/ROC/CUS/TDL obligation codes; question-bank rows remapped VAT+INCOME_TAX+WHT+SSCL→TAX_RATE_CHANGE, EPF+ETF→EPF_ETF_CHANGE, ROC→BUSINESS_REGISTRATION, CUS→IMPORT_EXPORT, TDL retired).

**Sync executed 2026-07-24 across:** `labels.py`, `samplers.py`, `sample_for_labeling.py` heuristics, Label Studio config(s incl. `mydata/media/upload/` copies), `calibration_set_v1.csv` (+ upload copies), backend seeds (`seed_lookups`, `seed_m23_questions`, `seed_regulations`, `seed_phase4`, `seed_demo_responses`, `seed_dev`, `seed_m1_worked_examples`), services (m2/admin-survey/survey-question/dashboard — `universal` sentinel removed, NULL-sector = general), API schema (`general_questions`), frontend (constants/types/sector-picker/profile-form/register), tests, and the enigmatrix-docs set. Pending mechanical follow-ups: regenerate `docs.generated/*.json` (`node scripts/extract-m1-docs.mjs`), run `pytest enigmatrix-ml/tests/m1/model`, `graphify update .` (sandbox required).

## 5. Survey instrument (confirmed shape)

Short (~5–8 min) in-person **intercept survey**, sector quotas (~30–40/sector, ~100–150 total) at Pettah (goods), a grocery cluster, a mall food court + street eateries. Questions built around 3–4 *named recent* regulations spanning the priority domains (one tax, one CAA price-control, one EPF/ETF, one import/standard): aware? when/how heard? complied? penalty? → measures awareness gap + diffusion lag, mapping 1:1 to the domains.

## 6. Empirical validation (after Phase-2 extraction)

Count `m1_regulations` per `change_category` (and per sector once annotated) to confirm §2's ordering; adjust emphasis if the real corpus differs. Doubles as a thesis figure.

## 7. Codebase/vault sync — DONE (rev. 2, 2026-07-24)

Executed per §4. This file + AI_WORK_LOG record the confirmed scope and the executed sync; remaining items are the three mechanical follow-ups listed in §4 (docs.generated regeneration, model tests, graphify update).
