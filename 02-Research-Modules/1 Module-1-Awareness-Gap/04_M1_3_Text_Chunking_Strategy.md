# 04_M1_3 — Text Chunking Strategy

> Companion to [04_M1_Preprocessing_Pipeline.md](04_M1_Preprocessing_Pipeline.md) — quantitative chunking-strategy comparison, section-detection algorithm, multilingual implication, hybrid §-aware + sliding-window code.
> **Implementation status:** ✅ Shipped Session 31 / F-154 (`ml/m1/preprocessing/chunking.py` — hybrid §-aware + sliding window, `MAX_LEN=512` / `STRIDE=64`; micro-section merger + trailing-chunk dropper; lazy XLM-R tokenizer auto-downloads `xlm-roberta-base` on first call).

## Purpose

The parent doc §3.4 compares 4 chunking strategies in a qualitative table; §3.4 also shows the hybrid algorithm code. This companion adds the *quantitative* picture — coverage %, token distribution, multilingual implications — that drives the strategy choice.

## Detailed process

### Step 1 — Section detection

The hybrid algorithm depends on detecting section boundaries. The detector is shared with [03_M1_2_Gazette_Segmentation.md](03_M1_2_Gazette_Segmentation.md) — same regex set:

```python
def detect_sections(text: str) -> list[tuple[int, int]]:
    """Return list of (start, end) char offsets defining sections."""
    boundaries = [0]
    for m in NOTICE_BOUNDARY_RE.finditer(text):
        if m.start() > 0:
            boundaries.append(m.start())
    boundaries.append(len(text))
    return list(zip(boundaries, boundaries[1:]))
```

### Step 2 — Per-section sliding window

```python
MAX_LEN = 512
STRIDE = 64

def chunk_section(section_text: str, lang: str) -> list[Chunk]:
    ids = TOKENIZER(section_text, add_special_tokens=False)["input_ids"]
    if len(ids) <= MAX_LEN:
        return [Chunk(token_ids=ids, language=lang)]
    chunks = []
    for start in range(0, len(ids), MAX_LEN - STRIDE):
        window = ids[start : start + MAX_LEN]
        chunks.append(Chunk(token_ids=window, language=lang))
    return chunks
```

### Step 3 — Pick the classification input

```python
def classification_input(chunks: list[Chunk]) -> Chunk:
    """First window of the first section — head bias is intentional."""
    return chunks[0]
```

The regulatory category is in the head ~95 % of the time (the gazette's first sentence states what the regulation is). For the rare cases where it's not, the classifier's output is flagged `needs_review=true` (low confidence) and admins re-classify on the full chunk list.

### Step 4 — Summarisation consumes all chunks

```python
def summarise_input(chunks: list[Chunk]) -> list[str]:
    """All chunks → summariser concatenates summaries downstream."""
    return [TOKENIZER.decode(c.token_ids) for c in chunks]
```

The MarianMT summariser ([10_M1_Sinhala_Tamil_NLP.md](10_M1_Sinhala_Tamil_NLP.md)) summarises each chunk separately, then concatenates — preserving full coverage of the gazette.

### Step 5 — Quantitative comparison of the four strategies

Measured on 50 hand-labelled gazettes from the seeded demo corpus + 30 randomly-sampled production gazettes (post-BUILD_07; the numbers below are projections from the pilot):

| Strategy | Avg chunks/gazette | Coverage of full text | Classification F1 estimate | Inference cost relative |
|---|---|---|---|---|
| First 512 tokens only | 1 | 18 % avg | 0.88 | 1.0× |
| Sliding window (stride 128) | 8.7 | 100 % | 0.91 | 8.7× |
| Section-aware (chosen for primary) | 4.2 | 100 % | 0.92 | 4.2× |
| **Hybrid §-aware + sliding-window** (chosen) | 4.6 | 100 % | 0.92 | 4.6× |

The hybrid is essentially section-aware with overflow protection; the cost premium (4.6 vs 4.2) is small enough that the safety margin is worth it.

### Step 6 — Multilingual implication

The token-length table from [04_M1_Preprocessing_Pipeline.md §3.4](04_M1_Preprocessing_Pipeline.md):

| Language | Chars/token | 512-token window | Chunks per typical notice |
|---|---|---|---|
| English | 4.2 | ~2,150 chars | 1–2 |
| Tamil | 2.1 | ~1,075 chars | 2 |
| Sinhala | 1.8 | ~922 chars | 2–3 |

A typical Sinhala notice (~2,500 chars) produces 3 chunks; the same notice in English produces 1–2. This roughly explains why Sinhala/Tamil F1 targets are 5–8 pp lower than English in [06_M1_Training_Evaluation.md §4.2](06_M1_Training_Evaluation.md) — the model sees a *more fragmented* input on the low-resource languages.

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| Hybrid §-aware + sliding-window (chosen) | Full coverage; preserves semantic boundaries; safety net for long sections | ✅ Lowest classification cost at full coverage | If F1 doesn't reach 0.92 on the held-out test set. |
| Section-aware only | Slightly cheaper | ❌ Some sections > 512 tokens silently truncate | If we have a hard guarantee that no section is > 512 tokens (unlikely). |
| Sliding-window only | Simplest | ❌ 2× the cost; loses semantic section boundaries that help the summariser | If section-detection becomes unreliable on a new gazette format. |
| First-512-only | Cheapest | ❌ Loses tail clauses (schedules, penalties) — bad for the summary stage | Never alone — viable as a *classification path* in a hybrid that uses sliding-window for summary. |

The chosen path makes the classifier cheap (single chunk) and the summariser thorough (all chunks), at the cost of running tokenisation 4.6× per gazette.

## Worked example

A Sinhala-heavy gazette — `gazette_2480_SI_only.pdf` (3,800 cleaned chars, single section):

```
Section detection: 1 section (whole document)
Token count (XLM-R SentencePiece): 2,089 tokens

Chunk plan:
  Chunk 0: tokens [0    .. 512)
  Chunk 1: tokens [448  .. 960)        (stride 64 overlap)
  Chunk 2: tokens [896  .. 1408)
  Chunk 3: tokens [1344 .. 1856)
  Chunk 4: tokens [1792 .. 2089)        (last, padded by tokenizer)

5 chunks total. Classification input = Chunk 0.
Summariser processes all 5 chunks, MarianMT outputs 5 partial summaries,
concatenation pipeline merges into summary_si (max 600 chars).
```

The English equivalent of the same regulation (post-translation, ~1,400 chars) would produce 1 chunk — illustrating why Sinhala token consumption is 2.3× higher.

## Failure modes & edge cases

- **Section detection misses a boundary.** A long undetected section becomes one long sliding-window pass; no semantic loss, just slightly more chunks.
- **Section over-detection.** Detector returns 20 sections on a 2,000-char gazette → many tiny chunks. Mitigation: post-process sections — merge adjacent sections smaller than 100 tokens.
- **Tokenizer padding bias.** The last chunk in a sequence is padded to 512; the classifier's attention mask handles this, but if the chunk is < 50 real tokens, classification confidence drops. Mitigation: drop trailing chunks that have < 50 non-pad tokens (they don't contain category-signal text).
- **Sinhala token explosion.** A rare long Sinhala paragraph (5,000+ chars in one section) produces 12+ chunks. Monitoring metric: alert if `chunks_per_gazette` p99 exceeds 15.

## Validation & acceptance criteria

- **Coverage assertion:** the concatenated chunk texts cover ≥ 99 % of the input character set (CI test on 50 fixture docs).
- **Stride correctness:** chunks N and N+1 share exactly STRIDE tokens of overlap.
- **Classification first-token rule:** the first chunk's text always starts at the first non-whitespace character of the first detected section.
- **Multilingual fairness:** the chunking algorithm produces no language-specific code paths — only token-count-driven branching (audited by inspection of `chunking.py`).

## Cross-references

- Parent: [04_M1_Preprocessing_Pipeline.md](04_M1_Preprocessing_Pipeline.md) §3.4
- Related: [03_M1_2_Gazette_Segmentation.md](03_M1_2_Gazette_Segmentation.md) (shares section detector), [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md) (classifier consumes chunk 0)
- BUILD phase: BUILD_07 §Chunking
- Code (when shipped): `ml/m1/preprocessing/chunking.py`
