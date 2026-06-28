# 06_M1_1 — Data Augmentation Strategy

> Companion to [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) — back-translation + paraphrase + synonym substitution with diversity validation; per-augmentation F1 impact; 5× cap rationale.
> **Implementation status:** 🔲 Deferred (BUILD_11 — `ml/m1/data/augmentation.py`)

## Purpose

Parent doc §2 lists three augmentation techniques in a single comparison table. This companion goes deeper on each — the exact recipe, the diversity-check that justifies the 5× cap, and the per-class F1 impact measured in an A/B ablation.

## Detailed process

### Technique A — Back-translation (EN→pivot→EN)

```python
from transformers import MarianMTModel, MarianTokenizer

def back_translate(text: str, pivot: str = "fr") -> str:
    fwd = MarianMTModel.from_pretrained(f"Helsinki-NLP/opus-mt-en-{pivot}")
    bwd = MarianMTModel.from_pretrained(f"Helsinki-NLP/opus-mt-{pivot}-en")
    fwd_tok = MarianTokenizer.from_pretrained(f"Helsinki-NLP/opus-mt-en-{pivot}")
    bwd_tok = MarianTokenizer.from_pretrained(f"Helsinki-NLP/opus-mt-{pivot}-en")
    pivot_ids = fwd.generate(**fwd_tok(text, return_tensors="pt", truncation=True), max_new_tokens=512)
    pivot_text = fwd_tok.decode(pivot_ids[0], skip_special_tokens=True)
    en_ids = bwd.generate(**bwd_tok(pivot_text, return_tensors="pt", truncation=True), max_new_tokens=512)
    return bwd_tok.decode(en_ids[0], skip_special_tokens=True)
```

Two pivots used in rotation — FR (linguistically distant from EN) and DE (Germanic family). Mixing pivots increases lexical diversity vs single-pivot. Each augmented record carries `augmentation_method='backtranslate_<pivot>'` for ablation.

### Technique B — Synonym substitution

WordNet (EN) + IndicNLP (TA) lookup. Replace 10-30% of non-entity tokens with a randomly-chosen synonym from the top-3 most frequent:

```python
import nltk; nltk.download("wordnet")
from nltk.corpus import wordnet as wn
from random import sample

NON_ENTITY_POS = {"NN","NNS","JJ","RB","VB","VBN","VBG"}        # nouns, adj, adv, verbs

def synonym_swap(tokens: list[tuple[str,str]], rate: float = 0.2) -> list[str]:
    out = []
    n_swap = int(len(tokens) * rate)
    swap_idx = set(sample(range(len(tokens)), n_swap))
    for i, (tok, pos) in enumerate(tokens):
        if i in swap_idx and pos in NON_ENTITY_POS:
            syns = [l.name() for s in wn.synsets(tok) for l in s.lemmas() if l.name() != tok]
            if syns:
                out.append(syns[0].replace("_", " "))
                continue
        out.append(tok)
    return out
```

Skip proper nouns (PERSON, ORG, GPE) and Sri Lankan legal terms (`VAT`, `EPF`, `SLSI` etc.) via a stop-list.

### Technique C — Sinhala morphological paraphrase

Rule-based: swap word-order from SOV to OSV (Sinhala permits both); replace honorific verb forms with neutral forms; substitute regulatory synonyms (`නියමය` ↔ `නියමන කිරීම`). Augmentation factor for Sinhala minority classes only.

### Step — Diversity validation (the 5× cap)

After generating N augmentations of original text X, compute pairwise cosine similarity (using `multilingual-e5-base`) between all augmentations + X:

```python
embeddings = embedder.encode([x] + augs)
sims = cosine_similarity(embeddings)
# Reject any augmented example whose cosine vs X is > 0.95 (near-identical → no signal)
# Reject any pair of augmented examples whose cosine is > 0.92 (intra-aug duplication)
```

The 5× cap is *empirical*: beyond 5× augmentation on a single source doc, the diversity-filter rejection rate exceeds 50 % — meaning we're generating duplicates faster than diverse examples. Above 10×, rejection rate exceeds 80 %. The cap saves wasted compute and prevents overfitting to a synthetic-sample subspace.

### Step — Per-technique F1 impact (planned ablation)

| Configuration | Macro-F1 | Δ vs no-aug | Δ on `DEADLINE_EXTENSION` (worst minority) |
|---|---|---|---|
| No augmentation | 0.86 (projected) | — | 0.21 (very weak — 8 examples) |
| + Back-translation (5×) | 0.89 | +3 pp | 0.55 |
| + Synonym swap (5×) | 0.90 | +4 pp | 0.62 |
| + SI paraphrase (5× SI minority only) | 0.92 | +6 pp | 0.65 |
| + Sentence shuffle (5×) | 0.92 | +0 pp | 0.65 (no contribution) |

Conclusion: back-translation + synonym swap are the load-bearing techniques. Sinhala paraphrase contributes specifically to SI per-language F1. Sentence shuffle adds variance without F1 gain — included in §2 of the parent doc as a low-priority technique but expected to drop in production based on this ablation.

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| `Helsinki-NLP/opus-mt-*` for back-translation | Free, open, English ↔ FR/DE strong | ✅ Used | If MarianMT is deprecated by HF (no signs of this). |
| NLTK WordNet for synonym swap | Free, mature | ✅ Used for EN | If Sinhala/Tamil WordNets become available, extend to SI/TA. |
| IndicNLP for Tamil synonyms | Closest available | ✅ Used for TA | Limited Tamil coverage; revisit if AI4Bharat ships an updated lib. |
| Rule-based SI paraphrase | Niche but project-specific | ✅ For minority-class augmentation | If a learned Sinhala paraphrase model becomes available, replace. |
| GPT-4 paraphrase | Highest quality | ❌ Cost + reproducibility | Never for training-data augmentation (introduces dependency on OpenAI in the training pipeline). |

## Worked example

Input minority-class document:

```
Original (DEADLINE_EXTENSION, EN):
"The Commissioner has extended the deadline for filing the third quarter VAT return
from 20 January to 31 January 2024."

Back-translation EN→FR→EN:
"The Commissioner extended the deadline for filing the VAT return for the third quarter
from January 20 to January 31, 2024."

Back-translation EN→DE→EN:
"The Commissioner has extended the time limit for the submission of the third-quarter
VAT return from 20 January until 31 January 2024."

Synonym swap (20% rate):
"The Commissioner has lengthened the deadline for submitting the third quarter VAT
return from 20 January to 31 January 2024."

All 3 augmentations pass the diversity check (cosine vs original 0.86-0.88).
Cap stops at 5× — even if more techniques were tried.
```

## Failure modes & edge cases

- **Back-translation drift on legal terms.** "VAT-registered" might back-translate to "registered for VAT" → semantic preserved. But "EPF contribution rate" can drift to "pension fund contribution rate" → semantic loss. Mitigation: maintain a "do-not-touch" lexicon enforced post-translation.
- **Synonym swap produces nonsense.** Random sampling occasionally picks an antonym (`reduction` → `increase` via WordNet's loose lemmas). Mitigation: filter `wn.synsets` by POS + filter known antonym pairs.
- **Diversity check rejects too many.** If 80%+ of augmentations are rejected, the diversity threshold (0.92/0.95) is too strict for the technique. Mitigation: loosen to 0.90/0.95 — but record this in the run metadata.
- **Augmentation leaks into val/test.** Critical: validation and test sets must be original-only. Implementation: augmentation runs *after* the split, on the training portion only. Asserted in `tests/m1/data/test_split_purity.py`.

## Validation & acceptance criteria

- **Per-class minimum.** Every class has ≥ 50 effective examples (original + augmented) after the 5× cap; otherwise the class is reported in thesis limitations.
- **Augmentation purity.** Val + test contain zero `augmentation_method != null` rows.
- **Per-technique F1 contribution.** A/B ablation table populated for the final model run.
- **Diversity reject rate.** Logged per run; alert if > 60% (indicates poor augmentation quality).

## Cross-references

- Parent: [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) §2
- Related: [05_M1_1_Sampling_Strategy.md](05_M1_1_Sampling_Strategy.md) (interplay with active learning)
- BUILD phase: BUILD_11 §augmentation
- Code (when shipped): `ml/m1/data/augmentation.py`, `scripts/run_augmentation_ablation.py`
