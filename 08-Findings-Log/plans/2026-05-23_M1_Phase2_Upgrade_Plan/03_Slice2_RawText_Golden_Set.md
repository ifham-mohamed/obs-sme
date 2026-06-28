---
tags: [m1, phase-2, slice-2, golden-set, raw-text, cer, transcription]
date: 2026-05-23
status: 🔲 not started — can run in parallel with slice 1
estimated-effort: 1 week (depends on second transcriber's pace)
prerequisites: none beyond access to ten source PDFs (already on disk)
---

# 03 — Slice 2: Raw-Text Golden Set Pilot

## What this slice produces

A small but rigorously-constructed reference set of ten hand-transcribed gazette PDFs across eight failure-mode strata, an inter-annotator-agreement (Cohen's κ) report per stratum, an adjudicated final `gold.txt` per page, and `jiwer`-based CER / WER tooling that future extraction profiles will be scored against.

Where slice 1 measures structured-field accuracy ("did we extract the right *values*"), this slice measures character-level accuracy ("did we extract the right *characters*"). Both matter, and both are independently variable: an extraction can produce a perfect title_en value while corrupting 30 % of the raw text, or vice versa.

## Why this slice can run in parallel with slice 1

Slice 1 is mostly Python plumbing. Slice 2 is mostly people work (recruiting a second transcriber, transcribing, adjudicating differences). The two share no code dependencies. The only convention to lock first is the canonical regulation_key format (e.g. `2468/44`), which slice 1 nails down anyway.

If you can find a second transcriber (a bilingual classmate, a project supervisor, a friend who reads Sinhala or Tamil natively), this slice produces real value. If you can't, scope it down: produce single-transcriber gold for the 10 PDFs, skip the κ step, document that the gold is single-source, and treat the resulting CER numbers as upper bounds.

## The eight strata

Pick one representative PDF per stratum from your existing `m1_regulations` rows:

| # | Stratum | Why it matters | Suggested example |
|---|---|---|---|
| 1 | Pure-English text PDF | Easiest case; sanity baseline | `2469_19` (Welisara Prison order) |
| 2 | Pure-Sinhala Unicode | Tests Unicode preservation | a post-2015 Sinhala-only gazette |
| 3 | Pure-Sinhala Wijesekara (legacy font) | The headline problem; expect heavy CID corruption with legacy_v1 | `2468_44` |
| 4 | Pure-Tamil | Tests Tamil OCR / extraction | a Tamil-only gazette |
| 5 | Mixed bilingual (EN body + SI/TA appendix) | Tests language detection's segmentation | typical IRD circular |
| 6 | Scanned image (no text layer) | Tests OCR branch + Tesseract Sinhala accuracy | a pre-2010 gazette page |
| 7 | Hybrid (text on cover, scanned body) | Tests per-page routing decisions | a digitised compilation |
| 8 | Tabular content (penalty schedules) | Tests pdfplumber / table extraction | a tax-rate schedule |

Two PDFs from stratum 3 are doubled up because Wijesekara is the highest-leverage case to fix.

## Tasks

### Task 2.1 — Select the ten source PDFs (½ day)

Open the existing `m1_regulations` table. Filter for one regulation per stratum (two for stratum 3). Record their `regulation_id`, `gazette_number`, and the path to the raw PDF in `storage/m1/raw/<source_id>/YYYY/MM/<slug>.pdf`. Copy each PDF into the vault at `_Attachments/golden_pdfs/<gazette_number>.pdf` so they don't move when the storage layout next changes.

### Task 2.2 — Write the transcription protocol (½ day)

Author `data/golden/raw_text/TRANSCRIPTION_PROTOCOL.md` covering:

- What to transcribe: every Sinhala / Tamil / English glyph visible to the eye, in reading order.
- What NOT to transcribe: page numbers, running headers/footers, repeated boilerplate, blank pages. (Mark them `[HEADER:<exact text>]` so they're observable but excluded from CER computation.)
- Format: one `.txt` file per page, UTF-8, LF line endings, no trailing whitespace, page breaks as `\f`.
- Naming: `<gazette_number>/page_001.t1.txt` (transcriber 1) and `_t2.txt` (transcriber 2).
- Uncertain glyphs: `[?]` for "cannot read", `[?:guess]` for "probably X". The adjudicator resolves these.
- Punctuation: transcribe exactly what is printed, including the Sinhala kunddaliya (`෴`), Tamil danda (`।`), or any other script-specific punctuation.
- Numbers: digits as-printed (Sinhala digits as `0-9` Arabic if the original is Arabic, as `෦-෯` Sinhala if the original is Sinhala numerals).

### Task 2.3 — Transcribe (½ to 3 days, depending on PDF length)

Transcriber 1 (you) and transcriber 2 work independently. Files land at:

```
data/golden/raw_text/
├── 2469_19/
│   ├── page_001.t1.txt
│   ├── page_001.t2.txt
│   ├── page_002.t1.txt
│   ├── page_002.t2.txt
│   └── ...
├── 2468_44/
│   ├── ...
└── TRANSCRIPTION_PROTOCOL.md
```

For a 4-page average × 10 PDFs × 2 transcribers, that's 80 transcription units. At 15–20 minutes per page (slow for Wijesekara, fast for clean English), expect 20–25 hours of total human time across both transcribers.

### Task 2.4 — Compute Cohen's κ per stratum (½ day)

Write `scripts/compute_transcription_kappa.py`. For each stratum, the script:

1. Reads both transcribers' files for every PDF in the stratum.
2. Normalises whitespace and case (configurable).
3. Computes character-level disagreement using `jiwer.cer(t1, t2)`.
4. Computes a 5-bucket categorical κ on character classes (per page: `eng`, `sin`, `tam`, `digit`, `punct` → which fraction of characters each transcriber labelled as belonging to that class).
5. Writes `data/golden/raw_text/kappa.json` with per-stratum κ and per-page CER between the two transcribers.

### Task 2.5 — Adjudicate disagreements (½ day to 1 day)

For pages where `cer(t1, t2) > 0.02` (≥ 2 % character disagreement), open both transcriptions side-by-side and produce `page_NNN.gold.txt` by hand. Document each adjudication decision in `data/golden/raw_text/<gazette_number>/adjudication_log.md` — what the disagreement was, which transcription you chose, why.

For pages where `cer(t1, t2) < 0.02`, accept `t1` as gold (with the rationale that 2 % disagreement is below the noise floor of any extraction we'd ship). Copy `t1` to `gold.txt`.

If any stratum has per-stratum κ < 0.65, the transcription guidelines are insufficient. Update the protocol, redo that stratum's transcriptions, re-compute κ. Do this BEFORE expanding the golden set in a later phase.

### Task 2.6 — Wire `jiwer` CER / WER computation into the evaluation package (½ day)

In `enigmatrix-ml/m1/evaluation/raw_text.py`, expose:

```python
def cer_against_gold(candidate_text: str, regulation_key: str, page_number: int) -> float | None: ...
def wer_against_gold(candidate_text: str, regulation_key: str, page_number: int) -> float | None: ...

def aggregate_cer_by_stratum(candidate_run: dict[str, str]) -> dict[str, dict]: ...
# returns {"wijesekara": {"mean_cer": 0.28, "n_pages": 4, "ci_low": 0.21, "ci_high": 0.36}, ...}
```

Bootstrap CI (95 %, 1 000 resamples) for each stratum. Tests live in `enigmatrix-ml/tests/evaluation/test_raw_text.py`.

### Task 2.7 — Extend the baseline script to emit raw-text CER (½ day)

Update `scripts/run_baseline_measurement.py` (from slice 1) so its JSON output includes a `raw_text_cer` block:

```json
"raw_text_cer": {
  "wijesekara": {"mean": 0.28, "ci_low": 0.21, "ci_high": 0.36, "n_pages": 4},
  "pure_english": {"mean": 0.02, "ci_low": 0.01, "ci_high": 0.04, "n_pages": 5},
  ...
}
```

This is the "Phase-1 raw-text baseline" row in Chapter 4 Table 4.2.

## Files touched

| Path | New/Edit | Purpose |
|---|---|---|
| `_Attachments/golden_pdfs/*.pdf` (vault) | new | Source PDFs (10 of them) |
| `data/golden/raw_text/TRANSCRIPTION_PROTOCOL.md` | new | Transcription rules |
| `data/golden/raw_text/<reg_key>/page_NNN.{t1,t2,gold}.txt` | new | The transcriptions |
| `data/golden/raw_text/<reg_key>/adjudication_log.md` | new (where needed) | Disagreement notes |
| `data/golden/raw_text/kappa.json` | new | Per-stratum κ + CER |
| `enigmatrix-ml/m1/evaluation/raw_text.py` | new | CER/WER helpers |
| `enigmatrix-ml/tests/evaluation/test_raw_text.py` | new | Unit tests |
| `scripts/compute_transcription_kappa.py` | new | One-off κ script |
| `scripts/run_baseline_measurement.py` | edit | Append raw_text_cer block to output |

## Gate

1. `data/golden/raw_text/kappa.json` exists and every stratum has κ ≥ 0.65 (preferably ≥ 0.70).
2. Every PDF has a `page_NNN.gold.txt` for every page.
3. `cer_against_gold(extracted_text, "2469_19", 1)` returns a number ≤ 0.05 for the clean-English stratum (extraction should be near-perfect there). For `2468_44`, the same function returns a number ≥ 0.20 (Wijesekara is broken, as expected).
4. `data/eval/baseline_v0.json` now has the `raw_text_cer` block.

## What this slice deliberately does NOT do

- It does NOT expand the golden set to 100 PDFs (that's a Phase 3 dependency for proper statistical power, per the original plan's risk #4).
- It does NOT score multiple profiles against the gold (slice 5 wires that into the measurement engine).
- It does NOT build a UI for browsing transcriptions (deferred indefinitely — gold lives in the file system).

## Risks specific to this slice

- **Transcriber 2 is unreliable / drops out.** Mitigation: run a 1-page pilot before committing to 10. If transcriber 2 misses the deadline, fall back to single-source gold and add a `single_source: true` flag to the JSON, downgrading the slice 7 statistical claims from "significant improvement" to "observed improvement, single-source baseline".
- **Sinhala / Tamil punctuation conventions are inconsistent across documents.** Mitigation: the protocol is explicit about transcribing exactly what is printed; adjudication log captures the calls.
- **The `2468_44` Wijesekara case is genuinely unreadable for both transcribers.** Mitigation: if neither can read the original glyphs, request a copy from the Sri Lankan archives in legible form, or substitute a different Wijesekara PDF where the original is photographed cleanly. Do not transcribe what you can't actually read.

## Statistical-power caveat (must read)

Ten PDFs across eight strata is a *pilot*, not a study. Each stratum has 1–2 PDFs. CER means computed on this set have wide CIs. You cannot claim "a 2-percentage-point CER improvement is statistically significant" with 1 PDF per stratum.

What you CAN claim with this set:
- *Existence claims*: "`legacy_v1` produces CID markers on Wijesekara documents (n=1 PDF, CER 0.28); `wijesekara_routing_v1` does not (CER 0.04)." — these are descriptive, not inferential.
- *Order-of-magnitude claims*: "OCR-branch CER is roughly 10× higher than text-branch CER on the strata we tested."
- *Pre-registered hypotheses*: "We hypothesise H1: wijesekara_routing_v1 has lower CER than legacy_v1 on the Wijesekara stratum. The pilot supports H1 (the CER drops from 0.28 to 0.04), and we plan to confirm with a Phase-3 expansion to 100 PDFs."

Document this caveat in `data/golden/raw_text/STATISTICAL_POWER.md` so it's not forgotten when Chapter 4 is written.

## Cross-references

- [02_Slice1_Measurement_Scaffolding](02_Slice1_Measurement_Scaffolding.md) — slice 1's overall_score is per-field; this slice's CER is per-character. Both feed Chapter 4.
- [08_Slice7_New_Extraction_Profiles](08_Slice7_New_Extraction_Profiles.md) — `wijesekara_routing_v1`'s gate is "CER on the Wijesekara stratum drops below 0.10".
- `enigmatrix-docs/m1/10_M1_2_OCR_Wijesekara_Conversion.md` — spec for the Wijesekara module that slice 7 expands.
