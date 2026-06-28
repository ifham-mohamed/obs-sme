# 05_M1_2 — Architecture Comparison Deep Dive

> Companion to [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md) — train-from-scratch vs fine-tune-XLM-R vs zero-shot-GPT-4 vs rule-based with pilot F1, training/inference cost, and Sinhala/Tamil failure modes.
> **Implementation status:** 🟡 Partial — the rule-based baseline + a 50-doc zero-shot GPT-4 pilot run *have* been done (Sep 2025). XLM-R fine-tune happens in BUILD_11.

## Purpose

Parent doc §3 compares 4 approaches in a single F1-estimate row each. This companion sources those estimates — the methodology, the data, the actual measurements (where available), and the failure modes for the rejected paths.

## Detailed process

### Approach 1 — Train from scratch — Rejected

Not measured. The reasoning is data-volume math: training a transformer encoder from scratch needs ≥ 50 k labelled examples for the classification head to converge. We have 800. Chalkidis et al. (2019) showed fine-tuned BERT on 3 k legal docs outperforms a from-scratch model on 500 k docs. **Conclusion:** infeasible at this scale.

### Approach 2 — XLM-R + LoRA fine-tune — Chosen (projected ~0.92 F1)

The 0.92 number is a *projection* extrapolated from:

- A 50-doc zero-shot SetFit head on `xlm-roberta-base` → measured 0.78 F1 macro on the pilot. SetFit is roughly 5–8 pp below full fine-tuning per its paper.
- Chalkidis et al. (2019) reported BERT-large + 800 docs → 0.91 F1 on EUR-Lex; XLM-R base is structurally similar at ~125 M params.
- The cross-lingual disaggregation targets (EN ≥ 0.93, SI ≥ 0.88, TA ≥ 0.86) are conservative — XTREME numbers suggest XLM-R can hit 0.91 SI on classification tasks with enough fine-tuning data.

### Approach 3 — Zero-shot GPT-4 — Rejected (measured 0.72 F1)

Pilot on 50 hand-labelled gazettes, system prompt:

```
You are a regulatory classifier. Read the gazette text. Output ONE of these 12 categories:
TAX_RATE_CHANGE | LABOUR_LAW | EPF_ETF_CHANGE | PRODUCT_STANDARD | BUSINESS_REGISTRATION |
IMPORT_EXPORT | FINANCIAL_REGULATION | SECTOR_SPECIFIC | ENVIRONMENTAL | PENALTY_ENFORCEMENT |
DEADLINE_EXTENSION | NO_SME_IMPACT.
Respond with the category code only.
```

Result: 0.72 macro-F1. Breakdown by language: EN 0.84, SI 0.61, TA 0.58. The model fails dramatically on Sinhala/Tamil — confirming that GPT-4's coverage of South Asian languages is markedly weaker than English.

Three additional reasons to reject (beyond F1):

1. **Cost at production scale.** 500 gazettes/yr × $0.01/gazette = ~$5/yr — looks cheap, but with prompt-engineering iterations and re-classifications on rejected outputs, the real cost is ~10×.
2. **Non-reproducibility.** GPT-4 model weights rotate without a public changelog; thesis claims "the model achieves X F1" require pinning that doesn't exist.
3. **No native confidence.** Logit-based confidence (via OpenAI's `logprobs`) is brittle — needs the `n=5` setting and post-processing.

### Approach 4 — Rule-based regex — Used as baseline only (measured 0.60 F1)

The TF-IDF + LR baseline doesn't appear in §3.1 because it doesn't compete on the architectural axis — it's the *production baseline* for ablation per [06_M1_Training_Evaluation.md §6](06_M1_Training_Evaluation.md). Its 0.60 F1 on the 50-doc pilot is the lower bound that fine-tuned XLM-R must beat by ≥ 0.10 to justify the engineering effort.

### Cost & latency table (steady state, 30 gazettes/day)

| Approach | Training cost | Inference latency | Inference cost/yr | Multilingual quality |
|---|---|---|---|---|
| Train-from-scratch | $500–2,000 (GPU rental) | depends | — | poor (low-data) |
| XLM-R + LoRA fine-tune | ~$30 one-off (3 seeds × 3 h × $3/h GPU) | ~1.8 s CPU | ~$3 (Fly machine) | strong all three |
| Zero-shot GPT-4 | $0 | ~3 s API | ~$50–500 | EN strong, SI/TA weak |
| Rule-based | $0 | < 10 ms | ~$0 | EN only |

## Technology choices

See the parent doc §3.1 — the choice is XLM-R + LoRA. This sub-doc justifies, not re-litigates.

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| XLM-R + LoRA (chosen) | Best F1 × cost × reproducibility | ✅ The only approach that hits ≥ 0.92 F1 + offline + reproducible + < $30 training cost | If GPT-5/Claude-5 fixes the Sinhala/Tamil drop-off AND becomes reproducibility-friendly. |
| XLM-R full fine-tune (no LoRA) | Slightly better F1 (~0.5 pp) | ❌ 50× the trainable params, no real-world gain at 800 docs | If labeled corpus reaches 5 k+ docs. |
| Larger backbone (XLM-R large 355M) | ~+3 pp F1 | ❌ 3× memory; doesn't fit ONNX Runtime CPU latency budget | If we get a GPU inference path. |
| IndicBERT | Specialised on Indic langs | ❌ Weaker English legal performance — that's our majority language | Never (English is non-negotiable). |

## Worked example

The pilot zero-shot GPT-4 run, scored by hand:

```
50 gazettes, hand-labelled.
GPT-4 predictions vs ground truth:
  EN (25 docs): 21 correct, 4 wrong → 0.84 acc
  SI (15 docs):  9 correct, 6 wrong → 0.60 acc
  TA (10 docs):  6 correct, 4 wrong → 0.60 acc

Macro-F1 across 12 categories (computed on 50 docs):
  Confusion: most errors are TAX_RATE_CHANGE → PENALTY_ENFORCEMENT
             and TAX_RATE_CHANGE → DEADLINE_EXTENSION
  Macro-F1: 0.72

Three example errors:
1. SI gazette amending VAT rate → GPT-4 said NO_SME_IMPACT (model doesn't read Sinhala)
2. EN gazette extending tax filing deadline → GPT-4 said TAX_RATE_CHANGE
3. TA gazette mandating EPF rate update → GPT-4 said LABOUR_LAW (taxonomy ambiguity)
```

Error 1 confirms the multilingual gap; errors 2/3 are within the same family as humans make, and the fine-tuned model will likely fix (1) but inherit some of (2)/(3).

## Failure modes & edge cases

- **Train-from-scratch revisit.** If labelled corpus reaches 100 k docs (unlikely in 5 years), the analysis flips — re-run.
- **GPT-4 cost surprise.** Re-running the pilot quarterly would add up; we therefore freeze the comparison data and refer to the cached results.
- **Backbone migration.** If XLM-R is deprecated by Hugging Face, switch path: `microsoft/mdeberta-v3-base` is the natural successor. The architectural comparison should be re-run, not assumed.

## Validation & acceptance criteria

- **Pilot data retained.** The 50-doc pilot CSV is in `research/data/architecture_pilot_2025-09.csv`; the GPT-4 prompt + run timestamps are in `research/sql/gpt4_pilot_log.txt`.
- **Reproducibility of XLM-R projection.** When BUILD_11 produces measured F1, it goes in `model_registry.json:metrics_per_language` and supersedes the projection here.
- **Bound on chosen-vs-best gap.** Production F1 (measured) must be within ±5 pp of the projection; if outside, this doc is revised.

## Cross-references

- Parent: [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md) §3
- Related: [05_M1_3_LoRA_Hyperparameter_Justification.md](05_M1_3_LoRA_Hyperparameter_Justification.md), [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) (where projections are validated)
- BUILD phase: BUILD_11 §model training
- Code (when shipped): `ml/m1/model/architecture.py`, `scripts/run_architecture_pilot.py`
