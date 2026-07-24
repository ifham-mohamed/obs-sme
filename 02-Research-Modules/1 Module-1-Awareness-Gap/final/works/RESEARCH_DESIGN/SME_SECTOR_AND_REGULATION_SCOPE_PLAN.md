# Research Design — CONFIRMED SME Sector & Regulation-Domain Scope

> Group: `RESEARCH_DESIGN`. Status: **CONFIRMED / FINAL (2026-07-24)** by the researcher. Supersedes the draft. Feeds doc 01 (scope), 09 (annotation), the Label Studio config, `m1/model/labels.py`, and the golden set `structured_v1.xlsx`.
> **Blocking note:** a taxonomy reconciliation (§4) must be resolved before the codebase "sync" — the repo currently carries three disagreeing sector vocabularies.

## 1. Confirmed SME sectors (survey units) — exactly three

| # | SME type (survey unit) | Intended sector label(s) | Notes |
|---|---|---|---|
| 1 | **Grocery / food retail** — neighbourhood kade, mini-marts, small supermarkets | `retail` + `food` | densest, most data-rich |
| 2 | **Food service** — restaurants, cafés, bakeries, take-aways | `food` (+ `tourism`/`hospitality`) | food-safety + tax + EPF/ETF |
| 3 | **General-goods retail** — textile/apparel, electronics/mobile, hardware | `retail` | import duty/CESS + VAT + SLSI |

All other sectors (agriculture, manufacturing, construction, it, transport, finance) are **out of survey scope** but remain valid classifier labels.

## 2. Confirmed regulation domains — the 7 priority categories (of 12)

Ordered by SME-shop relevance × gazette volume; all seven are existing `change_category` values:

1. **`TAX_RATE_CHANGE`** — anchor; VAT/SVAT/income/excise.
2. **`IMPORT_EXPORT`** — duty/CESS/SCL, import controls.
3. **`SECTOR_SPECIFIC`** — CAA maximum-retail-price, Food Act, NMRA (biggest shop-relevant stream).
4. **`EPF_ETF_CHANGE`** + **`LABOUR_LAW`** — employer obligations, wages-board/minimum-wage.
5. **`PRODUCT_STANDARD`** — SLSI standards, labelling.
6. **`BUSINESS_REGISTRATION`** — trade licences, registration.
7. **`PENALTY_ENFORCEMENT`** — fines/enforcement (the "cost of not knowing").

Kept in the label set but expected minor for this population: `FINANCIAL_REGULATION`, `ENVIRONMENTAL`, `DEADLINE_EXTENSION`, `NO_SME_IMPACT` (negative class). **The 12-category set is unchanged — this is a prioritisation, not a taxonomy edit.**

## 3. Golden set alignment (`structured_v1.xlsx`)

Canonical source: `C:\sme\_Attachments\structured_v1.xlsx` (working copy `data/golden/`, git-ignored, versioned-immutable). It carries a **21-field metadata schema** — note it uses `domain_code` (e.g. `tax`) as the topical domain and `change_category = amendment|repeal|new_act` (i.e. *amendment type*, a **different** field from the classifier's 12-category `change_category`). Any "sync" must not conflate these two `change_category` meanings.

## 4. ✅ Taxonomy reconciliation — RESOLVED 2026-07-24

The repo held **four disagreeing sector vocabularies**:

| Source | Sector list |
|---|---|
| `enigmatrix-ml/m1/model/labels.py` `SECTORS` | agriculture, manufacturing, retail, tourism, construction, services, finance, it, transport, food |
| `m1/data/samplers.py` + `research/data/label_studio_config.xml` | manufacturing, retail, services, agriculture, construction, it_bpo, hospitality, transport, healthcare, finance |
| **`enigmatrix-frontend/lib/constants/sectors.ts` — mirrors the seeded `sectors` DB table (SME registration/surveys use it)** | universal, manufacturing, retail, services, it, agriculture, construction, tourism, food_beverage, healthcare, education, transport |
| Golden `structured_v1.xlsx` | no sector column — topical `domain_code` only |

Bug: annotators picked `hospitality`/`it_bpo`, which `labels.py::parse_sectors` silently dropped → sectors never encoded into the model.

**Decision (researcher, 2026-07-24): the frontend/DB `sectors` table is canonical** — it's the app-wide source of truth with real SME-profile data and already SME-oriented. The classifier + annotation were **conformed to it** (no trained model or DB on that side → non-breaking; "keep full taxonomy" honoured). Changed: `labels.py::SECTORS` (→ the 12 canonical), `config.py num_sectors` auto-follows, `samplers.py::SECTORS_10`, `label_studio_config.xml affected_sectors`, and the coupled tests (`test_labels.py`, `test_data.py`). **The 12-category set is unchanged.**

**Study-focus mapping onto the canonical sectors:** grocery/food retail → `food_beverage`+`retail`; food service → `food_beverage`+`tourism`; general-goods retail → `retail`. Record shop sub-type as a survey field, not a separate classifier sector.

**Remaining follow-ups (mechanical, need the sandbox back):** regenerate `enigmatrix-frontend/lib/m1/docs.generated/*.json` from the docs; update prose sector lists in `09_M1_Annotation_Guidelines.md` + `14_M1_9_Category_Sector_Workflows.md`; refresh the two historical `label_studio_config.xml` copies under `mydata/media/upload/`; run `pytest enigmatrix-ml/tests/m1/model`. The app/DB side is already canonical and untouched.

## 5. Survey instrument (confirmed shape)

Short (~5–8 min) in-person **intercept survey**, sector quotas (~30–40/sector, ~100–150 total) at Pettah (goods), a grocery cluster, a mall food court + street eateries. Questions built around 3–4 *named recent* regulations spanning the priority categories (one tax, one CAA price-control, one EPF/ETF, one import/standard): aware? when/how heard? complied? penalty? → measures awareness gap + diffusion lag, mapping 1:1 to the categories.

## 6. Empirical validation (after Phase-2 extraction)

Count `m1_regulations` per `change_category` (and per sector once annotated) to confirm §2's ordering; adjust emphasis if the real corpus differs. Doubles as a thesis figure.

## 7. Codebase/vault sync — pending the §4 decision

Blast radius (~80 files): `labels.py`, `samplers.py`, Label Studio config(s), DB model + `202607230001` constraints/migration, `validation.py`, frontend filters + `docs.generated/*.json`, annotation guidelines (09), tests. **Not executed** until the canonical sector set and the sync depth are confirmed (see the two questions posed to the researcher 2026-07-24), and ideally until the sandbox is back so the change can be tested. This file + AI_WORK_LOG S81 record the confirmed *scope*; the *code sync* is a separate, tested change once decided.
