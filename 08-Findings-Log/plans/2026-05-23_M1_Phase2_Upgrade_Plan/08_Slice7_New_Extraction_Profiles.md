---
tags: [m1, phase-2, slice-7, extraction, page_routing, wijesekara, surya]
date: 2026-05-23
status: 🔲 not started
estimated-effort: 2 weeks (algorithm-heavy; the gate is measurable improvement, not a calendar date)
prerequisites: slices 5 + 6 shipped (so each new profile can be measured against legacy_v1 immediately)
---

# 08 — Slice 7: Three New Extraction Profiles

## What this slice produces

Three new extraction profiles, each implementing the `ExtractorProfile` protocol from slice 4, each registered in `m1_extraction_profiles` (rows already seeded in slice 4 with `is_active=FALSE`; this slice flips them to `TRUE`), each producing measurable improvement over `legacy_v1` on a documented stratum of the golden set.

The shape of this slice is fundamentally different from slices 3–6: those were system-engineering work with binary "did it ship" gates. This slice is research work with continuous gates ("did the F1 improve by ≥ 3 pp"). Each profile ships as soon as its gate passes; profiles can ship out of order; one or more profiles can be deferred to Phase 3 if their algorithm doesn't pan out by week 2.

## Profile 7.A — `page_routing_v1`

**Purpose.** Fix the document-level routing problem visible in `2468/44`: `classify_pdf` averages chars-per-page over the whole document, which means one heavy-text cover page hides a Wijesekara-corrupted body. Per-page routing eliminates this masking.

**Algorithm.**

```python
def extract(self, pdf_path, regulation_key):
    pages_out = []
    with fitz.open(pdf_path) as doc:
        for page_idx, page in enumerate(doc):
            page_class = classify_page(page)  # 'text' | 'hybrid' | 'scanned'
            if page_class == "text":
                # multi-engine consensus: run all three text extractors, pick best
                outputs = [
                    extract_pymupdf_page(page),
                    extract_pdfplumber_page(page),
                    extract_pypdfium2_page(page),
                ]
                best = max(outputs, key=lambda s: len(strip_cid_markers(s)))
                pages_out.append(best)
            elif page_class == "hybrid":
                pages_out.append(extract_pdfplumber_page(page))
            else:  # scanned
                pages_out.append(extract_tesseract_page(page))
    raw_text = "\n\f\n".join(pages_out)
    # the rest mirrors legacy_v1
```

`classify_page(page)` uses `page.get_text("dict")` to count text spans and compute image-area ratio:

| Heuristic | Class |
|---|---|
| text spans > 50 AND image_area_ratio < 0.2 | `text` |
| text spans < 10 AND image_area_ratio > 0.5 | `scanned` |
| otherwise | `hybrid` |

**Configuration JSON** (stored in `m1_extraction_profiles.config`):

```json
{
  "page_class_thresholds": {
    "text": {"min_spans": 50, "max_image_area_ratio": 0.2},
    "scanned": {"max_spans": 10, "min_image_area_ratio": 0.5}
  },
  "text_engines": ["pymupdf", "pdfplumber", "pypdfium2"],
  "consensus_rule": "longest_non_cid"
}
```

**New dep:** `pypdfium2` (Apache 2.0, see [01_Alignment_Audit §B + risk 5 in original plan]).

**Code location:** `enigmatrix-ml/m1/extraction/profiles/page_routing_v1.py` + `enigmatrix-ml/m1/extraction/page_engines/` (thin wrappers per engine).

**Gate.** Run a measurement against the manual GT baseline. The gate has two conditions:

1. Overall score ≥ legacy_v1 score + 3 percentage points (3 pp).
2. No individual field's `mismatch` count gets worse than legacy_v1's. (You can win on average and lose on a specific field — but if `effective_date` regresses, something is wrong, fix it before flipping `is_active=TRUE`.)

If condition 2 fails, debug the per-field regression before promoting. The per-regulation comparison view from slice 6 is your primary debugging surface — find a regulation where `effective_date` was `exact` for legacy and is now `mismatch`, see what changed.

## Profile 7.B — `wijesekara_routing_v1`

**Purpose.** Fix the CID-corruption case (`2468/44`). Adds font-name-based detection on top of `page_routing_v1` so legacy-font spans get routed through a font-specific Wijesekara converter before the page is assembled, instead of after.

**Algorithm.** Inherits from `page_routing_v1`. The only change is in `extract_pymupdf_page` for text-classified pages:

```python
def extract_pymupdf_page(page):
    spans = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                font = span["font"]
                text = span["text"]
                if any(font.startswith(prefix) for prefix in LEGACY_FONT_PREFIXES):
                    text = convert_with_font_table(text, font)
                spans.append(text)
    return " ".join(spans)
```

`LEGACY_FONT_PREFIXES` ships as a constant list:

```python
LEGACY_FONT_PREFIXES = (
    "FM", "DL-", "Iskoola Pota Wij", "Bindumathi",
    "Abhaya", "Mihintale", "Tikiri", "Malithi",
    "Bamini", "Kaputa", "Amalee", "Thibus",
)
```

The Wijesekara converter map is expanded from 87 entries to **~180 entries**. New entries come from porting the relevant tables in the [Open-SL JavaScript converter](https://github.com/sahanmal/open-sl) (verify license at port time — likely permissive, but confirm) and from the UCSC Language Technology Research Lab tables. Per-font sub-tables for FM-Abhaya, DL-Manel, and Bindumathi (the three commonest fonts in pre-2010 Sri Lankan publications) live in `enigmatrix-ml/m1/extraction/wijesekara_maps/<font_name>.yaml`.

**Configuration JSON:**

```json
{
  "inherits": "page_routing_v1",
  "legacy_font_prefixes": ["FM","DL-","Iskoola Pota Wij","Bindumathi","Abhaya","Mihintale","Tikiri","Malithi","Bamini","Kaputa","Amalee","Thibus"],
  "wijesekara_maps_dir": "wijesekara_maps/",
  "fallback_map": "wijesekara_map.yaml"
}
```

The `error_signals` returned by this profile includes `cid_marker_count` (number of `(cid:N)` substrings in the assembled raw_text, before and after font-aware routing) so the dashboard can show "CID count dropped from 4 800 to 0 on `2468/44`" as a concrete diagnostic.

**Code location:** `enigmatrix-ml/m1/extraction/profiles/wijesekara_routing_v1.py` + `enigmatrix-ml/m1/extraction/wijesekara_maps/*.yaml`.

**Gate.** Against the same manual GT baseline:

1. Overall score ≥ `page_routing_v1` score + 5 pp.
2. `title_si` `mismatch` count on the Wijesekara stratum (slice 2 stratum 3) drops to ≤ 10 % of `legacy_v1`'s count.
3. Raw-text CER on the Wijesekara stratum (slice 2 `aggregate_cer_by_stratum`) drops below 0.10 (legacy_v1's was ~0.28).

This is the most consequential profile in Phase 2. If only one of the three new profiles ships, it should be this one.

## Profile 7.C — `surya_fallback_v1` (deferrable)

**Purpose.** For pages where `wijesekara_routing_v1` still has low confidence (typically scanned Sinhala pages where Tesseract underperforms), re-extract through the Surya OCR model. The literature shows Surya beats Tesseract on Sinhala by a substantial margin on synthetic data; the real-world gap on Sri Lankan gazettes is what we'd be measuring.

**Algorithm.** Inherits from `wijesekara_routing_v1`. After page-level extraction, scan per-page confidence (built from the page classifier + Tesseract's `image_to_data` confidence average for scanned pages). For pages with confidence < 0.6, re-extract through Surya and replace.

**New deps:** `surya-ocr` (~700 MB model bundle), `torch`, GPU strongly preferred (CPU inference ~10–30 s / page).

**Configuration JSON:**

```json
{
  "inherits": "wijesekara_routing_v1",
  "surya_confidence_threshold": 0.6,
  "surya_model_checkpoint": "vikp/surya_rec2",
  "requires_gpu": true
}
```

`requires_gpu` is also set on the `m1_extraction_profiles` row so the dispatcher in slice 4 can fail-fast if no GPU is available.

**Code location:** `enigmatrix-ml/m1/extraction/profiles/surya_fallback_v1.py`.

**Gate.**

1. `title_si` mismatch count drops further below `wijesekara_routing_v1`.
2. ECE (Expected Calibration Error) on the calibration plot drops by ≥ 0.05 absolute vs `wijesekara_routing_v1`.

**Defer condition.** If no GPU is available on the dev / Railway environment and CPU Surya inference is > 15 s / page on a representative laptop, this profile is deferred to Phase 3. Document the deferral in the slice's outcome notes (`08_Slice7_Outcome.md` written at end of slice).

## Tasks (across all three profiles)

### Task 7.1 — `page_routing_v1` implementation (3 days)

- `enigmatrix-ml/m1/extraction/page_engines/pymupdf_engine.py` — page-level wrapper around PyMuPDF.
- `enigmatrix-ml/m1/extraction/page_engines/pdfplumber_engine.py` — page-level wrapper around pdfplumber.
- `enigmatrix-ml/m1/extraction/page_engines/pypdfium2_engine.py` — page-level wrapper around pypdfium2 (new dep).
- `enigmatrix-ml/m1/extraction/profiles/page_routing_v1.py` — the profile class.
- `enigmatrix-ml/m1/extraction/profiles/__init__.py` — register in `PROFILE_REGISTRY`.
- Unit tests + an integration test that runs the profile against the slice-2 golden PDF set and asserts CER on the `pure_english` stratum stays ≤ 0.05.

### Task 7.2 — `wijesekara_routing_v1` implementation (4 days)

- `enigmatrix-ml/m1/extraction/wijesekara_maps/` — three or more font-specific YAML maps.
- `enigmatrix-ml/m1/extraction/font_aware_wijesekara.py` — `convert_with_font_table(text, font_name) -> str` that picks the right map.
- `enigmatrix-ml/m1/extraction/profiles/wijesekara_routing_v1.py`.
- `enigmatrix-ml/m1/extraction/__init__.py` — export `convert_with_font_table` from the public surface.
- Register in `PROFILE_REGISTRY`.
- Unit tests covering: a Wijesekara span gets converted correctly; a non-Wijesekara span passes through unchanged; an unknown font falls back to the default 87-entry map.
- Integration test: run on `2468/44`, assert `cid_marker_count` in `error_signals` is 0, assert `title_si` extracts to a non-empty Sinhala string.

### Task 7.3 — Font-instrumentation (1 day, parallel to 7.2)

Before completing the 180-entry expansion, instrument `legacy_v1` to log the `font` field for every span containing `(cid:` in its text. Run this against the existing `m1_regulations` corpus, collect the font names you actually encounter, and prioritise the map expansion for those fonts first. This guarantees the 180-entry expansion is empirically grounded, not aspirational.

Implementation: add a temporary instrumentation flag `M1_LEGACY_LOG_FONTS=true` that activates a structured-log writer in `legacy_v1.extract`. Remove the flag after the survey is complete.

### Task 7.4 — `surya_fallback_v1` implementation (3 days, GPU-dependent) (½ day if deferred)

- `enigmatrix-ml/m1/extraction/surya_engine.py` — Surya wrapper.
- `enigmatrix-ml/m1/extraction/profiles/surya_fallback_v1.py`.
- Register in `PROFILE_REGISTRY`.
- Tests: requires GPU env var; skipped on CPU-only CI.

If deferred, drop a stub file with a `NotImplementedError("deferred to Phase 3")` and leave the registry row at `is_active=FALSE`.

### Task 7.5 — Per-profile measurement runs (1 day across all three)

For each profile, once implemented and unit-tested:

1. Flip the registry row to `is_active=TRUE` via `POST /api/v1/m1/extraction-profiles/{id}/activate`.
2. Trigger a full extraction run against the ground-truth scope via `/admin/m1/extractions/run`.
3. Wait for completion.
4. Trigger a measurement run (manual GT v1 as baseline, the new extraction version as candidate).
5. Check the gate on the dashboard. If passed, the profile ships. If failed, fix and re-run.

### Task 7.6 — Outcome write-up (½ day)

After all three are shipped or deferred, drop a `08_Slice7_Outcome.md` in this vault folder summarising:
- Per-profile final overall score against manual GT.
- Per-stratum CER improvement (slice 2's eight strata).
- Any unexpected per-field regressions and how they were resolved.
- Whether `surya_fallback_v1` shipped or was deferred.
- Phase-2 final-result table that will go into Chapter 4.

## Files touched

| Path | New/Edit | Purpose |
|---|---|---|
| `enigmatrix-ml/m1/extraction/page_engines/*.py` | new | Per-engine page wrappers |
| `enigmatrix-ml/m1/extraction/profiles/page_routing_v1.py` | new | Profile A |
| `enigmatrix-ml/m1/extraction/profiles/wijesekara_routing_v1.py` | new | Profile B |
| `enigmatrix-ml/m1/extraction/profiles/surya_fallback_v1.py` | new (or stub) | Profile C |
| `enigmatrix-ml/m1/extraction/font_aware_wijesekara.py` | new | Font-aware converter |
| `enigmatrix-ml/m1/extraction/wijesekara_maps/*.yaml` | new | Per-font maps |
| `enigmatrix-ml/m1/extraction/surya_engine.py` | new (or stub) | Surya wrapper |
| `enigmatrix-ml/m1/extraction/__init__.py` | edit | Export new symbols |
| `enigmatrix-ml/m1/extraction/profiles/__init__.py` | edit | Register classes |
| `enigmatrix-ml/pyproject.toml` | edit | Add `pypdfium2` + `surya-ocr` |
| `enigmatrix-ml/tests/m1/extraction/profiles/test_*.py` | new | Per-profile tests |
| `enigmatrix-backend/scripts/log_fonts_for_cid_spans.py` | new (temporary) | Font instrumentation |
| `2026-05-23_M1_Phase2_Upgrade_Plan/08_Slice7_Outcome.md` | new (end of slice) | Result write-up |

## Gates summary (consolidated)

| Profile | Gate 1 | Gate 2 |
|---|---|---|
| `page_routing_v1` | Overall score ≥ legacy + 3 pp | No per-field mismatch regression |
| `wijesekara_routing_v1` | Overall score ≥ page_routing + 5 pp; `title_si` mismatch ≤ 10 % of legacy | Wijesekara-stratum CER < 0.10 |
| `surya_fallback_v1` | `title_si` mismatch < wijesekara_routing; ECE drops by ≥ 0.05 | GPU available or CPU time ≤ 15 s/page (else defer) |

## Risks specific to this slice

(See also the original plan's risks #2 and #3 in `05_Build_Sequence_and_Risks.md`.)

- **Font names not in `LEGACY_FONT_PREFIXES`.** Mitigation: task 7.3 instruments the actual corpus and grows the list empirically. If a new font appears mid-slice, add the prefix and the map; ship a `wijesekara_routing_v1.1` later.
- **Surya is slower than tolerable.** Mitigation: gate-deferred.
- **PyMuPDF / pdfplumber / pypdfium2 producing dramatically different outputs on the same page.** Mitigation: the consensus rule is "longest non-CID-corrupted result". If the three engines disagree by > 30 % on character counts on > 5 % of pages, the page classification heuristic is wrong; tune the thresholds.
- **The expanded Wijesekara map breaks Unicode-already-clean Sinhala pages.** Mitigation: `convert_with_font_table` is only invoked when `is_likely_wijesekara(text)` is true (the heuristic from Session 30). For pages that are already clean Unicode, the converter is bypassed.
- **A new profile passes its gate against manual GT but regresses against the raw-text golden set.** Mitigation: gates 1 and 2 reference both. Slice 7's outcome write-up reports both gate evaluations.
- **AGPL licensing of PyMuPDF.** Per [01_Alignment_Audit §N] and original plan's risk 5: pypdfium2 (Apache 2.0) is being introduced precisely so a future commercialisation-driven switch is a one-file change.

## What this slice deliberately does NOT do

- It does NOT change `legacy_v1`. The legacy stays exactly as-shipped; it's the regression baseline.
- It does NOT introduce a fifth profile (`pymupdf4llm_v1` is mentioned in the original plan as deferred).
- It does NOT retrain or fine-tune anything — these are deterministic profiles, not ML models. (XLM-R classification is Phase 3.)

## Cross-references

- [05_Slice4_Extraction_Profile_Registry](05_Slice4_Extraction_Profile_Registry.md) — the registry this slice activates.
- [06_Slice5_Measurement_Engine](06_Slice5_Measurement_Engine.md) — the engine that decides whether a profile passes its gate.
- [07_Slice6_Comparison_UI](07_Slice6_Comparison_UI.md) — the dashboard you use to read those decisions.
- [03_Slice2_RawText_Golden_Set](03_Slice2_RawText_Golden_Set.md) — the CER reference for gate 2 of `wijesekara_routing_v1`.
- `enigmatrix-docs/m1/10_M1_2_OCR_Wijesekara_Conversion.md` — spec for the Wijesekara module being expanded.
