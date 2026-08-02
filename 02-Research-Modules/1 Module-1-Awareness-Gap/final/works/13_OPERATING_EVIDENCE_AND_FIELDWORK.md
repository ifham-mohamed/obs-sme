# M1 operating evidence audit

Generated: `2026-08-01T19:30:15.828334+00:00`. Database access was read-only.

## Remediation and decisions — 2026-08-02

- The 80-row deterministic English sample passed **80/80** grounding, source-hash, and hard-flag checks. This is an engineering audit, not a substitute for the planned human harm/faithfulness review.
- Four of the original 11 `review_required` summaries were false `summary_too_long` failures caused by treating `No.` in an Act citation as a sentence boundary. The sentence counter was repaired, the four summaries were regenerated, and their eight SI/TA jobs were queued. The remaining queue is **7 genuine low-margin classifier reviews**.
- The SI/TA audit passed only **10/152 (6.58%)** numeric-preservation checks. The 72 affected summaries were reopened for translation, producing **144 manual-priority jobs**. They remain pending because the existing Colab worker could not reach its expired tunnel and Colab reported that its GPU quota was unavailable. No translation-quality success is claimed.
- The seven low-margin rows were source-reviewed for expert follow-up. Recommended dispositions: `GZT_2480_04` → `LABOUR_LAW`; `GZT_2480_47` confirm `BUSINESS_REGISTRATION`; `GZT_2480_49` → `TAX_RATE_CHANGE`; `GZT_2481_09` confirm `SECTOR_SPECIFIC`; `GZT_2482_11` → `LABOUR_LAW`; `GZT_2486_08` confirm `LABOUR_LAW`; `GZT_2489_72` → `TAX_RATE_CHANGE`. These are recommendations only—no row was marked expert-verified and no classifier label was overwritten.
- The classifier now monitors LinearSVC decision-margin histograms, category-distribution drift, dominant-category concentration, active review-queue size, and review correction yield. The `0.40` margin remains **provisional** because the live audit contains zero completed review outcomes.
- `/portal/m1/survey` is built and browser-verified with EN/SI/TA messaging, consent, safe register/login return paths, and recruitment-channel propagation. Real completed unique SMEs remain **0/100**; invitations and participant responses cannot be fabricated.

## V7 weighted validation diagnostic — 2026-08-02

Kaggle ran exactly one weighted seed (`42`) on the no-leak `773/163` training/validation branch. The V6 test split was not loaded, no model was promoted, and the output explicitly records `claim_eligible=false`.

| Measure | Best validation result (epoch 13) |
|---|---:|
| Category macro-F1 | `0.899862` |
| Sector macro-F1 | `0.884312` |
| Sector micro-F1 | `0.884758` |
| Sector exact-set match | `0.907975` |
| Partial-sector exact match | `4/9 = 0.444444` |
| All-three prediction share | `0.269939` |

The weighted loss recovered the rejected model from collapse and predicted all eight categories, including two EPF/ETF validation rows. It did **not** clear the category gate (`0.92`) and the partial-sector denominator is only nine. Therefore the correct decision is to stop before a three-seed run, threshold selection, test evaluation, export, or promotion. Obtain a fresh temporal holdout plus genuine EPF/ETF and partial-sector examples first. Machine-readable evidence: `evidence/M1_V7_WEIGHTED_SEED42_VALIDATION_2026-08-02.json`.

## Stage E summaries

- English summaries evaluated: **80**; passed: **80 (100.0000%)**.
- Translated rows audited: **76**; locale checks: **152**; passed: **10 (6.5800%)**.
- Remaining `review_required`: **7**.
- Review hard flags: `{"classification_not_review_ready": 7, "classifier_review_required": 7}`.

Numeric-preservation failures:

- `GZT_2485_17` `si` — missing=['2485/17']; extra=[]
- `GZT_2485_17` `ta` — missing=['2485/17']; extra=[]
- `GZT_2498_14` `si` — missing=['2498/14', '262']; extra=[]
- `GZT_2495_33` `si` — missing=['2495/33']; extra=[]
- `GZT_2495_33` `ta` — missing=['2495/33']; extra=[]
- `GZT_2498_12` `si` — missing=['2498/12', '262']; extra=[]
- `GZT_2498_07` `si` — missing=['2498/07']; extra=[]
- `GZT_2498_07` `ta` — missing=['2498/07']; extra=[]
- `GZT_2485_18` `si` — missing=['2485/18']; extra=[]
- `GZT_2485_18` `ta` — missing=['2485/18']; extra=[]
- `GZT_2485_20` `si` — missing=['2485/20']; extra=[]
- `GZT_2485_20` `ta` — missing=['2485/20']; extra=[]
- `GZT_2488_21` `si` — missing=['2488/21']; extra=[]
- `GZT_2488_21` `ta` — missing=['2488/21']; extra=[]
- `GZT_2483_61` `si` — missing=['2483/61']; extra=[]
- `GZT_2483_61` `ta` — missing=['2483/61']; extra=[]
- `GZT_2495_91` `si` — missing=['2495/91']; extra=[]
- `GZT_2495_91` `ta` — missing=['2495/91']; extra=[]
- `GZT_2485_23` `si` — missing=['2485/23']; extra=[]
- `GZT_2485_23` `ta` — missing=['2485/23']; extra=[]
- `GZT_2495_16` `si` — missing=['2495/16']; extra=[]
- `GZT_2495_16` `ta` — missing=['2495/16']; extra=[]
- `GZT_2489_73` `si` — missing=['2489/73']; extra=[]
- `GZT_2489_73` `ta` — missing=['2489/73']; extra=[]
- `GZT_2485_24` `si` — missing=['2485/24']; extra=[]
- `GZT_2485_24` `ta` — missing=['2485/24']; extra=[]
- `GZT_2484_43` `si` — missing=['2484/43']; extra=[]
- `GZT_2484_43` `ta` — missing=['2484/43']; extra=[]
- `GZT_2485_27` `si` — missing=['2485/27']; extra=[]
- `GZT_2485_27` `ta` — missing=['2485/27']; extra=[]
- `GZT_2483_62` `si` — missing=['2483/62']; extra=[]
- `GZT_2483_62` `ta` — missing=['2483/62']; extra=[]
- `GZT_2485_25` `si` — missing=['2485/25']; extra=[]
- `GZT_2485_25` `ta` — missing=['2485/25']; extra=[]
- `GZT_2485_21` `si` — missing=['2485/21']; extra=[]
- `GZT_2485_21` `ta` — missing=['2485/21']; extra=[]
- `GZT_2486_11` `si` — missing=['2486/11']; extra=[]
- `GZT_2486_11` `ta` — missing=['2486/11']; extra=[]
- `GZT_2486_16` `si` — missing=['2486/16']; extra=[]
- `GZT_2486_16` `ta` — missing=['2486/16']; extra=[]
- `GZT_2483_14` `si` — missing=['2483/14']; extra=[]
- `GZT_2483_14` `ta` — missing=['2483/14']; extra=[]
- `GZT_2483_63` `si` — missing=['2483/63']; extra=[]
- `GZT_2483_63` `ta` — missing=['2483/63']; extra=[]
- `GZT_2485_31` `si` — missing=['2485/31']; extra=[]
- `GZT_2485_31` `ta` — missing=['2485/31']; extra=[]
- `GZT_2485_30` `si` — missing=['2485/30']; extra=[]
- `GZT_2485_30` `ta` — missing=['2485/30']; extra=[]
- `GZT_2489_44` `si` — missing=['2489/44']; extra=[]
- `GZT_2489_44` `ta` — missing=['2489/44']; extra=[]
- `GZT_2485_33` `si` — missing=['2485/33']; extra=[]
- `GZT_2485_33` `ta` — missing=['2485/33']; extra=[]
- `GZT_2483_64` `si` — missing=['2483/64']; extra=[]
- `GZT_2483_64` `ta` — missing=['2483/64']; extra=[]
- `GZT_2486_02` `si` — missing=['2486/02', '27.04.2026']; extra=[]
- `GZT_2486_02` `ta` — missing=['2486/02', '27.04.2026']; extra=[]
- `GZT_2486_13` `si` — missing=['2486/13']; extra=[]
- `GZT_2486_13` `ta` — missing=['2486/13']; extra=[]
- `GZT_2485_32` `si` — missing=['2485/32']; extra=[]
- `GZT_2485_32` `ta` — missing=['2485/32']; extra=[]
- `GZT_2483_41` `si` — missing=['2483/41']; extra=[]
- `GZT_2483_41` `ta` — missing=['2483/41']; extra=[]
- `GZT_2485_34` `si` — missing=['2485/34']; extra=[]
- `GZT_2485_34` `ta` — missing=['2485/34']; extra=[]
- `GZT_2486_06` `si` — missing=['2486/06']; extra=[]
- `GZT_2486_06` `ta` — missing=['2486/06']; extra=[]
- `GZT_2486_03` `si` — missing=['2486/03']; extra=[]
- `GZT_2486_03` `ta` — missing=['2486/03']; extra=[]
- `GZT_2484_14` `si` — missing=['2484/14']; extra=[]
- `GZT_2484_14` `ta` — missing=['2484/14']; extra=[]
- `GZT_2483_17` `si` — missing=['11,280.7', '2483/17']; extra=[]
- `GZT_2483_17` `ta` — missing=['11,280.7', '2483/17']; extra=[]
- `GZT_2484_44` `si` — missing=['2484/44']; extra=[]
- `GZT_2484_44` `ta` — missing=['2484/44']; extra=[]
- `GZT_2485_01` `si` — missing=['2485/01']; extra=[]
- `GZT_2485_01` `ta` — missing=['2485/01']; extra=[]
- `GZT_2486_05` `si` — missing=['2486/05']; extra=[]
- `GZT_2486_05` `ta` — missing=['2486/05']; extra=[]
- `GZT_2485_61` `si` — missing=['2485/61']; extra=[]
- `GZT_2485_61` `ta` — missing=['2485/61']; extra=[]
- `GZT_2485_44` `si` — missing=['2485/44']; extra=[]
- `GZT_2485_44` `ta` — missing=['2485/44']; extra=[]
- `GZT_2484_10` `si` — missing=['2484/10']; extra=[]
- `GZT_2484_10` `ta` — missing=['2484/10']; extra=[]
- `GZT_2484_09` `si` — missing=['2484/09']; extra=[]
- `GZT_2484_09` `ta` — missing=['2484/09']; extra=[]
- `GZT_2484_08` `si` — missing=['2484/08']; extra=[]
- `GZT_2484_08` `ta` — missing=['2484/08']; extra=[]
- `GZT_2489_42` `si` — missing=['2489/42']; extra=[]
- `GZT_2489_42` `ta` — missing=['2489/42']; extra=[]
- `GZT_2484_46` `si` — missing=['2484/46']; extra=[]
- `GZT_2484_46` `ta` — missing=['2484/46']; extra=[]
- `GZT_2485_62` `si` — missing=['2485/62']; extra=[]
- `GZT_2485_62` `ta` — missing=['2485/62']; extra=[]
- `GZT_2485_36` `si` — missing=['2485/36']; extra=[]
- `GZT_2485_36` `ta` — missing=['2485/36']; extra=[]
- `GZT_2485_54` `si` — missing=['2485/54']; extra=[]
- `GZT_2485_54` `ta` — missing=['2485/54']; extra=[]
- `GZT_2485_40` `si` — missing=['2485/40']; extra=[]
- `GZT_2485_40` `ta` — missing=['2485/40']; extra=[]
- `GZT_2484_11` `si` — missing=['2484/11']; extra=[]
- `GZT_2484_11` `ta` — missing=['2484/11']; extra=[]
- `GZT_2485_56` `si` — missing=['2485/56']; extra=[]
- `GZT_2485_56` `ta` — missing=['2485/56']; extra=[]
- `GZT_2485_22` `si` — missing=['2485/22']; extra=[]
- `GZT_2485_22` `ta` — missing=['2485/22']; extra=[]
- `GZT_2485_42` `si` — missing=['2485/42']; extra=[]
- `GZT_2485_42` `ta` — missing=['2485/42']; extra=[]
- `GZT_2483_35` `si` — missing=['2483/35']; extra=[]
- `GZT_2483_35` `ta` — missing=['2483/35']; extra=[]
- `GZT_2485_46` `si` — missing=['2485/46']; extra=[]
- `GZT_2485_46` `ta` — missing=['2485/46']; extra=[]
- `GZT_2489_45` `si` — missing=['2489/45']; extra=[]
- `GZT_2489_45` `ta` — missing=['2489/45']; extra=[]
- `GZT_2483_67` `si` — missing=['2483/67']; extra=[]
- `GZT_2483_67` `ta` — missing=['2483/67']; extra=[]
- `GZT_2489_17` `si` — missing=['2489/17']; extra=[]
- `GZT_2489_17` `ta` — missing=['2489/17']; extra=[]
- `GZT_2485_49` `si` — missing=['2485/49']; extra=[]
- `GZT_2485_49` `ta` — missing=['2485/49']; extra=[]
- `GZT_2483_68` `si` — missing=['2483/68']; extra=[]
- `GZT_2483_68` `ta` — missing=['2483/68']; extra=[]
- `GZT_2485_48` `si` — missing=['2485/48']; extra=[]
- `GZT_2485_48` `ta` — missing=['2485/48']; extra=[]
- `GZT_2484_16` `si` — missing=['2484/16']; extra=[]
- `GZT_2484_16` `ta` — missing=['2484/16']; extra=[]
- `GZT_2484_18` `si` — missing=['2484/18']; extra=[]
- `GZT_2484_18` `ta` — missing=['2484/18']; extra=[]
- `GZT_2484_20` `si` — missing=['2484/20']; extra=[]
- `GZT_2484_20` `ta` — missing=['2484/20']; extra=[]
- `GZT_2485_47` `si` — missing=['2485/47']; extra=[]
- `GZT_2485_47` `ta` — missing=['2485/47']; extra=[]
- `GZT_2484_21` `si` — missing=['2484/21']; extra=[]
- `GZT_2484_21` `ta` — missing=['2484/21']; extra=[]
- `GZT_2485_13` `si` — missing=['2485/13']; extra=[]
- `GZT_2485_13` `ta` — missing=['2485/13']; extra=[]
- `GZT_2484_22` `si` — missing=['2484/22']; extra=[]
- `GZT_2484_22` `ta` — missing=['2484/22']; extra=[]
- `GZT_2484_23` `si` — missing=['2484/23']; extra=[]
- `GZT_2484_23` `ta` — missing=['2484/23']; extra=[]
- `GZT_2484_19` `si` — missing=['2484/19']; extra=[]
- `GZT_2484_19` `ta` — missing=['2484/19']; extra=[]

Review queue:

- `GZT_2480_04` — category `SECTOR_SPECIFIC`, margin `0.0376`, flags `classification_not_review_ready, classifier_review_required`
- `GZT_2480_47` — category `BUSINESS_REGISTRATION`, margin `0.3209`, flags `classification_not_review_ready, classifier_review_required`
- `GZT_2480_49` — category `SECTOR_SPECIFIC`, margin `0.1352`, flags `classification_not_review_ready, classifier_review_required`
- `GZT_2481_09` — category `SECTOR_SPECIFIC`, margin `0.2494`, flags `classification_not_review_ready, classifier_review_required`
- `GZT_2482_11` — category `SECTOR_SPECIFIC`, margin `0.3762`, flags `classification_not_review_ready, classifier_review_required`
- `GZT_2486_08` — category `LABOUR_LAW`, margin `0.3896`, flags `classification_not_review_ready, classifier_review_required`
- `GZT_2489_72` — category `SECTOR_SPECIFIC`, margin `0.3915`, flags `classification_not_review_ready, classifier_review_required`

## Classifier operating evidence

- Live classified rows: **898**; margin rows: **898**.
- Margin min / p10 / median / p90 / max: `0.0087` / `1.1215` / `1.8098` / `2.0820` / `2.2455`.
- Configured threshold: `0.4000`; all rows below it: **18**; active queue: **18**.
- Review outcomes: `{"confirmed": 0, "corrected": 0, "correction_yield": null, "reviewed": 0}`.
- Threshold decision: **provisional_no_review_outcomes**. With no completed review outcomes, the correction yield is unknown; 0.40 is neither frozen nor revised by this evidence.
- Category counts: `{"BUSINESS_REGISTRATION": 6, "IMPORT_EXPORT": 25, "LABOUR_LAW": 26, "PRODUCT_STANDARD": 3, "SECTOR_SPECIFIC": 831, "TAX_RATE_CHANGE": 7}`.

## M1 recruitment

- M1 sessions: **0**.
- Completed unique SMEs: **0 / 100**; remaining: **100**.
- Completed by channel: `{}`.
