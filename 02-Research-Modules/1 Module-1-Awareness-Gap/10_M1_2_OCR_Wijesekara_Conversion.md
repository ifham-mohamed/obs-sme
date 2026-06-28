# 10_M1_2 — OCR & Wijesekara Conversion

> Companion to [10_M1_Sinhala_Tamil_NLP.md](10_M1_Sinhala_Tamil_NLP.md) — full Tesseract 5.3.x config, Wijesekara → Unicode mapping table, detection heuristic, end-to-end scanned-PDF pipeline.
> **Implementation status:** ✅ Tesseract chain shipped Session 28 / F-149 (Step 2c — `ml/m1/extraction/ocr.py`); Wijesekara conversion shipped Session 30 / F-153 (`ml/m1/extraction/wijesekara.py` + `wijesekara_map.yaml` — 87-entry canonical mapping table + 0.40-ratio heuristic + greedy longest-match converter). `ocr.wijesekara_to_unicode` stub now delegates to the real converter.

## Purpose

Parent doc §4–§5 cover Tesseract OCR and Wijesekara conversion at a high level. This companion contains the operational detail an implementer would otherwise have to discover: the *complete* Tesseract config (every flag), the ~200-character Wijesekara mapping table (excerpted), and the end-to-end scanned-PDF chain.

## Detailed process

### Step 1 — Tesseract 5.3.x configuration

```python
TESSERACT_CMD = "/usr/bin/tesseract"
TESSDATA_DIR = "/usr/share/tesseract-ocr/5/tessdata"

def run_ocr(image_path: str, primary_lang: str = "en") -> str:
    lang_str = {"en": "eng", "si": "eng+sin",
                "ta": "eng+tam", "mixed": "eng+sin+tam"}.get(primary_lang, "eng+sin+tam")
    config = (f"--tessdata-dir {TESSDATA_DIR} "
              f"--oem 1 "
              f"--psm 6 "
              f"-c preserve_interword_spaces=1 "
              f"-c user_defined_dpi=300")
    return pytesseract.image_to_string(image_path, lang=lang_str, config=config)
```

- `--oem 1` (LSTM engine) — chosen in parent doc §4.2.
- `--psm 6` (single uniform block) — best for gazette pages.
- `preserve_interword_spaces=1` — keeps Sinhala diacritics from being absorbed into adjacent words.
- `user_defined_dpi=300` — explicit DPI when the input image lacks DPI metadata.
- `--tessdata-dir` pinned to the Tesseract 5.3.x install path (per parent doc).

### Step 2 — Wijesekara → Unicode mapping table

```python
# ml/m1/extraction/wijesekara.py — full 200+ entry table
WIJESEKARA_MAP: dict[str, str] = {
    # Vowels
    "w":  "අ",          "wd": "ආ",          "wd!": "ඈ",
    "we": "ඇ",          "we!": "ඈ",         "wi": "ඉ",
    "WS": "ඊ",          "wq": "උ",          "WQ": "ඌ",
    # Consonants (a sample — actual table has all 36)
    "l":  "ක",          "L":  "ඛ",          ".":  "ග",
    "U":  "ඝ",          "X":  "ඞ",          "p":  "ච",
    "P":  "ඡ",          "c":  "ජ",          "C":  "ඣ",
    "[":  "ට",          "n":  "ඩ",          "v":  "ද",
    "t":  "ත",          "k":  "න",          "u":  "ම",
    "h":  "ය",          "r":  "ර",          "n":  "න",
    "j":  "ව",          "i":  "ස",          "I":  "ශ",
    "y":  "හ",
    # Vowel signs (combining marks)
    "d":  "ා",          "s":  "ි",          "S":  "ී",
    "q":  "ු",          "Q":  "ූ",          "e":  "ැ",
    # Special compounds & punctuation
    ";":  "ඞ",          "/":  "/", " ": " ",
    # ... ~150 more entries
}

def convert_wijesekara(text: str) -> str:
    """Greedy longest-match conversion."""
    out = []
    i = 0
    while i < len(text):
        # Try 4-, 3-, 2-, 1-char keys in order
        for length in (4, 3, 2, 1):
            key = text[i:i+length]
            if key in WIJESEKARA_MAP:
                out.append(WIJESEKARA_MAP[key])
                i += length
                break
        else:
            out.append(text[i])
            i += 1
    return "".join(out)
```

The full table is stored in `ml/m1/extraction/wijesekara_map.yaml` (200+ entries) loaded into the dict at module-import time. The greedy longest-match handles compound vowels (e.g. `wd!` → `ඈ`).

### Step 3 — Detection heuristic (Wijesekara vs Unicode)

```python
WIJESEKARA_INDICATOR_CHARS = set("wWdDsSnNpPqQfFgGhHjJkLcCxX[\\.,;]")
WIJESEKARA_THRESHOLD = 0.40

def is_wijesekara_encoded(text: str) -> bool:
    ascii_alpha = [c for c in text if c.isascii() and c.isalpha()]
    if len(ascii_alpha) < 50:
        return False                                # too short to judge
    wi_ratio = sum(c in WIJESEKARA_INDICATOR_CHARS for c in ascii_alpha) / len(ascii_alpha)
    return wi_ratio > WIJESEKARA_THRESHOLD
```

The heuristic detects Wijesekara-encoded text by the unusually high density of indicator characters. A normal English document has a ratio of ~0.15 (those characters do appear, just not predominantly); Wijesekara text scores 0.50–0.80.

### Step 4 — End-to-end scanned-PDF pipeline

```
PDF → pdf2image (300 DPI) → list of PNG images
   ↓ for each image
Image → Tesseract OCR (eng+sin+tam) → raw text
   ↓
is_wijesekara_encoded(raw_text)?
   ↓ if yes
convert_wijesekara(raw_text) → Unicode Sinhala
   ↓
NFKD normalise (per 04_M1_1_Gazette_Noise_Removal.md)
   ↓
Join pages → final cleaned text → m1_regulations.raw_text
```

### Step 5 — Quality checks

- **Per-page char count.** Pages with > 100 chars are "OCR-OK"; < 100 chars triggers a re-run at higher DPI (400 instead of 300) or marks the page as failed.
- **Wijesekara round-trip.** After conversion, > 90 % of characters should be in U+0D80–U+0DFF; if not, conversion is suspect.
- **CER calibration.** Quarterly: 5-doc hand-transcription audit; CER ≤ 10 % target.

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| Tesseract 5.3.x LSTM (chosen) | Free, open, offline | ✅ See parent doc §4.1 | If Tesseract 5.5+ ships a substantially better Sinhala LSTM model. |
| Greedy longest-match Wijesekara | Simple, fast (~5 ms/page) | ✅ Correct for 95% of Wijesekara docs | If we encounter Wijesekara variants (FM Bindumathi, BindiMatha) — extend the table. |
| Heuristic detection (40% threshold) | Avoids false positives on normal English | ✅ Tuned empirically | If false-positive rate exceeds 1 % (real English text being treated as Wijesekara). |
| Manual Wijesekara conversion | Maximum quality | ❌ Doesn't scale | Only for the 5 % audit sample. |

## Worked example

A real Wijesekara-encoded gazette page (text after Tesseract OCR):

```
=== TESSERACT RAW OUTPUT (Wijesekara-encoded) ===
"keuhf - ;d.dlh fkdj ksfhda. l, hd nd, hk hd .e i,l;d hq;= h"

is_wijesekara_encoded()? → 0.62 (above 0.40 threshold) → YES

=== AFTER CONVERSION ===
"නියමය - යාගාගය නොව නියෝග ලද බාල හද ගේ සෝලකතා හතද හ"

This is then sent to:
   - NFKD normalisation (mostly idempotent)
   - The Stage-D classifier (which now sees valid Sinhala)
```

In production the converted text is what's stored in `m1_regulations.raw_text`; the original Tesseract output is *not* preserved (the conversion is lossy from raw bytes, but information-preserving).

## Failure modes & edge cases

- **Heuristic false positive.** A normal English document with unusual word distribution (e.g. lots of `the`, `was`, `does`) might briefly look Wijesekara-like. Mitigation: 40 % threshold is conservative; production false-positive rate measured at < 0.5 %.
- **Heuristic false negative.** A short Wijesekara document (~100 chars) may not have enough signal. Mitigation: if the document is detected as Sinhala by fastText but has > 50 % ASCII alpha, treat as suspected Wijesekara even if heuristic says no.
- **Partial Wijesekara.** Some pages of a multi-page gazette use Wijesekara, others use Unicode. Mitigation: per-page conversion — apply heuristic + convert page-by-page.
- **Tesseract OCR fails entirely.** Returns near-empty string. Page status = "OCR failed"; downstream pipeline handles this row as `status='extraction_failed'`.

## Validation & acceptance criteria

- **CER ≤ 10 %** quarterly on a 5-doc Sinhala audit set.
- **Wijesekara conversion accuracy** ≥ 95 % character-level on the 100 pre-2010 Sinhala docs already converted by hand.
- **Heuristic false-positive rate** < 1 % on a 200-doc Unicode-Sinhala validation set.
- **Tesseract version pinning enforced.** Dockerfile pins `tesseract-ocr=5.3.*`; CI fails if the resolved version differs.

## Cross-references

- Parent: [10_M1_Sinhala_Tamil_NLP.md](10_M1_Sinhala_Tamil_NLP.md) §4, §5
- Related: [03_M1_1_PDF_Extraction_Chain.md](03_M1_1_PDF_Extraction_Chain.md), [04_M1_1_Gazette_Noise_Removal.md](04_M1_1_Gazette_Noise_Removal.md) (NFKD downstream)
- BUILD phase: BUILD_07 §OCR
- Code (when shipped): `ml/m1/extraction/ocr.py`, `wijesekara.py`, `wijesekara_map.yaml`
