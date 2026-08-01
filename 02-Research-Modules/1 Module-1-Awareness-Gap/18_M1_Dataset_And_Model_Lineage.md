# 18 — Module 1: Dataset and Model Lineage

> One page that traces every M1 classification dataset from the raw gold standard to the frozen production model: which version came from which, what changed between them, what the split was, what each artifact hashes to, and which model was trained on which. Companion to [[06_M1_Training_Evaluation]] (method) and [[09_M1_Annotation_Guidelines]] (how labels were produced).
>
> Evidence base: `documentation/m1/records/ENIGMATRIX_M1_COMPLETE_END_TO_END_RECORD_2026-07-31_2313_IST.md` (5,642 lines) and `datasets/m1_regulations_v6_1110_clean_fixedsplit/dataset_manifest_v6.json`.
> Verified: 2026-08-01.

---

## 1. Lineage at a glance

```text
Label Studio batches 01–07
        │  2 annotations per task · 1128 tasks · 2256 annotations
        ▼
gold_standard.csv  (research/data/labeling/)
        │
        ├─ Legacy experiment branch inside enigmatrix-ml/datasets/
        │
        │  L1      m1_regulations                     800 rows · 560 / 120 / 120
        │  Smoke   m1_regulations_smoke                32 rows · 16 / 8 / 8
        │  L2      m1_regulations_v2_1000             1000 rows · 700 / 150 / 150
        │  L2s     m1_regulations_v2_1000_stratified  1000 rows · 700 / 150 / 150
        │  L3      m1_regulations_v3_1128_stratified  1128 rows · 790 / 169 / 169
        │
        └─ Fixed reporting branch
           │
           ▼
           V4  m1_regulations_v4_1128            ── 1128 rows, raw gold freeze
           │  drop 18 OCR/page-number artifacts (ML use only — gold history keeps them)
           ▼
           V5  m1_regulations_v5_1110_clean_fixedsplit
           │  + 3 PDF-adjudicated category corrections (all in test split)
           │  fixed reporting split established: 777 / 166 / 167
           ▼
           V6  m1_regulations_v6_1110_clean_fixedsplit   ◄── FROZEN, current
              + 4 EPF/ETF label corrections (all in train split)
              split preserved byte-for-byte from V5
```

Three rules keep the lineage clean:

1. **Legacy datasets are provenance only.** They explain how early baselines were produced, but they are not used for final model claims.
2. **The reporting split never moved from V5 to V6.** 777 train / 166 validation / 167 test, so a V5-vs-V6 score difference is a labelling effect, never a split effect.
3. **Nothing was deleted from the gold history.** The 18 excluded artifacts are excluded from *ML training and evaluation only*; they remain in the adjudicated gold record.

---

## 2. Version-by-version

### V4 — `m1_regulations_v4_1128`

The first freeze of the 1128-row gold set. Also present as `_stratified` and `_clean_stratified` variants from the pre-fixed-split era. Superseded — kept for provenance only.

### V5 — `m1_regulations_v5_1110_clean_fixedsplit`

1110 rows after excluding 18 OCR/page-number artifacts, plus three adjudicated corrections resolved against the source PDFs — all three landed in the test split:

| Key | Was | Corrected to |
|---|---|---|
| `GZT_2491_01` | `SECTOR_SPECIFIC` | `IMPORT_EXPORT` |
| `official-egz-2337-19` | `IMPORT_EXPORT` | `PRODUCT_STANDARD` |
| `GZT_2471_56` | `SECTOR_SPECIFIC` | `LABOUR_LAW` |

Ships with `dataset_manifest.json`, `label_changes_from_v4_to_v5.csv`, `split_distribution.csv`, and both CSV and Parquet forms.

### V6 — `m1_regulations_v6_1110_clean_fixedsplit` (current, frozen)

Produced by `scripts/build_m1_v6_fixedsplit.py` from a Kaggle correction bundle (SHA256 `2C9169B5…86597`). The change is narrow and deliberate: four Presidential duties/functions gazettes carried incidental ETF mentions and had been labelled `EPF_ETF_CHANGE` when their subject matter was not an EPF/ETF change.

| Key | V5 label | V6 label |
|---|---|---|
| `official-pdf-2226-17` | `EPF_ETF_CHANGE` | `SECTOR_SPECIFIC` |
| `official-pdf-2235-59` | `EPF_ETF_CHANGE` | `SECTOR_SPECIFIC` |
| `official-pdf-2248-35` | `EPF_ETF_CHANGE` | `SECTOR_SPECIFIC` |
| `official-pdf-2412-08` | `EPF_ETF_CHANGE` | `SECTOR_SPECIFIC` |

All four are in the **train** split, so the test set is untouched between V5 and V6. Cross-split key leakage was verified as zero.

**Class distribution (V6):**

| Category | Train | Total |
|---|---:|---:|
| `SECTOR_SPECIFIC` | 478 | 679 |
| `IMPORT_EXPORT` | 78 | 112 |
| `TAX_RATE_CHANGE` | 58 | 82 |
| `LABOUR_LAW` | 52 | 75 |
| `PENALTY_ENFORCEMENT` | 46 | 66 |
| `PRODUCT_STANDARD` | 36 | 53 |
| `BUSINESS_REGISTRATION` | 25 | 36 |
| `EPF_ETF_CHANGE` | 4 | 7 |

`EPF_ETF_CHANGE` at 4 training rows and **1 test row** is the dataset's structural weakness: its per-class F1 is a one-sample estimate and cannot be treated as a stable measurement.

**Integrity:**

| File | SHA256 |
|---|---|
| `train.parquet` | `17AAA80E7BEE8DE2513705753C6C045043D6308BD1E4AE115ADB9387C3E1312C` |
| `val.parquet` | `D7E8115A6E7546281936BE5081AE7D5C54F4656189EC123A5550736ACD315BF4` |
| `test.parquet` | `83583F15E95FA28795DDDBA16D5BECEDCCD1649271ADFFC879466FD7614224F9` |
| dataset ZIP | `66EF4CF6FB187146641173BBB71628AD711C635FCEADE34CAB01AADDD99F35F0` |

**Local artifact map (verified 2026-08-01):**

```text
C:\Reasearch\xyz\datasets\m1_regulations_v6_1110_clean_fixedsplit\
C:\Reasearch\xyz\kaggle_bundle\m1_regulations_v6_1110_clean_fixedsplit.zip
C:\Reasearch\xyz\kaggle_bundle\m1_regulations_v5_1110_clean_fixedsplit.zip
C:\Reasearch\xyz\kaggle_bundle\m1_v6_epf_etf_corrections\m1_v6_epf_etf_corrections_bundle.zip
C:\Reasearch\xyz\kaggle_bundle\m1_v6_epf_etf_corrections\extracted\
```

| Archive | SHA256 |
|---|---|
| `m1_regulations_v6_1110_clean_fixedsplit.zip` | `66EF4CF6FB187146641173BBB71628AD711C635FCEADE34CAB01AADDD99F35F0` |
| `m1_regulations_v5_1110_clean_fixedsplit.zip` | `E1CA910E690F59C77F9859F57BE15069E48CBC6DF9C952BC8B28106C5A25FB29` |
| `m1_v6_epf_etf_corrections_bundle.zip` | `2C9169B54C99B21241354E378172DEF8BC8071AC8FF40AAA22ED9551BD386597` |

### Legacy L1 — `enigmatrix-ml\datasets\m1_regulations`

800 rows with a deterministic/key split of 560 / 120 / 120. This is the earliest retained ML split and is historical only. It is not comparable with V6 because `EPF_ETF_CHANGE` is absent from train and test, while the test split is dominated by `SECTOR_SPECIFIC` (115 of 120 rows).

### Legacy smoke — `enigmatrix-ml\datasets\m1_regulations_smoke`

32 rows with a 16 / 8 / 8 split. This is a CPU smoke-test fixture only. It is not a research dataset and must not be used for reported model quality.

### Legacy L2 — `enigmatrix-ml\datasets\m1_regulations_v2_1000`

1000 rows with a 700 / 150 / 150 split. Superseded. The split is not well balanced by category: `SECTOR_SPECIFIC` has 583 training rows but only 16 test rows, while some rarer categories appear mostly in validation/test. Keep only as an early experiment record.

### Legacy L2-stratified — `enigmatrix-ml\datasets\m1_regulations_v2_1000_stratified`

1000 rows with a 700 / 150 / 150 stratified split. Superseded by the larger 1128-row set, but useful as the first retained stratified classical-baseline comparison.

### Legacy L3 — `enigmatrix-ml\datasets\m1_regulations_v3_1128_stratified`

1128 rows with a 790 / 169 / 169 stratified split. This is the rare-domain baseline predecessor: it includes all eight categories, including 7 / 2 / 2 `EPF_ETF_CHANGE` rows. It is superseded by V6 for final model claims because V6 removes known artifacts, applies adjudicated corrections, and freezes the final reporting split.

All legacy folders are currently retained inside `enigmatrix-ml/datasets/`, still untracked in git (`?? datasets/`). They are the sets the module docstrings use as `--data` examples. Left in place deliberately; superseded for any result that will be reported.

Verified legacy split inventory:

| Folder | Split rows | Role now |
|---|---:|---|
| `enigmatrix-ml\datasets\m1_regulations` | 560 / 120 / 120 | V1 deterministic/key split; historical only |
| `enigmatrix-ml\datasets\m1_regulations_smoke` | 16 / 8 / 8 | CPU smoke-test fixture only |
| `enigmatrix-ml\datasets\m1_regulations_v2_1000` | 700 / 150 / 150 | superseded |
| `enigmatrix-ml\datasets\m1_regulations_v2_1000_stratified` | 700 / 150 / 150 | superseded |
| `enigmatrix-ml\datasets\m1_regulations_v3_1128_stratified` | 790 / 169 / 169 | rare-domain baseline predecessor; superseded by V6 for final model claims |

---

## 3. Models trained on these datasets

### Current/final model evidence

| Model                                     | Dataset | Val macro-F1 | Test macro-F1 | Verdict                             |
| ----------------------------------------- | ------- | -----------: | ------------: | ----------------------------------- |
| XLM-R LoRA, category-only, unweighted     | V5      |      ~0.0946 |       ~0.0936 | Collapsed to majority class         |
| XLM-R LoRA, balanced (seed 42, 16 ep)     | V5      |     0.596014 |      0.685348 | Rejected — 0 EPF predictions        |
| XLM-R LoRA, underfit-fix (seed 42, 20 ep) | V6      |     0.902693 |      0.743563 | Experimental only — failed the gate |
| **TF-IDF + balanced LinearSVC**           | **V6**  | **0.924476** |  **0.947220** | **Primary — frozen**                |
| TF-IDF + Logistic Regression              | V6      |            — |      0.882481 | Baseline reference                  |

### Historical legacy model records

These rows explain the path to the frozen model. They should not be mixed into final claims about production performance because the data versions, splits and label corrections differ from V6.

| Model | Dataset / run | Val macro-F1 | Test macro-F1 | Record source | Status |
|---|---|---:|---:|---|---|
| TF-IDF + Logistic Regression | V1 deterministic/key | — | 0.498039 | archived Kaggle `baselines_v1/baselines.json` | historical |
| TF-IDF + balanced LinearSVC | V1 deterministic/key | — | 0.616745 | archived Kaggle `baselines_v1/baselines.json` | historical |
| TF-IDF + Logistic Regression | V1 stratified archived run | — | 0.771087 | archived Kaggle `baselines_v1_stratified/baselines.json` | historical |
| TF-IDF + balanced LinearSVC | V1 stratified archived run | — | 0.789365 | archived Kaggle `baselines_v1_stratified/baselines.json` | historical |
| TF-IDF + Logistic Regression | V2 1000 | — | 0.294196 | local `baselines_v2_1000/baselines.json` | superseded |
| TF-IDF + balanced LinearSVC | V2 1000 | — | 0.210263 | local `baselines_v2_1000/baselines.json` | superseded |
| TF-IDF + Logistic Regression | V2 1000 stratified | — | 0.698545 | local `baselines_v2_1000_stratified/baselines.json` | superseded |
| TF-IDF + balanced LinearSVC | V2 1000 stratified | — | 0.808523 | local `baselines_v2_1000_stratified/baselines.json` | superseded |
| TF-IDF + Logistic Regression | V3 1128 stratified | — | 0.862652 | local `baselines_v3_1128_stratified/baselines.json` | rare-domain predecessor |
| TF-IDF + balanced LinearSVC | V3 1128 stratified | — | 0.908012 | local `baselines_v3_1128_stratified/baselines.json` | rare-domain predecessor |

Archived V1 GPU records also exist under `storage/models/m1/kaggle_v1/kaggle/working/storage/models/m1/`: `xlmr_lora_v1_seed42_diag` (val 0.154762, test 0.155556), `xlmr_lora_v1_fixed_seed42` (val 0.266328, test 0.487084), and `xlmr_lora_v1_catonly_seed42_e16` (val 0.403285, test 0.641471). All failed the gate and are retained for chronology only.

There is also a separate local `baselines_v1/baselines.json` rerun with LogReg 0.743363 and LinearSVC 0.872826. Do not cite it as the archived Kaggle V1 result unless the rerun command and local dataset state are included.

### Why the transformer lost

The V6 underfit-fix run reached **0.969340 training** macro-F1 — the optimization fixes (separate LoRA/head learning rates, √-balanced clipped loss weights, α=0.5 minority sampling, gradient clipping) demonstrably solved the underfitting. But test macro-F1 fell to 0.743563 while validation held at 0.902693. On the temporal test split the classical model beat it by **+0.204 macro-F1**, was right on 10 records the transformer got wrong, and correctly classified the single EPF/ETF test record the transformer missed (transformer put 0.803 confidence on `LABOUR_LAW`, with `EPF_ETF_CHANGE` second at 0.197).

Read carefully, this is a generalization result, not a "classical beats neural" result: 777 training rows across 8 classes with a 4-row minority is well inside the regime where a lexical model with strong regularization is the better estimator.

### Frozen primary artifact

```text
C:\Reasearch\xyz\models\m1\linearsvc_v6_primary\linearsvc_pipeline.joblib
SHA256  1D7F84754421A881EE1B5FA0F008A0CC3DB4E24F52CE6D97CE155CB4D1923CFA
Bundle  2F80BEFE494F1275DCB14FCB5352902A8BF98C1CC3FA86F919D53B7958C5F11B
```

Configuration: `TfidfVectorizer(max_features=50000, ngram_range=(1,2), min_df=2)` → `LinearSVC(class_weight="balanced")`. Test accuracy 0.958084, 160/167 correct. The score reproduced **exactly** after serialization, download to Windows and reload — `0.9472199858964565` on both Kaggle and local.

Per-class test F1: `LABOUR_LAW` 1.000 · `EPF_ETF_CHANGE` 1.000 (n=1) · `SECTOR_SPECIFIC` 0.970 · `IMPORT_EXPORT` 0.970 · `PRODUCT_STANDARD` 0.941 · `BUSINESS_REGISTRATION` 0.923 · `TAX_RATE_CHANGE` 0.917 · `PENALTY_ENFORCEMENT` 0.857.

---

## 4. The confidence contract

`LinearSVC.decision_function` returns signed margins, **not** calibrated probabilities. The inference adapter therefore returns:

```json
{ "confidence": null, "confidence_type": "not_available_uncalibrated_linearsvc" }
```

and exposes `decision_score`, `decision_margin`, `second_category`, `second_decision_score`, `class_scores` instead. These rank well and are fine for review-queue prioritisation. **They must never be rendered as percentages in the UI.** If calibrated probabilities are needed, train and evaluate a calibration layer separately — do not transform margins.

The frozen primary model also has **no sector head**; it returns `"sectors": []` and `"sector_probs": {}`. Sector prediction still belongs to the older ONNX dual-head `GazetteInference`.

---

## 5. Standing constraints

1. **The V6 test split is spent for tuning.** It is final-evaluation only. Any further model selection needs a fresh split or nested CV.
2. **`EPF_ETF_CHANGE` needs real data, not resampling.** 4 train / 1 test rows. The next annotation round should target genuine EPF/ETF regulations before any per-class claim is made about this category.
3. **Do not rename or move `datasets/` or `models/`.** Their paths are recorded inside `model_registry.json`, `SHA256SUMS.json`, `local_windows_verification.json` and the frozen record.
4. **Re-derive, don't hand-edit.** Every table here is regenerable from the record generator; if a number changes, change the source and regenerate.

---

## 6. Kaggle and local recovery commands

Use this section when the final report needs the exact dataset/model metric evidence from Kaggle or the local downloaded bundle.

### Kaggle input locations

```text
Original Kaggle project dataset:
/kaggle/input/datasets/ifhammohamed1/m1-training-v1/enigmatrix-ml

Legacy V1 dataset inside original Kaggle project dataset:
/kaggle/input/datasets/ifhammohamed1/m1-training-v1/enigmatrix-ml/datasets/m1_regulations

V6 Kaggle input dataset:
/kaggle/input/datasets/ifhammohamed1/m1-regulations-v6-1110-clean-fixed-split/m1_regulations_v6_1110_clean_fixedsplit

Kaggle working model artifact:
/kaggle/working/storage/models/m1/linearsvc_v6_primary
```

Current Kaggle inputs verified from the notebook expose V1, V5 and V6. V2, V2-stratified and V3 will print as missing unless those legacy folders are attached/uploaded as a Kaggle dataset.

### Discover attached legacy datasets in Kaggle

Run this first. It finds the dataset folders wherever Kaggle mounted them and prints exact split counts, class distributions and Parquet hashes.

```python
from pathlib import Path
import hashlib
import json
import pandas as pd

SPLITS = ("train", "val", "test")
LEGACY_NAMES = [
    "m1_regulations",
    "m1_regulations_smoke",
    "m1_regulations_v2_1000",
    "m1_regulations_v2_1000_stratified",
    "m1_regulations_v3_1128_stratified",
]

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()

def find_dataset_dir(name: str) -> Path | None:
    for path in Path("/kaggle/input").rglob(name):
        if path.is_dir() and all((path / f"{split}.parquet").exists() for split in SPLITS):
            return path
    return None

report = {}
for name in LEGACY_NAMES:
    base = find_dataset_dir(name)
    if base is None:
        report[name] = {"status": "missing_from_attached_kaggle_inputs"}
        continue

    report[name] = {"status": "found", "path": str(base), "splits": {}}
    for split in SPLITS:
        parquet = base / f"{split}.parquet"
        df = pd.read_parquet(parquet)
        report[name]["splits"][split] = {
            "rows": int(len(df)),
            "sha256": sha256_file(parquet),
            "category_counts": {
                str(k): int(v)
                for k, v in df["category"].value_counts().sort_index().items()
            },
        }

print(json.dumps(report, indent=2))
```

### Rebuild legacy classical baseline scores in Kaggle

Run this only after the discovery cell. It copies the codebase into `/kaggle/working`, then runs the project baseline command against every attached legacy dataset.

```python
from pathlib import Path
import json
import shutil
import subprocess
import sys

SPLITS = ("train", "val", "test")
LEGACY_NAMES = [
    "m1_regulations",
    "m1_regulations_smoke",
    "m1_regulations_v2_1000",
    "m1_regulations_v2_1000_stratified",
    "m1_regulations_v3_1128_stratified",
]

def find_dataset_dir(name: str) -> Path | None:
    for path in Path("/kaggle/input").rglob(name):
        if path.is_dir() and all((path / f"{split}.parquet").exists() for split in SPLITS):
            return path
    return None

CODE_INPUT = Path("/kaggle/input/datasets/ifhammohamed1/m1-training-v1/enigmatrix-ml")
CODE_WORK = Path("/kaggle/working/enigmatrix-ml")

if CODE_WORK.exists():
    shutil.rmtree(CODE_WORK)
shutil.copytree(CODE_INPUT, CODE_WORK)

subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q", "pandas", "pyarrow", "scikit-learn"],
    check=True,
)

baseline_results = {}
for name in LEGACY_NAMES:
    base = find_dataset_dir(name)
    if base is None or name == "m1_regulations_smoke":
        continue

    out = Path("/kaggle/working/storage/models/m1") / f"baselines_{name}"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "m1.model.baselines",
            "--data",
            str(base),
            "--report",
            str(out),
        ],
        cwd=CODE_WORK,
        check=True,
    )
    baseline_results[name] = json.loads((out / "baselines.json").read_text())

print(json.dumps(baseline_results, indent=2))
```

Expected locally verified legacy score records:

| Dataset | LogReg test macro-F1 | LinearSVC test macro-F1 |
|---|---:|---:|
| V1 deterministic/key, archived Kaggle | 0.498039 | 0.616745 |
| V1 stratified archived run | 0.771087 | 0.789365 |
| V2 1000 | 0.294196 | 0.210263 |
| V2 1000 stratified | 0.698545 | 0.808523 |
| V3 1128 stratified | 0.862652 | 0.908012 |

### Find any saved metric JSON files in Kaggle

Use this instead of opening one hard-coded path. It avoids `FileNotFoundError` when the model artifact is not present in the current Kaggle session.

```python
from pathlib import Path
import json

patterns = ["baselines.json", "metrics.json", "model_registry.json", "validation_summary.json", "test_summary.json"]
roots = [Path("/kaggle/working"), Path("/kaggle/input")]

found = []
for root in roots:
    for pattern in patterns:
        found.extend(root.rglob(pattern))

print("FOUND FILES:", len(found))
for path in sorted(set(found)):
    print("\n" + "=" * 100)
    print(path)
    print("=" * 100)
    try:
        print(json.dumps(json.loads(path.read_text()), indent=2))
    except Exception as exc:
        print(f"Could not parse JSON: {exc}")
```

### Print the frozen model metrics in Kaggle

```bash
python - <<'PY'
import json
from pathlib import Path

model_dir = Path("/kaggle/working/storage/models/m1/linearsvc_v6_primary")
for name in ["model_registry.json", "validation_summary.json", "test_summary.json"]:
    path = model_dir / name
    print(f"\n== {path} ==")
    print(json.dumps(json.loads(path.read_text()), indent=2))
PY
```

### Print the V6 dataset split distribution in Kaggle

```bash
python - <<'PY'
from pathlib import Path
import pandas as pd

base = Path("/kaggle/working/enigmatrix-ml/datasets/m1_regulations_v6_1110_clean_fixedsplit")
if not base.exists():
    base = Path("/kaggle/input/datasets/ifhammohamed1/m1-regulations-v6-1110-clean-fixed-split/m1_regulations_v6_1110_clean_fixedsplit")

for split in ["train", "val", "test"]:
    df = pd.read_parquet(base / f"{split}.parquet")
    print(f"\n{split}: {len(df)} rows")
    print(df["category"].value_counts().sort_index().to_string())
PY
```

### Re-score the frozen LinearSVC locally after downloading from Kaggle

```powershell
cd C:\Reasearch\xyz\enigmatrix-ml
uv run python - <<'PY'
from pathlib import Path
import joblib
import pandas as pd
from sklearn.metrics import classification_report, f1_score, accuracy_score

model_path = Path(r"C:\Reasearch\xyz\models\m1\linearsvc_v6_primary\linearsvc_pipeline.joblib")
test_path = Path(r"C:\Reasearch\xyz\datasets\m1_regulations_v6_1110_clean_fixedsplit\test.parquet")

model = joblib.load(model_path)
df = pd.read_parquet(test_path)
pred = model.predict(df["text"].fillna("").astype(str))
y = df["category"].astype(str)

print("rows", len(df))
print("macro_f1", f1_score(y, pred, average="macro"))
print("accuracy", accuracy_score(y, pred))
print(classification_report(y, pred, digits=6))
PY
```

Expected local result: macro-F1 `0.9472199858964565`, accuracy `0.9580838323353293`, 160/167 correct.

### Kaggle CLI recovery commands

Run these on Windows only if Kaggle API credentials are configured.

```powershell
kaggle datasets download ifhammohamed1/m1-regulations-v6-1110-clean-fixed-split `
  -p C:\Reasearch\xyz\kaggle_bundle `
  --unzip

kaggle datasets download ifhammohamed1/m1-training-v1 `
  -p C:\Reasearch\xyz\kaggle_bundle\m1-training-v1 `
  --unzip
```

If a future correction bundle is uploaded as its own Kaggle dataset, download it the same way and verify its SHA256 before deriving a new dataset version.

---

## 7. Cross-references

- **Training method and metrics:** [[06_M1_Training_Evaluation]]
- **Architecture and sampling:** [[05_M1_Model_Architecture]]
- **Annotation, taxonomy and IAA protocol:** [[09_M1_Annotation_Guidelines]]
- **Physical layout of `datasets/` and `models/`:** [[17_M1_Repo_Structure_Map]]
- **Full chronology with every epoch and error:** `documentation/m1/records/ENIGMATRIX_M1_COMPLETE_END_TO_END_RECORD_2026-07-31_2313_IST.md`
