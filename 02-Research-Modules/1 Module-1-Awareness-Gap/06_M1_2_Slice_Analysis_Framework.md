# 06_M1_2 — Slice Analysis Framework

> Companion to [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) — per-language / per-quarter / per-text-length / per-extraction-method slice analyses with visualization templates + extension to confidence-bucket and category-balance slices.
> **Implementation status:** 🔲 Deferred (BUILD_11 — `ml/m1/model/evaluation.py:slice_analysis()`)

## Purpose

Parent doc §4.2 names four slice axes (language, year-quarter, text-length, extraction-method) but doesn't show how the slice analyses are computed or visualised. This companion provides the implementation, the visualization templates, and the failure-mode taxonomy that catches "cliff" patterns in production.

## Detailed process

### Core slice computation

```python
import pandas as pd
from sklearn.metrics import f1_score

def slice_f1(predictions: pd.DataFrame, slice_col: str, n_min: int = 30) -> pd.DataFrame:
    """Compute macro-F1 per slice value; drop slices with <n_min samples."""
    out = []
    for slice_val, g in predictions.groupby(slice_col):
        if len(g) < n_min:
            out.append({slice_col: slice_val, "n": len(g), "macro_f1": None,
                       "note": f"sample size < {n_min} — F1 unreliable"})
            continue
        f1 = f1_score(g["actual_category"], g["predicted_category"], average="macro")
        out.append({slice_col: slice_val, "n": len(g), "macro_f1": f1})
    return pd.DataFrame(out)
```

### Four standard slices (from parent doc)

```python
def run_standard_slices(predictions: pd.DataFrame) -> dict:
    return {
        "by_language":            slice_f1(predictions, "primary_language"),
        "by_year_quarter":        slice_f1(predictions, predictions["gazette_year_quarter"]),
        "by_text_length_bucket":  slice_f1(predictions, predictions["text_length"].apply(bucket_text_length)),
        "by_extraction_method":   slice_f1(predictions, "extraction_method"),
    }
```

### Two additional slices (this companion's contribution)

#### Confidence-bucket slice

```python
def bucket_confidence(conf: float) -> str:
    if conf < 0.50: return "low (<0.50)"
    if conf < 0.70: return "med-low (0.50-0.70)"
    if conf < 0.85: return "med-high (0.70-0.85)"
    return "high (>=0.85)"

predictions["confidence_bucket"] = predictions["confidence"].apply(bucket_confidence)
slice_f1(predictions, "confidence_bucket")
```

Expected pattern: monotonic — higher-confidence buckets have higher F1. If `low` bucket F1 is *higher* than `med-low`, the calibration is broken (a known XLM-R weakness; flag for temperature scaling in `ml/m1/model/calibration.py`).

#### Category-balance slice

Highlights how F1 varies with the *prevalence* of each category in production:

```python
def category_balance(predictions: pd.DataFrame) -> pd.DataFrame:
    out = []
    for cat, g in predictions.groupby("actual_category"):
        out.append({
            "category": cat,
            "n_actual": len(g),
            "n_predicted_as_this": (predictions["predicted_category"] == cat).sum(),
            "precision": (g["predicted_category"] == cat).mean(),
            "recall": (g["predicted_category"] == cat).mean(),         # same as above on actual=cat
            "f1": f1_score(g["actual_category"], g["predicted_category"], average="micro"),
        })
    return pd.DataFrame(out)
```

### Failure-mode taxonomy (4 cliffs)

| Cliff | Pattern | Likely cause | Mitigation |
|---|---|---|---|
| **Confidence cliff** | F1 drops > 10 pp in low-confidence bucket | Calibration miscalibrated | Temperature scaling (`ml/m1/model/calibration.py`) |
| **Length cliff** | F1 drops > 8 pp on long texts (> 4 chunks) | Classification picks chunk 0 only; category signal in later sections | Aggregate logits across chunks (logit-mean over all chunks) |
| **Language cliff** | F1 SI > 8 pp below EN | Insufficient SI training data | Targeted SI paraphrase augmentation (technique C in [06_M1_1_Data_Augmentation_Strategy.md](06_M1_1_Data_Augmentation_Strategy.md)) |
| **Extraction-method cliff** | F1 on `tesseract` rows > 5 pp below `pymupdf` rows | OCR noise propagates to classifier | Tighten OCR threshold; or retrain on more scanned examples |

### Visualization templates

Standard set of figures for the BUILD_11 evaluation notebook:

- `slice_f1_bar_per_language.png` — bar chart, F1 + error bars (seed std)
- `slice_f1_heatmap_year_x_language.png` — heatmap with annotation
- `confidence_distribution_per_class.png` — overlapping kernel density
- `confusion_matrix_top12.png` — categorical confusion matrix
- `f1_vs_text_length.png` — scatter + smoothed line

Templates committed to `research/notebooks/_figure_templates.py`; called by the evaluation notebook with the run's prediction dataframe.

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| Slice F1 with `n_min=30` guard | Reports unreliable slices honestly | ✅ Drops noisy small-sample F1 estimates | If n=30 is too aggressive (lots of slices dropped); revisit at 1000+ test docs. |
| Logit-aggregation for length-cliff fix | Cheap; improves long-text F1 | ✅ Adds < 5 ms per gazette; deferred until cliff is *measured* in BUILD_11 | If cliff doesn't appear, defer indefinitely. |
| Temperature scaling | Standard calibration fix | ✅ Single-parameter fit on val set; trivial | If F1 calibration target (ECE ≤ 0.05) is missed. |
| Per-language fine-tuning heads | Maximum per-language accuracy | ❌ Defeats the shared-encoder advantage of XLM-R | If SI/TA F1 cliffs persist after augmentation. |

## Worked example

A representative slice run output:

```
by_language:
  en  (n=320, macro_f1=0.934)
  si  (n=180, macro_f1=0.882)
  ta  (n= 80, macro_f1=0.861)

by_text_length_bucket:
  short  (<1k chars, n=120, macro_f1=0.940)
  medium (1k–4k,    n=290, macro_f1=0.925)
  long   (>4k,      n=170, macro_f1=0.868)    ← Length cliff (8 pp below short)

by_confidence_bucket:
  high       (n=410, macro_f1=0.961)
  med-high   (n=125, macro_f1=0.879)
  med-low    (n= 35, macro_f1=0.722)
  low        (n= 10, macro_f1=None — sample <30)

Decision triggered:
  - Length cliff: open ticket "implement logit-aggregation across chunks" — target +4 pp on long-text F1.
  - Confidence calibration looks well-behaved (monotonic) — no temperature scaling needed.
```

## Failure modes & edge cases

- **Test slice too small.** If a slice has < 30 samples, F1 reported as None — the alternative (report it anyway) misleads. Decision: report `n` + "insufficient data" note.
- **Confidence bucket boundaries chosen post-hoc.** Buckets are fixed at `[0.50, 0.70, 0.85]` — chosen *before* the run, not tuned to make the model look good.
- **Year-quarter slice with one quarter only.** Happens when temporal split is narrow (e.g. test = 30 days). Mitigation: skip the slice; flag for thesis methodology.
- **Slice-internal class imbalance.** A slice with only one class (e.g. all `TAX_RATE_CHANGE`) has trivially perfect macro-F1. Mitigation: report per-class breakdown alongside macro-F1.

## Validation & acceptance criteria

- **All 6 slices run.** Evaluation notebook produces all 4 standard + 2 extended slices end-to-end.
- **Cliff detection wired up.** Each cliff has a specific pattern + ticket-template; CI tests assert the patterns are detected on synthetic data.
- **Visualization parity.** Same template generates same figure across runs (no random-seed drift); CI snapshots compare PNG hashes.
- **Documented in thesis.** Each slice analysis with N > 30 is reported in the thesis evaluation chapter.

## Cross-references

- Parent: [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) §4.2, §5
- Related: [12_M1_1_Performance_Monitoring_Alerting.md](12_M1_1_Performance_Monitoring_Alerting.md) (same slice computations run on production data)
- BUILD phase: BUILD_11 §evaluation suite
- Code (when shipped): `ml/m1/model/evaluation.py`, `research/notebooks/findings_classifier_evaluation.ipynb`
