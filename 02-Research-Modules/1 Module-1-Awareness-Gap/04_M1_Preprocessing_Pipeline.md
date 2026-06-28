# 04 — Module 1: Text Preprocessing Pipeline

> **Cross-references:** [03_M1_Data_Collection.md](03_M1_Data_Collection.md) · [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md) · [10_M1_Sinhala_Tamil_NLP.md](10_M1_Sinhala_Tamil_NLP.md)
> **See also:** [13_M1_Folder_Structure_and_Implementation_Flow.md](13_M1_Folder_Structure_and_Implementation_Flow.md) — `ml/m1/preprocessing/` ownership + chunking output shape.
> **Sub-step companions:** [04_M1_1_Gazette_Noise_Removal.md](04_M1_1_Gazette_Noise_Removal.md) · [04_M1_2_Metadata_Extraction_Patterns.md](04_M1_2_Metadata_Extraction_Patterns.md) · [04_M1_3_Text_Chunking_Strategy.md](04_M1_3_Text_Chunking_Strategy.md)
> **Implementation status:** ✅ Shipped Session 31 / F-154 (Step 2e — `ml/m1/preprocessing/{cleaning,metadata_extractor,chunking}.py` + orchestrator `preprocess_gazette()`). Backend persistence + Celery wiring shipped Session 32 / F-155 (Step 2f).

---

## Abstract

Raw gazette text extracted by the collection pipeline requires structured preprocessing before it can be fed to the XLM-R classification model. This document specifies the full preprocessing pipeline: noise removal, language-aware tokenization, text chunking for long documents, and structured metadata extraction (gazette number, effective date, penalty amounts). Four tokenization frameworks are evaluated — spaCy, NLTK, IndicNLP, and HuggingFace Tokenizers — and the HuggingFace XLM-R tokenizer is selected as the production tokenizer for its native support of Sinhala and Tamil subword vocabulary. The preprocessing pipeline produces normalised, chunked text segments of ≤ 512 tokens, enriched with structured metadata, ready for model inference.

---

## 1. Preprocessing Challenges

### 1.1 Gazette-Specific Noise

Sri Lankan gazette PDFs, when extracted to text, contain several classes of noise:

| Noise Type | Example | Cause | Treatment |
|---|---|---|---|
| Header/footer repetition | `GAZETTE EXTRAORDINARY No. 2486/22 – FRIDAY, SEPTEMBER 15, 2023` repeated on every page | PDF page headers | Regex deduplication |
| Page number artefacts | `- 3 -` or `iii` | Page numbering | Regex removal |
| Column artefacts from bilingual layout | Interleaved English/Sinhala characters | PyMuPDF linearisation of 2-column layout | Language-based line filtering |
| Hyphenation across lines | `regulat-\nion` | PDF typesetting | Dehyphenation |
| OCR artefacts (Tesseract) | `Thc Act` instead of `The Act` | OCR character confusion | Spell correction (regex for common patterns) |
| Special characters | `§`, `¶`, unicode control chars | PDF encoding | Unicode normalization (NFKD) |
| Repeated whitespace | `This    Act    amends` | PDF extraction | Whitespace collapsing |

### 1.2 Multilingual Complexity

Gazette documents are frequently bilingual or trilingual within a single PDF. A 2023 extraordinary gazette may contain:
- English legal text in the left column
- Sinhala translation in the right column (Unicode range U+0D80–U+0DFF)
- Tamil translation in a supplementary section (Unicode range U+0B80–U+0BFF)

For classification, the primary English text is used as the model input. Sinhala and Tamil texts are routed to the summarisation stage (Stage E) rather than the classifier, because the training corpus is predominantly English-labelled.

---

## 2. Tokenization Framework Selection

### 2.1 Comparison Table

| Criterion | spaCy | NLTK | IndicNLP | HuggingFace Tokenizers |
|---|---|---|---|---|
| **Sinhala tokenization** | ❌ No Sinhala model | ❌ No Sinhala model | ⚠️ Basic Sinhala | ✅ XLM-R covers Sinhala subwords |
| **Tamil tokenization** | ❌ Limited | ❌ Limited | ✅ Good Tamil | ✅ XLM-R covers Tamil subwords |
| **English legal text** | ✅ `en_core_web_lg` | ✅ Punkt | ✅ | ✅ |
| **Subword tokenization** | ❌ Word-level | ❌ Word-level | ❌ Word-level | ✅ BPE/Unigram |
| **Model compatibility** | ❌ Must re-tokenize for BERT | ❌ Must re-tokenize | ❌ Must re-tokenize | ✅ Native to XLM-R |
| **Speed** | Fast | Fast | Moderate | Very fast (Rust implementation) |
| **Max sequence length** | Unlimited | Unlimited | Unlimited | 512 tokens (XLM-R limit) |
| **Truncation/padding** | ❌ Manual | ❌ Manual | ❌ Manual | ✅ Built-in |
| **Special tokens** | ❌ Manual | ❌ Manual | ❌ Manual | ✅ `[CLS]`, `[SEP]` auto-inserted |
| **Production maturity** | High | High | Medium | Very high |
| **Why chosen** | Preprocessing only | Preprocessing only | Not chosen | ✅ **Selected for model input** |

### 2.2 Justification for HuggingFace XLM-R Tokenizer

1. **End-to-end consistency:** Using the same tokenizer for preprocessing and model inference eliminates the risk of token-boundary mismatch. Any other tokenizer would require a mapping step that introduces subtle errors.
2. **Multilingual subword vocabulary:** XLM-R's 250,002-token SentencePiece vocabulary includes Sinhala (U+0D80–U+0DFF) and Tamil (U+0B80–U+0BFF) subword units. spaCy and NLTK lack Sinhala models entirely.
3. **Truncation semantics:** The HuggingFace tokenizer's `truncation=True, max_length=512` correctly handles gazette texts longer than 512 tokens by splitting at subword boundaries, not word boundaries, preserving more semantic content per chunk.

> **spaCy and NLTK are still used** for the preprocessing steps that do not feed the model: sentence splitting (for chunking heuristics), NER for date/penalty extraction, and named entity recognition for gazette metadata. This is a deliberate separation: `spaCy` for linguistic preprocessing, `HuggingFace` for model tokenization.

---

## 3. Preprocessing Pipeline Steps

### 3.1 Step 1 — Noise Removal

```python
import re
import unicodedata

def clean_gazette_text(raw_text: str) -> str:
    # Unicode normalization
    text = unicodedata.normalize("NFKD", raw_text)
    # Remove page headers/footers (gazette header pattern)
    text = re.sub(
        r"GAZETTE\s+(EXTRA)?ORDINARY\s+No\.\s*\d+/\d+\s*[–\-]\s*\w+,\s*\w+\s*\d+,\s*\d{4}",
        "", text, flags=re.IGNORECASE
    )
    # Dehyphenate split words
    text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Remove page number artefacts
    text = re.sub(r"\s[-–]\s*\d+\s*[-–]\s", " ", text)
    return text
```

### 3.2 Step 2 — Language Routing

```python
import fasttext

LID_MODEL = fasttext.load_model("lid.176.bin")

def detect_language(text: str) -> str:
    """Returns 'en', 'si', 'ta', or 'mixed'."""
    labels, probs = LID_MODEL.predict(text[:500], k=3)
    top_lang = labels[0].replace("__label__", "")
    if probs[0] < 0.70:
        return "mixed"
    return top_lang if top_lang in ("en", "si", "ta") else "en"
```

For multilingual documents, the English section is extracted by filtering lines where character set is predominantly ASCII + Latin. The actual filtering code is below — it implements the Unicode-range routing using `unicodedata.category()` for Latin classification and explicit codepoint ranges for Sinhala (U+0D80–U+0DFF) and Tamil (U+0B80–U+0BFF). This is the production language-routing implementation; the `detect_language()` call above gives a *document-level* hint, while `route_lines_by_language()` does the actual *per-line* filtering for trilingual extraction.

```python
import unicodedata

SINHALA_RANGE = range(0x0D80, 0x0E00)   # U+0D80..U+0DFF
TAMIL_RANGE   = range(0x0B80, 0x0C00)   # U+0B80..U+0BFF

def is_sinhala_char(c: str) -> bool:
    return ord(c) in SINHALA_RANGE

def is_tamil_char(c: str) -> bool:
    return ord(c) in TAMIL_RANGE

def is_latin_char(c: str) -> bool:
    return unicodedata.category(c).startswith("L") and unicodedata.name(c, "").startswith("LATIN")

def line_language(line: str, threshold: float = 0.5) -> str:
    """Return 'en', 'si', 'ta', or 'mixed' for a single text line.
    Threshold defaults to 0.5 — the line is classified as language X iff > 50%
    of its non-whitespace characters belong to X's script.
    """
    chars = [c for c in line if not c.isspace()]
    if not chars:
        return "en"  # default — empty lines don't matter
    si = sum(is_sinhala_char(c) for c in chars) / len(chars)
    ta = sum(is_tamil_char(c) for c in chars) / len(chars)
    en = sum(is_latin_char(c) for c in chars) / len(chars)
    top = max(("si", si), ("ta", ta), ("en", en), key=lambda kv: kv[1])
    return top[0] if top[1] >= threshold else "mixed"

def route_lines_by_language(text: str) -> dict[str, str]:
    """Split a multilingual block into per-language subtexts."""
    buckets: dict[str, list[str]] = {"en": [], "si": [], "ta": [], "mixed": []}
    for line in text.splitlines():
        buckets[line_language(line)].append(line)
    return {lang: "\n".join(lines) for lang, lines in buckets.items() if lines}
```

The English bucket feeds the XLM-R classifier (Stage D); the Sinhala and Tamil buckets feed the MarianMT summariser (Stage E). The `mixed` bucket is logged and inspected — production data shows < 2 % of lines fall into `mixed` (typically table cells with bilingual labels). The per-script token-length implications (Sinhala consumes 2.3× the tokens of English) are documented inline in §3.4 and detailed in [04_M1_3_Text_Chunking_Strategy.md](04_M1_3_Text_Chunking_Strategy.md).

### 3.3 Step 3 — Metadata Extraction

Structured fields are extracted from cleaned text using regex patterns before tokenization:

```python
GAZETTE_NUMBER_RE = re.compile(r"(?:Gazette\s+)?No\.\s*(\d{4}/\d+)", re.I)
EFFECTIVE_DATE_RE = re.compile(r"(?:with effect from|effective from|w\.e\.f\.)\s+(\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4})", re.I)
PENALTY_RE = re.compile(r"(?:fine|penalty)\s+(?:of\s+)?(?:not exceeding\s+)?(?:Rs\.?|LKR)\s*([\d,]+(?:\s*[-–]\s*[\d,]+)?)", re.I)
PRINCIPAL_ACT_RE = re.compile(r"(?:amends?|amendment to)\s+the\s+([\w\s]+Act(?:\s+No\.\s*\d+\s+of\s+\d{4})?)", re.I)
```

Extracted fields map directly to `m1_regulations` columns: `gazette_number`, `effective_date`, `penalty_range_lkr`, `principal_act_amended`.

**Multi-penalty extraction.** A single gazette can specify *several* penalty ranges (e.g. "first offence: LKR 50,000–500,000; subsequent offences: LKR 500,000–2,000,000; in addition, imprisonment up to 6 months OR license revocation"). The regex above returns only the first match — losing the rest. The production path uses `re.finditer` and stores all matches as a JSONB array against `m1_regulation_penalties` rather than a single string in `m1_regulations.penalty_range_lkr`:

```python
def extract_all_penalties(text: str) -> list[dict]:
    """Return every penalty mentioned in the regulation text.
    Each entry is a dict {penalty_type, min_lkr, max_lkr, imprisonment_months, context}.
    Empty list if none found.
    """
    matches = []
    for m in PENALTY_RE.finditer(text):
        amount_str = m.group(1).replace(",", "")
        if "-" in amount_str or "–" in amount_str:
            lo, hi = re.split(r"[-–]", amount_str)
            matches.append({"penalty_type": "fine",
                            "min_lkr": int(lo.strip()),
                            "max_lkr": int(hi.strip()),
                            "imprisonment_months": None,
                            "context": text[max(0, m.start()-40):m.end()+40]})
        else:
            matches.append({"penalty_type": "fine",
                            "min_lkr": int(amount_str),
                            "max_lkr": int(amount_str),
                            "imprisonment_months": None,
                            "context": text[max(0, m.start()-40):m.end()+40]})
    # Augment with imprisonment-only patterns; details in 04_M1_2_*.md
    for m in IMPRISONMENT_RE.finditer(text):
        months = int(m.group(1)) * (12 if "year" in m.group(0).lower() else 1)
        matches.append({"penalty_type": "imprisonment",
                        "min_lkr": None, "max_lkr": None,
                        "imprisonment_months": months,
                        "context": text[max(0, m.start()-40):m.end()+40]})
    return matches
```

The legacy single-string column `m1_regulations.penalty_range_lkr` is kept as a denormalized convenience (the lowest min, the highest max — for quick sort + filter), but the authoritative source is now `m1_regulation_penalties` rows. Edge cases — alternative penalty clauses ("fine OR imprisonment"), tiered penalties by offence-count, future-dated penalty effective dates — are detailed in [04_M1_2_Metadata_Extraction_Patterns.md](04_M1_2_Metadata_Extraction_Patterns.md).

### 3.4 Step 4 — Text Chunking

XLM-R accepts a maximum of 512 tokens per input. Gazette documents average 3,000–15,000 characters (approximately 600–3,000 tokens). Three chunking strategies are compared:

| Strategy | Description | Pros | Cons |
|---|---|---|---|
| **First 512 tokens** | Truncate at model limit | Simple, fast | Misses tail content (schedules, penalties) |
| **Sliding window (stride 128)** | 512-token windows with 128-token overlap | Full coverage | 5–10x inference calls per gazette |
| **Section-aware chunking** | Split at natural section boundaries (numbered clauses, "PART I", etc.) | Semantically meaningful | Requires robust section detector |
| **Hierarchical aggregation** | Classify each chunk → pool logits → argmax | Best for long docs | Most complex |

**Selected strategy:** Section-aware chunking (primary) + first 512 tokens for classifier input (the regulatory category is almost always stated in the first 300 tokens of a gazette). Section-aware chunking is used for the summarisation stage (Stage E) where full coverage is needed.

**Hybrid §-aware + sliding-window algorithm.** "Section-aware + first-512" hides two boundary conditions: (a) some sections are themselves > 512 tokens (long EPF rate-change tables); (b) the regulatory verdict sometimes lives in the *last* section (effective-date clauses near the end). The hybrid below detects sections via the same `NOTICE_BOUNDARY_RE` patterns from [03_M1_2_Gazette_Segmentation.md](03_M1_2_Gazette_Segmentation.md), then for each section emits one or more 512-token windows with 64-token overlap. The result is the input for both stages: the classifier picks the *first* window (head bias is OK — the regulatory category is in the head 95% of the time), while the summariser consumes the *full* chunk list.

```python
from transformers import AutoTokenizer

TOKENIZER = AutoTokenizer.from_pretrained("facebook/xlm-roberta-base")
MAX_LEN = 512
STRIDE = 64                # overlap between adjacent windows in a long section

def chunk_hybrid(text: str, lang: str) -> list[dict]:
    """Section-aware split → for each section, emit one or more 512-token windows.
    Returns list of {section_idx, window_idx, token_ids, text, language}.
    The first element's `text` is what the classifier sees; the full list is what
    the summariser sees.
    """
    sections = segment_by_headings(text) or [text]      # from 03_M1_2_*
    chunks = []
    for sidx, section in enumerate(sections):
        ids = TOKENIZER(section, add_special_tokens=False)["input_ids"]
        if len(ids) <= MAX_LEN:
            chunks.append({"section_idx": sidx, "window_idx": 0,
                           "token_ids": ids,
                           "text": TOKENIZER.decode(ids),
                           "language": lang})
            continue
        # Long section → sliding window with overlap
        for widx, start in enumerate(range(0, len(ids), MAX_LEN - STRIDE)):
            window = ids[start : start + MAX_LEN]
            chunks.append({"section_idx": sidx, "window_idx": widx,
                           "token_ids": window,
                           "text": TOKENIZER.decode(window),
                           "language": lang})
    return chunks

def classification_input(chunks: list[dict]) -> str:
    """Pick the first window of the first section — the regulatory category lives here ~95% of the time."""
    return chunks[0]["text"]
```

**Token-length implication for multilingual chunking.** Sinhala and Tamil consume ~2.3× and ~2.0× the XLM-R tokens of English for the same semantic content. The 512-token window therefore captures less *information* per chunk for SI/TA than EN; the hybrid above mitigates this by emitting more windows per section. The full table comes from the language-routing measurement on 50 hand-paired EN/SI/TA gazette excerpts:

| Language | Chars per token (XLM-R SentencePiece) | 512-token window covers | Implications |
|---|---|---|---|
| English | ~4.2 | ~2,150 characters (≈ 350–400 words) | One window often covers an entire short notice |
| Sinhala | ~1.8 | ~920 characters (≈ 80–120 Sinhala words) | A typical notice spans 2–3 windows |
| Tamil | ~2.1 | ~1,070 characters (≈ 90–140 Tamil words) | A typical notice spans 2 windows |

The exit criterion for chunking (when to stop emitting windows) and the §-aware section-boundary regex set live in [04_M1_3_Text_Chunking_Strategy.md](04_M1_3_Text_Chunking_Strategy.md).

### 3.5 Step 5 — Final Preprocessing Output

Each gazette produces:

```python
@dataclass
class PreprocessedGazette:
    regulation_id: str
    gazette_number: str | None          # Extracted by regex
    effective_date: str | None          # ISO date string
    penalty_range_lkr: str | None       # e.g. "LKR 50,000 – 500,000"
    principal_act_amended: str | None
    primary_language: str               # en/si/ta/mixed
    cleaned_text: str                   # Full cleaned text
    classification_chunk: str           # First 512-token window
    section_chunks: list[str]           # Section-split chunks for summarization
```

---

## 4. Full Preprocessing Pipeline Diagram

```mermaid
flowchart TD
    A[raw_text from m1_regulations\nstatus=extracted] --> B[Step 1: Noise Removal\nregex clean + unicode normalization]
    B --> C[Step 2: Language Detection\nfastText lid.176.bin per paragraph]
    C --> D{Primary Language}
    D -->|en| E[English text extracted\ndirectly]
    D -->|si| F[Sinhala text extracted\nfor summarization pipeline]
    D -->|ta| G[Tamil text extracted\nfor summarization pipeline]
    D -->|mixed| H[Language-split by character range\nRoute each segment]

    E --> I[Step 3: Metadata Extraction\nRegex: gazette_number, date, penalty, act]
    I --> J[Step 4: Text Chunking\nSection-aware split]
    J --> K[Classification chunk\nFirst 512 HuggingFace XLM-R tokens]
    J --> L[Summarization chunks\nAll sections for MarianMT]

    K --> M[UPDATE m1_regulations\ncleaned_text, classification_chunk\ngazette_number, effective_date\npenalty_range_lkr]
    M --> N[Enqueue classify_gazette\nCelery task]
```

---

## 5. Sinhala/Tamil Handling

See [10_M1_Sinhala_Tamil_NLP.md](10_M1_Sinhala_Tamil_NLP.md) for the full multilingual NLP deep-dive. Key points for the preprocessing context:

- **Sinhala tokenization:** XLM-R's SentencePiece tokenizer handles Sinhala without a dedicated Sinhala tokenizer, using character-level subwords (average 1.8 characters per token for Sinhala vs 4.2 for English). This results in longer token sequences for equivalent semantic content.
- **Tamil tokenization:** Similar to Sinhala — approximately 2.1 characters/token.
- **Implication for chunking:** A 512-token window captures ~2,100 Sinhala characters vs ~4,300 English characters. Section-aware chunking is therefore more critical for Sinhala/Tamil documents.

---

## 6. Conclusion

The preprocessing pipeline converts raw, noisy gazette PDF text into structured, tokenized inputs ready for the XLM-R classifier. The HuggingFace XLM-R tokenizer is the single authoritative tokenizer for model inputs, while spaCy handles linguistic preprocessing (sentence splitting, NER for metadata extraction). The 512-token classification chunk contains the regulatory category signal for ~95% of gazette documents, based on analysis of the first 300 tokens of 50 labeled examples. The full preprocessing pipeline adds approximately 800ms per gazette document (CPU-only server), well within the 6-hour ingestion SLA.

---

## References

- Wolf et al. (2020). *Transformers: State-of-the-Art Natural Language Processing*. EMNLP 2020. [huggingface.co/transformers](https://huggingface.co/transformers)
- Conneau et al. (2019). *Unsupervised Cross-lingual Representation Learning at Scale*. [arxiv.org/abs/1911.02116](https://arxiv.org/abs/1911.02116)
- Honnibal et al. (2020). *spaCy: Industrial-strength Natural Language Processing in Python*. [spacy.io](https://spacy.io)
- Bojanowski et al. (2016). *Enriching Word Vectors with Subword Information (fastText)*. [arxiv.org/abs/1607.04606](https://arxiv.org/abs/1607.04606)
- Bird et al. (2009). *Natural Language Processing with Python (NLTK)*. O'Reilly.
