---
tags: [setup, ml, local-dev, wsl]
source: synthesised
layer: meta
module: m1
---

# ML Local Development (WSL)

> **Prereqs**: complete [00_LOCAL_DEV_HANDBOOK §1](../../00_LOCAL_DEV_HANDBOOK.md) first. Specifically the WSL Ubuntu setup, apt deps (Tesseract + Sinhala + Tamil + poppler), and uv install.

`enigmatrix-ml/` is a Python package that's a **uv workspace member** of the root `pyproject.toml`. Setup runs from the workspace root so backend + ml share one venv. Production-grade ML code lives here: PDF extraction chain (Step 2c/F-149), language detection + Wijesekara conversion (Step 2d/F-153), preprocessing chain (Step 2e/F-154 + Session 34/F-157 segmenter promotion).

> **Critical:** every Python invocation below goes through `uv run …`. Bare
> `python` / `pytest` resolve to the **system** Python (e.g.
> `/usr/bin/python3` on Ubuntu 24.04), which does NOT have the project deps
> installed (`pytesseract`, `fitz`/PyMuPDF, `fasttext-wheel`, `transformers`,
> `dateparser`, …). You'll see `ModuleNotFoundError: No module named
> 'pytesseract'` / `'fitz'` / etc. `uv run` always selects the uv-managed
> workspace venv built by `uv sync`.

---

## 1 · Pre-flight check

```bash
which uv tesseract pdftoppm
tesseract --list-langs | grep -E '^(eng|sin|tam)$'   # all three present
python3 --version    # 3.11 or 3.12
```

If any fail, see [00_LOCAL_DEV_HANDBOOK §1.3](../../00_LOCAL_DEV_HANDBOOK.md).

---

## 2 · Workspace sync

The ml package is installed as part of the workspace `uv sync` triggered from the backend:

```bash
cd ~/repos/xyz
uv sync   # picks up both members
```

Or from the ml side directly:

```bash
cd ~/repos/xyz/enigmatrix-ml
uv sync
```

Verify:

```bash
uv run python -c "from m1.extraction import classify_pdf, detect_document_language, convert_wijesekara, detect_sections_with_labels; print('OK')"
uv run python -c "from m1.preprocessing import preprocess_gazette, PreprocessedGazette, SectionInfo; print('OK')"
```

---

## 3 · Download the fastText language model

The ml package needs `lid.176.bin` (~125 MB) at `storage/models/m1/baseline/lid.176.bin` for the document-level language detection in `m1.extraction.language_detection`.

```bash
cd ~/repos/xyz/enigmatrix-ml
uv run python scripts/download_lid_model.py --target storage/models/m1/baseline/lid.176.bin
```

The script is idempotent: re-runs skip when the file exists with size ≥ 100 MB.

Verify:

```bash
ls -la storage/models/m1/baseline/lid.176.bin   # ~125 MB
M1_LID_MODEL_PATH=storage/models/m1/baseline/lid.176.bin uv run python -m m1.extraction.language_detection --detect "Hello world this is English text"
# primary=en confidence=0.99.. is_mixed=False
```

---

## 4 · Pre-warm the XLM-R tokenizer

`m1.preprocessing.chunking` uses HuggingFace's `xlm-roberta-base` tokenizer (~1.1 GB). Lazy-loaded on first call to `chunk_hybrid()`. Pre-warm to avoid the first run blocking for a minute:

```bash
uv run python -c "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('xlm-roberta-base')"
```

Downloads to `~/.cache/huggingface/hub/models--xlm-roberta-base/`. Subsequent loads are instant.

Verify:

```bash
uv run python -c "from m1.preprocessing import is_tokenizer_cached; print(is_tokenizer_cached())"   # True
```

---

## 5 · Run the test suite

```bash
cd ~/repos/xyz/enigmatrix-ml
M1_LID_MODEL_PATH=storage/models/m1/baseline/lid.176.bin uv run pytest tests/m1 -v
# Expect: 127 passed / 8 skipped (Session 34 baseline)
```

The 8 skipped tests are intentional:

- 4 DoD-corpus tests gated on fixture data (`tests/m1/fixtures/{lid_gold.tsv, wijesekara_gold.tsv, audit/, ocr_gold/}` — research deliverables).
- 1 Tesseract-binary smoke (skipped unless `tesseract` binary is on PATH — should pass if you did §1).
- 3 tokenizer-gated tests (skip when `xlm-roberta-base` isn't in HF cache — should pass after §4).

Per-module test runs:

```bash
uv run pytest tests/m1/extraction/ -v          # 55 tests (extraction + segmenter)
uv run pytest tests/m1/preprocessing/ -v       # 72 tests (cleaning + metadata + chunking + pipeline)
```

---

## 6 · CLI smoke checks per module

Each ml module ships a CLI for quick local verification:

### 6.1 PDF classifier (Step 2c / F-149)

```bash
# Run the 50-doc threshold calibration (gated on fixture corpus):
uv run python -m m1.extraction.pdf_classifier --calibrate tests/m1/fixtures/audit/
```

### 6.2 OCR + CER measurement (Step 2c / F-149)

```bash
uv run python -m m1.extraction.ocr --tesseract-available   # exit 0 if tesseract on PATH
uv run python -m m1.extraction.ocr --measure-cer pred.txt gold.txt   # CER on hand-transcribed pair
```

### 6.3 Language detection (Step 2d / F-153)

```bash
M1_LID_MODEL_PATH=storage/models/m1/baseline/lid.176.bin \
  uv run python -m m1.extraction.language_detection --detect "ශ්‍රී ලංකා රජයේ අතිවිශේෂ ගැසට් පත්‍රය"
# primary=si confidence=0.99.. is_mixed=False
```

DoD measurement (gated):

```bash
uv run python -m m1.extraction.language_detection --measure-accuracy tests/m1/fixtures/lid_gold.tsv
# Exits 0 iff accuracy ≥ 0.95
```

### 6.4 Wijesekara conversion (Step 2d / F-153)

```bash
uv run python -m m1.extraction.wijesekara --convert "w"        # අ
uv run python -m m1.extraction.wijesekara --detect "wdwsdfgknfpqhxXLcCwd wkn pPqQ.,;["    # is_wijesekara_encoded: True (provided text ≥ 50 alpha chars)
```

### 6.5 Full preprocessing orchestrator (Step 2e + Session 34)

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
EOF
```

Expected:

```
gazette_number     = '2369/14'
effective_date     = 2024-01-01
penalty_range_lkr  = 'LKR 1,000,000'
principal_act      = 'Value Added Tax Act, No. 14 of 2002'
amendment_type     = 'amendment'
primary_language   = en
penalties count    = 1
sections count     = 1   (or 2 with the preamble)
section_chunks     = 1   (or more depending on tokenizer chunking)
```

### 6.6 Segmenter (Session 34 / F-157)

```bash
uv run python - <<'EOF'
from m1.extraction import detect_sections_with_labels
text = "preamble before any boundary\nPART I\nfirst part body\nSchedule 1\nschedule body"
for s in detect_sections_with_labels(text):
    print(f"  [{s.sequence_idx}] type={s.section_type!r} label={s.section_label!r} offsets=({s.char_offset_start},{s.char_offset_end})")
EOF
```

Expected output: 3 sections (preamble, part, schedule).

---

## 7 · Verifying changes after each edit

Typical loop after touching `m1/extraction/` or `m1/preprocessing/`:

1. **Edit** `m1/<area>/<module>.py`.
2. **Targeted test**: `uv run pytest tests/m1/<area>/test_<module>.py -v`.
3. **Full ml regression**: `uv run pytest tests/m1 -v` → must stay at 127/8.
4. **Backend regression** (if you changed the public API): `cd ../enigmatrix-backend && uv run pytest app/tests/integration/test_celery_preprocess_gazette.py -v`.
5. **CLI smoke** for the function you changed (§6).
6. **Update Step 2c/2d/2e/2f/Session-34 plan docs** at [planned-for-devlopment/](../../../02-Research-Modules/1%20Module-1-Awareness-Gap/planned-for-devlopment/) and [local-dev/](../../../02-Research-Modules/1%20Module-1-Awareness-Gap/local-dev/00_INDEX.md) if the change affects user-facing behaviour.

---

## 8 · Adding a new ml module

Pattern from `m1.extraction.language_detection` (Step 2d / F-153):

1. New module `m1/<area>/<new_module>.py` with:
   - Type aliases at top.
   - Lazy model load via `@lru_cache` if it pulls a big artifact.
   - Public API as plain functions (no class containers unless state is needed).
   - CLI entrypoint at the bottom: `if __name__ == "__main__": sys.exit(main())`.
2. Add to `m1/<area>/__init__.py` `__all__`.
3. Add to top-level `m1/__init__.py` if cross-area exposure is needed.
4. New tests at `tests/m1/<area>/test_<new_module>.py`.
5. Update [m1/SETUP/00_LOCAL_DEV_WSL.md](.) (this doc) §6 with the CLI smoke command.
6. Update [BUILD/BUILD_11_ML_Training_Pipeline](../BUILD/BUILD_11_ML_Training_Pipeline.md) if the module is part of the training pipeline.

---

## 9 · HF cache management

The HuggingFace cache at `~/.cache/huggingface/` grows over time:

```bash
du -sh ~/.cache/huggingface/   # current size
ls -la ~/.cache/huggingface/hub/   # what's in there
```

To reset (forces re-download on next use):

```bash
rm -rf ~/.cache/huggingface/hub/models--xlm-roberta-base
# Or nuke the entire cache:
rm -rf ~/.cache/huggingface/
```

Set a custom cache location to keep it off `/home`:

```bash
export HF_HOME=/path/to/big/disk/huggingface
echo "export HF_HOME=/path/to/big/disk/huggingface" >> ~/.bashrc
```

---

## 10 · Storage layout

```
enigmatrix-ml/
├── m1/
│   ├── extraction/                       (PDF + language + Wijesekara + segmenter)
│   │   ├── pdf_classifier.py             (Step 2c)
│   │   ├── text_extractors.py            (Step 2c + Step 2d per-page OCR fallback)
│   │   ├── ocr.py                        (Step 2c + Wijesekara delegate)
│   │   ├── language_detection.py         (Step 2d)
│   │   ├── wijesekara.py                 (Step 2d)
│   │   ├── wijesekara_map.yaml           (87-entry mapping table)
│   │   ├── segmenter.py                  (Session 34 — promoted from chunking.py)
│   │   └── types.py                      (ExtractedText, PageResult, SectionInfo)
│   └── preprocessing/                     (Step 2e — clean + metadata + chunking)
│       ├── cleaning.py                   (8-step NOISE_PIPELINE)
│       ├── metadata_extractor.py         (4 regex + multi-penalty + amendment_type)
│       ├── chunking.py                   (hybrid §-aware + sliding window)
│       └── types.py                      (Penalty, Chunk, PreprocessedGazette)
├── scripts/
│   └── download_lid_model.py             (lid.176.bin downloader)
├── storage/models/m1/baseline/
│   └── lid.176.bin                       (125 MB; gitignored)
└── tests/m1/
    ├── extraction/                        (5 test files)
    └── preprocessing/                     (4 test files)
```

---

## 11 · Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ValueError: Unable to avoid copy while creating an array as requested` | NumPy 2.x with fasttext-wheel 0.9.x | pyproject.toml pins `numpy<2.0` — `uv sync` again |
| `FileNotFoundError: fastText model not found` | lid.176.bin missing | `uv run python scripts/download_lid_model.py --target storage/models/m1/baseline/lid.176.bin` |
| `ModuleNotFoundError: No module named 'pytesseract' / 'fitz'` during `pytest …` | Bare `pytest` ran on the system Python interpreter, which doesn't have project deps | Use `uv run pytest …` (the workspace venv has all deps). The system Python is intentionally NOT the dev surface. |
| `Command 'python' not found, did you mean: command 'python3' from deb python3` | Ubuntu 24.04 has no `python` symlink | Either use `uv run python …` (preferred) OR `sudo apt install python-is-python3` for muscle-memory fallback |
| `xlm-roberta-base` taking forever on first run | HF download (~1.1 GB) | Pre-warm per §4 |
| `tests/m1/extraction/test_language_detection.py` skips all fastText tests | Model file not at `M1_LID_MODEL_PATH` | Re-run §3 download |
| `tests/m1/preprocessing/test_chunking.py` skips tokenizer-gated tests | xlm-roberta-base not in HF cache | Pre-warm per §4 |
| `ImportError: cannot import name 'X' from 'm1...'` | Workspace not synced | `cd ~/repos/xyz && uv sync` |
| `pytest` collects nothing | Bare `pytest` ran on the system Python (no project deps) | Use `uv run pytest …` from `enigmatrix-ml/` (the workspace venv has all deps + the `m1` package import path) |
| Slow first chunk on real corpus | HF model not pre-warmed + cold disk | Pre-warm §4 + let Linux page-cache warm up |
| Tesseract fails on Sinhala/Tamil PDFs | apt language packs missing | `sudo apt install tesseract-ocr-sin tesseract-ocr-tam` |

---

## 12 · Cross-references

- **ml overview**: [../00_ML_Overview](../00_ML_Overview.md)
- **ML training pipeline**: [../BUILD/BUILD_11_ML_Training_Pipeline](../BUILD/BUILD_11_ML_Training_Pipeline.md)
- **Module 1 docs** (full spec set): [02-Research-Modules/1 Module-1-Awareness-Gap/00_INDEX](../../../02-Research-Modules/1%20Module-1-Awareness-Gap/00_INDEX.md)
- **Per-phase run + verify**: [02-Research-Modules/1 Module-1-Awareness-Gap/local-dev/00_INDEX](../../../02-Research-Modules/1%20Module-1-Awareness-Gap/local-dev/00_INDEX.md)
- **Retrospective specs**: [02-Research-Modules/1 Module-1-Awareness-Gap/planned-for-development/](../../../02-Research-Modules/1%20Module-1-Awareness-Gap/planned-for-development/4_setup.md)
- **Backend WSL setup**: [../../backend/SETUP/00_LOCAL_DEV_WSL](../../backend/SETUP/00_LOCAL_DEV_WSL.md)
- **Top-level handbook**: [../../00_LOCAL_DEV_HANDBOOK](../../00_LOCAL_DEV_HANDBOOK.md)