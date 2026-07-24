# SME Regulatory Intelligence Platform
## Predefined Question Bank — Modules 2 & 3
### Coverage: 8 Regulation Domains × 3 Study Sectors (grocery_retail / food_service / general_retail)

> **Canonical copy (2026-07-24 taxonomy revision):** this note previously duplicated the full question-bank spec under the old 9-domain × 12-sector vocabulary. The maintained, fully updated spec now lives at [[module_2_and_3_data_architecture]] (`03-Data-Sources/format/module_2_and_3_data_architecture.md`); the executable form is `enigmatrix-backend/app/scripts/seed_m23_questions.py`. This stub replaces the stale duplicate so the old taxonomy cannot resurface from here.

---

## Current taxonomy (shop-focused study scope, confirmed 2026-07-24)

**Regulation domains — exactly eight** (single-label `change_category` / `domain_code`):

1. `TAX_RATE_CHANGE` — anchor; VAT/SVAT/income/excise (tax deadline extensions fold in here)
2. `IMPORT_EXPORT` — duty/CESS/SCL, import controls
3. `SECTOR_SPECIFIC` — CAA maximum-retail-price, Food Act, NMRA (biggest shop-relevant stream)
4. `EPF_ETF_CHANGE` — employer obligations
5. `LABOUR_LAW` — wages-board/minimum-wage
6. `PRODUCT_STANDARD` — SLSI standards, labelling
7. `BUSINESS_REGISTRATION` — trade licences, registration
8. `PENALTY_ENFORCEMENT` — fines/enforcement (the "cost of not knowing")

Retired: `FINANCIAL_REGULATION`, `ENVIRONMENTAL`, `DEADLINE_EXTENSION`, `NO_SME_IMPACT` (out-of-scope gazettes are handled by `is_sme_relevant = FALSE` + empty sectors). The old obligation-code lookup (VAT / INCOME_TAX / WHT / SSCL / EPF / ETF / ROC / CUS / TDL) is replaced by the 8 domains; question rows were remapped (VAT+INCOME_TAX+WHT+SSCL→TAX_RATE_CHANGE, EPF+ETF→EPF_ETF_CHANGE, ROC→BUSINESS_REGISTRATION, CUS→IMPORT_EXPORT, TDL retired).

**Study sectors — exactly three** (multi-label `affected_sectors` / single `sector_code` on questions; NULL = general):

| Code | Survey unit |
|---|---|
| `grocery_retail` | Grocery / food retail — neighbourhood kade, mini-marts, small supermarkets |
| `food_service` | Food service — restaurants, cafés, bakeries, take-aways |
| `general_retail` | General-goods retail — textile/apparel, electronics/mobile, hardware |

No `universal` sentinel — economy-wide regulations are tagged with all three sectors. M2 sector-specific questions: `VAT_RTL_001` (general_retail), `VAT_FNB_001` (grocery_retail), `VAT_FSV_001` (food_service). M3 sector risk blocks: `M3_SEC_GRC_*`, `M3_SEC_FSV_*`, `M3_SEC_GRT_*`.

See also: [[SME_SECTOR_AND_REGULATION_SCOPE_PLAN]] (RESEARCH_DESIGN — the confirming decision record).
