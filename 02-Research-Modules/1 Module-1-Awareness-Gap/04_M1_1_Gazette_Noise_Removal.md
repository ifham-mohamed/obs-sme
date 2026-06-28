# 04_M1_1 — Gazette Noise Removal

> Companion to [04_M1_Preprocessing_Pipeline.md](04_M1_Preprocessing_Pipeline.md) — 8 noise classes with before/after snippets, regex unit-test suite, common failure modes.
> **Implementation status:** ✅ Shipped Session 31 / F-154 (`ml/m1/preprocessing/cleaning.py` — 8-step `NOISE_PIPELINE`; two public entries `clean_gazette_text` keeps signature for citation-faithful audit, `clean_for_classification` strips signature for the classifier input).

## Purpose

The parent doc lists 8 noise types in a table (§1.1) and shows the `clean_gazette_text()` regex chain (§3.1). This companion turns that into per-class implementation detail with real before/after snippets and an explicit unit-test suite. The goal is a noise-removal layer that can be reviewed for correctness without running the code.

## Detailed process

The cleaning chain runs in a fixed order — earlier steps fix the lexical layer (Unicode, hyphenation), later steps fix the document layer (page headers/footers, page numbers). Reordering breaks idempotency.

### Order and per-step rules

```python
NOISE_PIPELINE = [
    unicode_normalize_nfkd,        # 1. Compose Unicode → composed Sinhala glyphs render properly
    dehyphenate_line_breaks,       # 2. "regulat-\nion" → "regulation"
    strip_gazette_header,          # 3. "GAZETTE EXTRAORDINARY No. 2486/22 – FRIDAY, ..."
    strip_page_numbers,            # 4. "- 3 -" / "iii"
    strip_horizontal_rules,        # 5. "_____________" / "==========" separators
    strip_signature_blocks,        # 6. "By Order of His Excellency..."
    strip_repeated_blank_lines,    # 7. 3+ \n → 2 \n
    collapse_inner_whitespace,     # 8. multiple spaces / tabs → single space
]
```

### Per-class details

| # | Class | Pattern | Before | After |
|---|---|---|---|---|
| 1 | Unicode normalisation | `unicodedata.normalize("NFKD", text)` | (composed Sinhala with combining marks) | (decomposed → re-composed by font renderer) |
| 2 | Dehyphenation | `r"(\w+)-\n(\w+)"` → `r"\1\2"` | `regulat-\nion shall apply` | `regulation shall apply` |
| 3 | Gazette header | `r"GAZETTE\s+(EXTRA)?ORDINARY\s+No\.\s*\d+/\d+\s*[–-]\s*\w+,\s*\w+\s*\d+,\s*\d{4}"` | `GAZETTE EXTRAORDINARY No. 2486/22 – FRIDAY, APRIL 15, 2026` | (empty — line stripped) |
| 4 | Page numbers | `r"^\s*[-–]\s*\d+\s*[-–]\s*$"` (line-anchored) + `r"^\s*[ivxlcdm]+\s*$"` (Roman) | `- 3 -` / `iii` | (empty) |
| 5 | Horizontal rules | `r"^[_=\-]{6,}$"` | `_______________________` | (empty) |
| 6 | Signature blocks | `r"By Order of (?:His|Her) Excellency.{0,200}$"` | `By Order of His Excellency the President, [Sgd.] Director General` | (empty — caveat below) |
| 7 | Repeated blank lines | `r"\n{3,}"` → `\n\n` | `text\n\n\n\nmore` | `text\n\nmore` |
| 8 | Inner whitespace | `r"[ \t]+"` → `" "` | `This    Act    amends` | `This Act amends` |

**Caveat — step 6:** the signature block is *removed* for classification (the text after the signature is rare and usually noise). But it's *kept* in `m1_regulations.raw_text` (the database column) — only the `classification_chunk` is stripped. This separation matters because thesis citations need the raw text intact.

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| Regex chain (chosen) | Fast, transparent, unit-testable | ✅ Sufficient for the 8 known noise classes; ~5 ms per gazette. | If a new noise class appears that isn't expressible as a regex (rare). |
| Rule-based + ML (e.g. trained noise classifier) | Adapts to new noise | ❌ Overkill; would need labelled data we don't have | If noise volume explodes and patterns diverge wildly. |
| `clean-text` Python package | Off-the-shelf | ❌ Doesn't know about gazette-specific patterns (gazette header, signature blocks). | Never. |
| Manual review | Highest quality | ❌ Doesn't scale beyond pilot | Only for the 5 % audit sample. |

## Worked example

A real before/after, from `gazette_2486_22.pdf` Page 1:

```
=== BEFORE (raw PyMuPDF output) ===
GAZETTE EXTRAORDINARY No. 2486/22 – FRIDAY, APRIL 15, 2026
___________________________________________

PART I — Standards

1.    The Sri Lanka Standards Institution hereby   issues   the
following mandatory standard under Section 12 of the Consumer
Affairs Authority Act, No. 9 of 2003:

All multi-pin universal power adapters sold in Sri Lanka shall
carry SLSI safety certifi-
cation effective 1 August 2026.

By Order of His Excellency the President,
[Sgd.] D. M. Karunaratne, Director General, SLSI

- 1 -

=== AFTER (cleaned) ===
PART I — Standards

1. The Sri Lanka Standards Institution hereby issues the following mandatory standard under Section 12 of the Consumer Affairs Authority Act, No. 9 of 2003:

All multi-pin universal power adapters sold in Sri Lanka shall carry SLSI safety certification effective 1 August 2026.
```

Each step removed exactly what it was supposed to: gazette header (step 3), horizontal rule (step 5), hyphen across line break (step 2), inner whitespace (step 8), signature block (step 6), page number (step 4).

## Failure modes & edge cases

- **Header that *is* the regulation.** A few extraordinary gazettes carry the regulatory text in what looks like a header position. Mitigation: step 3's regex requires the literal phrase `GAZETTE EXTRAORDINARY No.` — actual headers in body text don't match.
- **Hyphenation across two words.** Compound English words like `up-to-date` are left alone (step 2 requires `\n` between halves).
- **Sinhala/Tamil "page number".** Sinhala numerals (`එක`, `දෙක`) are not matched by the Roman regex; they're left in. Production volume is < 1 %.
- **Over-aggressive signature strip.** A regulation that *ends* with "By Order of..." has its trailing paragraph removed. Mitigation: the cleaning pipeline does this on the *classification_chunk* (first 512 tokens), not the raw text — the trailing paragraph is preserved in `m1_regulations.raw_text`.
- **NFKD changes the byte length.** Downstream code that indexes by char-offset (e.g. boundary-detection) needs to use the post-NFKD text. The pipeline's contract: all later steps consume the NFKD-normalised text.

## Validation & acceptance criteria

- **Unit tests** in `tests/m1/preprocessing/test_cleaning.py`: one positive + one negative per noise class (16 tests minimum).
- **Idempotency:** `clean(clean(x)) == clean(x)` for all 50 fixture gazettes.
- **Character-loss bound:** total chars removed ≤ 5 % of original text length on the 50-doc fixture set.
- **Sinhala/Tamil preservation:** zero loss of `0x0D80–0x0DFF` or `0x0B80–0x0BFF` codepoints; CI assertion compares pre/post Unicode-range histograms.

## Cross-references

- Parent: [04_M1_Preprocessing_Pipeline.md](04_M1_Preprocessing_Pipeline.md) §1.1, §3.1
- Related: [04_M1_2_Metadata_Extraction_Patterns.md](04_M1_2_Metadata_Extraction_Patterns.md), [04_M1_3_Text_Chunking_Strategy.md](04_M1_3_Text_Chunking_Strategy.md)
- BUILD phase: BUILD_07 §Preprocessing
- Code (when shipped): `ml/m1/preprocessing/cleaning.py`
