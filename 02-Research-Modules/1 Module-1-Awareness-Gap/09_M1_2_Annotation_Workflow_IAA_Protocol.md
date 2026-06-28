# 09_M1_2 — Annotation Workflow & IAA Protocol

> Companion to [09_M1_Annotation_Guidelines.md](09_M1_Annotation_Guidelines.md) — full IAA computation, resolution paths, calibration test design + performance-tracking.
> **Implementation status:** 🔲 Deferred (BUILD_07 — annotators onboarded once Label Studio is set up)

## Purpose

Parent doc §4–§5 describes IAA protocol and annotator qualifications at a high level. This companion specifies the *operational* details: the exact calibration test design (already added to parent doc §5.1 but expanded here), the per-annotator performance-tracking schema, and the resolution workflow when annotators consistently disagree.

## Detailed process

### Step 1 — Calibration test

A 20-document hand-picked set spanning all 12 categories + 3 languages + 4 edge-case patterns. Stored in `research/data/calibration_set_v1.csv`. Document IDs `cal_001` through `cal_020`. The "expert reference" labels are set by the domain expert (CA / Attorney) and locked.

**Coverage matrix** (the calibration set has at least one doc in each cell):

| | EN | SI | TA |
|---|---|---|---|
| TAX_RATE_CHANGE | ✅ | ✅ | ✅ |
| LABOUR_LAW | ✅ | ✅ | — (single combined doc) |
| EPF_ETF_CHANGE | ✅ | ✅ | — |
| ...etc | | | |
| Edge cases | 4 docs spanning multi-penalty, repeal, no-SME-impact, gazette-with-tables | | |

### Step 2 — Calibration result table

After each annotator candidate completes the test:

| Annotator | Attempt | κ category | κ sector | Edge-case pass? | Outcome |
|---|---|---|---|---|---|
| `ann_001` | 1 | 0.84 | 0.79 | 3/4 | ✅ Pass |
| `ann_002` | 1 | 0.74 | 0.71 | 2/4 | 🟡 Conditional → retest |
| `ann_002` | 2 | 0.86 | 0.82 | 4/4 | ✅ Pass |
| `ann_003` | 1 | 0.61 | 0.55 | 1/4 | ❌ Fail |

Stored in `m1_annotator_calibration` table (parent doc §5.1).

### Step 3 — Cohen's κ computation

```python
from sklearn.metrics import cohen_kappa_score

def category_kappa(a: list[str], b: list[str]) -> float:
    return cohen_kappa_score(a, b)
```

For sectors (multi-label):

```python
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.metrics import cohen_kappa_score

def sector_kappa(a_lists: list[list[str]], b_lists: list[list[str]]) -> float:
    """Mean per-sector binary κ — practical proxy for Fleiss' κ on multi-label."""
    mlb = MultiLabelBinarizer(classes=[...10 sectors...])
    a_bin = mlb.fit_transform(a_lists)
    b_bin = mlb.transform(b_lists)
    return float(np.mean([cohen_kappa_score(a_bin[:,i], b_bin[:,i]) for i in range(a_bin.shape[1])]))
```

### Step 4 — Per-annotator ongoing performance tracking

Each annotator's rolling κ (vs majority vote) is computed weekly:

```sql
SELECT
  ann.annotator_id,
  -- rolling 4-week category κ against the consensus (majority vote)
  COUNT(*) AS docs_in_window,
  AVG(CASE WHEN ann.category = consensus.category THEN 1 ELSE 0 END) AS exact_agreement_rate
FROM m1_annotations ann
JOIN (
  SELECT regulation_id, mode() WITHIN GROUP (ORDER BY category) AS category
  FROM m1_annotations
  GROUP BY regulation_id
) consensus ON consensus.regulation_id = ann.regulation_id
WHERE ann.created_at >= NOW() - INTERVAL '4 weeks'
GROUP BY ann.annotator_id;
```

Annotators whose 4-week exact-agreement rate drops below 0.75 are paused for a 1-hour "drift correction" session with the domain expert (refresher on common confusable pairs).

### Step 5 — Resolution paths (recap from parent doc + extension)

| κ range (annotator A vs annotator B) | Action | Decision authority |
|---|---|---|
| ≥ 0.75 | Accept; consensus label = both agree | Automated |
| 0.60–0.74 | Domain expert reviews; expert breaks tie | Domain expert |
| < 0.60 | Suspend annotation for that batch; both annotators retake calibration | Lead researcher |

For the sector multi-label case, the resolution rules from [09_M1_Annotation_Guidelines.md §4.4](09_M1_Annotation_Guidelines.md) (strict-subset → union, overlap-with-extras → expert, disjoint → expert + guideline review) apply.

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| Cohen's κ (chosen) | Standard metric; comparable across studies | ✅ Single number per annotator pair | Switch to Fleiss' κ when ≥ 3 annotators per item routinely (currently 2 + expert). |
| Per-sector binary κ proxy for sector multi-label | Simpler than true Fleiss' κ on multi-label | ✅ Adequate; documented as a proxy | If a future reviewer requires true multi-label κ, switch to Krippendorff's α. |
| 20-doc calibration set | Compact; can be completed in ~1 hour | ✅ Long enough for statistical signal, short enough to take seriously | If pass rate drops below 50 % consistently — set is too hard, revise. |
| Quarterly recalibration | Catches annotator drift | ✅ Aligned with the annotation campaign cadence | Increase to monthly if drift incidents rise. |

## Worked example

The full workflow for a single document, end-to-end:

```
Doc reg_2491_14 (VAT amendment) enters Label Studio queue
   ↓
[Annotator A] labels: category=TAX_RATE_CHANGE, sectors=[manufacturing, retail, services]
[Annotator B] labels: category=TAX_RATE_CHANGE, sectors=[manufacturing, retail]
   ↓
IAA computation:
   - Category: A = B → κ undefined for n=1; treat as agreement
   - Sector: B's set ⊂ A's set → STRICT-SUBSET case → UNION
   ↓
Consensus label written to m1_regulation_labels:
   category=TAX_RATE_CHANGE
   sectors=[manufacturing, retail, services]
   match_method='consensus_strict_subset_union'
   ↓
Doc joins the training set; both annotators credited
```

A disagreement case:

```
Doc reg_2492_03 ("textile-dyeing effluent pH limits")
   ↓
[Annotator A] labels: ENVIRONMENTAL, [manufacturing]
[Annotator B] labels: PRODUCT_STANDARD, [manufacturing]
   ↓
IAA: category disagreement → route to domain expert
   ↓
Expert review: "Effluent rules → ENVIRONMENTAL. Product standards would govern the
product itself, not its byproducts. Annotator A is correct."
   ↓
Consensus label = A's label
m1_annotations records:
   ann_A.resolution_status = 'expert_confirmed'
   ann_B.resolution_status = 'expert_overruled'
   ↓
Annotator B notified via dashboard; this counts toward B's drift metric
```

## Failure modes & edge cases

- **Annotator never disagrees** (lazy labelling). Detected: > 95 % exact-agreement rate on calibration items where the expert reference is *intentionally ambiguous*. Mitigation: 2/20 calibration items are intentionally ambiguous; annotators who unanimously agree on these are flagged.
- **Domain expert unavailable.** A backlog of "0.60–0.74 κ" items waits for expert review. Mitigation: 48-hour SLA; auto-escalation to research lead if expert is OOO for > 5 days.
- **Calibration set leaked.** If candidate annotators study the test answers before taking it, the test is meaningless. Mitigation: calibration set is kept in a private S3 bucket; only the lead researcher generates per-candidate test instances (with random doc shuffle to prevent rote memorisation).
- **Multi-annotator drift in same direction.** Both A and B drift toward over-tagging `TAX_RATE_CHANGE` → "consensus" is wrong. Caught by quarterly expert audit (50-doc sample re-labelled by expert).

## Validation & acceptance criteria

- **Pass rate target ≥ 60 % first-attempt, ≥ 80 % including conditional retest.** Audited annually.
- **κ rolling 4-week ≥ 0.80** per annotator.
- **Expert review SLA ≤ 48 h.**
- **Calibration set integrity:** zero post-publication edits to `calibration_set_v1.csv` (any edit triggers a v2 set + recalibration of all active annotators).

## Cross-references

- Parent: [09_M1_Annotation_Guidelines.md](09_M1_Annotation_Guidelines.md) §4, §5, §5.1
- Related: [09_M1_1_Category_Taxonomy_Examples.md](09_M1_1_Category_Taxonomy_Examples.md), [09_M1_3_SME_Survey_Instrument.md](09_M1_3_SME_Survey_Instrument.md)
- BUILD phase: BUILD_07 §annotator workflow
- Code (when shipped): `m1_annotator_calibration` table, `research/data/calibration_set_v1.csv`
