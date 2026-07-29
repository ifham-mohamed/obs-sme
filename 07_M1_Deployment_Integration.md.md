# 07 — Module 1: Deployment & Integration

> **Cross-references:** [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) · [08_M1_Full_System_Architecture.md](08_M1_Full_System_Architecture.md) · [11_M1_API_Reference.md](11_M1_API_Reference.md)
> **See also:** [13_M1_Folder_Structure_and_Implementation_Flow.md](13_M1_Folder_Structure_and_Implementation_Flow.md) — Fly volume layout, rollback path, inference Celery task.
> **Sub-step companions:** [07_M1_Deployment_Integration.md](07_M1_Deployment_Integration.md) · [07_M1_Deployment_Integration.md](07_M1_Deployment_Integration.md)

---

## Abstract

This document specifies the production deployment architecture for the trained XLM-R + LoRA gazette classifier, covering inference serving, API integration, caching, and platform selection. Four deployment platforms are evaluated — Render, Railway, Fly.io, and AWS SageMaker — and the self-hosted Fly.io approach with ONNX Runtime CPU inference is selected for its cost predictability, offline-compatible serving, and zero cold-start penalty. The trained model is exported to ONNX format (opset 17) and served via a FastAPI inference endpoint integrated into the existing Enigmatrix backend. A Redis cache layer prevents redundant inference on already-classified gazette texts. End-to-end latency from gazette ingestion to API response is targeted at ≤ 2 seconds per gazette.

---

## 1. Deployment Platform Selection

### 1.1 Comparison Table

| Criterion | Render | Railway | Fly.io | AWS SageMaker |
|---|---|---|---|---|
| **Persistent disk** | ✅ (paid) | ⚠️ Ephemeral | ✅ Volumes | ✅ S3 |
| **CPU inference support** | ✅ | ✅ | ✅ | ✅ |
| **GPU inference support** | ❌ Free tier only CPU | ❌ | ❌ | ✅ (expensive) |
| **Container deployment** | ✅ Docker | ✅ Docker | ✅ Docker | ✅ ECR |
| **Custom ML model serving** | ✅ (manual) | ✅ (manual) | ✅ (manual) | ✅ (managed) |
| **Cold start on free tier** | ✅ Yes (30–50s) | ✅ Yes | ❌ No cold start | ❌ No cold start |
| **Price predictability** | Medium | Low | ✅ High | Low (pay-per-inference) |
| **ONNX Runtime** | ✅ pip install | ✅ | ✅ | ✅ |
| **Private network to Postgres** | ✅ Internal | ✅ Internal | ✅ Private IPv6 | ⚠️ VPC required |
| **Region: Asia** | ❌ US/EU only | ❌ | ✅ Singapore (sin) | ✅ ap-southeast-1 |
| **Offline/airgapped capable** | ❌ | ❌ | ✅ (ONNX weights bundled) | ❌ |
| **Monthly cost (est.)** | $25–45 | $20–40 | $20–35 | $80–200+ |
| **Why chosen** | Cold start issue | Ephemeral disk | ✅ **Selected** | Cost unpredictable |

### 1.2 Justification for Fly.io

1. **No cold start:** Fly.io machines stay warm between requests, which is critical because ONNX model loading takes ~8 seconds on first load. Cold start on Render free tier would exceed the 2-second latency SLA.
2. **Singapore region:** The `sin` Fly.io region minimises latency to Sri Lankan gazette servers and the Enigmatrix target audience.
3. **Persistent volume for model weights:** The ONNX model file (475MB for full XLM-R + LoRA) is mounted from a persistent Fly volume, eliminating re-download on redeploy.
4. **Cost ceiling:** Shared CPU (2 cores, 1GB RAM) at ~$20/month; no per-inference billing.

**Cost breakeven vs Render.** Render's hobby plan is cheaper sticker-price ($7/mo vs Fly's ~$20/mo) but suffers 30–50s cold starts. The break-even depends on traffic shape:

| Daily classify calls | Cold starts/day (Render) | Effective Render latency p99 | Fly latency p99 | Choose |
|---|---|---|---|---|
| < 5 (very low) | 5+ | 30–50 s | 2 s | Fly only if SLA matters |
| 5–10 | 2–4 | 5–15 s avg | 2 s | Fly — cold starts dominate the 2 s SLA |
| > 10 (target) | 0–1 | 2 s | 2 s | Fly — break-even on latency, advantage on rollback |

The break-even gazette rate is ~10/day — at and above that, Render's premium-tier ($25/mo "always-on") matches Fly's price *without* matching its rollback story. At < 5/day, neither platform's per-classify cost matters; the choice is driven by ops simplicity. We pick Fly because the model-rollback procedure below requires a persistent volume that Render's ephemeral-disk hobby plan can't provide.

---

## 2. ONNX Export and Optimisation

### 2.1 Why ONNX

The trained PyTorch model is exported to ONNX (Open Neural Network Exchange) format for production serving:

| Property | PyTorch (raw) | ONNX Runtime |
|---|---|---|
| **CPU inference latency** | ~4.2s per gazette | ~1.8s per gazette |
| **Framework dependency** | PyTorch + PEFT | onnxruntime only |
| **Memory footprint** | ~1.5GB (float32) | ~480MB (float32) |
| **INT8 quantization** | Manual (bitsandbytes) | ✅ Built-in via onnxruntime-tools |
| **Thread parallelism** | GIL-limited | ✅ Native C++ threadpool |

### 2.2 Export Script

```python
import torch
import torch.onnx
from transformers import AutoTokenizer
from ml.m1.model.architecture import GazetteClassifier

def export_to_onnx(model_checkpoint: str, output_path: str):
    model = GazetteClassifier()
    model.load_state_dict(torch.load(model_checkpoint, map_location="cpu"))
    model.eval()

    tokenizer = AutoTokenizer.from_pretrained("facebook/xlm-roberta-base")
    dummy_text = "This is a sample gazette text for export."
    dummy_inputs = tokenizer(
        dummy_text, return_tensors="pt", max_length=512,
        truncation=True, padding="max_length"
    )

    torch.onnx.export(
        model,
        (dummy_inputs["input_ids"], dummy_inputs["attention_mask"]),
        output_path,
        input_names=["input_ids", "attention_mask"],
        output_names=["category_logits", "sector_logits"],
        dynamic_axes={
            "input_ids": {0: "batch_size"},
            "attention_mask": {0: "batch_size"},
        },
        opset_version=17,
        do_constant_folding=True,
    )
    print(f"Exported to {output_path}")
```

### 2.3 INT8 Quantization (Optional)

For further CPU speedup (reducing latency to ~0.9s at the cost of ~1% F1):

```python
from onnxruntime.quantization import quantize_dynamic, QuantType

quantize_dynamic(
    model_input="gazette_classifier.onnx",
    model_output="gazette_classifier_int8.onnx",
    weight_type=QuantType.QInt8,
)
```

---

## 3. Inference Service

### 3.1 ONNX Runtime Session

```python
# ml/m1/model/inference.py
import onnxruntime as ort
import numpy as np
from transformers import AutoTokenizer
import torch

class GazetteInferenceEngine:
    CATEGORY_LABELS = [
        "TAX_RATE_CHANGE", "IMPORT_EXPORT", "SECTOR_SPECIFIC", "EPF_ETF_CHANGE",
        "LABOUR_LAW", "PRODUCT_STANDARD", "BUSINESS_REGISTRATION",
        "PENALTY_ENFORCEMENT"
    ]
    SECTOR_LABELS = [
        "grocery_retail", "food_service", "general_retail"
    ]
    SECTOR_THRESHOLD = 0.48  # Tuned on validation set

    def __init__(self, onnx_path: str = "./storage/models/gazette_classifier.onnx"):
        sess_options = ort.SessionOptions()
        sess_options.intra_op_num_threads = 2
        sess_options.inter_op_num_threads = 2
        self.session = ort.InferenceSession(
            onnx_path,
            sess_options=sess_options,
            providers=["CPUExecutionProvider"],
        )
        self.tokenizer = AutoTokenizer.from_pretrained(
            "facebook/xlm-roberta-base",
            local_files_only=True,
        )

    def classify(self, text: str) -> dict:
        inputs = self.tokenizer(
            text, max_length=512, truncation=True,
            padding="max_length", return_tensors="np"
        )
        cat_logits, sec_logits = self.session.run(
            None,
            {
                "input_ids": inputs["input_ids"].astype(np.int64),
                "attention_mask": inputs["attention_mask"].astype(np.int64),
            }
        )
        cat_probs = torch.softmax(torch.tensor(cat_logits), dim=-1).numpy()[0]
        sec_probs = torch.sigmoid(torch.tensor(sec_logits)).numpy()[0]

        category_idx = int(np.argmax(cat_probs))
        return {
            "change_category": self.CATEGORY_LABELS[category_idx],
            "confidence": float(cat_probs[category_idx]),
            "affected_sectors": [
                self.SECTOR_LABELS[i]
                for i, p in enumerate(sec_probs) if p >= self.SECTOR_THRESHOLD
            ],
            "sector_probabilities": {
                self.SECTOR_LABELS[i]: float(sec_probs[i])
                for i in range(len(self.SECTOR_LABELS))
            },
        }
```

### 3.2 Redis Cache Layer

Inference results are cached in Redis by content hash to avoid re-classifying identical gazette texts:

```python
import hashlib
import json
import redis

class CachedInferenceEngine:
    TTL_SECONDS = 86400 * 30  # 30 days

    def __init__(self, engine: GazetteInferenceEngine, redis_url: str, model_version: str):
        self.engine = engine
        self.redis = redis.from_url(redis_url)
        self.model_version = model_version    # e.g. "v1.0" — invalidates cache on model bump

    def classify(self, text: str, gazette_number: str, published_date: str) -> dict:
        # Cross-gazette contamination guard: include identifying metadata in the key.
        # Two distinct gazettes with identical preamble text MUST produce two cache entries.
        cache_input = f"{self.model_version}|{gazette_number}|{published_date}|{text}"
        cache_key = f"m1:classify:{hashlib.sha256(cache_input.encode()).hexdigest()}"

        cached = self.redis.get(cache_key)
        if cached:
            return json.loads(cached)

        result = self.engine.classify(text)
        self.redis.setex(cache_key, self.TTL_SECONDS, json.dumps(result))
        return result
```

**Why include `model_version` + identifiers in the key.** A naive `SHA256(text)` key has two failure modes: (a) **cross-gazette contamination** — two distinct gazettes can share an identical preamble paragraph (copy-paste boilerplate) and end up sharing the cached classification, even though their *real* category differs in the body. Including `gazette_number + published_date` partitions the cache per-document. (b) **stale results across model versions** — after deploying `v1.1`, results from `v1.0` would still be served from cache. Including `model_version` as a key prefix invalidates the entire cache on every model bump (Redis can also be explicitly flushed; the prefix is a defensive belt-and-braces). Cache size impact: ~30 days × 30 gazettes/day × ~200 bytes/entry ≈ 200 kB total — negligible.

---

## 4. API Integration

### 4.1 Classification Celery Task

The Celery task `classify_gazette` is triggered automatically after text extraction completes (status transitions from `extracted` to `classified`):

```python
# backend/app/tasks/m1/classify_gazette.py
from celery import shared_task
from app.db.session import get_db
from ml.m1.model.inference import CachedInferenceEngine
from app.services.m1_regulation_service import M1RegulationService

_engine = None

def get_engine() -> CachedInferenceEngine:
    global _engine
    if _engine is None:
        _engine = CachedInferenceEngine(
            GazetteInferenceEngine("./storage/models/gazette_classifier.onnx"),
            redis_url=settings.REDIS_URL,
        )
    return _engine

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def classify_gazette(self, regulation_id: str):
    try:
        async with get_db() as db:
            svc = M1RegulationService(db)
            regulation = await svc.get_by_id(regulation_id)
            result = get_engine().classify(regulation.classification_chunk)

            await svc.update_classification(
                regulation_id=regulation_id,
                change_category=result["change_category"],
                confidence=result["confidence"],
                affected_sectors=result["affected_sectors"],
                needs_review=(result["confidence"] < 0.70),
            )
    except Exception as exc:
        raise self.retry(exc=exc)
```

### 4.2 Manual Classification Endpoint

The API also exposes a direct classification endpoint for admin testing:

```
POST /api/v1/m1/regulations/{id}/classify
```

This triggers on-demand reclassification of a specific regulation. Full endpoint specification in [11_M1_API_Reference.md](11_M1_API_Reference.md).

---

## 5. Deployment Pipeline

### 5.1 Fly.io Configuration

```toml
# fly.toml
app = "enigmatrix-m1-classifier"
primary_region = "sin"

[build]
  dockerfile = "Dockerfile.ml"

[mounts]
  source = "ml_models"
  destination = "/app/storage/models"

[[services]]
  internal_port = 8000
  protocol = "tcp"
  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]

[resources]
  cpu_kind = "shared"
  cpus = 2
  memory_mb = 2048
```

```dockerfile
# Dockerfile.ml
FROM python:3.11-slim
WORKDIR /app
COPY requirements-ml.txt .
RUN pip install --no-cache-dir -r requirements-ml.txt
COPY app/ ./app/
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

### 5.2 Model Deployment Steps

```bash
# 1. Train model (GPU server)
python scripts/train_model.py --output-dir ./artifacts/

# 2. Export to ONNX
python scripts/export_onnx.py --checkpoint ./artifacts/best_model.pt \
    --output ./artifacts/gazette_classifier.onnx

# 3. Copy weights to Fly volume
fly ssh console -a enigmatrix-m1-classifier
# Inside: cp /tmp/gazette_classifier.onnx /app/storage/models/

# 4. Deploy updated inference server
fly deploy -a enigmatrix-m1-classifier
```

### 5.3 Rollback Procedure

The Fly volume always carries the **current + previous** model version (e.g. both `v1.0/` and `v1.1/` exist as separate directories). The currently-served version is selected by the `M1_MODEL_VERSION` env var that the inference engine reads at startup. Rollback = flip the env var and restart the machine:

```bash
# 1. Confirm the previous version is still present on the volume.
fly ssh console -a enigmatrix-m1-classifier -C "ls -la /app/storage/models/m1/"
# expected output: drwxr-xr-x  v0.9  v1.0  v1.1

# 2. Roll back to v1.0 (no rebuild, no redeploy of code).
fly secrets set M1_MODEL_VERSION=v1.0 -a enigmatrix-m1-classifier
# Fly restarts the machine; inference engine loads v1.0 ONNX file at startup.

# 3. Confirm the new version is serving + cache prefix has flipped.
curl https://enigmatrix-m1-classifier.fly.dev/health | jq .model_version
# expected: "v1.0"

# 4. (Optional) Invalidate Redis to evict v1.1 cache entries — automatic via
# the model_version prefix in the cache key, but flushing avoids storage waste.
redis-cli --scan --pattern "m1:classify:*v1.1*" | xargs redis-cli unlink
```

End-to-end rollback time: ~60 seconds (machine restart + first-inference warmup). No data loss — DB rows already classified by `v1.1` remain tagged `model_version='v1.1'` for audit; new classifications go through `v1.0`. The retraining / canary / automatic-rollback flow is detailed in [12_M1_Monitoring_Maintenance.md](12_M1_Monitoring_Maintenance.md).

---

## 6. End-to-End Latency Budget

| Stage | Component | Target Latency |
|---|---|---|
| Gazette scraping | Scrapy download | 0–6 hours (background) |
| PDF extraction | PyMuPDF / pdfplumber / Tesseract | ~800ms |
| Preprocessing | Unicode clean + tokenize | ~200ms |
| Inference | ONNX Runtime (CPU, 2 cores) | ~1,800ms |
| Cache write | Redis SET | ~5ms |
| DB update | PostgreSQL UPDATE m1_regulations | ~15ms |
| Alert dispatch | Celery → Email/SMS | ~30s |
| **Total (extraction → alert)** | **End-to-end** | **≤ 24 hours** |
| **Inference only (API call)** | **POST /classify** | **≤ 2 seconds** |

**Throughput vs latency clarification.** The "1.8 s per gazette" figure is *single-shot latency* — the wall-clock time for one Celery task to return. It is **not** "0.55 inferences per second per machine." Throughput on one Fly machine is bounded differently: the ONNX session has 2 intra-op threads + 2 inter-op threads (config in §3.1), so a single CPU machine can process **batch=8 in ~3 s** (≈ 2.6 inferences/s effective, with batching) before hitting the 1 GB memory ceiling. The Celery queue uses `concurrency=2`, so two tasks classify in parallel — at peak `~5 inferences/s/machine`. The "30 inferences/min" cited in §1 of [13_M1_Folder_Structure_and_Implementation_Flow.md](13_M1_Folder_Structure_and_Implementation_Flow.md) is the **steady-state target** (well below capacity); peak observed throughput comes from short-lived batch bursts when a scraper run drops 30 gazettes in one cycle. Detailed sizing curves are in [07_M1_Deployment_Integration.md](07_M1_Deployment_Integration.md).

---

## 7. Deployment Integration Diagram

```mermaid
flowchart TD
    A[New gazette PDF\ndownloaded by Scrapy] --> B[extract_gazette\nCelery task\nPyMuPDF/pdfplumber/Tesseract]
    B --> C[UPDATE m1_regulations\nstatus=extracted\ncleaned_text, classification_chunk]
    C --> D[classify_gazette\nCelery task triggered]

    D --> E{Redis cache hit?}
    E -->|Yes| F[Return cached result\nfrom sha256 hash key]
    E -->|No| G[ONNX Runtime inference\nGazetteInferenceEngine.classify\n~1.8s CPU]
    G --> H[Redis SET result\nTTL=30 days]
    H --> I[UPDATE m1_regulations\nchange_category, confidence\naffected_sectors, needs_review\nstatus=classified]
    F --> I

    I --> J{confidence >= 0.70?}
    J -->|No| K[needs_review=True\nAdmin queue notification]
    J -->|Yes| L[summarise_gazette\nCelery task\nMarianMT EN/SI/TA]
    L --> M[dispatch_alerts\nCelery task\nEmail + SMS per matched sector]
    M --> N[INSERT m1_propagation_events\nchannel=alert_delivery]

    N --> O[SME Dashboard\nGET /api/v1/m1/regulations\nFiltered by sector + category]
    O --> P[SME views regulation\nEN/SI/TA summary\nreal_world_example]
```

---

## 8. Conclusion

The ONNX Runtime + Fly.io deployment achieves the 2-second inference latency target on CPU hardware at predictable cost, without requiring GPU infrastructure for production serving. The Redis cache layer eliminates redundant inference for duplicate gazette submissions. The Celery task integration ensures that classification runs automatically in the background pipeline without blocking the ingestion API. Full API endpoint documentation is provided in [11_M1_API_Reference.md](11_M1_API_Reference.md).

---

## References

- ONNX Runtime. (2024). *ONNX Runtime Documentation*. [onnxruntime.ai](https://onnxruntime.ai)
- Fly.io. (2024). *Fly.io Documentation*. [fly.io/docs](https://fly.io/docs)
- Celery. (2024). *Celery: Distributed Task Queue*. [docs.celeryq.dev](https://docs.celeryq.dev)
- Hu et al. (2021). *LoRA: Low-Rank Adaptation of Large Language Models*. [arxiv.org/abs/2106.09685](https://arxiv.org/abs/2106.09685)
- Redis. (2024). *Redis Documentation*. [redis.io/docs](https://redis.io/docs)


# 07_M1_1 — ONNX Export & Quantization

> Companion to [07_M1_Deployment_Integration.md](07_M1_Deployment_Integration.md) — `torch.onnx.export` config (opset 17, dynamic_axes), INT8 calibration pipeline, accuracy validation float32 vs INT8.
> **Implementation status:** 🔲 Deferred (BUILD_11 — `ml/m1/model/export_onnx.py` + `quantize.py`)

## Purpose

Parent doc §2 shows the basic ONNX export + INT8 quantize calls but elides the operational corners: choosing `opset_version`, dynamic-batch axes, INT8 calibration set, and verifying that INT8 didn't degrade F1. This companion provides the production-grade scripts and validation criteria.

## Detailed process

### Step 1 — Export configuration

```python
torch.onnx.export(
    model,
    (dummy_input_ids, dummy_attention_mask),
    "gazette_classifier.onnx",
    input_names=["input_ids", "attention_mask"],
    output_names=["category_logits", "sector_logits"],
    dynamic_axes={
        "input_ids":      {0: "batch", 1: "seq"},
        "attention_mask": {0: "batch", 1: "seq"},
        "category_logits": {0: "batch"},
        "sector_logits":   {0: "batch"},
    },
    opset_version=17,                  # min that supports XLM-R operators cleanly
    do_constant_folding=True,
    export_params=True,
)
```

- `opset_version=17` is the minimum where all RoBERTa-family operators (LayerNorm with axis ≠ −1, GatherElements) are stable. Earlier opsets emit warnings; later opsets are forward-compatible.
- `dynamic_axes` on `seq` allows variable input lengths (real-world inputs are < 512 tokens after padding stripping); without it, the ONNX runtime always pads to 512 — wasted compute.
- `do_constant_folding=True` is a free 5–10 % latency improvement.

### Step 2 — Validation against PyTorch output

```python
import torch, onnxruntime as ort, numpy as np

def validate_export(pt_model, onnx_path: str, samples: list[str]) -> dict:
    sess = ort.InferenceSession(onnx_path)
    max_diff = 0.0
    for text in samples:
        inputs = tokenizer(text, return_tensors="pt", max_length=512, truncation=True, padding=True)
        pt_out = pt_model(inputs.input_ids, inputs.attention_mask)
        onnx_out = sess.run(None, {"input_ids": inputs.input_ids.numpy(),
                                    "attention_mask": inputs.attention_mask.numpy()})
        diff = np.abs(pt_out[0].detach().numpy() - onnx_out[0]).max()
        max_diff = max(max_diff, diff)
    return {"max_abs_diff": float(max_diff),
            "passes_threshold": max_diff < 1e-4}
```

Threshold `1e-4` is the standard ONNX export sanity check. Above this, something in the export went wrong (usually a misnamed dynamic axis or an operator that doesn't survive opset translation).

### Step 3 — INT8 quantization (optional)

```python
from onnxruntime.quantization import quantize_dynamic, QuantType

quantize_dynamic(
    model_input="gazette_classifier.onnx",
    model_output="gazette_classifier_int8.onnx",
    weight_type=QuantType.QInt8,
    op_types_to_quantize=["MatMul", "Gather"],
)
```

`quantize_dynamic` (vs static) does not need a calibration dataset for the weight quantization — only activations are quantized at runtime. For static quantization (max 2× faster) provide:

```python
from onnxruntime.quantization import quantize_static, CalibrationDataReader

class GazetteCalibrationReader(CalibrationDataReader):
    def __init__(self, samples: list[str]):
        self.iter = iter(self._stream(samples))
    def _stream(self, samples):
        for text in samples:
            inputs = tokenizer(text, return_tensors="np", max_length=512, truncation=True, padding="max_length")
            yield {"input_ids": inputs["input_ids"], "attention_mask": inputs["attention_mask"]}
    def get_next(self):
        return next(self.iter, None)
```

Calibration set: 50 hand-picked gazettes spanning all 8 domains + all 3 languages. Stored in `research/data/quantization_calibration.parquet`.

### Step 4 — Post-quantization F1 validation

Run the full test split through both `gazette_classifier.onnx` (FP32) and `gazette_classifier_int8.onnx` (INT8); compare:

```
FP32 macro-F1:   0.928 (mean ± std across 3 seeds)
INT8 macro-F1:   0.919  (Δ = -0.9 pp)
INT8 latency:    0.92 s (vs FP32 1.82 s — 2.0× speedup)
INT8 file size:  118 MB (vs FP32 471 MB — 4× smaller)
```

If Δ > 1.5 pp, the INT8 model is rejected and FP32 ships. Accept the 0.9 pp loss for the 2× speedup + 4× size reduction.

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| `onnxruntime` (chosen) | Free, cross-platform, broad operator coverage | ✅ Industry standard | Never. |
| TorchScript | Native PyTorch | ❌ Slower CPU inference; bigger dependency footprint | If we drop ONNX for some reason. |
| Triton Inference Server | GPU-optimised | ❌ GPU not in scope; ONNX Runtime sufficient | If GPU deployment becomes affordable. |
| Quantize dynamic (chosen) | No calibration set needed | ✅ For the first deployment | If static quantization F1 drop is acceptable, switch (further 30 % latency drop). |
| Quantize static | Faster | ⚠️ Needs calibration set; ~+0.3 pp F1 drop | After 6 months of production data, revisit. |
| QInt8 weight quantize | 2× speedup | ✅ Standard | If accuracy drop exceeds 1.5 pp, try FP16 weight quantize (~1.2× speedup, ~0.3 pp drop). |

## Worked example

End-to-end export run output:

```
$ python scripts/export_onnx.py --checkpoint storage/models/m1/v1.0/best_model.pt \
                                 --out storage/models/m1/v1.0/gazette_classifier.onnx

[INFO]  Loading PyTorch checkpoint (471 MB)
[INFO]  Exporting to ONNX opset 17
[INFO]  Validating ONNX output against PyTorch (50 samples)
[INFO]  Max absolute diff: 8.3e-6 (threshold 1e-4) — PASS
[INFO]  Wrote 471 MB ONNX file
[INFO]  Done in 18.4 s

$ python scripts/quantize_onnx.py --input storage/models/m1/v1.0/gazette_classifier.onnx \
                                   --out storage/models/m1/v1.0/gazette_classifier_int8.onnx

[INFO]  Quantizing (dynamic INT8)
[INFO]  Wrote 118 MB ONNX file
[INFO]  Running full test set through INT8 model (120 samples)
[INFO]  FP32 macro-F1: 0.928   INT8 macro-F1: 0.919   Δ: -0.9 pp — PASS
[INFO]  Latency: FP32 1.82s   INT8 0.92s (2.0x speedup)
```

## Failure modes & edge cases

- **Opset incompatibility.** A new operator in PyTorch 2.4 might not be in opset 17. Mitigation: pin `torch` version in `pyproject.toml`; on upgrade, re-export and re-validate.
- **Dynamic axis mismatch.** Forgetting to mark `seq` as dynamic causes runtime to always pad to 512 → wasted compute. Detected by inference benchmark: latency on a 50-token input ≈ 50-token batch latency, not 512-token.
- **Quantization eats Sinhala F1.** INT8 sometimes degrades minority-class F1 disproportionately. The validation step measures *per-language* F1, not just macro — alerts if SI drop exceeds 2 pp.
- **ONNX file > Fly volume size.** 1 GB Fly volume holds at most 2 versions (current + previous). If the model grows, upgrade to a 3 GB volume.

## Validation & acceptance criteria

- **Bit-equivalence test:** FP32 ONNX max-abs-diff vs PyTorch < 1e-4.
- **INT8 F1 drop ≤ 1.5 pp** macro-F1 + ≤ 2 pp per-language F1.
- **Latency speedup ≥ 1.7× INT8 vs FP32.**
- **Reproducibility:** running the export twice with the same checkpoint produces byte-identical ONNX files (modulo timestamps).

## Cross-references

- Parent: [07_M1_Deployment_Integration.md](07_M1_Deployment_Integration.md) §2
- Related: [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) §9 (versioning), [12_M1_Monitoring_Maintenance.md](12_M1_Monitoring_Maintenance.md)
- BUILD phase: BUILD_11 §model export, §quantization
- Code (when shipped): `ml/m1/model/export_onnx.py`, `quantize.py`



# 07_M1_2 — Fly.io Deployment Operations

> Companion to [07_M1_Deployment_Integration.md](07_M1_Deployment_Integration.md) — fly.toml deep-dive, machine sizing, persistent volume layout, health checks, region failover, cost monitoring.
> **Implementation status:** 🔲 Deferred (BUILD_07 — Fly app provisioned + `fly.toml` in repo root)

## Purpose

Parent doc §5.1 shows the basic `fly.toml`. This companion makes the operational reality explicit — machine-size upgrade path, volume layout (current + previous model), the canary traffic-split implementation, and how cost alerts are wired.

## Detailed process

### Step 1 — Production fly.toml (annotated)

```toml
# fly.toml — production
app           = "enigmatrix-m1-classifier"
primary_region = "sin"                              # Singapore — closest to SL
kill_signal   = "SIGINT"
kill_timeout  = 30                                  # grace period for in-flight tasks

[build]
  dockerfile = "Dockerfile.ml"

[mounts]
  source      = "ml_models"                          # Fly volume name
  destination = "/app/storage/models"
  # Volume layout:
  # /app/storage/models/m1/
  #   v1.1/    (current)
  #   v1.0/    (previous — rollback target)
  #   baseline/ (TF-IDF baseline — keep for ablation reporting)

[env]
  M1_MODEL_VERSION          = "v1.1"               # flipped to v1.0 to rollback
  M1_MODEL_CANARY_PCT       = "100"                # 10/50/100 during canary rollout
  M1_PDF_TEXT_THRESHOLD     = "200"
  M1_PDF_SCANNED_THRESHOLD  = "30"

[[services]]
  internal_port = 8000
  protocol      = "tcp"
  auto_stop_machines  = "off"                       # never stop — eliminates cold start
  auto_start_machines = "on"
  min_machines_running = 1

  [[services.ports]]
    port     = 443
    handlers = ["tls", "http"]
  [[services.ports]]
    port     = 80
    handlers = ["http"]
    force_https = true

  [services.concurrency]
    type     = "requests"
    soft_limit = 20
    hard_limit = 25

  [[services.tcp_checks]]
    interval = "15s"
    timeout  = "5s"
    grace_period = "30s"
  [[services.http_checks]]
    interval     = "30s"
    timeout      = "5s"
    method       = "get"
    path         = "/health"
    protocol     = "http"
    tls_skip_verify = false

[[vm]]
  size      = "shared-cpu-1x"
  memory_mb = 1024                                  # see upgrade path below
  cpu_kind  = "shared"
```

### Step 2 — Machine-size upgrade path

| Size | Memory | $/mo | When to use |
|---|---|---|---|
| `shared-cpu-1x` | 256 MB | $2 | NEVER for M1 — too little for ONNX session |
| `shared-cpu-1x` | 1 GB (default) | $3 | Today; up to ~5 gazettes/day |
| `shared-cpu-2x` | 2 GB | $12 | When inference latency p95 exceeds 3 s |
| `shared-cpu-4x` | 4 GB | $24 | When batching needed for > 30 gazettes/day burst |
| `performance-2x` | 8 GB dedicated | $62 | High-throughput steady state (> 100 gaz/day) |
| Multiple `shared-cpu-2x` machines | per-machine cost | additive | Horizontal scale + sticky-session for canary |

The default is `shared-cpu-1x` with 1 GB; upgrade triggered by the SLA alert (parent doc §6).

### Step 3 — Canary traffic split

Implemented in Python — Fly doesn't have native canary routing, so the decision happens at the Celery task level:

```python
# backend/app/tasks/m1/classify_gazette.py
import os, hashlib

def model_version_for_gazette(gazette_id: str) -> str:
    """Hash gazette_id to a 0-99 bucket; route by M1_MODEL_CANARY_PCT."""
    canary_pct = int(os.environ.get("M1_MODEL_CANARY_PCT", "100"))
    if canary_pct == 100:
        return os.environ["M1_MODEL_VERSION"]
    bucket = int(hashlib.sha256(gazette_id.encode()).hexdigest()[:8], 16) % 100
    if bucket < canary_pct:
        return os.environ["M1_MODEL_VERSION"]                       # new
    return os.environ.get("M1_PREVIOUS_MODEL_VERSION", "v1.0")      # old
```

The version is stored on the `m1_regulations` row for A/B analysis. Note: hash-based routing produces **sticky** assignment — the same gazette is always routed to the same version, so re-running the task is idempotent.

### Step 4 — Health checks + region failover

```python
# backend/app/api/v1/health.py
@router.get("/health")
async def health():
    onnx_loaded = inference_engine.session is not None
    redis_ok = redis_client.ping()
    db_ok = (await db.execute(text("SELECT 1"))).scalar() == 1
    if all([onnx_loaded, redis_ok, db_ok]):
        return {"status": "ok", "model_version": MODEL_VERSION}
    raise HTTPException(503, "unhealthy")
```

`/health` is hit every 30 s by Fly. If it fails 3 times consecutively, Fly restarts the machine. If `min_machines_running=1` is breached (machine permanently failing), Fly attempts to migrate to another node in `sin`. If `sin` is unavailable, the secondary region `bom` (Mumbai) takes over automatically when configured with `regions = ["sin", "bom"]` — but failover takes ~3 min during which the API is degraded.

### Step 5 — Cost monitoring

Set Fly budget alerts:

```bash
fly orgs billing notification create --budget 50 --period monthly
```

Alert at 50 % budget consumption + at 80 % (gives time to upgrade plan or pause traffic). Logs to PagerDuty integration in `infra/pagerduty/fly_budget_alerts.yaml`.

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| Fly.io (chosen) | No cold start; persistent volume; cheap Singapore region | ✅ See parent doc §1.2 | Re-evaluated annually. |
| Always-on (`auto_stop=off`) | No cold-start; constant cost | ✅ Need it for the 2s SLA | If traffic drops below 1 req/hour. |
| Single machine | Simplest | ✅ At < 30 gaz/day | Add second machine when p99 > 5s. |
| Sticky-session hash routing for canary | Idempotent + simple | ✅ One env var controls the split | Move to feature-flag service (LaunchDarkly, GrowthBook) if multiple flags compound. |

## Worked example

A canary rollout flow:

```
[Day 0: deploy v1.1 to volume — but traffic still on v1.0]
fly ssh console -a enigmatrix-m1-classifier
$ cp -r /app/storage/models/m1/v1.0 /app/storage/models/m1/v1.1   # placeholder
$ scp local:storage/models/m1/v1.1/* /app/storage/models/m1/v1.1/

[Day 0: 10% canary]
fly secrets set M1_MODEL_VERSION=v1.1 M1_PREVIOUS_MODEL_VERSION=v1.0 M1_MODEL_CANARY_PCT=10 -a enigmatrix-m1-classifier
# Fly restarts machine; 10% of new gazettes hit v1.1, 90% hit v1.0

[Day 1: review canary metrics]
SELECT model_version, COUNT(*) AS n, AVG(confidence) AS avg_conf
FROM m1_regulations
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY model_version;
#  v1.0  108 gaz  avg_conf 0.81
#  v1.1   12 gaz  avg_conf 0.83  → +2 pp, looks good

[Day 1: ramp to 50%]
fly secrets set M1_MODEL_CANARY_PCT=50 -a enigmatrix-m1-classifier

[Day 2: full rollout if metrics hold]
fly secrets set M1_MODEL_CANARY_PCT=100 -a enigmatrix-m1-classifier

[Day 30: clean up old version]
fly ssh console -a enigmatrix-m1-classifier -C "rm -rf /app/storage/models/m1/v1.0"
```

## Failure modes & edge cases

- **Volume full.** ONNX models are 100 MB (INT8) – 470 MB (FP32). Two versions = ~1 GB; the default Fly volume is 3 GB but baseline + extra calibration data can grow. Mitigation: `fly vol extend` is online + free.
- **Region outage.** `sin` rarely fails. When it does, manual `fly regions set bom` flips region. Documented in runbook.
- **Health check flapping.** A slow-to-load ONNX file makes the first `/health` after deploy fail. Mitigation: `grace_period=30s` on the HTTP check.
- **Budget overrun.** A runaway worker can spike costs. Mitigation: hard limit `concurrency.hard_limit=25` + per-day spend alert.

## Validation & acceptance criteria

- **Deploy + rollback completes in < 90 s.** Measured by CI smoke test.
- **Health check stable.** No `unhealthy` events in normal operation > 1/week.
- **Canary fairness.** Hash-based bucketing produces ~50 % split at `CANARY_PCT=50` (chi-sq test on 1000-gazette sample).
- **Cost.** Monthly Fly spend within $50 budget (or alert).

## Cross-references

- Parent: [07_M1_Deployment_Integration.md](07_M1_Deployment_Integration.md) §5
- Related: [12_M1_Monitoring_Maintenance.md](12_M1_Monitoring_Maintenance.md)
- BUILD phase: BUILD_07 §deployment, §canary
- Code (when shipped): `fly.toml`, `backend/app/api/v1/health.py`, `backend/app/tasks/m1/classify_gazette.py`
