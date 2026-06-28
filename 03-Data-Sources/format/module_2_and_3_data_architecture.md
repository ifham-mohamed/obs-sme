# SME Regulatory Intelligence Platform
## Predefined Question Bank — Modules 2 & 3
### Coverage: All 9 Regulatory Domains × 12 Sectors

---

## ⚠️ Critical Disclaimer Before Use

**Every "correct answer" in this bank MUST be re-verified by a practising Chartered Accountant or tax consultant before deployment.** Sri Lankan tax law changed significantly in April 2026 (VAT/SSCL threshold dropped from LKR 60M → 36M, SVAT was abolished, new VAT invoice format mandated). The answers below reflect publicly available information as of May 2026 but tax law is dynamic — your ground truth must be certified by a qualified professional and dated. Without this certification, your "knowledge gap score" measures nothing.

---

# PART A — MODULE 2: KNOWLEDGE GAP QUESTIONS

Each question is tagged with:
- **`question_code`** — for the database
- **`domain`** — which regulation
- **`sector`** — which sectors it applies to (UNIVERSAL = all)
- **`knowledge_type`** — factual / procedural / application / exception
- **`format`** — MCQ / numeric / ordered_steps / scenario_response
- **`correct_answer`** — verified against official sources
- **`source`** — where the ground truth comes from

---

## DOMAIN 1: VALUE ADDED TAX (VAT)

> **VAT/SSCL merge (April 2026) — worked M0→M2→M3 chain.** From 1 April 2026 the SSCL (~2.5%) is abolished as a separate levy and folded into VAT at a single 20% rate. Most businesses were already paying ~18%+SSCL ≈ 20%, so this is a **restructuring of two line items into one, not a real 2-point increase** — invoices must now show one "20% VAT" line. This is seeded as the M1 regulation `VAT_SSCL_MERGE_2026` and a full cross-module chain (see [`../SETUP/11_Survey_System.md`](../SETUP/11_Survey_System.md) §10.3): M0 awareness `awareness.v1.q13` ("aware it's a restructuring" / "aware but think it's a hike" / "no" / "unsure" — the non-ideal three route to M2) → M2 knowledge `VAT_SSCL_MERGE_FACT_001` ("which two charges does the 20% VAT replace?" → A: VAT 18% + SSCL ✓) and `VAT_SSCL_MERGE_APP_001` ("compute the VAT on a LKR 1M supply" → A: LKR 200,000 as one line ✓; wrong → M3) → M3 behaviour `M3_VAT_SSCL_MERGE_PRACTICE` ("one 20% line, or still VAT+SSCL separately?" → wrong → M3 stress `M3_VAT_SSCL_MERGE_PENALTY` — back-VAT + 25-50% penalty + re-issuing non-compliant invoices). The M3 follow-ups are junction-linked to `VAT_SSCL_MERGE_2026` (so the reg-scoped flow traverses them) but carry no `m3_field_mapping`, so they don't project into the legacy snapshot tables — an admin can opt them in via that column if the risk model should use them.

### Universal VAT Questions (all sectors)

**VAT_FACT_001** | Universal | Factual | MCQ
> What is the current standard VAT rate in Sri Lanka?
- A) 8%
- B) 15%
- C) 18% ✓
- D) 20%

*Source: VAT Amendment Act, effective 1 January 2024. Verify rate hasn't changed. (Becomes 20% from 1 April 2026 under the VAT/SSCL merge — see the note above.)*

---

**VAT_FACT_002** | Universal | Factual | MCQ
> As of April 2026, what is the annual turnover threshold above which a business MUST register for VAT?
- A) LKR 12 million
- B) LKR 36 million ✓
- C) LKR 60 million
- D) LKR 80 million

*Source: 2026 Budget — threshold reduced from 60M to 36M effective 1 April 2026.*

---

**VAT_FACT_003** | Universal | Factual | MCQ
> By which date of the following month must monthly VAT returns be filed?
- A) Last day of the next month ✓
- B) 15th of the next month
- C) 7th of the next month
- D) End of the quarter

*Source: VAT Act — returns due by the last day of the month following the taxable period.*

---

**VAT_PROC_001** | Universal | Procedural | Ordered Steps
> Arrange the following steps in the correct order for filing a monthly VAT return:
1. Calculate output VAT (VAT collected on sales)
2. Calculate input VAT (VAT paid on purchases)
3. Reconcile sales records and tax invoices issued
4. Submit return through IRD e-filing portal
5. Pay the net VAT liability
6. Net off input VAT against output VAT to determine liability

*Correct order: 3 → 1 → 2 → 6 → 4 → 5*
*Scoring: full marks for correct order; partial credit if first and last steps correct.*

---

**VAT_APP_001** | Universal | Application | Scenario Response
> A customer pays you LKR 118,000 on March 25th as advance payment for goods you will deliver in May. In which VAT return period must you account for this VAT?
- A) March return (the period of payment) ✓
- B) May return (the period of delivery)
- C) Either period — your choice
- D) Spread across both periods

*Source: VAT Act — time of supply rule; tax point is the earlier of payment or invoice for advances.*

---

**VAT_APP_002** | Universal | Application | Scenario Response
> You issued a tax invoice for LKR 200,000 + 18% VAT in January. In April, the customer returns 50% of the goods. What is the correct VAT treatment?
- A) Issue a credit note and adjust output VAT in the April return ✓
- B) Refund the customer in cash; no VAT adjustment needed
- C) Reverse the original January return
- D) No adjustment needed since the invoice was already filed

*Source: VAT Act — credit notes for returned goods adjusted in the period the credit note is issued.*

---

**VAT_EXC_001** | Universal | Exception | MCQ
> You purchased raw materials worth LKR 200,000 + VAT but the supplier issued only a cash receipt — not a formal tax invoice. Can you claim the input VAT?
- A) Yes, any receipt is sufficient
- B) No — input VAT can only be claimed against a valid tax invoice ✓
- C) Yes, but only 50% of the VAT
- D) Yes, if the supplier is VAT registered

*Source: VAT Act — input VAT credit requires valid tax invoice with prescribed details.*

---

**VAT_EXC_002** | Universal | Exception | MCQ
> Effective 1 October 2025, what happened to the SVAT (Simplified VAT) scheme?
- A) It was made mandatory for all exporters
- B) It was abolished and replaced with an approved refund process ✓
- C) The threshold was raised
- D) Nothing — it continues unchanged

*Source: 2026 Budget proposals; SVAT abolished from 1 October 2025.*

---

### Sector-Specific VAT Questions

**VAT_MFG_001** | Manufacturing | Application | MCQ
> A manufacturer exports finished textiles to the UK and receives payment in GBP within 4 months. The export sale is:
- A) Standard rated at 18%
- B) Zero-rated (you can claim input VAT) ✓
- C) Exempt (no input VAT recoverable)
- D) Subject to special export tax

*Source: VAT Act Section 7 — exports zero-rated if foreign currency received within 6 months.*

---

**VAT_RTL_001** | Retail & Wholesale | Procedural | MCQ
> When selling to another VAT-registered business, which detail is NOT mandatory on the tax invoice?
- A) Buyer's VAT registration number
- B) Buyer's date of birth ✓
- C) Description of goods/services
- D) VAT amount shown separately

*Source: IRD prescribed VAT invoice format (new standardized format effective 1 April 2026).*

---

**VAT_ITS_001** | IT & Software | Exception | MCQ
> Your IT firm exports software services to a US client. Payment arrives in USD via a Sri Lankan bank within 5 months of invoice. The VAT treatment is:
- A) Standard rated at 18%
- B) Zero-rated, with input VAT recoverable ✓
- C) Exempt
- D) Subject to 8% reduced rate

*Source: VAT Act Section 7 — exported services zero-rated when consumed outside SL and forex received within 6 months.*

---

**VAT_ITS_002** | IT & Software | Factual | MCQ
> As of April 2026, do all commercial exporters of services need to register for VAT regardless of turnover?
- A) Yes — registration is mandatory for all commercial exporters ✓
- B) No — only if turnover exceeds LKR 36M
- C) No — exporters are fully exempt
- D) Only if exporting to specific countries

*Source: 2026 VAT regime changes — mandatory for exporters regardless of threshold.*

---

**VAT_TRH_001** | Tourism & Hospitality | Application | MCQ
> Your hotel charges a guest LKR 25,000 for the room and adds a 10% service charge. VAT is calculated on:
- A) Room charge only
- B) Room charge + service charge ✓
- C) Service charge only
- D) Room charge minus 10% discount

*Source: VAT Act — service charges form part of taxable value.*

---

**VAT_FNB_001** | Food & Beverage | Exception | MCQ
> Which of the following food categories is generally VAT EXEMPT in Sri Lanka?
- A) Restaurant prepared meals
- B) Locally produced unprocessed rice ✓
- C) Imported chocolates
- D) Bottled soft drinks

*Source: VAT Act First Schedule — list of exempt items including essential local agricultural produce.*

---

**VAT_CON_001** | Construction | Procedural | Scenario Response
> You are a contractor working on a 24-month construction project. How is VAT typically accounted for on long-running projects?
- A) Only when the project completes
- B) On each progress billing/certified payment as it is invoiced ✓
- C) At the start of the project on the full contract value
- D) Annually on the project value

*Source: VAT Act — time of supply for construction services tied to invoicing/payment milestones.*

---

**VAT_AGR_001** | Agriculture | Exception | MCQ
> A farmer sells unprocessed paddy directly to a wholesale buyer. The sale is:
- A) Standard rated at 18%
- B) VAT exempt ✓
- C) Zero-rated
- D) Subject to special agricultural tax

*Source: VAT exemption schedule for unprocessed agricultural produce.*

---

**VAT_TPT_001** | Transport | Exception | MCQ
> Passenger transport services in Sri Lanka are generally:
- A) Standard rated at 18%
- B) Zero-rated
- C) VAT exempt ✓
- D) Subject to a special 5% rate

*Source: VAT Act exempt services schedule.*

---

**VAT_HLT_001** | Healthcare | Exception | MCQ
> Medical services provided by a registered hospital to patients are generally:
- A) Standard rated at 18%
- B) VAT exempt ✓
- C) Zero-rated
- D) Subject to a healthcare-specific levy only

*Source: VAT Act — healthcare services are exempt supplies.*

---

**VAT_EDU_001** | Education | Exception | MCQ
> Tuition fees charged by a registered educational institution are:
- A) Standard rated at 18%
- B) VAT exempt ✓
- C) Zero-rated
- D) Subject to 8% reduced rate

*Source: VAT Act — educational services are exempt supplies.*

---

## DOMAIN 2: INCOME TAX (Corporate)

**IT_FACT_001** | Universal | Factual | MCQ
> What is the standard corporate income tax rate in Sri Lanka?
- A) 15%
- B) 24%
- C) 30% ✓
- D) 35%

*Source: Inland Revenue Act — standard corporate rate. Verify against current schedule.*

---

**IT_FACT_002** | Universal | Factual | MCQ
> By what date must a company file its annual corporate income tax return for the year ending 31 March?
- A) 30 June (3 months after year-end)
- B) 30 September
- C) 30 November (8 months after year-end) ✓
- D) 31 March of the following year

*Source: Inland Revenue Act — annual return due 8 months after year-end.*

---

**IT_FACT_003** | Universal | Factual | MCQ
> Within how many days of incorporation must a new company register with the Inland Revenue Department?
- A) 14 days
- B) 30 days ✓
- C) 60 days
- D) 90 days

*Source: Inland Revenue Act — registration required within 30 days of incorporation.*

---

**IT_PROC_001** | Universal | Procedural | Ordered Steps
> A company makes an income tax payment via four quarterly installments. Order these correctly through the year for a 1 April – 31 March year of assessment:
1. First installment due
2. Second installment due
3. Third installment due
4. Fourth installment due
5. Final return filed and balance settled

*Correct dates approximately: 15 Aug → 15 Nov → 15 Feb → 15 May → 30 Nov following year-end.*
*Scoring: partial credit for getting the sequence right even if exact dates uncertain.*

---

**IT_APP_001** | Universal | Application | Scenario Response
> Your business made a NET LOSS of LKR 5 million this assessment year. Are you required to file a tax return?
- A) No, since there is no tax payable
- B) Yes — a return must still be filed; the loss can be carried forward ✓
- C) Only if losses exceed LKR 10 million
- D) Only every alternate year

*Source: Inland Revenue Act — returns mandatory; tax losses carried forward up to 6 years (verify current limit).*

---

**IT_EXC_001** | Universal | Exception | MCQ
> If a company underpays tax negligently and the underpayment exceeds LKR 10 million OR 25% of total tax liability, what is the penalty?
- A) 10% of underpayment
- B) 25% of underpayment
- C) 50% of underpayment
- D) 75% of underpayment ✓

*Source: Inland Revenue Act Section 180 — negligent/fraudulent underpayment penalty.*

---

## DOMAIN 3: WITHHOLDING TAX (WHT)

**WHT_FACT_001** | Universal | Factual | MCQ
> What is the WHT rate on payments exceeding LKR 100,000 per month to a resident independent service provider (e.g., consultant, freelancer)?
- A) 2%
- B) 5% ✓
- C) 10%
- D) 14%

*Source: Inland Revenue Act — 5% WHT on independent service provider payments above threshold.*

---

**WHT_FACT_002** | Universal | Factual | MCQ
> What is the final WHT rate on dividends paid by a resident company?
- A) 5%
- B) 10%
- C) 15% ✓
- D) 20%

*Source: With effect from 1 January 2023, dividends subject to 15% final WHT.*

---

**WHT_PROC_001** | Universal | Procedural | Ordered Steps
> You make a payment of LKR 150,000 to a freelance designer. Order the correct WHT actions:
1. Calculate 5% WHT (LKR 7,500)
2. Pay net amount (LKR 142,500) to designer
3. Issue withholding tax certificate to designer
4. Remit LKR 7,500 to IRD by 15th of following month
5. Report in monthly WHT statement

*Correct order: 1 → 2 → 3 → 4 → 5*

---

**WHT_APP_001** | Universal | Application | MCQ
> A company pays a dividend on 20th April. By what date must the WHT be remitted to IRD?
- A) Within 7 days
- B) Within 15 days after end of the calendar month of payment ✓
- C) Within 30 days
- D) By the next quarterly filing

*Source: Inland Revenue Act — WHT on dividends remitted within 15 days after end of month of payment.*

---

## DOMAIN 4: SOCIAL SECURITY CONTRIBUTION LEVY (SSCL)

**SSCL_FACT_001** | Universal | Factual | MCQ
> What is the standard SSCL rate?
- A) 1%
- B) 2.5% ✓
- C) 5%
- D) 10%

*Source: SSCL Act — verify current rate.*

---

**SSCL_FACT_002** | Universal | Factual | MCQ
> As of April 2026, what is the SSCL registration threshold?
- A) LKR 12 million
- B) LKR 36 million ✓
- C) LKR 60 million
- D) LKR 120 million

*Source: 2026 Budget — aligned with VAT threshold reduction to 36M effective 1 April 2026.*

---

**SSCL_APP_001** | Manufacturing/Retail | Application | MCQ
> Your annual turnover for the past 12 months is LKR 45 million. Are you required to register for SSCL?
- A) No — below threshold
- B) Yes — exceeds the 36M threshold ✓
- C) Only if you also exceed VAT threshold
- D) Only if you sell to other businesses

*Source: 2026 SSCL/VAT registration threshold = 36M.*

---

## DOMAIN 5: EMPLOYEES PROVIDENT FUND (EPF)

**EPF_FACT_001** | Universal | Factual | MCQ
> What is the employer's monthly EPF contribution as a percentage of an employee's gross monthly earnings?
- A) 8%
- B) 10%
- C) 12% ✓
- D) 20%

*Source: EPF Act — employer minimum 12%.*

---

**EPF_FACT_002** | Universal | Factual | MCQ
> What is the employee's monthly EPF contribution rate?
- A) 8% ✓
- B) 10%
- C) 12%
- D) 15%

*Source: EPF Act — employee minimum 8%.*

---

**EPF_FACT_003** | Universal | Factual | MCQ
> By what date must EPF contributions for a given month be remitted?
- A) 7th of the following month
- B) 15th of the following month
- C) Last day of the following month ✓
- D) Within 60 days

*Source: EPF regulations — contributions due by last day of succeeding month.*

---

**EPF_FACT_004** | Universal | Factual | MCQ
> Within how many days of hiring the first employee must an employer register with the Department of Labour?
- A) 7 days
- B) 14 days ✓
- C) 30 days
- D) 90 days

*Source: Department of Labour — registration within 14 days of first hire.*

---

**EPF_PROC_001** | Universal | Procedural | Ordered Steps
> Order the correct steps for monthly EPF/ETF processing:
1. Calculate gross EPF-eligible earnings per employee
2. Compute employee 8% deduction and employer 12% contribution
3. Compute employer 3% ETF contribution
4. Complete Form C (EPF) and Form R1/R4 (ETF)
5. Remit total payment with forms before month-end deadline
6. Retain receipts and update employee EPF/ETF records

*Correct order: 1 → 2 → 3 → 4 → 5 → 6*

---

**EPF_APP_001** | Universal | Application | MCQ
> An employee earns LKR 50,000 basic + LKR 10,000 cost-of-living allowance + LKR 5,000 overtime + LKR 8,000 performance bonus. What is the EPF-eligible monthly earning?
- A) LKR 50,000
- B) LKR 60,000 ✓ (basic + COL allowance only)
- C) LKR 65,000
- D) LKR 73,000

*Source: EPF Act — total earnings include salary, COL, holiday pay, food allowances; EXCLUDES overtime and bonus.*

---

**EPF_EXC_001** | Universal | Exception | MCQ
> A new employee joins on the 20th of the month. EPF contribution is calculated on:
- A) The full month's salary
- B) The proportional salary actually earned in that month ✓
- C) Zero — contributions start from the next full month
- D) Half the monthly salary

*Source: EPF — contributions based on actual earnings paid for the month.*

---

**EPF_APP_002** | Universal | Application | Scenario Response
> You forgot to remit last month's EPF contribution. What is the correct procedure?
> (Open answer — score on whether they mention: 1) Pay arrears with surcharge, 2) Use proper remittance form, 3) Inform EPF department, 4) Surcharge accrues based on days delayed)

*Scoring rubric: 1 point per correct element, max 4.*

---

## DOMAIN 6: EMPLOYEES TRUST FUND (ETF)

**ETF_FACT_001** | Universal | Factual | MCQ
> ETF contribution is paid by:
- A) Employee only
- B) Employer only ✓
- C) Both employer and employee equally
- D) Government

*Source: ETF Act — employer-only contribution; cannot be deducted from employee salary.*

---

**ETF_FACT_002** | Universal | Factual | MCQ
> What is the ETF contribution rate as a percentage of employee's total monthly earnings?
- A) 1%
- B) 2%
- C) 3% ✓
- D) 8%

*Source: ETF Act — 3% employer contribution.*

---

**ETF_PROC_001** | Universal | Procedural | MCQ
> An employer with 18 employees should use which remittance form for ETF?
- A) Form R4
- B) Form R1 ✓
- C) Form II only
- D) Form C

*Source: ETF — R1 for employers with 15+ employees, R4 for fewer than 15.*

---

**ETF_EXC_001** | Universal | Exception | MCQ
> Can an employer deduct ETF contributions from an employee's salary?
- A) Yes, partially
- B) Yes, the full 3%
- C) No — it must be paid by the employer ✓
- D) Only with employee's written consent

*Source: ETF Act — strict prohibition on deducting ETF from employee earnings.*

---

## DOMAIN 7: COMPANY REGISTRATION (eROC)

**ROC_FACT_001** | Universal | Factual | MCQ
> A Private Limited Company in Sri Lanka must file annual returns with the Registrar of Companies within how long after the financial year-end?
- A) 30 days
- B) 3 months
- C) 6 months
- D) Within 30 working days of the AGM ✓

*Source: Companies Act No. 7 of 2007. Verify current timing requirement.*

---

**ROC_FACT_002** | Universal | Factual | MCQ
> What is the minimum number of shareholders required to incorporate a Private Limited Company in Sri Lanka?
- A) 1 ✓
- B) 2
- C) 5
- D) 7

*Source: Companies Act — minimum 1 shareholder for Pvt Ltd.*

---

**ROC_PROC_001** | Universal | Procedural | Ordered Steps
> Order the steps to incorporate a Pvt Ltd company:
1. Reserve company name with eROC
2. Prepare Articles of Association and incorporation forms
3. Submit Form 1, Form 18, Form 19 with name approval
4. Pay incorporation fees
5. Receive Certificate of Incorporation
6. Register with IRD within 30 days

*Correct order: 1 → 2 → 3 → 4 → 5 → 6*

---

## DOMAIN 8: CUSTOMS DUTY (Import/Export businesses)

**CUS_FACT_001** | Manufacturing/Retail/IT (Import-dependent) | Factual | MCQ
> As of April 2026, the revised customs import duty bands are:
- A) 5%, 10%, 15%, 25%
- B) 0%, 10%, 20%, 30% ✓
- C) 0%, 15%, 25%, 35%
- D) 10%, 20%, 30%, 40%

*Source: 2026 Budget — national tariff policy revision effective April 2026.*

---

## DOMAIN 9: TOURISM DEVELOPMENT LEVY (TDL) — Tourism only

**TDL_FACT_001** | Tourism & Hospitality | Factual | MCQ
> The Tourism Development Levy is calculated on:
- A) Net profit
- B) Gross turnover from tourism services ✓
- C) Number of guests
- D) Property value

*Source: TDL Act — verify current rate and base.*

---

# PART B — MODULE 3: RISK GAP / VULNERABILITY QUESTIONS

These questions are NOT about correct/incorrect — they are about capturing **behavioral signals and history** that predict compliance failure. Every response is a feature for your ML model.

---

## SECTION B1: COMPLIANCE HISTORY (Universal)

**M3_HIST_001** | Universal | Yes/No
> In the last 24 months, has your business missed ANY tax filing deadline (VAT, EPF, ETF, Income Tax, or any other)?
- Yes / No / Prefer not to say

**M3_HIST_002** | Universal | Numeric
> If yes, approximately how many times?
- 1 / 2-3 / 4-6 / 7+ / Don't remember

**M3_HIST_003** | Universal | Multi-select
> Which deadlines have you missed? (Select all that apply)
- VAT return / VAT payment / EPF contribution / ETF contribution / Income tax installment / Annual income tax return / Annual return to ROC / WHT remittance / Other

**M3_HIST_004** | Universal | Yes/No
> Have you received a penalty notice from IRD, EPF Dept, ETF Board, or any regulatory body in the last 24 months?

**M3_HIST_005** | Universal | Range
> Approximate total penalty paid in last 24 months:
- None / Under LKR 25,000 / 25K-100K / 100K-500K / 500K-2M / Above 2M / Prefer not to say

**M3_HIST_006** | Universal | Yes/No
> Are you currently under any tax audit, inquiry, or investigation?

**M3_HIST_007** | Universal | Yes/No
> Have you ever had to pay back-taxes or revised assessments due to errors in original filing?

**M3_HIST_008** | Universal | 1-5 Scale
> On a scale of 1 to 5, how confident are you that your business is FULLY compliant with all regulatory requirements RIGHT NOW?
- 1 = Not at all confident → 5 = Completely confident

---

## SECTION B2: BEHAVIORAL & OPERATIONAL SIGNALS (Universal)

**M3_BEH_001** | Universal | Single-select
> How do you typically file your taxes?
- Self via IRD e-filing / Self via paper submission / Through external accountant / Through tax agent / Mixed

**M3_BEH_002** | Universal | Single-select
> What method do you use to maintain your business books?
- No formal books / Manual ledger / Excel spreadsheets / Accounting software / Mixed

**M3_BEH_003** | Universal | Single-select
> If you use accounting software, which one?
- QuickBooks / Zoho Books / Sage / Tally / Local Sri Lankan software (specify) / None

**M3_BEH_004** | Universal | Single-select
> How often do you update your business records/books?
- Daily / Weekly / Monthly / Quarterly / Only at filing time / Don't keep formal books

**M3_BEH_005** | Universal | Yes/No
> Do you maintain a calendar or system that tracks all your filing deadlines?

**M3_BEH_006** | Universal | Verifiable Open Text
> Without checking, what is the date of your NEXT VAT return filing? (And what about EPF?)
> *(System checks against actual ground truth — measures real awareness vs claimed awareness)*

**M3_BEH_007** | Universal | Single-select
> When did you last attend any tax/compliance training, seminar, or workshop?
- Within last 6 months / 6-12 months / 1-2 years / More than 2 years / Never

**M3_BEH_008** | Universal | Single-select
> Who is responsible for compliance in your business?
- Owner personally / Dedicated finance staff / Shared informally / External accountant only / No one specifically

**M3_BEH_009** | Universal | Single-select
> Has your finance/accounts staff changed in the last 12 months?
- No change / 1 person changed / Multiple changes / We have no dedicated finance staff

**M3_BEH_010** | Universal | Numeric
> How many different regulatory bodies do you regularly file with?
- 1 / 2 / 3 / 4 / 5+ / Not sure

---

## SECTION B3: STRESS & CAPACITY INDICATORS (Universal)

**M3_STR_001** | Universal | 1-5 Scale
> How often do cash flow problems affect your ability to pay taxes on time? (1=Never, 5=Very often)

**M3_STR_002** | Universal | Yes/No
> Have you ever delayed filing or payment because you couldn't afford the tax amount at the time?

**M3_STR_003** | Universal | 1-5 Scale
> How difficult do you find it to understand official tax notices or letters when you receive them? (1=Very easy, 5=Very difficult)

**M3_STR_004** | Universal | Multi-select
> What are your biggest barriers to staying compliant? (Select all that apply, then rank top 3)
- Time constraints / Cost of accountant / Complex rules / Language barrier (English documents) / Cash flow / Volume of paperwork / Frequent rule changes / Lack of training / Tech literacy / Unclear official communication / Other

---

## SECTION B4: SECTOR-SPECIFIC RISK QUESTIONS

### Manufacturing
**M3_SEC_MFG_001** | Yes/No
> Do you handle VAT on work-in-progress, partial deliveries, or stage-billed contracts?

**M3_SEC_MFG_002** | Yes/No
> Do you systematically track input tax credits across multiple raw material suppliers?

**M3_SEC_MFG_003** | Yes/No
> Do you export any portion of your output? (Export VAT zero-rating compliance triggers)

---

### Retail & Wholesale
**M3_SEC_RTL_001** | Yes/No
> Do you reconcile daily sales totals with your VAT records at end of each day?

**M3_SEC_RTL_002** | Yes/No
> Do you have a documented process for handling returns and refunds in your VAT records?

**M3_SEC_RTL_003** | Single-select
> What proportion of your sales are cash vs card/bank transfer?
- Mostly cash (>70%) / Mostly digital (>70%) / Roughly even / Don't track separately

---

### IT & Software / Services
**M3_SEC_ITS_001** | Yes/No
> Do you receive payments in foreign currency for exported services?

**M3_SEC_ITS_002** | Yes/No
> Do you ensure foreign currency receipts arrive within 6 months of invoice (for VAT zero-rating)?

**M3_SEC_ITS_003** | Yes/No
> Are you aware of and compliant with the new April 2026 VAT regime for exporters?

---

### Tourism & Hospitality
**M3_SEC_TRH_001** | Yes/No
> Do you separately track Tourism Development Levy obligations?

**M3_SEC_TRH_002** | Multi-select
> Which annual licenses/registrations apply to your establishment?
- SLTDA registration / Local council license / Liquor license / Health/food license / Fire safety / Other

**M3_SEC_TRH_003** | Yes/No
> Do you accept foreign currency from tourists, and have proper records of forex conversion?

---

### Food & Beverage
**M3_SEC_FNB_001** | Yes/No
> Are you clear on which of your menu items/products are VAT exempt vs taxable?

**M3_SEC_FNB_002** | Yes/No
> Do you maintain renewed health, hygiene, and food safety registrations?

**M3_SEC_FNB_003** | Yes/No
> Do you sell any excise-applicable items (alcohol, tobacco) requiring separate licensing?

---

### Construction
**M3_SEC_CON_001** | Yes/No
> Do you correctly apply WHT on subcontractor payments above thresholds?

**M3_SEC_CON_002** | Yes/No
> Do you maintain CIDA registration appropriate to your business size?

**M3_SEC_CON_003** | Single-select
> Are you handling any government/public sector contracts?
- Yes — major / Yes — minor / No / Bidding for some

---

### Agriculture
**M3_SEC_AGR_001** | Yes/No
> Do you process raw produce or sell only unprocessed crops? (Different VAT treatment)

**M3_SEC_AGR_002** | Yes/No
> Do you have agriculture-specific tax incentive registrations?

**M3_SEC_AGR_003** | Single-select
> What proportion of your suppliers (input providers) issue formal invoices?
- All / Most / Some / None / Don't know

---

### Transport
**M3_SEC_TPT_001** | Multi-select
> What types of transport services do you provide?
- Passenger / Goods / Both

**M3_SEC_TPT_002** | Yes/No
> Do all your route permits and vehicle licenses have current renewal status?

---

### Healthcare / Education
**M3_SEC_HE_001** | Yes/No
> Are you clear which of your services are VAT exempt vs taxable (e.g., consultation vs commercial activities)?

**M3_SEC_HE_002** | Yes/No
> Are your professional council/board registrations current?

---

# PART C — QUESTION COVERAGE MATRIX

| Sector | VAT | IT | WHT | SSCL | EPF | ETF | ROC | CUS | TDL | Total Q's |
|--------|-----|-----|-----|------|-----|-----|-----|-----|-----|-----------|
| Manufacturing | ✓ +MFG | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ~25 |
| Retail & Wholesale | ✓ +RTL | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ~24 |
| Services | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | ~22 |
| IT & Software | ✓ +ITS | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | ~25 |
| Agriculture | ✓ +AGR | ✓ | ✓ | — | ✓ | ✓ | ✓ | — | — | ~21 |
| Construction | ✓ +CON | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | ~24 |
| Tourism & Hosp. | ✓ +TRH | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ~25 |
| Food & Beverage | ✓ +FNB | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ~25 |
| Healthcare | ✓ +HLT | ✓ | ✓ | — | ✓ | ✓ | ✓ | — | — | ~21 |
| Education | ✓ +EDU | ✓ | ✓ | — | ✓ | ✓ | ✓ | — | — | ~21 |
| Transport | ✓ +TPT | ✓ | ✓ | — | ✓ | ✓ | ✓ | — | — | ~21 |

---

# PART D — DATABASE INSERTION NOTES

For each Module 2 question, insert into `m2_questions` with:
- `question_code` = the code shown (e.g., VAT_FACT_001)
- `domain_id` = FK to regulatory_domains
- `sector_id` = NULL if Universal, else FK to sectors
- `knowledge_type` = factual / procedural / application / exception
- `question_format` = mcq_single / numeric / ordered_steps / scenario_response
- `correct_answer` = JSONB, e.g. `{"selected_option": "C"}` or `{"steps_order": [3,1,2,6,4,5]}`
- `scoring_rubric` = JSONB with partial credit logic for procedural/scenario
- `ground_truth_source` = official document reference
- `ground_truth_verified_by` = CA name (FILL IN AFTER VERIFICATION)

For each Module 3 question, insert into the appropriate table per the schema:
- Compliance history → `m3_compliance_history` + `m3_violation_types`
- Behavioral signals → `m3_behavioral_signals`
- Stress indicators → `m3_behavioral_signals` (cash_flow_difficulty, etc.)
- Barriers → `m3_compliance_barriers`
- Sector-specific → `m3_sector_specific.sector_responses` (JSONB)

---

# PART E — RECOMMENDED SURVEY FLOW

## Total estimated time per respondent
- Module 2 universal questions: ~25 questions × 45 sec = ~19 min
- Module 2 sector-specific: ~5 questions × 60 sec = ~5 min
- Module 3 history + behavior + sector: ~30 questions × 30 sec = ~15 min
- **Total: ~40 minutes** — split across 2 sessions if possible.

## Recommended ordering
1. Consent + Profile (5 min) — keeps simple and warm
2. Module 3 behavioral & history (15 min) — non-test, builds trust
3. Module 2 knowledge test (20 min) — test-like, harder cognitive load
4. Module 3 stress/barriers + sector-specific (5 min) — closing reflection

## Critical UX recommendations
- **Show confidence slider AFTER each Module 2 answer** — captures the overconfidence signal
- **Allow "Don't know" as a valid answer** — better than forcing a wrong guess
- **Save progress** — 40 min surveys WILL be abandoned without resume capability
- **Multilingual from day 1** — translate AT LEAST Module 3 questions to Sinhala and Tamil. Module 2 knowledge questions need expert translation since technical terms matter.
- **Pilot with 5-10 SMEs first** — test actual time, comprehension, dropout points
- **Get ethics approval** — you're collecting self-reported violations, which is sensitive

---

*End of question bank — version 1.0*
*Next step: Get every "correct answer" certified by a practising CA and a tax professional.*
