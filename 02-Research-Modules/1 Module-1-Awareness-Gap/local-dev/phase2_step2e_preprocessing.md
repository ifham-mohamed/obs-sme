---
tags: [tracker, m1, local-dev, phase2, step-2e]
source: synthesised
layer: tracker
module: m1
---

# Phase 2 Step 2e — Preprocessing chain (cleaning + metadata + chunking) (local dev)

> **Shipped:** Session 31 / F-154 (ml-package only; backend wiring in Step 2f).
> **Spec**: [planned-for-development/5_setup.md](../planned-for-development/5_setup.md) · [04_M1_Preprocessing_Pipeline](../04_M1_Preprocessing_Pipeline.md) + 04_M1_1/2/3 companions.

## 1 · What this step does

Consumes the cleaned + language-routed text from Step 2d → produces a `PreprocessedGazette` dataclass with:

- `cleaned_text` (post-8-step noise removal)
- 4 extracted metadata fields (`gazette_number`, `effective_date`, `penalty_range_lkr`, `principal_act_amended`)
- `amendment_type` (amendment / repeal / new_act)
- `penalties: list[Penalty]` (multi-penalty with alternative-merger → `penalty_type='both'`)
- `sections: list[SectionInfo]` (Session 34 — added by segmenter promotion)
- `section_chunks: list[Chunk]` (XLM-R-tokenized, MAX_LEN=512 / STRIDE=64)
- `primary_language` (en/si/ta/mixed)

In-memory only at this stage — backend persistence ships in Step 2f.

## 2 · Prerequisites

- Step 2d passing.
- `transformers>=4.40,<5` + `dateparser>=1.2,<2` installed (handled by `uv sync`).
- `xlm-roberta-base` tokenizer pre-warmed (~1.1 GB to HF cache).

```bash
cd ~/repos/xyz && uv sync
```

## 3 · Pre-warm the XLM-R tokenizer

> **Note**: every Python/pytest invocation below uses `uv run`. Bare
> `python`/`pytest` resolve to the system interpreter on Ubuntu 24.04
> and lack the project deps (`transformers`, `dateparser`,
> `pytesseract`, `fitz`/PyMuPDF). `uv run` selects the workspace venv.

```bash
uv run python -c "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('xlm-roberta-base')"
```

Verify:

```bash
cd ~/repos/xyz/enigmatrix-ml
uv run python -c "from m1.preprocessing import is_tokenizer_cached; print(is_tokenizer_cached())"
# True
```

## 4 · Run the preprocessing tests

```bash
cd ~/repos/xyz/enigmatrix-ml
M1_LID_MODEL_PATH=storage/models/m1/baseline/lid.176.bin uv run pytest tests/m1/preprocessing -v
```

Expected: **72 passed / 2 skipped** (Session 34 baseline):

- `test_cleaning.py` — 30 tests (2/noise class × 8 + idempotency + Unicode preservation + worked example).
- `test_metadata_extractor.py` — 24 tests (per-field + multi-penalty + alternative merger + millions + worked example).
- `test_chunking.py` — 11 tests (5 moved to test_segmenter.py in Session 34; chunking-specific tests stay here).
- `test_pipeline.py` — 7 tests (orchestrator + DoD round-trip + section integration).

Full ml regression (Session 34):

```bash
M1_LID_MODEL_PATH=storage/models/m1/baseline/lid.176.bin uv run pytest tests/m1 -v
# Expected: 127 passed / 8 skipped
```

## 5 · End-to-end orchestrator smoke

Run the worked example from the spec ([04_M1_2 §worked-example](../04_M1_2_Metadata_Extraction_Patterns.md)) directly:

```bash
M1_LID_MODEL_PATH=storage/models/m1/baseline/lid.176.bin uv run python - <<'EOF'
from datetime import date
from m1.preprocessing import preprocess_gazette

raw = (
    "GAZETTE EXTRAORDINARY No. 2369/14 - FRIDAY, DECEMBER 22, 2023\n\n"
    "The Value Added Tax (Amendment) Act, No. 8 of 2024, amends the Value Added "
    "Tax Act, No. 14 of 2002. The Act comes into operation on 1 January 2024.\n\n"
    "Any person who fails to register at the threshold of LKR 80,000,000 shall "
    "be guilty of an offence and on conviction shall be liable to a fine not "
    "exceeding LKR 1,000,000 or to imprisonment of either description for a "
    "term not exceeding 6 months or to both such fine and imprisonment."
)
r = preprocess_gazette(raw, regulation_id="test-vat", published_date=date(2023, 12, 22))
print(f"gazette_number     = {r.gazette_number!r}")
print(f"effective_date     = {r.effective_date}")
print(f"penalty_range_lkr  = {r.penalty_range_lkr!r}")
print(f"principal_act      = {r.principal_act_amended!r}")
print(f"amendment_type     = {r.amendment_type!r}")
print(f"primary_language   = {r.primary_language}")
print(f"penalties count    = {len(r.penalties)}")
print(f"sections count     = {len(r.sections)}")
print(f"section_chunks     = {len(r.section_chunks)}")
print(f"penalties[0]       = {r.penalties[0] if r.penalties else None}")
print(f"sections[0]        = {r.sections[0] if r.sections else None}")
EOF
```

Expected output:

```
gazette_number     = '2369/14'
effective_date     = 2024-01-01
penalty_range_lkr  = 'LKR 1,000,000'
principal_act      = 'Value Added Tax Act, No. 14 of 2002'
amendment_type     = 'amendment'
primary_language   = en
penalties count    = 1
sections count     = 1   (preamble — no PART/Schedule markers in this short input)
section_chunks     = 1   (single chunk; whole doc fits in 512 tokens)
penalties[0]       = Penalty(penalty_type='both', min_lkr=1000000, max_lkr=1000000, imprisonment_months=6, context='...')
sections[0]        = SectionInfo(sequence_idx=0, section_label=None, section_type='preamble', char_offset_start=0, char_offset_end=..., text='...')
```

## 6 · Verifying changes after each edit

### Cleaning change

```bash
uv run pytest tests/m1/preprocessing/test_cleaning.py -v
uv run python -c "from m1.preprocessing import clean_gazette_text; print(clean_gazette_text('regulat-\nion shall apply'))"
# regulation shall apply
```

### Metadata regex change

```bash
uv run pytest tests/m1/preprocessing/test_metadata_extractor.py -v
uv run python -c "
from m1.preprocessing import extract_metadata
m = extract_metadata('Gazette No. 2486/22 ... amends the Test Act, No. 1 of 2020.')
print(m['gazette_number'], m['principal_act_amended'], m['amendment_type'])
"
# 2486/22 Test Act, No. 1 of 2020 amendment
```

### Chunking change

```bash
uv run pytest tests/m1/preprocessing/test_chunking.py -v
```

If you changed `MAX_LEN` or `STRIDE`, also verify the full regression suite stays green.

### Orchestrator change

```bash
uv run pytest tests/m1/preprocessing/test_pipeline.py -v
```

## 7 · DoD corpora (gated)

```bash
# Cleaning idempotency on 50-doc fixture
uv run pytest tests/m1/preprocessing/test_cleaning.py::test_cleaning_idempotency_50_doc_corpus_gated -v

# Metadata per-field PR on 100-doc fixture
uv run pytest tests/m1/preprocessing/test_metadata_extractor.py::test_per_field_precision_recall_corpus_gated -v
```

Both skip until the fixture corpora ship.

## 8 · Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Tokenizer download blocks the first chunk call | xlm-roberta-base not cached | Pre-warm per §3 |
| `chunk_hybrid` returns empty list | Empty input OR all sections dropped by trailing-chunk filter | Check `is_tokenizer_cached()`; verify cleaned text is non-empty |
| `extract_metadata` returns all-None | Cleaning stripped the gazette header (containing the number) | Orchestrator already runs metadata on RAW text — verify your call site does the same |
| `test_clean_preserves_tamil_codepoints` fails with `after > before` is too lenient | NumPy decomposition added Tamil chars (NFKD on U+0BCA → U+0BC6 + U+0BBE) | Invariant is `after >= before`, NOT equality (Tamil decomposition grows the count) |
| HF cache too big | xlm-roberta-base ~1.1 GB | `rm -rf ~/.cache/huggingface/hub/models--xlm-roberta-base/` to reset |

## 9 · After verifying

```powershell
graphify update C:\Reasearch\xyz
```

## 10 · Cross-references

- [planned-for-development/5_setup.md](../planned-for-development/5_setup.md) — Step 2e setup spec
- [phase2_step2d_language_wijesekara](phase2_step2d_language_wijesekara.md) — predecessor (provides cleaned + routed input)
- [phase2_step2f_celery_wiring](phase2_step2f_celery_wiring.md) — successor (backend wiring + DB persistence)
- [04_M1_Preprocessing_Pipeline](../04_M1_Preprocessing_Pipeline.md) — parent spec
- [04_M1_1_Gazette_Noise_Removal](../04_M1_1_Gazette_Noise_Removal.md) · [04_M1_2_Metadata_Extraction_Patterns](../04_M1_2_Metadata_Extraction_Patterns.md) · [04_M1_3_Text_Chunking_Strategy](../04_M1_3_Text_Chunking_Strategy.md)