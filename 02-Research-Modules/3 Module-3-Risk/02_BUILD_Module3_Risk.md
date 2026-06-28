# BUILD 09 — Module 3: Compliance Risk Prediction

> **Goal:** wire up the full Module 3 pipeline — feature engineering across firmographic, behavioral, sectoral, M1-exposure, and M2-knowledge signals → optional synthetic augmentation → XGBoost (with optional LSTM) training → SHAP-based explanations → async serving from MLflow registry → drift monitoring with auto-retrain triggers.
>
> **Scope:** **Feature engineering, training, serving, and drift monitoring.** The shared *training infrastructure* (MLflow tracking server, Optuna study harness, baseline classes, model registry promotion logic) lives in `BUILD_11_ML_Training_Pipeline.md`. The *raw data ingestion* (IRD defaulter scrapes, court records via `lawnet.gov.lk`, scheduled SME survey re-collection) is owned by `BUILD_12_Data_Ingestion_and_Scheduling.md`.
>
> **Read first:** `research/04_Technology_Stack_Justification.md`, `research/14_Module3_Risk_Architecture.md`, `research/module_2_and_3_data_architecture.md` (the schema source-of-truth for `m3_*` tables), `BUILD_08_Module2_Knowledge.md` (knowledge-score endpoint we consume), `BUILD_11_ML_Training_Pipeline.md`, `BUILD_12_Data_Ingestion_and_Scheduling.md`.

Module 3 is **"Compliance Vulnerability & Risk Profiling."** It predicts a binary outcome:

> *Will this SME experience a compliance failure in the next 24 months — defined as ≥1 penalty on record OR a missed known statutory deadline?*

The primary model is a gradient-boosted tree ensemble (XGBoost, with LightGBM as a fallback). An LSTM secondary model is trained only when temporal sequences are available for ≥50 SMEs. SHAP supplies per-prediction interpretability. The acceptance bar is **ROC-AUC ≥ 0.75** and **precision @ top-10% ≥ 0.60**. Sample-size floors: **≥100 SMEs with complete data** and **≥30 in the positive class**.

---

## 1. Component Map

| Concern | Code path | Talks to |
|---------|-----------|----------|
| Schema (six `m3_*` tables) | `backend/app/models/m3.py` | Postgres |
| Feature engineering | `ml/m3/features.py` | `m3_*` tables, M2 knowledge endpoint, M1 exposure |
| Synthetic augmentation | `ml/m3/synth.py` | SDV `GaussianCopulaSynthesizer` |
| XGBoost training + Optuna HPO | `ml/m3/train_xgb.py` | MLflow, BUILD_11 base classes |
| Optional LSTM | `ml/m3/train_lstm.py` | PyTorch |
| SHAP explainer | `ml/m3/explain.py` | `shap.TreeExplainer` |
| Serving | `backend/app/modules/m3/predict.py` | `mlflow.pyfunc`, `m3_predictions` |
| Drift monitoring | `ml/m3/drift.py` | PSI, rolling AUC, `training_runs` |
| Eval harness | `ml/m3/eval.py` | confusion matrix, calibration, fairness slices |

> **Cross-module wiring.** Feature engineering pulls `knowledge_score` and per-instrument breakdown for each SME via `GET /api/v1/m2/sme/{sme_id}/knowledge_score` (BUILD_08 §6 — Contract **C2**). M1 *exposure* features come from joining `regulations` against `sme_alert_subscriptions` and `alerts`. The M3 *vulnerability survey* (module 3 in `survey_questions`) is answered via the unified flow — those answers land in `survey_responses` (`module_number=3`) and are projected into `m3_compliance_history` / `m3_behavioural_signals` by `survey_service._project_m3_snapshots`, driven by each question's `m3_field_mapping` JSONB (canonical `M3_HIST_*`/`M3_BEH_*`/`M3_STR_*` codes have built-in defaults; admin-authored M3 questions opt in via that column — OQ32, resolved). See [`../SETUP/11_Survey_System.md`](../SETUP/11_Survey_System.md) §3 (C2), §10.4.

---

## 2. Schema — `m3_*` Tables

The six tables below are the source-of-truth structures from `research/module_2_and_3_data_architecture.md` §4.2. SQLAlchemy 2.0 async style matches BUILD_03/04.

```python
# FILE: backend/app/models/m3.py
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import String, Date, DateTime, Numeric, Integer, ForeignKey, JSON, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, UUID
from app.db.base import Base
import uuid


class M3ComplianceHistory(Base):
    __tablename__ = "m3_compliance_history"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("smes.sme_id", ondelete="CASCADE"), index=True)
    instrument: Mapped[str] = mapped_column(String(64))         # 'VAT'|'EPF'|'ETF'|...
    event_type: Mapped[str] = mapped_column(String(32))         # 'penalty'|'late_filing'|'audit'|'notice'
    event_date: Mapped[date] = mapped_column(Date, index=True)
    amount_lkr: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    source: Mapped[str] = mapped_column(String(32))             # 'ird_defaulter'|'court_record'|'self_report'
    source_ref: Mapped[str | None] = mapped_column(String(512))
    notes: Mapped[str | None] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class M3BehavioralSignals(Base):
    __tablename__ = "m3_behavioral_signals"
    sme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("smes.sme_id", ondelete="CASCADE"), primary_key=True)
    snapshot_date: Mapped[date] = mapped_column(Date, primary_key=True)
    filing_method: Mapped[str | None] = mapped_column(String(32))     # 'online'|'paper'|'mixed'
    books_method: Mapped[str | None] = mapped_column(String(32))      # 'manual'|'spreadsheet'|'software'
    accounting_software: Mapped[str | None] = mapped_column(String(64))
    deadline_tracking: Mapped[str | None] = mapped_column(String(32)) # 'calendar'|'reminder_app'|'none'
    advisor_relationship: Mapped[str | None] = mapped_column(String(32))
    self_check_frequency_per_year: Mapped[int | None] = mapped_column(Integer)


class M3ComplianceBarriers(Base):
    __tablename__ = "m3_compliance_barriers"
    sme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("smes.sme_id", ondelete="CASCADE"), primary_key=True)
    snapshot_date: Mapped[date] = mapped_column(Date, primary_key=True)
    barriers: Mapped[dict] = mapped_column(JSONB)  # {'cost': 4, 'complexity': 5, 'time': 3, ...} 1–5 Likert


class M3SectorSpecific(Base):
    __tablename__ = "m3_sector_specific"
    sme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("smes.sme_id", ondelete="CASCADE"), primary_key=True)
    snapshot_date: Mapped[date] = mapped_column(Date, primary_key=True)
    sector: Mapped[str] = mapped_column(String(64))
    sector_items: Mapped[dict] = mapped_column(JSONB)
    # e.g. {'food_safety_cert': True, 'labour_dept_reg': False, 'epz_status': None}


class M3Features(Base):
    """Denormalized feature store. One row per (sme_id, snapshot_date)."""
    __tablename__ = "m3_features"
    sme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("smes.sme_id", ondelete="CASCADE"), primary_key=True)
    snapshot_date: Mapped[date] = mapped_column(Date, primary_key=True)
    features: Mapped[dict] = mapped_column(JSONB)        # 40+ keys, see ml/m3/features.py
    label: Mapped[bool | None] = mapped_column(Boolean)  # 24-mo failure label, NULL during cold-start
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    feature_version: Mapped[str] = mapped_column(String(16), default="v1")
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class M3Predictions(Base):
    __tablename__ = "m3_predictions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("smes.sme_id", ondelete="CASCADE"), index=True)
    model_version: Mapped[str] = mapped_column(String(32))      # MLflow registry version
    risk_probability: Mapped[float] = mapped_column(Numeric(6, 5))
    risk_band: Mapped[str] = mapped_column(String(8))           # 'low'|'medium'|'high'|'critical'
    top_features_json: Mapped[dict] = mapped_column(JSONB)      # SHAP top-5
    feature_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    predicted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

> The `m3_features.features` JSONB stores the full 40+-feature vector so we never re-derive at serving time. `is_synthetic=True` rows must be excluded from the holdout fold and from drift monitoring.

---

## 3. Feature Engineering — `ml/m3/features.py`

Forty-plus features grouped into five families. All derivations enforce the **leakage rule**: no feature may use a fact whose `event_date > snapshot_date`. The training script asserts this at row construction.

```python
# FILE: ml/m3/features.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any
import httpx
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.sme import Sme
from app.models.m3 import (
    M3ComplianceHistory, M3BehavioralSignals,
    M3ComplianceBarriers, M3SectorSpecific,
)
from app.models.regulation import Regulation
from app.models.alert import Alert

FEATURE_VERSION = "v1"

@dataclass(frozen=True)
class FeatureRow:
    sme_id: str
    snapshot_date: date
    features: dict[str, Any]
    label: bool | None


async def build_feature_row(
    db: AsyncSession,
    *,
    sme_id: str,
    snapshot_date: date,
    knowledge_api_base: str,   # e.g. "http://api:8000/api/v1"
) -> FeatureRow:
    """Compute the full feature dict for one (sme, snapshot) pair."""
    sme = (await db.execute(select(Sme).where(Sme.sme_id == sme_id))).scalar_one()
    feats: dict[str, Any] = {}

    # --- Family 1: firmographic ---
    feats["sector"] = sme.sector
    feats["employee_count_band"] = sme.employee_count_band     # 'micro'|'small'|'medium'
    feats["business_age_years"] = max(0, (snapshot_date - sme.registration_date).days // 365)
    feats["region"] = sme.district
    feats["is_export_oriented"] = bool(sme.export_oriented)

    # --- Family 2: behavioral (snapshot-aligned, no future leakage) ---
    bh = await _latest_behavioral(db, sme_id, snapshot_date)
    feats["filing_method"] = bh.filing_method if bh else "unknown"
    feats["books_method"] = bh.books_method if bh else "unknown"
    feats["uses_accounting_software"] = bool(bh and bh.accounting_software)
    feats["deadline_tracking"] = bh.deadline_tracking if bh else "none"
    feats["self_check_freq"] = (bh.self_check_frequency_per_year if bh else 0) or 0

    # --- Family 3: sectoral (JSONB unfolded) ---
    sec = await _latest_sector(db, sme_id, snapshot_date)
    if sec:
        for k, v in (sec.sector_items or {}).items():
            feats[f"sector__{k}"] = v

    # --- Family 4: M1-exposure ---
    m1 = await _m1_exposure(db, sme_id, snapshot_date)
    feats.update(m1)   # categories_seen_count, distinct_categories, days_since_last_alert, ...

    # --- Family 5: M2-knowledge (consumes BUILD_08 endpoint) ---
    async with httpx.AsyncClient(timeout=8.0) as c:
        r = await c.get(f"{knowledge_api_base}/m2/sme/{sme_id}/knowledge_score")
        r.raise_for_status()
        kn = r.json()
    feats["knowledge_score"] = kn["overall_score"]
    for inst, sc in (kn.get("instrument_breakdown") or {}).items():
        feats[f"knowledge__{inst.lower()}"] = sc

    # --- Compliance-history rollups (only events strictly before snapshot) ---
    hist = await _history_before(db, sme_id, snapshot_date)
    feats["penalties_count_24mo"] = sum(
        1 for h in hist
        if h.event_type == "penalty" and h.event_date >= snapshot_date - timedelta(days=730)
    )
    feats["late_filings_24mo"] = sum(
        1 for h in hist
        if h.event_type == "late_filing" and h.event_date >= snapshot_date - timedelta(days=730)
    )
    feats["lifetime_penalty_amount_lkr"] = float(sum((h.amount_lkr or 0) for h in hist))

    # --- Label = forward-looking, only used in training ---
    label = await _compute_label(db, sme_id, snapshot_date)

    # Leakage assertion: every contributing event must be before snapshot
    _assert_no_future_leakage(hist, snapshot_date)

    return FeatureRow(sme_id=sme_id, snapshot_date=snapshot_date, features=feats, label=label)


def _assert_no_future_leakage(hist, snapshot_date: date) -> None:
    bad = [h for h in hist if h.event_date > snapshot_date]
    if bad:
        raise AssertionError(
            f"Leakage: {len(bad)} compliance-history events post-date snapshot {snapshot_date}"
        )
```

Helpers (`_latest_behavioral`, `_latest_sector`, `_m1_exposure`, `_history_before`, `_compute_label`) follow the same `select(...).where(snapshot_date >= ...).order_by(... desc()).limit(1)` pattern; the label join uses the **next 24 months** of compliance history and is therefore forbidden in serving.

```python
# FILE: ml/m3/features.py  (continued — exposure and label helpers)
async def _m1_exposure(db: AsyncSession, sme_id: str, snapshot_date: date) -> dict[str, Any]:
    rows = (await db.execute(
        select(Alert.regulation_id, Regulation.predicted_category, Alert.created_at)
        .join(Regulation, Regulation.regulation_id == Alert.regulation_id)
        .where(and_(Alert.sme_id == sme_id, Alert.created_at < snapshot_date))
    )).all()
    cats = {r.predicted_category for r in rows if r.predicted_category}
    last = max((r.created_at.date() for r in rows), default=None)
    return {
        "categories_seen_count": len(rows),
        "distinct_categories_seen": len(cats),
        "days_since_last_alert": (snapshot_date - last).days if last else 9999,
    }


async def _compute_label(db: AsyncSession, sme_id: str, snapshot_date: date) -> bool | None:
    """Positive iff a penalty or missed deadline fires within the 24mo forward window."""
    end = snapshot_date + timedelta(days=730)
    rows = (await db.execute(
        select(M3ComplianceHistory).where(and_(
            M3ComplianceHistory.sme_id == sme_id,
            M3ComplianceHistory.event_date > snapshot_date,
            M3ComplianceHistory.event_date <= end,
            M3ComplianceHistory.event_type.in_(("penalty", "late_filing")),
        ))
    )).scalars().all()
    if not rows and snapshot_date > date.today() - timedelta(days=730):
        return None   # forward window not yet observed → exclude from supervised set
    return bool(rows)
```

---

## 4. Synthetic Augmentation — `ml/m3/synth.py`

The combined survey + scrape corpus will land near 120–150 SMEs at submission; the positive class is the bottleneck. We use SDV's `GaussianCopulaSynthesizer` with explicit constraints, and we **cap the synthetic ratio at 30%** of the training set so the panel keeps face-validity for the viva.

```python
# FILE: ml/m3/synth.py
from __future__ import annotations
import pandas as pd
from sdv.metadata import SingleTableMetadata
from sdv.single_table import GaussianCopulaSynthesizer
from sdv.constraints import FixedCombinations, ScalarRange

VALID_BANDS = ("micro", "small", "medium")

def fit_synthesizer(df: pd.DataFrame) -> GaussianCopulaSynthesizer:
    md = SingleTableMetadata()
    md.detect_from_dataframe(df)
    md.update_column("employee_count_band", sdtype="categorical")

    constraints = [
        ScalarRange(column_name="business_age_years", low_value=0, high_value=80, strict_boundaries=False),
        FixedCombinations(column_names=["sector", "employee_count_band"]),  # preserve joint
    ]
    syn = GaussianCopulaSynthesizer(metadata=md, default_distribution="beta")
    syn.add_constraints(constraints)
    syn.fit(df)
    return syn


def augment(real: pd.DataFrame, synth: GaussianCopulaSynthesizer, *, target_pos_rate: float = 0.35,
            max_synth_ratio: float = 0.30) -> pd.DataFrame:
    n_real = len(real)
    n_synth_max = int(n_real * max_synth_ratio / (1 - max_synth_ratio))
    sampled = synth.sample(num_rows=n_synth_max * 3)        # over-sample then filter
    # Conditional re-balance toward the target positive rate
    pos = sampled[sampled["label"] == True].head(int(n_synth_max * target_pos_rate))
    neg = sampled[sampled["label"] == False].head(n_synth_max - len(pos))
    sampled = pd.concat([pos, neg]).assign(is_synthetic=True)

    real = real.assign(is_synthetic=False)
    out = pd.concat([real, sampled], ignore_index=True)

    # Hard guard — abort if cap exceeded
    ratio = out["is_synthetic"].mean()
    assert ratio <= max_synth_ratio + 1e-6, f"Synthetic ratio {ratio:.3f} exceeds cap {max_synth_ratio}"

    # Reject rows violating domain constraints (defensive — SDV usually honours them)
    out = out[out["employee_count_band"].isin(VALID_BANDS)]
    out = out[out["business_age_years"] >= 0]
    return out.reset_index(drop=True)
```

Required version pin: `sdv>=1.13,<2`.

---

## 5. XGBoost Training — `ml/m3/train_xgb.py`

Stratified 5-fold, Optuna HPO (50 trials), isotonic calibration, `scale_pos_weight` for imbalance, MLflow logging, and registry promotion gated by **AUC ≥ 0.75 AND P@10% ≥ 0.60**.

```python
# FILE: ml/m3/train_xgb.py
from __future__ import annotations
import json
import mlflow
import mlflow.xgboost
import numpy as np
import optuna
import pandas as pd
import xgboost as xgb
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score
from ml.m3.eval import precision_at_top_k, expected_calibration_error
from ml.training.base import register_if_better   # BUILD_11

EXPERIMENT = "m3-risk"
MIN_AUC, MIN_P_AT_10 = 0.75, 0.60


def _objective(trial: optuna.Trial, X: pd.DataFrame, y: np.ndarray, spw: float) -> float:
    params = {
        "objective": "binary:logistic",
        "eval_metric": "auc",
        "max_depth": trial.suggest_int("max_depth", 3, 8),
        "learning_rate": trial.suggest_float("learning_rate", 1e-3, 0.3, log=True),
        "n_estimators": trial.suggest_int("n_estimators", 200, 1500),
        "min_child_weight": trial.suggest_float("min_child_weight", 0.5, 10.0),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
        "scale_pos_weight": spw,
        "tree_method": "hist",
    }
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    aucs: list[float] = []
    for tr, va in skf.split(X, y):
        m = xgb.XGBClassifier(**params)
        m.fit(X.iloc[tr], y[tr], eval_set=[(X.iloc[va], y[va])], verbose=False)
        aucs.append(roc_auc_score(y[va], m.predict_proba(X.iloc[va])[:, 1]))
    return float(np.mean(aucs))


def train(df: pd.DataFrame) -> dict:
    real = df[~df["is_synthetic"]]
    holdout = real.sample(frac=0.2, random_state=7)
    train_df = df.drop(index=holdout.index)
    y = train_df["label"].astype(int).to_numpy()
    X = train_df.drop(columns=["label", "is_synthetic", "sme_id", "snapshot_date"])
    spw = float((y == 0).sum() / max((y == 1).sum(), 1))

    mlflow.set_experiment(EXPERIMENT)
    with mlflow.start_run() as run:
        study = optuna.create_study(direction="maximize",
                                    sampler=optuna.samplers.TPESampler(seed=42))
        study.optimize(lambda t: _objective(t, X, y, spw), n_trials=50, show_progress_bar=False)
        best = study.best_params

        base = xgb.XGBClassifier(**best, scale_pos_weight=spw, tree_method="hist")
        cal = CalibratedClassifierCV(base, method="isotonic", cv=5)
        cal.fit(X, y)

        Xh = holdout.drop(columns=["label", "is_synthetic", "sme_id", "snapshot_date"])
        yh = holdout["label"].astype(int).to_numpy()
        ph = cal.predict_proba(Xh)[:, 1]
        auc = roc_auc_score(yh, ph)
        p10 = precision_at_top_k(yh, ph, k=0.10)
        ece = expected_calibration_error(yh, ph)

        mlflow.log_params(best)
        mlflow.log_metrics({"holdout_auc": auc, "p_at_10pct": p10, "ece": ece,
                            "scale_pos_weight": spw, "synth_ratio": float(df["is_synthetic"].mean())})
        mlflow.log_dict({"feature_columns": list(X.columns)}, "feature_columns.json")
        mlflow.sklearn.log_model(cal, artifact_path="model",
                                 registered_model_name="m3-risk")

        if auc >= MIN_AUC and p10 >= MIN_P_AT_10:
            register_if_better(model_name="m3-risk", run_id=run.info.run_id,
                               metric="holdout_auc", value=auc, stage="Production")

        return {"run_id": run.info.run_id, "auc": auc, "p_at_10": p10, "ece": ece}
```

Versions: `xgboost>=2,<3`, `optuna>=3.6,<4`, `mlflow>=2.13,<3`. LightGBM (`lightgbm>=4,<5`) is wired identically as a swappable estimator behind the same MLflow run.

---

## 6. Optional LSTM — `ml/m3/train_lstm.py`

Trained only when temporal sequences (filings + deadlines) are available for **≥50 SMEs**; otherwise this module logs a skip message and exits zero so the orchestrator does not fail.

```python
# FILE: ml/m3/train_lstm.py
from __future__ import annotations
import logging
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

log = logging.getLogger(__name__)
MIN_SEQUENCES = 50


class FilingsLSTM(nn.Module):
    def __init__(self, in_dim: int = 6, hidden: int = 32, layers: int = 1):
        super().__init__()
        self.lstm = nn.LSTM(in_dim, hidden, layers, batch_first=True, dropout=0.1)
        self.head = nn.Sequential(nn.Linear(hidden, 16), nn.ReLU(), nn.Linear(16, 1))

    def forward(self, x):                        # x: (B, T, in_dim)
        out, _ = self.lstm(x)
        return self.head(out[:, -1, :]).squeeze(-1)


def train_if_enough(sequences, labels) -> dict | None:
    if len(sequences) < MIN_SEQUENCES:
        log.info("LSTM skipped: %d sequences < %d", len(sequences), MIN_SEQUENCES)
        return None
    X = torch.tensor(sequences, dtype=torch.float32)
    y = torch.tensor(labels, dtype=torch.float32)
    loader = DataLoader(TensorDataset(X, y), batch_size=16, shuffle=True)
    model = FilingsLSTM(in_dim=X.shape[-1])
    opt = torch.optim.Adam(model.parameters(), lr=2e-3)
    loss_fn = nn.BCEWithLogitsLoss()
    for epoch in range(40):
        for xb, yb in loader:
            opt.zero_grad(); loss = loss_fn(model(xb), yb); loss.backward(); opt.step()
    return {"epochs": 40, "n": len(sequences)}
```

The LSTM's per-SME risk score is logged as an *auxiliary* feature into a v2 feature store row; the production model in the registry remains XGBoost unless the LSTM-augmented variant beats it on the same holdout.

---

## 7. SHAP Explainer — `ml/m3/explain.py`

`TreeExplainer` runs in milliseconds on the calibrated XGBoost. We persist the **top-5** signed contributions in `m3_predictions.top_features_json` so the frontend can render the "why" panel without a second model call.

```python
# FILE: ml/m3/explain.py
from __future__ import annotations
import numpy as np
import pandas as pd
import shap

class M3Explainer:
    def __init__(self, calibrated_model, feature_columns: list[str]):
        # Calibrated wrapper exposes the underlying booster via .calibrated_classifiers_[0].estimator
        booster = calibrated_model.calibrated_classifiers_[0].estimator
        self._explainer = shap.TreeExplainer(booster)
        self._cols = feature_columns

    def top_features(self, x_row: pd.Series, k: int = 5) -> list[dict]:
        sv = self._explainer.shap_values(x_row.to_frame().T)
        if isinstance(sv, list):     # binary returns [neg, pos]
            sv = sv[1]
        contribs = sv[0]
        order = np.argsort(np.abs(contribs))[::-1][:k]
        return [
            {"feature": self._cols[i],
             "value": _json_safe(x_row.iloc[i]),
             "shap": float(contribs[i]),
             "direction": "increases" if contribs[i] > 0 else "decreases"}
            for i in order
        ]


def _json_safe(v):
    if isinstance(v, (np.integer, np.floating, np.bool_)):
        return v.item()
    return v
```

---

## 8. Serving — `backend/app/modules/m3/predict.py`

Async FastAPI endpoint, in-process LRU cache for the loaded model, and a write-through to `m3_predictions`. Pydantic v2 schemas mirror the BUILD_03/04 conventions.

```python
# FILE: backend/app/modules/m3/predict.py
from __future__ import annotations
import os
from functools import lru_cache
from typing import Any
import mlflow.pyfunc
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, require_user
from app.models.m3 import M3Predictions
from ml.m3.explain import M3Explainer
from ml.m3.features import build_feature_row, FEATURE_VERSION

router = APIRouter(prefix="/m3", tags=["m3"])
MODEL_URI = os.getenv("M3_MODEL_URI", "models:/m3-risk/Production")


@lru_cache(maxsize=1)
def _load_model():
    pyfunc = mlflow.pyfunc.load_model(MODEL_URI)
    cols = pyfunc.metadata.get_input_schema().input_names()
    explainer = M3Explainer(pyfunc.unwrap_python_model().model, cols)  # if custom wrapper
    return pyfunc, explainer, cols


class RiskResponse(BaseModel):
    sme_id: str
    risk_probability: float = Field(ge=0, le=1)
    risk_band: str
    top_features: list[dict[str, Any]]
    model_version: str
    feature_version: str


def _band(p: float) -> str:
    if p < 0.20: return "low"
    if p < 0.50: return "medium"
    if p < 0.75: return "high"
    return "critical"


@router.get("/sme/{sme_id}/risk", response_model=RiskResponse)
async def predict_risk(sme_id: str, db: AsyncSession = Depends(get_db),
                       _user=Depends(require_user)) -> RiskResponse:
    pyfunc, explainer, cols = _load_model()
    today = pd.Timestamp.utcnow().date()
    fr = await build_feature_row(
        db, sme_id=sme_id, snapshot_date=today,
        knowledge_api_base=os.getenv("INTERNAL_API_BASE", "http://api:8000/api/v1"),
    )
    x = pd.DataFrame([{c: fr.features.get(c) for c in cols}])
    proba = float(pyfunc.predict(x)[0])
    top = explainer.top_features(x.iloc[0], k=5)

    row = M3Predictions(
        sme_id=sme_id, model_version=str(pyfunc.metadata.run_id),
        risk_probability=proba, risk_band=_band(proba),
        top_features_json={"top": top},
    )
    db.add(row); await db.commit()
    return RiskResponse(
        sme_id=sme_id, risk_probability=proba, risk_band=_band(proba),
        top_features=top, model_version=str(pyfunc.metadata.run_id),
        feature_version=FEATURE_VERSION,
    )
```

---

## 9. Drift Monitoring — `ml/m3/drift.py`

Two signals, both run by APScheduler (see BUILD_07 §10 / BUILD_12 §3): **PSI** on input features and **rolling 90-day AUC** on the labelled holdout. A breach writes a `training_runs` row with `notes='auto-drift-trigger'` so BUILD_11's harness can pick it up.

```python
# FILE: ml/m3/drift.py
from __future__ import annotations
import logging
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.m3 import M3Features, M3Predictions
from app.models.training_runs import TrainingRun

log = logging.getLogger(__name__)
PSI_HIGH = 0.25
AUC_FLOOR = 0.70


def psi(expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
    edges = np.quantile(expected, np.linspace(0, 1, bins + 1))
    edges[0], edges[-1] = -np.inf, np.inf
    e, _ = np.histogram(expected, bins=edges)
    a, _ = np.histogram(actual, bins=edges)
    e = np.where(e == 0, 1e-6, e / e.sum())
    a = np.where(a == 0, 1e-6, a / a.sum())
    return float(np.sum((a - e) * np.log(a / e)))


async def check_drift(db: AsyncSession, *, baseline: pd.DataFrame) -> dict:
    cutoff = datetime.utcnow() - timedelta(days=90)
    rows = (await db.execute(
        select(M3Features).where(M3Features.computed_at >= cutoff)
    )).scalars().all()
    recent = pd.DataFrame([r.features for r in rows])

    drifts = {col: psi(baseline[col].to_numpy(), recent[col].to_numpy())
              for col in baseline.columns if pd.api.types.is_numeric_dtype(baseline[col])
              and col in recent.columns and recent[col].notna().sum() > 30}
    high = {k: v for k, v in drifts.items() if v > PSI_HIGH}

    auc = await _rolling_auc(db, cutoff)
    breach = bool(high) or (auc is not None and auc < AUC_FLOOR)

    if breach:
        db.add(TrainingRun(
            module_number=3, status="queued",
            notes="auto-drift-trigger",
            metadata_json={"psi_high": high, "rolling_auc": auc},
        ))
        await db.commit()
        log.warning("M3 drift trigger fired: psi_high=%s auc=%s", high, auc)
    return {"psi": drifts, "rolling_auc": auc, "breach": breach}
```

The baseline parquet (training feature distribution) is dropped to `s3://enigmatrix/m3/baseline_v1.parquet` at registry promotion time and re-loaded by the cron.

---

## 10. Eval Harness — `ml/m3/eval.py`

Confusion matrix, calibration curve (Brier + ECE), and **fairness slices** by `sector`, `district`, and `employee_count_band`. Each slice reports AUC, P@10%, and positive rate; slices below the n=15 floor are flagged not-significant rather than hidden.

```python
# FILE: ml/m3/eval.py
from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import roc_auc_score, confusion_matrix


def precision_at_top_k(y_true: np.ndarray, y_score: np.ndarray, k: float = 0.10) -> float:
    n = max(int(round(len(y_true) * k)), 1)
    idx = np.argsort(y_score)[::-1][:n]
    return float(y_true[idx].mean())


def expected_calibration_error(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    prob_true, prob_pred = calibration_curve(y, p, n_bins=bins, strategy="quantile")
    weights = np.histogram(p, bins=bins)[0] / len(p)
    return float(np.sum(weights[: len(prob_true)] * np.abs(prob_true - prob_pred)))


def fairness_slices(df: pd.DataFrame, score_col: str = "score",
                    label_col: str = "label") -> pd.DataFrame:
    rows = []
    for axis in ("sector", "district", "employee_count_band"):
        for value, sub in df.groupby(axis):
            if len(sub) < 15:
                rows.append({"axis": axis, "value": value, "n": len(sub),
                             "auc": None, "p_at_10": None, "note": "n<15"})
                continue
            rows.append({
                "axis": axis, "value": value, "n": len(sub),
                "auc": roc_auc_score(sub[label_col], sub[score_col]),
                "p_at_10": precision_at_top_k(sub[label_col].to_numpy(),
                                              sub[score_col].to_numpy(), 0.10),
                "pos_rate": float(sub[label_col].mean()),
            })
    return pd.DataFrame(rows)


def confusion_at_threshold(y, p, thr: float = 0.5) -> dict:
    cm = confusion_matrix(y, (p >= thr).astype(int)).tolist()
    return {"threshold": thr, "matrix": cm}
```

---

## 11. Acceptance Criteria

- [ ] `m3_features` populated for **≥100 SMEs** with non-null label and ≥30 in the positive class
- [ ] Holdout **ROC-AUC ≥ 0.75** logged to MLflow under experiment `m3-risk`
- [ ] **Precision @ top-10% ≥ 0.60** on the holdout
- [ ] Calibration **ECE < 0.05** after isotonic wrapping
- [ ] Fairness slice report exists for `sector`, `district`, `employee_count_band` with per-slice AUC/P@10 (or n<15 note)
- [ ] Each `m3_predictions` row carries SHAP top-5 contributions in `top_features_json`
- [ ] **Synthetic ratio in training set ≤ 30%**, asserted in `ml/m3/synth.py::augment`
- [ ] Drift cron run on a synthetic shifted batch creates a `training_runs` row with `notes='auto-drift-trigger'`
- [ ] Production model registered at `models:/m3-risk/Production` and loaded by the predict endpoint
- [ ] No-future-leakage assertion passes on the full feature build (CI check)

---

## 12. Claude Prompts

### Prompt 1 — Feature pipeline with leakage assertions

```
Implement ml/m3/features.py per BUILD_09 §3. Requirements:
- async function build_feature_row(db, sme_id, snapshot_date, knowledge_api_base)
- 40+ features across 5 families (firmographic, behavioral, sectoral JSONB-unfolded,
  M1-exposure, M2-knowledge via httpx GET to {knowledge_api_base}/m2/sme/{id}/knowledge_score)
- Compute the 24-month forward label using m3_compliance_history events strictly after snapshot
- Raise AssertionError on any contributing event with event_date > snapshot_date
- Return None label when the forward 24mo window is not yet observed (cold-start exclusion)
- Add pytest cases that construct in-memory fixtures and assert leakage detection fires.
```

### Prompt 2 — SDV synthesizer + constraint validation

```
Implement ml/m3/synth.py using sdv>=1.13,<2:
- fit_synthesizer(df) returns a GaussianCopulaSynthesizer with metadata auto-detected
  and constraints: ScalarRange on business_age_years (0–80) and FixedCombinations on
  (sector, employee_count_band).
- augment(real, synth, target_pos_rate=0.35, max_synth_ratio=0.30) over-samples then
  filters to a positive rate, asserts the synthetic ratio cap, and rejects rows that
  violate domain rules (employee_count_band whitelist, non-negative ages).
- Add a CLI: python -m ml.m3.synth --in real.parquet --out aug.parquet --cap 0.30.
```

### Prompt 3 — XGBoost + Optuna training script with MLflow logging

```
Implement ml/m3/train_xgb.py per §5:
- Stratified 5-fold CV inside an Optuna TPE study (n_trials=50) maximising mean fold AUC
- Hyperparameters: max_depth, learning_rate, n_estimators, min_child_weight, subsample,
  colsample_bytree, reg_lambda; tree_method='hist'
- scale_pos_weight = neg/pos on the training set
- Wrap the best model in CalibratedClassifierCV(method='isotonic', cv=5)
- Log params, holdout AUC, P@10%, ECE, scale_pos_weight, synthetic ratio, and the
  feature_columns.json artifact to MLflow
- Promote to models:/m3-risk/Production only if holdout AUC ≥ 0.75 AND P@10 ≥ 0.60.
```

### Prompt 4 — SHAP service returning JSON-friendly explanations

```
Implement ml/m3/explain.py with class M3Explainer:
- Construct shap.TreeExplainer from the underlying XGBoost booster inside the
  CalibratedClassifierCV wrapper.
- top_features(x_row, k=5) returns a list of {feature, value, shap, direction} dicts
  with all numpy scalars converted to Python types.
- Add a unit test that asserts the sum of returned shap values has the same sign
  as the model's logit prediction on a known fixture row.
```

### Prompt 5 — Drift-monitoring cron job

```
Implement ml/m3/drift.py per §9 and a APScheduler job that runs daily at 03:00 Asia/Colombo:
- Compute PSI per numeric feature against the baseline parquet pinned at registry promotion.
- Compute rolling 90-day AUC on real (non-synthetic) holdout predictions joined to labels
  that have aged past the 24mo forward window.
- If any feature PSI > 0.25 OR rolling AUC < 0.70, insert a TrainingRun row with
  status='queued' and notes='auto-drift-trigger'.
- Emit a structured log line and a metric to Prometheus (drift_psi_max, m3_rolling_auc).
```

---

**Prev:** `BUILD_08_Module2_Knowledge.md` &nbsp;·&nbsp; **Next:** `BUILD_10_Module4_Misinformation.md`
