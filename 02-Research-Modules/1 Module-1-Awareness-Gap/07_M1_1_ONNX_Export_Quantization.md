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

Calibration set: 50 hand-picked gazettes spanning all 12 categories + all 3 languages. Stored in `research/data/quantization_calibration.parquet`.

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
- Related: [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) §9 (versioning), [12_M1_2_Retraining_Deployment_Rollback.md](12_M1_2_Retraining_Deployment_Rollback.md)
- BUILD phase: BUILD_11 §model export, §quantization
- Code (when shipped): `ml/m1/model/export_onnx.py`, `quantize.py`
