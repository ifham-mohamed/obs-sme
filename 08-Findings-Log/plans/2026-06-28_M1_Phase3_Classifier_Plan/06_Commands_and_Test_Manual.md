---
tags: [m1, phase-3, runbook, commands, manual, tests]
date: 2026-06-28
status: reference — copy-paste runbook for all 5 slices
---

# Phase 3 — Commands & Test Manual (copy-paste runbook)

> Every command to implement and test each slice, in order. Paths assume the vault root `C:\sme` and the code repo `C:\Reasearch\xyz`. On macOS/Linux the repo path differs — adjust. Run code commands from inside the relevant submodule.

## 0. Environment (once)
```bash
# Code repo (uv workspace: backend + ml)
cd C:\Reasearch\xyz
uv sync                                  # resolves enigmatrix-backend + enigmatrix-ml
# ML extras for training (torch is large — use a GPU box / Colab if possible)
cd enigmatrix-ml && uv sync --extra ml   # torch transformers peft datasets scikit-learn mlflow onnxruntime
# System packages for extraction (if re-extracting text): tesseract (sin+tam) + poppler
#   macOS:  brew install tesseract tesseract-lang poppler
#   Ubuntu: sudo apt-get install tesseract-ocr tesseract-ocr-sin tesseract-ocr-tam poppler-utils
```

## 1. Slice 1 — labeling prep ✅ (already run; re-run if needed)
```bash
cd C:\sme
python "08-Findings-Log/plans/2026-06-28_M1_Phase3_Classifier_Plan/scripts/prepare_labeling_dataset.py" \
    --csv-dir "03-Data-Sources/m1/raw/csv" --out-dir "03-Data-Sources/m1/raw/labeling" \
    --batch-size 250 --seed 42
# verify
python - <<'PY'
import json; d=json.load(open("03-Data-Sources/m1/raw/labeling/label_studio_import.json"))
assert len(d)==250 and all(t["predictions"] for t in d); print("OK 250 pre-annotated tasks")
PY
```
**Optional — enrich tasks with fresh full text from the PDFs** (slow; needs pdfplumber + the PDFs):
```bash
python - <<'PY'
import csv, glob, os, pdfplumber
src="03-Data-Sources/m1/raw"
for r in list(csv.DictReader(open(f"{src}/labeling/batch_01.csv",encoding="utf-8")))[:25]:
    p=os.path.join(src, (r["raw_pdf_path"] or "").replace("m1/raw/",""))
    if os.path.exists(p):
        with pdfplumber.open(p) as pdf:
            print(r["gazette_number"], "->", len((pdf.pages[0].extract_text() or "")), "chars p1")
PY
```

## 2. Slice 2 — annotation + gold set
```bash
# start Label Studio
pip install label-studio && label-start          # http://localhost:8080
# (paste the labeling config from 02_Slice2; import labeling/label_studio_import.json)

# Cohen's kappa on a dual-annotated export (annotator A vs B category columns)
pip install scikit-learn pandas
python - <<'PY'
import pandas as pd; from sklearn.metrics import cohen_kappa_score
df=pd.read_csv("03-Data-Sources/m1/raw/labeling/dual_annotated.csv")   # cols: gazette_number, cat_A, cat_B
k=cohen_kappa_score(df.cat_A, df.cat_B)
print(f"Cohen's kappa = {k:.3f}  ({'PASS' if k>=0.75 else 'BELOW 0.75 — refine guidelines'})")
PY

# temporal split once gold_standard.csv (>=800 rows) is exported
cd C:\Reasearch\xyz\enigmatrix-ml
uv run python -m m1.model.data --in datasets/m1_regulations/gold_standard.csv \
     --out datasets/m1_regulations/ --ratios 0.70 0.15 0.15 --by gazette_published_date
```

## 3. Slice 3 — train
```bash
cd C:\Reasearch\xyz\enigmatrix-ml
uv run pytest tests/m1/model -v                  # shape/config tests (no GPU)
uv run python -m m1.model.train_xlmr --data datasets/m1_regulations \
     --seeds 42 1 2 --base xlm-roberta-base --lora-r 16 --epochs 8 --fp16 \
     --out storage/models/m1/xlmr_lora_v1
# check the gate
python - <<'PY'
import json; m=json.load(open("storage/models/m1/xlmr_lora_v1/model_registry.json"))
print("macro-F1 mean:", m["macro_f1_mean"], "PASS" if m["macro_f1_mean"]>=0.92 else "BELOW 0.92")
PY
```

## 4. Slice 4 — eval + baselines
```bash
cd C:\Reasearch\xyz\enigmatrix-ml
uv run python -m m1.model.eval --model storage/models/m1/xlmr_lora_v1 \
     --test datasets/m1_regulations/test.parquet --report storage/models/m1/eval_v1
uv run python -m m1.model.baselines --data datasets/m1_regulations --report storage/models/m1/baselines_v1
cat storage/models/m1/eval_v1/metrics.json     # confirm per-language + slice gates
```

## 5. Slice 5 — export + wire
```bash
cd C:\Reasearch\xyz\enigmatrix-ml
uv run python -m m1.model.export_onnx --model storage/models/m1/xlmr_lora_v1 \
     --out storage/models/m1/onnx/v1 --int8
cd ..\enigmatrix-backend
uv run alembic revision -m "m1_classified_status_and_confidence" && uv run alembic upgrade head
uv run pytest app/tests/integration/test_celery_classify_gazette.py -v
# end-to-end smoke (dev): crawl one day, watch a row reach status='classified'
uv run celery -A app.celery_config worker -l info &      # terminal A
uv run celery -A app.celery_config beat   -l info &      # terminal B (optional)
# trigger via /admin/m1/pipeline extraction, then:
uv run python -c "import asyncio; from app.scripts.peek import last_status; print(asyncio.run(last_status()))"
```

## Rollback (any slice)
```bash
# data artifacts are additive — delete to revert:
rm -rf "C:/sme/03-Data-Sources/m1/raw/labeling"           # Slice 1
# backend migration:
cd C:\Reasearch\xyz\enigmatrix-backend && uv run alembic downgrade -1   # Slice 5
# model artifacts:
rm -rf C:\Reasearch\xyz\enigmatrix-ml\storage\models\m1\xlmr_lora_v1
```

## Pre-flight hygiene (do alongside; from the status report P0)
```bash
# fix the /admin/m1/pipeline/recent 503 (F-184) before demoing
# reconcile the F1 gate: BUILD_11 says >=0.80, RQ1 says >=0.92 — pick 0.92 and grep-replace
grep -rn "0.80\|f1_macro >= 0.8" C:\Reasearch\xyz\enigmatrix-ml\m1 C:\sme\04-Technology-Stack\ml\BUILD
# refresh the knowledge graph after code lands
cd C:\Reasearch\xyz && graphify update .
```
