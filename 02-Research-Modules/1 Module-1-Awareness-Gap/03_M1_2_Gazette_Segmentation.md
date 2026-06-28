# 03_M1_2 — Gazette Segmentation (strategies A/B/C deep dive)

> Companion to [03_M1_Data_Collection.md](03_M1_Data_Collection.md) — examples where each strategy fails, boundary-detection F1 benchmarks, regex-pattern troubleshooting.
> **Implementation status:** ✅ Shipped Session 34 / F-157 (`ml/m1/extraction/segmenter.py` — `NOTICE_BOUNDARY_RE` + `detect_sections` + `detect_sections_with_labels` promoted from chunking.py) + `m1_sub_documents` junction (migration `202605260001`). Boundary-detection F1 benchmarks (strategies A/B/C) still pending — see this doc's body.

## Purpose

The parent doc (§3.3) describes three segmentation strategies — heading-regex (A), block-gap (B), LLM fallback (C) — in priority order. This companion makes the *failure modes* of each strategy concrete: which gazette layouts break A, where B over-segments, when C is the only option. The goal is to give an implementer the troubleshooting guide they'd otherwise have to discover by trial.

## Detailed process

A single gazette PDF (especially weekly issues) contains many unrelated notices: tax amendments, appointment notices, public auctions, name-change announcements. Per-notice classification is far more accurate than whole-gazette classification — but only if segmentation is correct.

### Strategy A — Heading-regex (primary)

Used on ~70 % of gazettes. Patterns from the parent doc are the seed set; the live config is in `ml/m1/extraction/segmenter.py:NOTICE_BOUNDARY_RE`.

**When A succeeds:** modern (2018+) extraordinary gazettes with `PART I` / `By Order of` markers + numbered acts (`No. 8 of 2024`).

**When A fails:**

| Failure pattern | Cause | Mitigation |
|---|---|---|
| Single-section gazette | Only one notice; the regex matches once, yielding one section (correct — but boundary count = 0, falls through to B). | Detect: `len(sections) == 1` AND `len(text) > 5000` → trust the single section. |
| Embedded "Part I" inside a notice body | Some notices quote previous gazettes ("amending Part I of the principal Act"). Regex false-matches → over-segmentation. | Require boundary patterns to be at line start (`re.MULTILINE`) + preceded by at least one blank line. |
| Sinhala-only gazette | The regex set is English. | Add Sinhala/Tamil equivalents to `NOTICE_BOUNDARY_RE` per [10_M1_1_Language_Detection_Routing.md](10_M1_1_Language_Detection_Routing.md). |
| Hand-typed legacy gazette | Inconsistent capitalisation, OCR errors. | Try strategy B; if B also fails, fall through to C. |

### Strategy B — Block-gap (fallback)

Used when A returns < 2 sections on a > 5,000-char gazette. Detects notice boundaries via vertical whitespace in the PyMuPDF block bounding boxes.

**When B succeeds:** older gazettes (pre-2015) with consistent column layout and clear notice separation.

**When B fails:**

| Failure pattern | Cause | Mitigation |
|---|---|---|
| Tightly-packed multi-notice page | All notices on one page with < 30-pixel gap. | Lower `gap_threshold` to 15 — but watch for over-segmentation of paragraph breaks. |
| Single long notice that spans pages | Each page break introduces a "gap" → false segment boundary. | Detect page-break artefacts by checking if the gap coincides with a `\f` form-feed char in the upstream text. |
| Scanned gazette (no real blocks) | PyMuPDF blocks are unreliable when fed Tesseract output. | Fall through to C immediately. |

### Strategy C — LLM-assisted segmentation (last resort)

Used in ≤ 3 % of cases. The full text (truncated to 6,000 chars) goes to a local Llama-3-8B-Instruct model with a strict JSON-output prompt.

**When C succeeds:** gazettes with no conventional structure (e.g. an entirely tabular notice catalogue).

**When C fails:**

| Failure pattern | Cause | Mitigation |
|---|---|---|
| LLM hallucinates section titles | The model invents content not in the input. | Validate: every returned `title` substring must appear verbatim in the input text. Reject the segmentation otherwise. |
| LLM returns malformed JSON | Common on long inputs. | Wrap in `pydantic.parse_raw`; on parse failure, retry once with a stricter "JSON-only" suffix. |
| LLM rate-limited / model down | Local Llama-3 host overloaded. | Final fallback: treat the whole gazette as one section (lose multi-notice granularity but keep the gazette in the pipeline). |

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| Three-strategy fallback chain (chosen) | Maximum coverage; clear escalation cost | ✅ Each strategy has a distinct cost profile (μs / ms / s + LLM cost). | If one strategy reaches > 95 % coverage alone, simplify. |
| Regex-only | Cheapest | ❌ ~70 % coverage — leaves 30 % of gazettes unsegmented. | Never the only strategy. |
| LLM-only | Highest quality | ❌ ~$0.001/gazette × 500/yr = trivial cost, but 1–3 s latency on every gazette + LLM availability risk. | If local LLM inference becomes free + < 100 ms. |
| Train a sequence-tagger | Best-in-class | ❌ Requires labelled segment-boundary data; too small a corpus to be worth the engineering effort vs the regex+LLM combo. | At 10× corpus size. |

## Worked example

A real over-segmentation case caught by the boundary-validation step:

```
Input (extract of gazette 2491/14):
   "...in compliance with PART I of the Customs Ordinance (Cap. 232).
    By Order of His Excellency the President,
    [Signature]
    PART I — Customs Tariff Amendments
    1. Section 12 is amended as follows..."

Strategy A naïve output: 3 sections
   (1) "...in compliance with PART I of the Customs Ordinance (Cap. 232)."
   (2) "By Order of His Excellency the President, [Signature]"
   (3) "PART I — Customs Tariff Amendments 1. Section 12 is amended..."

Boundary-validation rule fires:
   - section (1) doesn't start with a boundary pattern → MERGE up
   - section (2) is < 100 chars (just signature) → MERGE into preceding section
Final output: 2 sections
   (a) "...in compliance with PART I... By Order of... [Signature]"
   (b) "PART I — Customs Tariff Amendments 1. Section 12..."
```

The signature line is treated as a *boundary marker* but not its own section — it adheres to the preceding notice as its closing.

## Failure modes & edge cases

- **OCR noise breaks regex.** Tesseract occasionally produces `PARI I` (zero-width-space + capital-i). Mitigation: regex permits `[A-Z]\s?[IVX]+` and allows zero-width chars between letters.
- **Tabular notices.** Tax schedules (e.g. customs tariff lists) have hundreds of small rows — strategies A and B both fail. C handles them as one large section.
- **Bilingual notices.** A single notice has English text followed by Sinhala translation. Both languages share the same notice boundary; segmentation must not split them.
- **Strategy oscillation.** A → 1 segment → B → 6 segments → wins. Risk: B over-segments. Mitigation: if B produces > 20 segments on a < 10-page gazette, fall through to C.

## Validation & acceptance criteria

- **Boundary F1.** Hand-annotated 50 gazettes → measure `segmenter.segment(text)` against ground truth. Target: F1 ≥ 0.85.
- **Strategy-share monitoring.** Production metric: % of gazettes segmented by each strategy. Targets — A: 70 %, B: 25 %, C: ≤ 5 %. Alert if C exceeds 10 % (data drift signal).
- **Anti-hallucination test.** For Strategy C, every returned `title` must appear in the input text. Unit test fuzzes this with bad LLM outputs.

## Cross-references

- Parent: [03_M1_Data_Collection.md](03_M1_Data_Collection.md) §3.3 (segmentation), §3.4 (NOT_REGULATORY filter)
- Related: [04_M1_3_Text_Chunking_Strategy.md](04_M1_3_Text_Chunking_Strategy.md) (downstream chunking)
- BUILD phase: BUILD_07 §Segmentation
- Code (when shipped): `ml/m1/extraction/segmenter.py`
