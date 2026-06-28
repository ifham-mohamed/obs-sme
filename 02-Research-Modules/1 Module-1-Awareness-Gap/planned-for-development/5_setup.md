# 5_setup — Step 2e setup + verification guide

> Companion to [5.md](5.md) — user-actionable setup + verification for the `m1.preprocessing` package.
> **Status:** ✅ Shipped Session 31 / F-154.

## 1. Deployment context

`enigmatrix-ml/m1/preprocessing/` is library code consumed by:
- **Step 2f's `preprocess_gazette_task`** Celery task (backend) — calls `preprocess_gazette()` and persists the result.
- **Stage D's classifier** (future, Phase 3) — consumes `PreprocessedGazette.classification_chunk` + `cleaned_text`.

Live URLs unchanged. Worker hosting still local dev today.

## 2. Prerequisites

Same as [4_setup.md](4_setup.md) §2 + 2 new Python deps:

| Dep | Why |
|---|---|
| `transformers>=4.40,<5` | XLM-R tokenizer (`xlm-roberta-base`). Auto-downloads ~1.1 GB to `~/.cache/huggingface/` on first `chunk_hybrid()` call. |
| `dateparser>=1.2,<2` | Parses `"1st August 2026"`, `"August 1, 2026"`, `"1 August 2026"`, `"w.e.f. 2024"` uniformly. |

## 3. Pre-warm the XLM-R tokenizer (one-time, ~1.1 GB)

> **Use `uv run` for every Python invocation.** Bare `python` / `pytest`
> resolve to the system interpreter (e.g. `/usr/bin/python3.14` on Ubuntu
> 24.04) which lacks the project deps (`pytesseract`, `fitz`/PyMuPDF,
> `fasttext-wheel`, `transformers`). `uv run` selects the workspace venv
> built by `uv sync`. `PYTHONPATH=$PWD` is unnecessary because `uv run`
> resolves the `m1` package automatically.

```bash
uv run python -c "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('xlm-roberta-base')"
# Downloads to ~/.cache/huggingface/hub/models--xlm-roberta-base/...
# Subsequent loads are instant.
```

Tests gate cleanly via `m1.preprocessing.is_tokenizer_cached()` — if you skip this step, the tokenizer-dependent tests skip but the structural tests (section detection with a fake tokenizer) still run.

## 4. Run the test suite

```bash
cd enigmatrix-ml
M1_LID_MODEL_PATH=storage/models/m1/baseline/lid.176.bin \
  uv run pytest tests/m1/preprocessing -v
```

Expected: **71 passed** (without tokenizer) or **76 passed** (with tokenizer pre-warmed).

Full extraction + preprocessing regression:

```bash
uv run pytest tests/m1 -v
# 117 passed / 8 skipped (DoD-corpus + Tesseract-binary + tokenizer gates).
```

## 5. CLI smoke checks

```bash
cd enigmatrix-ml

# 5a — End-to-end orchestrator on the spec's VAT-amendment worked example
uv run python - <<'EOF'
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
print(f"section_chunks     = {len(r.section_chunks)}")
print(f"classification_chunk[:80] = {r.classification_chunk[:80]!r}")
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
section_chunks     = 1   (or more, depending on tokenizer chunking)
classification_chunk[:80] = 'The Value Added Tax (Amendment) Act, No. 8 of 2024, amends the Value Added Tax...'
```

```bash
# 5b — Cleaning only
uv run python -c "
from m1.preprocessing import clean_gazette_text
print(clean_gazette_text('regulat-\nion shall apply'))
# 'regulation shall apply'
"

# 5c — Metadata extraction only
uv run python -c "
from m1.preprocessing import extract_metadata
m = extract_metadata('Gazette No. 2486/22 ... amends the Test Act, No. 1 of 2020.')
print(m['gazette_number'], '|', m['principal_act_amended'], '|', m['amendment_type'])
# 2486/22 | Test Act, No. 1 of 2020 | amendment
"
```

## 6. Manual smoke on a real gazette PDF

```bash
cd enigmatrix-ml
M1_LID_MODEL_PATH=storage/models/m1/baseline/lid.176.bin uv run python - <<'EOF'
from m1.extraction import extract_with_chain
from m1.preprocessing import preprocess_gazette

extracted = extract_with_chain("tests/m1/fixtures/sample_gazette_2486_22.pdf")
pp = preprocess_gazette(extracted.text, regulation_id="2486-22")
print(f"gazette_number={pp.gazette_number!r}  amendment_type={pp.amendment_type!r}")
print(f"cleaned_text length = {len(pp.cleaned_text)}")
print(f"section_chunks      = {len(pp.section_chunks)}")
EOF
```

## 7. DoD corpus harnesses (gated)

```bash
# Language detection accuracy DoD (≥ 95%)
uv run python -m m1.extraction.language_detection \
  --measure-accuracy tests/m1/fixtures/lid_gold.tsv
# Exits 0 iff accuracy ≥ 0.95; otherwise 1.

# Wijesekara conversion accuracy DoD (≥ 95% char-level)
uv run python -m m1.extraction.wijesekara \
  --measure-accuracy tests/m1/fixtures/wijesekara_gold.tsv
```

Both corpus files are research deliverables; the harnesses ship now, the data follows.

## 8. Rollback

```bash
cd enigmatrix-ml
git revert 07b5246    # Step 2e commit
# Drops m1/preprocessing/ package + the 2 new deps. Step 2d surface unchanged.
```

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ValueError: Unable to avoid copy while creating an array as requested` | NumPy 2.x with fasttext-wheel | Pin `numpy<2.0` (from Step 2d's pyproject change) |
| Test `test_clean_preserves_tamil_codepoints` fails with `after > before` | Test still uses strict `==` invariant | Use `after >= before` — NFKD legitimately grows the codepoint count for Tamil precomposed vowel signs |
| `chunk_hybrid` returns empty list | Empty input OR all sections dropped by trailing-chunk filter | Check `is_tokenizer_cached()`; verify text is non-empty after `clean_gazette_text` |
| HF cache fills the disk | xlm-roberta-base downloaded twice (mirrored repo) | `rm -rf ~/.cache/huggingface/hub/models--xlm-roberta-base/*.lock` |
| `extract_metadata` returns all-None | Cleaning stripped the gazette header (which contains the number) | Orchestrator already runs metadata on RAW text — verify if calling extract_metadata directly that you pass the pre-cleaning string |

## 10. What's deferred

- **`cleaning_corpus/`** (50 hand-labelled docs for idempotency + char-loss-bound DoDs).
- **`metadata_gold.json`** (100 hand-validated docs for per-field precision ≥ 95% / recall ≥ 90%).
- **Production Dockerfile pre-warm of xlm-roberta-base.**
- **`m1_regulation_penalties` junction table + `amendment_type` column persistence** → Step 2f.
- **Move `NOTICE_BOUNDARY_RE` out of `chunking.py`** when 03_M1_2 ships as a standalone segmentation module.

## 11. Cross-references

- Plan: [5.md](5.md)
- Predecessor setup: [4_setup.md](4_setup.md) (Step 2d)
- Successor setup: [6_setup.md](6_setup.md) (Step 2f)
- Spec: [../04_M1_Preprocessing_Pipeline.md](../04_M1_Preprocessing_Pipeline.md) + companions 04_M1_1 / 04_M1_2 / 04_M1_3
- Tracker: F-154 in `c:\sme\08-Findings-Log\FEATURES.md`; Session 31 in `SESSIONS.md`.
