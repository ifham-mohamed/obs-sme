# 09_M1_1 — Category Taxonomy: Worked Examples

> Companion to [09_M1_Annotation_Guidelines.md](09_M1_Annotation_Guidelines.md) — 5–8 examples per category showing decision criteria in action + contrastive examples for confusable pairs.
> **Implementation status:** 🟡 Examples below are template-generated (anchored on the 5 seeded demo regulations + Session-15 unified flow); real annotated examples land with BUILD_07.

## Purpose

The parent doc §2 has decision criteria for each of the 12 categories, plus the 3 contrastive pairs in §6.1. This companion fills in the *examples* an annotator needs to internalise the criteria — 5–8 short snippets per category, with the "correct label" and "why".

> **Note on examples.** Where we have real seeded regulations (`VAT_2024_AMD`, `EPF_2024_RATE`, the multi-pin adapter case), we use them. Otherwise, examples are clearly marked `[template]` — realistic but synthetic, drawn from the patterns that recur in the IRD/EPF gazette stream.

## Detailed process

The training procedure for a new annotator is:

1. Read the 12-category taxonomy in [09_M1_Annotation_Guidelines.md §2](09_M1_Annotation_Guidelines.md).
2. Read this doc — every example, in order.
3. Take the 20-doc calibration test ([09_M1_2_Annotation_Workflow_IAA_Protocol.md](09_M1_2_Annotation_Workflow_IAA_Protocol.md)).
4. If κ ≥ 0.80 on first attempt → start annotating production batches.

### 12-category examples

Below: at minimum 3 examples per category, with the correct label and a brief "why" (the decision signal that anchors it).

#### `TAX_RATE_CHANGE`

- *Example 1.* "The VAT rate is hereby increased from 15 % to 18 % with effect from 1 January 2024." — **TAX_RATE_CHANGE.** Decision signal: "VAT rate", numerical change, IRD-issued.
- *Example 2.* "The Schedule to the Customs Tariff Ordinance is amended by substituting Tariff Code 8504.40 (custom duty 30 %) with rate 25 %." — **TAX_RATE_CHANGE.** Customs duty schedule amendment.
- *Example 3* [template]. "The annual stamp duty payable on certificates of deposit shall be Rs. 1,000 (previously Rs. 500)." — **TAX_RATE_CHANGE.** Stamp duty amendment.

#### `LABOUR_LAW`

- *Example 1* [template]. "The minimum daily wage in the Wages Boards covering shop and office employees is set at Rs. 1,300 (previously Rs. 1,200)." — **LABOUR_LAW.** Wages-board order.
- *Example 2* [template]. "Maternity leave for shop and office employees is extended from 84 to 98 calendar days." — **LABOUR_LAW.** Leave entitlement.

#### `EPF_ETF_CHANGE` (real: `EPF_2024_RATE`)

- *Example 1.* "The employer's contribution to the Employees' Provident Fund is increased from 12 % to 13 % of gross monthly remuneration with effect from 1 February 2024." — **EPF_ETF_CHANGE.**
- *Example 2* [template]. "The salary cap for compulsory EPF eligibility is raised from Rs. 75,000 to Rs. 100,000 per month." — **EPF_ETF_CHANGE.** Eligibility threshold change.

#### `PRODUCT_STANDARD` (real: multi-pin adapter)

- *Example 1.* "All multi-pin universal power adapters sold in Sri Lanka shall carry SLSI safety certification effective 1 August 2026." — **PRODUCT_STANDARD.** SLSI mandatory.
- *Example 2* [template]. "The Sri Lanka Standards Institution issues mandatory standard SLS 1234:2024 for bottled drinking water." — **PRODUCT_STANDARD.** SLSI-prefixed standard.

#### `BUSINESS_REGISTRATION`

- *Example 1* [template]. "Annual return filing fees for limited liability companies are revised from Rs. 1,000 to Rs. 5,000 with effect from 1 April 2024." — **BUSINESS_REGISTRATION.** eROC fee.
- *Example 2* [template]. "Sole proprietorships with annual turnover above Rs. 50 million must register with the Registrar of Companies by 31 December 2024." — **BUSINESS_REGISTRATION.** New registration obligation.

#### `IMPORT_EXPORT`

- *Example 1* [template]. "Import of vehicles with engine capacity above 1500 cc is prohibited under the Imports and Exports (Control) Regulations 2023." — **IMPORT_EXPORT.** Import ban.
- *Example 2* [template]. "A non-tariff measure requires SLSI certification for imports of refurbished electrical appliances effective 1 July 2024." — **IMPORT_EXPORT.** (Note: also touches `PRODUCT_STANDARD` — the import-control framing wins because the issuing authority is the Department of Imports and Exports, not SLSI.)

#### `FINANCIAL_REGULATION`

- *Example 1* [template]. "All non-bank financial institutions are required to maintain a minimum capital adequacy ratio of 11 % effective 1 January 2024 (Central Bank Direction No. 4 of 2023)." — **FINANCIAL_REGULATION.** CBSL-issued.
- *Example 2* [template]. "Foreign exchange permits for outward remittances above USD 50,000 require additional documentation per Central Bank Direction." — **FINANCIAL_REGULATION.** Forex controls.

#### `SECTOR_SPECIFIC`

- *Example 1* [template]. "All restaurants serving alcoholic beverages must obtain a tourism-board license effective 1 April 2024." — **SECTOR_SPECIFIC.** Hospitality only.
- *Example 2* [template]. "Drone operations within 5 km of major airports are restricted by the Civil Aviation Authority effective immediately." — **SECTOR_SPECIFIC.** Aviation/transport only.

#### `ENVIRONMENTAL`

- *Example 1* [template]. "Effluent discharge from textile dyeing facilities must comply with revised pH limits of 6.0–8.5 effective 1 June 2024 (Central Environmental Authority directive)." — **ENVIRONMENTAL.** CEA-issued; ecological harm framing.
- *Example 2* [template]. "Lead content in industrial paints reduced from 0.06 % to 0.009 % by mass effective 1 January 2024." — **ENVIRONMENTAL.** Contrast with PRODUCT_STANDARD: this targets pollution, not consumer safety.

#### `PENALTY_ENFORCEMENT`

- *Example 1* [template]. "The penalty for non-payment of VAT after due date is increased to 1.5 % per month (previously 1.0 %)." — **PENALTY_ENFORCEMENT.** Modifying an existing penalty.
- *Example 2* [template]. "Public naming of defaulting employers under EPF non-compliance is authorised by Department of Labour direction." — **PENALTY_ENFORCEMENT.** New enforcement mechanism.

#### `DEADLINE_EXTENSION`

- *Example 1* [template]. "The deadline for filing the third-quarter VAT return is extended from 20 January to 31 January 2024." — **DEADLINE_EXTENSION.** Contrast with TAX_RATE_CHANGE: schedule changes, not substance.
- *Example 2* [template]. "The grace period for SME annual return filing is extended by 90 days due to the year-end cash-flow crunch." — **DEADLINE_EXTENSION.**

#### `NO_SME_IMPACT`

- *Example 1* [template]. "The Governor appoints Mr. X to the Board of the Public Service Commission with effect from 1 March 2024." — **NO_SME_IMPACT.** Government appointment.
- *Example 2* [template]. "Notice is given of intention to provide compensation to landowners under the Land Acquisition Act for road widening." — **NO_SME_IMPACT.** (Unless an SME owns the land — but the gazette text alone has no SME-impact signal.)
- *Example 3* [template]. "Lost-document notice: passport No. N1234567 issued to Mr. Y is reported lost." — **NO_SME_IMPACT.** Personal notice; would be caught by NOT_REGULATORY pre-filter before reaching the annotator.

### Contrastive pairs (extended)

The parent doc covers 3 pairs in §6.1. Three more:

| Pair | Example A | Example B | Discriminator |
|---|---|---|---|
| `EPF_ETF_CHANGE` vs `LABOUR_LAW` | "EPF rate 12 → 13 %" | "Minimum wage 1,200 → 1,300" | EPF/ETF acts vs Wages Boards Ordinance / Shop and Office Act |
| `IMPORT_EXPORT` vs `PRODUCT_STANDARD` | "Import ban on >1500cc vehicles" | "All cars sold in SL must meet Euro-5 emissions" | Issuing agency: Customs/Trade vs SLSI/CEA |
| `ENVIRONMENTAL` vs `PENALTY_ENFORCEMENT` | "Effluent pH limits 6.0–8.5" | "Fine for breach of pH limits: LKR 100 k" | The first is the substantive rule; the second is the penalty for breaking it |

## Technology choices

This is an annotation-training doc; the "technology" is the calibration-test design. See [09_M1_2_Annotation_Workflow_IAA_Protocol.md](09_M1_2_Annotation_Workflow_IAA_Protocol.md).

## Worked example

A new annotator's calibration-test walkthrough (selected items):

```
Test doc #7:
   "The Sri Lanka Standards Institution issues mandatory standard SLS 1100:2024
    for safety helmets used in construction, with mandatory certification from
    1 July 2024. Non-compliant helmets shall be prohibited from sale."

Annotator A: PRODUCT_STANDARD (sectors: construction, retail, manufacturing)
Annotator B: PRODUCT_STANDARD (sectors: construction)
Domain expert reference: PRODUCT_STANDARD (sectors: construction, retail)

Category agreement: ✅
Sector disagreement (strict-subset): B's set is a strict subset of A's
  Resolution rule from 09_M1_Annotation_Guidelines.md §4.4: UNION → take A's set
Final: PRODUCT_STANDARD, sectors=[construction, retail, manufacturing]
```

## Failure modes & edge cases

- **Example becomes stale.** If a regulation cited in an example is repealed, the example still has *training* value — it teaches the pattern. Update the doc only when the *category* meaning changes.
- **Templates leak as real data.** Risk if a real regulation matches a template. Mitigation: every `[template]` example is hand-checked before publication against the seeded regulation set.
- **Annotator memorises examples.** A failure mode of any worked-examples doc. Mitigation: the calibration set ([09_M1_2_*.md](09_M1_2_Annotation_Workflow_IAA_Protocol.md)) is *different* from this doc's examples.

## Validation & acceptance criteria

- **Every category has ≥ 3 examples.** Audited at publication time.
- **Every contrastive pair has at least one example per side.**
- **Real regulations cited verbatim.** Marked clearly vs `[template]`.
- **No PII** in any example (templates use generic names; real cases are public-record gazettes).

## Cross-references

- Parent: [09_M1_Annotation_Guidelines.md](09_M1_Annotation_Guidelines.md) §2, §6.1
- Related: [09_M1_2_Annotation_Workflow_IAA_Protocol.md](09_M1_2_Annotation_Workflow_IAA_Protocol.md)
- BUILD phase: BUILD_07 §annotator onboarding
- Code (when shipped): `research/data/calibration_set_v1.csv`, `tests/m1/fixtures/category_examples/`
