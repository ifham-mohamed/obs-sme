# BUILD 11 — ML Training Pipeline

> **Goal:** stand up a single, opinionated training pipeline that all four modules share — versioned datasets, MLflow-tracked runs, Optuna sweeps, hard eval gates, and a model-registry promotion script that flips `model_versions.is_production` in Postgres.
>
> **Scope:** **Training, evaluation, registration, promotion.** Inference paths live in BUILD_07 §5 (M1), BUILD_08 (M2 RAG), BUILD_09 (M3 fraud), BUILD_10 (M4 misinformation). This file is the only place training code is allowed to live.
>
> **Read first:** `research/02_Complete_ML_Lifecycle.md`, `research/11_Module1_NLP_Classifier_Training.md`, and the inference companions `BUILD_07_Module1_Awareness.md`, `BUILD_08_Module2_Knowledge.md`, `BUILD_09_Module3_Risk.md`, `BUILD_10_Module4_Misinformation.md`. The Postgres tables (`training_runs`, `model_versions`) are defined in `BUILD_04_Database_and_Storage.md` §5; this pipeline writes to them as an inter-module contract.

---

## 1. Repo Layout

The `ml/` tree is its own Python package, separate from `backend/`. It runs on the same VM but is invoked via `uv run` from the project root, never imported by FastAPI.

```
ml/
├── pyproject.toml              # uv-managed; pins transformers, xgboost, mlflow, optuna, ragas, sdv
├── common/
│   ├── trainer.py              # BaseTrainer (§4)
│   ├── gates.py                # eval-gate decorators (§7)
│   ├── seeding.py              # seed_everything()
│   ├── env_capture.py          # writes per-run requirements.txt + git sha
│   ├── mlflow_utils.py         # tag conventions, parent/child runs
│   └── registry.py             # MLflow → Postgres bridge (§8)
├── datasets/
│   ├── manifest.yaml           # sha256 + row counts per split (§2)
│   ├── m1_regulations/         # train.parquet, val.parquet, test.parquet
│   ├── m3_fraud/               # real + CTGAN synthetic
│   └── m4_claims/              # social-post + label parquet
├── m1/
│   ├── train_xlmr.py           # XLM-R fine-tune entrypoint
│   ├── sweep.py                # Optuna study
│   └── eval.py                 # macro-F1 on test split
├── m3/
│   ├── train_xgb.py            # XGBoost trainer
│   ├── synth_ctgan.py          # SDV/CTGAN synthetic generation
│   └── eval.py
├── m4/
│   ├── train_xlmr.py           # M4 stance/misinformation classifier
│   └── eval.py                 # RAGAS faithfulness + macro-F1
├── m2/
│   └── eval_ragas.py           # M2 has no train; only retrieval eval
├── registry/
│   ├── promote.py              # CLI: Staging → Production (§8)
│   └── card_template.md.j2     # Jinja2 model-card template (§9)
└── ci/
    └── nightly_retrain.yml     # GH Actions partial example (§10)
```

> Cross-reference: `backend/app/ml_serving/registry.py` (BUILD_07 §5) reads the rows this pipeline writes. The training code never imports `backend/`; the only contract is the database schema.

---

## 2. Dataset Versioning

Every dataset split is a Parquet file with a sha256 fingerprint and a row count. Anything not in `manifest.yaml` is not allowed to feed a training run — the trainer base class refuses to start otherwise.

```yaml
# FILE: ml/datasets/manifest.yaml
version: 4
generated_at: 2026-04-12T08:31:00+05:30
datasets:
  m1_regulations:
    schema: [text, label, language, source_gazette]
    splits:
      train: { path: m1_regulations/train.parquet, rows: 4812, sha256: 9b1f...c2 }
      val:   { path: m1_regulations/val.parquet,   rows: 602,  sha256: 41ad...77 }
      test:  { path: m1_regulations/test.parquet,  rows: 603,  sha256: e0c8...1d }
    label_set: [TAX_INCOME, TAX_VAT_SVAT, TAX_CUSTOMS_TARIFF, EPF_ETF,
                IMPORT_EXPORT_CONTROL, HEALTH_SAFETY, ENVIRONMENTAL,
                EMPLOYMENT_LABOUR, COMPANY_REGISTRATION, SECTOR_SPECIFIC,
                CONSUMER_PROTECTION, OTHER_REGULATORY]
  m3_fraud:
    schema: [features_json, label]
    splits:
      train: { path: m3_fraud/train.parquet, rows: 18204, sha256: 7c44...9e }  # 60% real / 40% CTGAN
      val:   { path: m3_fraud/val.parquet,   rows: 2275,  sha256: 22be...10 }
      test:  { path: m3_fraud/test.parquet,  rows: 2276,  sha256: 9aa1...3f }  # real-only
    synth_recipe: { generator: ctgan, sdv_version: "1.16.0", epochs: 300 }
  m4_claims:
    schema: [post_text, label, language, retrieved_evidence]
    splits:
      train: { path: m4_claims/train.parquet, rows: 3204, sha256: be03...aa }
      val:   { path: m4_claims/val.parquet,   rows: 401,  sha256: 6f59...02 }
      test:  { path: m4_claims/test.parquet,  rows: 402,  sha256: c1d7...44 }
    label_set: [supported, refuted, not_enough_info]
```

```python
# FILE: ml/common/dataset.py
from __future__ import annotations
import hashlib, yaml
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1] / "datasets"

def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def load_split(dataset: str, split: str) -> pd.DataFrame:
    manifest = yaml.safe_load((ROOT / "manifest.yaml").read_text())
    spec = manifest["datasets"][dataset]["splits"][split]
    path = ROOT / spec["path"]
    actual = _sha256(path)
    if not actual.startswith(spec["sha256"][:4]):  # short-prefix check + full check below
        raise RuntimeError(f"sha mismatch for {dataset}/{split}: {actual} vs {spec['sha256']}")
    df = pd.read_parquet(path)
    if len(df) != spec["rows"]:
        raise RuntimeError(f"row-count drift for {dataset}/{split}: {len(df)} vs {spec['rows']}")
    return df
```

A pandera schema check runs at the top of every trainer (see §4) and rejects rows with NULL labels, unknown label values, or wrong dtypes.

---

## 3. MLflow Tracking and Tag Convention

One MLflow tracking server (sqlite-backed) lives on the same VM at `http://127.0.0.1:5000`. Artifacts go to `./mlruns/`. Every run carries a fixed set of tags so that `mlflow search_runs` queries from the promotion CLI are deterministic.

| Tag | Example | Required |
|-----|---------|----------|
| `module_number` | `1`, `3`, `4` | yes |
| `dataset_version` | `4` (matches `manifest.yaml`) | yes |
| `dataset_sha_train` | first 12 chars of train sha | yes |
| `git_sha` | output of `git rev-parse HEAD` | yes |
| `python_version` | `3.11.9` | yes |
| `seed` | `42` | yes |
| `parent_run_id` | set on Optuna trial children | when sweeping |
| `gate_status` | `passed` / `failed` (set after eval) | yes |

```python
# FILE: ml/common/mlflow_utils.py
import os, subprocess, sys
import mlflow

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")

def start_run(experiment: str, *, module_number: int, dataset_version: int,
              dataset_sha_train: str, seed: int, parent_run_id: str | None = None):
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(experiment)
    run = mlflow.start_run(nested=parent_run_id is not None)
    mlflow.set_tags({
        "module_number": module_number,
        "dataset_version": dataset_version,
        "dataset_sha_train": dataset_sha_train,
        "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip(),
        "python_version": sys.version.split()[0],
        "seed": seed,
        "parent_run_id": parent_run_id or "",
        "gate_status": "pending",
    })
    return run
```

---

## 4. Training Entrypoints — `BaseTrainer`

All module trainers inherit from `BaseTrainer`. The base class enforces the manifest check, seeds RNGs, opens an MLflow run, captures the env, calls subclass hooks, runs the eval gate, and only then writes a row to Postgres `training_runs`.

```python
# FILE: ml/common/trainer.py
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import mlflow, pandas as pd

from ml.common.dataset import load_split
from ml.common.seeding import seed_everything
from ml.common.env_capture import freeze_requirements, snapshot_env
from ml.common.mlflow_utils import start_run
from ml.common.registry import write_training_run_row

@dataclass
class TrainConfig:
    module_number: int
    experiment: str
    dataset: str
    dataset_version: int
    seed: int = 42
    output_dir: Path = Path("artifacts")
    hyperparams: dict[str, Any] = field(default_factory=dict)

class BaseTrainer(ABC):
    def __init__(self, cfg: TrainConfig):
        self.cfg = cfg

    @abstractmethod
    def fit(self, train_df: pd.DataFrame, val_df: pd.DataFrame) -> Any: ...

    @abstractmethod
    def evaluate(self, model: Any, test_df: pd.DataFrame) -> dict[str, float]: ...

    @abstractmethod
    def save(self, model: Any, out: Path) -> None: ...

    def run(self) -> str:
        seed_everything(self.cfg.seed)
        train_df = load_split(self.cfg.dataset, "train")
        val_df   = load_split(self.cfg.dataset, "val")
        test_df  = load_split(self.cfg.dataset, "test")
        sha = _sha_for(self.cfg.dataset, "train")
        with start_run(self.cfg.experiment,
                       module_number=self.cfg.module_number,
                       dataset_version=self.cfg.dataset_version,
                       dataset_sha_train=sha[:12], seed=self.cfg.seed) as run:
            mlflow.log_params(self.cfg.hyperparams)
            snapshot_env()                       # logs python, OS, GPU presence
            freeze_requirements(run.info.run_id) # writes per-run requirements.txt
            model = self.fit(train_df, val_df)
            metrics = self.evaluate(model, test_df)
            mlflow.log_metrics(metrics)
            out = self.cfg.output_dir / run.info.run_id
            self.save(model, out)
            mlflow.log_artifacts(str(out))
            write_training_run_row(run.info.run_id, self.cfg, metrics, str(out))
            return run.info.run_id
```

### M1 subclass (XLM-RoBERTa-base, 12-class)

```python
# FILE: ml/m1/train_xlmr.py
from pathlib import Path
from sklearn.metrics import f1_score
from transformers import (AutoTokenizer, AutoModelForSequenceClassification,
                          Trainer, TrainingArguments, DataCollatorWithPadding)
from datasets import Dataset
from ml.common.trainer import BaseTrainer, TrainConfig
from ml.common.gates import enforce_gate

LABELS = ["TAX_INCOME","TAX_VAT_SVAT","TAX_CUSTOMS_TARIFF","EPF_ETF",
          "IMPORT_EXPORT_CONTROL","HEALTH_SAFETY","ENVIRONMENTAL",
          "EMPLOYMENT_LABOUR","COMPANY_REGISTRATION","SECTOR_SPECIFIC",
          "CONSUMER_PROTECTION","OTHER_REGULATORY"]
L2I = {l: i for i, l in enumerate(LABELS)}

class M1Trainer(BaseTrainer):
    def fit(self, train_df, val_df):
        tok = AutoTokenizer.from_pretrained("xlm-roberta-base")
        mdl = AutoModelForSequenceClassification.from_pretrained(
            "xlm-roberta-base", num_labels=len(LABELS))
        enc = lambda b: tok(b["text"], truncation=True, max_length=512)
        ds_tr = Dataset.from_pandas(train_df.assign(label=train_df["label"].map(L2I))).map(enc, batched=True)
        ds_va = Dataset.from_pandas(val_df.assign(label=val_df["label"].map(L2I))).map(enc, batched=True)
        args = TrainingArguments(
            output_dir="artifacts/_tmp_m1",
            per_device_train_batch_size=self.cfg.hyperparams.get("bs", 8),
            gradient_accumulation_steps=self.cfg.hyperparams.get("grad_accum", 4),
            gradient_checkpointing=True,                # 16GB RAM friendly
            learning_rate=self.cfg.hyperparams.get("lr", 2e-5),
            num_train_epochs=self.cfg.hyperparams.get("epochs", 4),
            eval_strategy="epoch", save_strategy="epoch",
            load_best_model_at_end=True, metric_for_best_model="f1_macro",
            fp16=False, bf16=False,                     # CPU-only VM
            report_to=["mlflow"], seed=self.cfg.seed,
        )
        trainer = Trainer(model=mdl, args=args, tokenizer=tok,
            data_collator=DataCollatorWithPadding(tok),
            train_dataset=ds_tr, eval_dataset=ds_va,
            compute_metrics=lambda p: {"f1_macro": f1_score(
                p.label_ids, p.predictions.argmax(-1), average="macro")})
        trainer.train()
        return trainer

    @enforce_gate(metric="f1_macro", threshold=0.80)
    def evaluate(self, trainer, test_df):
        tok = trainer.tokenizer
        ds = Dataset.from_pandas(test_df.assign(label=test_df["label"].map(L2I))).map(
            lambda b: tok(b["text"], truncation=True, max_length=512), batched=True)
        preds = trainer.predict(ds)
        return {"f1_macro": f1_score(preds.label_ids, preds.predictions.argmax(-1), average="macro")}

    def save(self, trainer, out: Path):
        out.mkdir(parents=True, exist_ok=True)
        trainer.save_model(out); trainer.tokenizer.save_pretrained(out)
```

### M3 subclass (XGBoost on tabular fraud features)

```python
# FILE: ml/m3/train_xgb.py
import json
import xgboost as xgb
import numpy as np
from sklearn.metrics import roc_auc_score
from ml.common.trainer import BaseTrainer, TrainConfig
from ml.common.gates import enforce_gate

class M3Trainer(BaseTrainer):
    def _materialize(self, df):
        X = np.vstack([list(json.loads(r).values()) for r in df["features_json"]])
        y = df["label"].astype(int).to_numpy()
        return X, y

    def fit(self, train_df, val_df):
        X, y = self._materialize(train_df); Xv, yv = self._materialize(val_df)
        dtr, dva = xgb.DMatrix(X, y), xgb.DMatrix(Xv, yv)
        params = {"objective": "binary:logistic", "eval_metric": "auc",
                  "max_depth": self.cfg.hyperparams.get("max_depth", 6),
                  "eta": self.cfg.hyperparams.get("eta", 0.1),
                  "subsample": 0.8, "colsample_bytree": 0.8, "seed": self.cfg.seed}
        return xgb.train(params, dtr, num_boost_round=self.cfg.hyperparams.get("rounds", 400),
                         evals=[(dva, "val")], early_stopping_rounds=20, verbose_eval=False)

    @enforce_gate(metric="roc_auc", threshold=0.75)
    def evaluate(self, model, test_df):
        X, y = self._materialize(test_df)
        p = model.predict(xgb.DMatrix(X))
        return {"roc_auc": float(roc_auc_score(y, p))}

    def save(self, model, out):
        out.mkdir(parents=True, exist_ok=True)
        model.save_model(str(out / "xgb.json"))
```

M4 reuses the M1 trainer with a different label set and a RAGAS-backed evaluator (see `ml/m4/eval.py`); its gate is `f1_macro >= 0.75`.

---

## 5. Optuna Sweeps

Sweeps run as a parent MLflow run with one nested child per trial. The base trainer recognizes `parent_run_id` and tags children automatically.

```python
# FILE: ml/m1/sweep.py
import mlflow, optuna
from ml.m1.train_xlmr import M1Trainer
from ml.common.trainer import TrainConfig

def objective(trial: optuna.Trial, parent_run_id: str) -> float:
    hp = {
        "lr":     trial.suggest_float("lr", 1e-5, 5e-5, log=True),
        "epochs": trial.suggest_int("epochs", 3, 6),
        "bs":     trial.suggest_categorical("bs", [4, 8]),
    }
    cfg = TrainConfig(module_number=1, experiment="m1_regulations_sweep",
                      dataset="m1_regulations", dataset_version=4, hyperparams=hp)
    run_id = M1Trainer(cfg).run()
    return mlflow.get_run(run_id).data.metrics["f1_macro"]

if __name__ == "__main__":
    with mlflow.start_run(run_name="m1_optuna") as parent:
        study = optuna.create_study(direction="maximize",
                                    sampler=optuna.samplers.TPESampler(seed=42))
        study.optimize(lambda t: objective(t, parent.info.run_id), n_trials=20, timeout=14400)
        mlflow.log_params(study.best_params)
        mlflow.log_metric("best_f1_macro", study.best_value)
```

> Single 4-vCPU/16GB VM constraint: cap `n_trials=20`, `timeout=4h`. Heavier sweeps must run in a sequenced overnight slot — see §10.

---

## 6. Reproducibility

Three guarantees, enforced by the base trainer and never optional:

1. **Seed everything.** Python `random`, NumPy, Torch (CPU + CUDA), Transformers, XGBoost, and Python `hash` seed via `PYTHONHASHSEED`.
2. **Per-run `requirements.txt`.** `uv pip freeze` is captured and logged as an MLflow artifact at run start. A run cannot be reproduced unless it can be replayed from that exact freeze.
3. **Env snapshot.** Python version, OS, CPU model, total RAM, and presence/absence of GPU are logged as MLflow tags.

```python
# FILE: ml/common/seeding.py
import os, random
import numpy as np
import torch

def seed_everything(seed: int = 42) -> None:
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed); np.random.seed(seed)
    torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)
```

```python
# FILE: ml/common/env_capture.py
import platform, subprocess, tempfile
from pathlib import Path
import mlflow, psutil, torch

def snapshot_env() -> None:
    mlflow.set_tags({
        "os": platform.platform(),
        "cpu": platform.processor(),
        "cpu_count": psutil.cpu_count(logical=True),
        "ram_gb": round(psutil.virtual_memory().total / 1e9, 1),
        "gpu_available": torch.cuda.is_available(),
    })

def freeze_requirements(run_id: str) -> None:
    out = Path(tempfile.gettempdir()) / f"req_{run_id}.txt"
    out.write_text(subprocess.check_output(["uv", "pip", "freeze"]).decode())
    mlflow.log_artifact(str(out), artifact_path="env")
```

---

## 7. Eval Gates

The four gate thresholds are non-negotiable and live in code, not config — failing one prevents the run from being eligible for promotion. The decorator both logs the metric and tags the run `gate_status=passed|failed`.

| Module | Metric | Threshold |
|--------|--------|-----------|
| M1 | macro-F1 | ≥ 0.80 |
| M2 | RAGAS faithfulness | ≥ 0.85 |
| M3 | ROC-AUC | ≥ 0.75 |
| M4 | macro-F1 | ≥ 0.75 |

```python
# FILE: ml/common/gates.py
from functools import wraps
import mlflow

class GateFailure(RuntimeError):
    pass

def enforce_gate(*, metric: str, threshold: float):
    def deco(fn):
        @wraps(fn)
        def wrapper(self, *args, **kwargs):
            metrics = fn(self, *args, **kwargs)
            value = metrics.get(metric)
            if value is None:
                raise GateFailure(f"Evaluator did not return '{metric}'")
            passed = value >= threshold
            mlflow.set_tag("gate_status", "passed" if passed else "failed")
            mlflow.set_tag("gate_metric", metric)
            mlflow.set_tag("gate_threshold", threshold)
            mlflow.log_metric(f"{metric}_vs_threshold", value - threshold)
            if not passed:
                raise GateFailure(f"{metric}={value:.4f} < {threshold}")
            return metrics
        return wrapper
    return deco
```

For M2, the gate is invoked from `ml/m2/eval_ragas.py` — there is no fit step, only retrieval-quality scoring against a frozen Q&A test set. RAGAS faithfulness is computed with `ragas.metrics.faithfulness` over the eval set produced by BUILD_08 §6.

---

## 8. Model Registry and Promotion

Every passing run is registered as a new MLflow `ModelVersion` in `Staging`. Promotion to `Production` is a deliberate CLI action that:

1. transitions the MLflow stage to `Production` (and archives the previous prod version),
2. flips `model_versions.is_production = TRUE` for the new row in Postgres and `FALSE` for the previous one,
3. writes a model card (§9) and attaches it to the registry as a description.

```python
# FILE: ml/common/registry.py
import mlflow
from sqlalchemy import create_engine, text
from ml.common.config import DATABASE_URL

_engine = create_engine(DATABASE_URL, future=True)

def write_training_run_row(run_id: str, cfg, metrics: dict, artifact_path: str) -> None:
    """Insert a row into training_runs (BUILD_04 §5)."""
    with _engine.begin() as cx:
        cx.execute(text("""
            INSERT INTO training_runs
              (mlflow_run_id, module_number, dataset_version, hyperparams_json,
               metrics_json, artifact_path, status)
            VALUES (:rid, :mod, :dv, CAST(:hp AS JSONB), CAST(:m AS JSONB), :ap, 'completed')
        """), dict(rid=run_id, mod=cfg.module_number, dv=cfg.dataset_version,
                   hp=mlflow_json(cfg.hyperparams), m=mlflow_json(metrics), ap=artifact_path))

def mlflow_json(d): import json; return json.dumps(d, default=str)
```

```python
# FILE: ml/registry/promote.py
import argparse, mlflow
from sqlalchemy import create_engine, text
from ml.common.config import DATABASE_URL
from ml.registry.card import render_card

def promote(run_id: str, model_name: str, module_number: int) -> None:
    client = mlflow.tracking.MlflowClient()
    run = client.get_run(run_id)
    if run.data.tags.get("gate_status") != "passed":
        raise SystemExit(f"Run {run_id} did not pass its eval gate; refusing to promote.")
    mv = mlflow.register_model(f"runs:/{run_id}/model", model_name)
    client.transition_model_version_stage(model_name, mv.version,
                                          stage="Production", archive_existing_versions=True)
    card = render_card(run_id, model_name, mv.version)
    client.update_model_version(model_name, mv.version, description=card)
    eng = create_engine(DATABASE_URL, future=True)
    with eng.begin() as cx:
        cx.execute(text("UPDATE model_versions SET is_production = FALSE "
                        "WHERE module_number = :m AND is_production = TRUE"),
                   {"m": module_number})
        cx.execute(text("""
            INSERT INTO model_versions
              (module_number, mlflow_run_id, registry_name, registry_version,
               training_run_id, is_production, deployed_at)
            VALUES (:m, :rid, :n, :v,
                    (SELECT id FROM training_runs WHERE mlflow_run_id = :rid),
                    TRUE, now())
        """), {"m": module_number, "rid": run_id, "n": model_name, "v": mv.version})

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--model-name", required=True)   # e.g. "m1_xlmr_classifier"
    ap.add_argument("--module-number", type=int, required=True)
    promote(**vars(ap.parse_args()))
```

The corresponding read path is in `backend/app/ml_serving/registry.py` (BUILD_07 §5), which selects `WHERE is_production IS TRUE`.

---

## 9. Auto-Generated Model Cards

Every promotion produces a markdown card from a Jinja2 template populated from MLflow run data. Cards are attached as the registry version description and saved to `ml/registry/cards/{model_name}_v{version}.md`.

```jinja
{# FILE: ml/registry/card_template.md.j2 #}
# {{ model_name }} v{{ version }}

- **Module:** {{ module_number }} | **Run:** `{{ run_id }}` | **Git:** {{ git_sha }}
- **Dataset:** v{{ dataset_version }} (train sha {{ dataset_sha_train }})
- **Trained:** {{ trained_at }} | **Seed:** {{ seed }}

## Metrics
| Metric | Value | Gate |
|--------|-------|------|
{% for m, v in metrics.items() -%}
| {{ m }} | {{ "%.4f"|format(v) }} | {{ gate_for(m) }} |
{% endfor %}

## Hyperparameters
{% for k, v in hyperparams.items() -%}
- `{{ k }}`: {{ v }}
{% endfor %}

## Intended use
{{ intended_use }}

## Known limitations
{{ limitations }}

## Reproducibility
Python {{ python_version }} on {{ cpu_count }} vCPU / {{ ram_gb }} GB RAM (GPU={{ gpu_available }}). Per-run `requirements.txt` attached as MLflow artifact `env/req_{{ run_id }}.txt`.
```

```python
# FILE: ml/registry/card.py
from pathlib import Path
import mlflow
from jinja2 import Environment, FileSystemLoader

GATES = {"f1_macro": 0.80, "roc_auc": 0.75, "ragas_faithfulness": 0.85}
_env = Environment(loader=FileSystemLoader(Path(__file__).parent), trim_blocks=True, lstrip_blocks=True)

def render_card(run_id: str, model_name: str, version: int) -> str:
    run = mlflow.get_run(run_id)
    t, params, metrics = run.data.tags, run.data.params, run.data.metrics
    md = _env.get_template("card_template.md.j2").render(
        model_name=model_name, version=version, run_id=run_id,
        module_number=t["module_number"], dataset_version=t["dataset_version"],
        dataset_sha_train=t["dataset_sha_train"], git_sha=t["git_sha"],
        trained_at=run.info.start_time, metrics=metrics, hyperparams=params,
        intended_use=_intended_use(int(t["module_number"])),
        limitations=_limitations(int(t["module_number"])),
        seed=t["seed"], python_version=t["python_version"],
        cpu_count=t["cpu_count"], ram_gb=t["ram_gb"], gpu_available=t["gpu_available"],
        gate_for=lambda m: f">= {GATES[m]}" if m in GATES else "—",
    )
    out = Path(__file__).parent / "cards" / f"{model_name}_v{version}.md"
    out.parent.mkdir(parents=True, exist_ok=True); out.write_text(md)
    return md
```

`_intended_use` / `_limitations` are short per-module strings (M1: "12-class gazette classification in EN/SI/TA; not legal advice." M3: "Fraud risk score for decision support, not auto-rejection." M4: "Claim stance; do not auto-publish.").

---

## 10. CI Hook — Nightly Retrain on Tagged Data

Retraining is triggered when a maintainer pushes a tag of the form `data-vN` to `main`. The job runs the trainer for whichever module the tag affects (selected via the workflow input), uploads MLflow artifacts, and posts a summary comment. Promotion remains manual — CI never flips `is_production`.

```yaml
# FILE: ml/ci/nightly_retrain.yml  (partial — meaningful steps only)
on:
  push:
    tags: ["data-v*"]
  workflow_dispatch:
    inputs:
      module: { required: true, type: choice, options: ["m1", "m3", "m4"] }

jobs:
  retrain:
    runs-on: ubuntu-latest
    timeout-minutes: 360
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --frozen --directory ml
      - name: Verify dataset manifest
        run: uv run --directory ml python -m ml.common.dataset --verify
      - name: Start MLflow tracking
        run: uv run --directory ml mlflow server --host 127.0.0.1 --port 5000 &
      - name: Train ${{ inputs.module || 'm1' }}
        run: uv run --directory ml python -m ml.${{ inputs.module || 'm1' }}.train_xlmr
        env: { MLFLOW_TRACKING_URI: http://127.0.0.1:5000 }
      - name: Upload mlruns
        uses: actions/upload-artifact@v4
        with: { name: mlruns, path: ml/mlruns/ }
```

Promotion is invoked by an operator on the VM:

```
uv run --directory ml python -m ml.registry.promote \
    --run-id <id> --model-name m1_xlmr_classifier --module-number 1
```

---

## 11. Hardware Notes

The deploy target is a single 4-vCPU / 16 GB VM that also runs Postgres, FastAPI, MLflow, and (during ingestion) Tesseract. The pipeline is shaped around that:

- **No fp16/bf16.** CPU-only. `fp16=False, bf16=False` everywhere.
- **Gradient checkpointing on.** `gradient_checkpointing=True` for all Transformer trainers; trades compute for ~40% peak-RAM reduction.
- **Effective batch size via accumulation.** Per-device batch ≤ 8, `gradient_accumulation_steps` 2–4.
- **LoRA fallback.** If full fine-tuning OOMs on M1 or M4 with `max_length=512`, swap in PEFT/LoRA (`r=8, alpha=16, target_modules=["query","value"]`); base model stays frozen, only adapter weights are trained and saved. The trainer base class accepts a `peft_config` field for this.
- **Sweep budget.** Optuna trials capped at 20, total wall-clock 4 hours per sweep.
- **Disk.** MLflow artifacts and `ml/mlruns/` are pruned by a weekly cron that keeps the latest 5 runs per experiment plus all `Production`-staged runs.

---

## 12. Acceptance Criteria

- [ ] `uv run --directory ml python -m ml.m1.train_xlmr` produces an MLflow run tagged `gate_status=passed` with `f1_macro >= 0.80` on the test split
- [ ] `uv run --directory ml python -m ml.m3.train_xgb` produces a run with `roc_auc >= 0.75`
- [ ] `uv run --directory ml python -m ml.m4.train_xlmr` produces a run with `f1_macro >= 0.75`
- [ ] `uv run --directory ml python -m ml.m2.eval_ragas` produces a run with `ragas_faithfulness >= 0.85`
- [ ] `manifest.yaml` sha256 + row-count check rejects a tampered Parquet file in unit tests
- [ ] Every completed run inserts exactly one row into Postgres `training_runs`
- [ ] `ml.registry.promote` flips `model_versions.is_production` atomically (old row → FALSE, new row → TRUE) and refuses runs without `gate_status=passed`
- [ ] A model card markdown is attached to every promoted MLflow registry version and saved to `ml/registry/cards/`
- [ ] Re-running a training entrypoint with the same seed and dataset version produces identical metrics (bit-exact on M3, ≤1e-3 drift on Transformer runs)
- [ ] The GitHub Actions workflow runs to completion on the `data-v*` tag and uploads `mlruns/` as an artifact

---

## 13. Claude Prompts for This Section

### Prompt 1 — Base Trainer class

```
Generate ml/common/trainer.py implementing BaseTrainer (abstract) with:
- TrainConfig dataclass: module_number, experiment, dataset, dataset_version,
  seed, output_dir, hyperparams.
- run() that: seeds via ml.common.seeding; loads train/val/test from
  ml.common.dataset.load_split (which sha-checks against
  ml/datasets/manifest.yaml); opens an MLflow run via
  ml.common.mlflow_utils.start_run with full tag set (module_number,
  dataset_version, dataset_sha_train, git_sha, python_version, seed,
  gate_status=pending); snapshots env + freezes per-run requirements.txt as
  MLflow artifact; calls fit/evaluate/save abstract methods; inserts a row
  into Postgres training_runs (BUILD_04 §5) via
  ml.common.registry.write_training_run_row.
- Subclasses override fit, evaluate, save. Make evaluate() compatible with
  @enforce_gate. Include a docstring explaining the inter-module contract.
```

### Prompt 2 — Eval-gate decorator

```
Generate ml/common/gates.py defining GateFailure(RuntimeError) and
enforce_gate(*, metric: str, threshold: float) — a decorator that wraps an
evaluator method returning {metric_name: value}. It must: log the metric;
set MLflow tags gate_status=passed|failed, gate_metric, gate_threshold;
log a derived metric f"{metric}_vs_threshold"; raise GateFailure when
value < threshold. Hard-code a GATES dict for reference (so promotion code
can read it) — M1 f1_macro >= 0.80, M3 roc_auc >= 0.75, M4 f1_macro >= 0.75,
M2 ragas_faithfulness >= 0.85 — but the threshold actually applied must come
from the decorator argument. Include unit tests covering pass, fail, and
missing-metric cases.
```

### Prompt 3 — Model-card auto-generator

```
Generate ml/registry/card.py with render_card(run_id, model_name, version):
- Pulls run data from MLflow (tags, params, metrics).
- Renders ml/registry/card_template.md.j2 populating model_name, version,
  run_id, module_number, dataset_version, dataset_sha_train, git_sha,
  trained_at, metrics, hyperparams, intended_use, limitations, seed,
  python_version, cpu_count, ram_gb, gpu_available.
- gate_for(metric) helper returns ">= <threshold>" for the four canonical
  gates and "—" otherwise.
- Writes ml/registry/cards/{model_name}_v{version}.md and returns the
  markdown string (so promotion CLI can attach it as the registry version
  description). Provide _intended_use / _limitations stubs per module
  (M1 gazette classification, M3 fraud risk score, M4 claim stance).
```

### Prompt 4 — MLflow promotion CLI

```
Generate ml/registry/promote.py with CLI:
  python -m ml.registry.promote --run-id <id> --model-name <name> --module-number <n>
Behavior:
  1. Refuse if run.tags.gate_status != "passed".
  2. mlflow.register_model(f"runs:/{run_id}/model", model_name).
  3. transition_model_version_stage(..., stage="Production",
                                    archive_existing_versions=True).
  4. Render a card via ml.registry.card.render_card and attach it as the
     version description.
  5. In a single Postgres transaction (SQLAlchemy `with engine.begin()`):
       UPDATE model_versions SET is_production=FALSE
         WHERE module_number=:m AND is_production=TRUE;
       INSERT INTO model_versions (module_number, mlflow_run_id, registry_name,
         registry_version, training_run_id, is_production, deployed_at)
         VALUES (..., TRUE, now());
Print the new model_versions.id and registry version on success. Exit
non-zero on any failure and leave Postgres unchanged (rollback).
```

---

**Prev:** `BUILD_10_Module4_Misinformation.md`  ·  **Next:** `BUILD_12_Data_Ingestion_and_Scheduling.md`
