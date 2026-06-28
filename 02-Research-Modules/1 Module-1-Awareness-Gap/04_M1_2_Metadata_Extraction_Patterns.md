# 04_M1_2 — Metadata Extraction Patterns

> Companion to [04_M1_Preprocessing_Pipeline.md](04_M1_Preprocessing_Pipeline.md) — full regex set for gazette#, effective date, penalty range, principal act; multi-penalty handling, future-dated effective dates, repeal vs amendment disambiguation.
> **Implementation status:** ✅ Shipped Session 31 / F-154 (`ml/m1/preprocessing/metadata_extractor.py` — 4 anchored regex patterns + multi-penalty `finditer` + alternative-merger → `penalty_type='both'` + sanity-bounded effective_date + amendment-type classifier). `m1_regulation_penalties` junction-table persistence shipped Session 32 / F-155 (Step 2f).

## Purpose

Parent doc §3.3 shows 4 regex patterns (gazette#, effective date, penalty, principal act). This companion expands them into a production-grade extractor — with the multi-penalty `finditer` pattern from the parent doc and the edge-case handling that the four basic patterns miss.

## Detailed process

### Field 1 — Gazette number

```python
GAZETTE_NUMBER_RE = re.compile(r"(?:Gazette\s+)?(?:Extraordinary\s+)?No\.\s*(\d{4}/\d+)", re.I)
```

Catches `Gazette No. 2486/22`, `Gazette Extraordinary No. 2486/22`, `No. 2486/22`. Returns the bare `XXXX/N` value.

### Field 2 — Effective date

```python
EFFECTIVE_DATE_RE = re.compile(
    r"(?:with effect from|effective from|w\.e\.f\.?|comes into operation on)\s+"
    r"((?:\d{1,2}(?:st|nd|rd|th)?\s+)?\w+\s+\d{1,2},?\s+\d{4}|\d{1,2}\s+\w+\s+\d{4})",
    re.I,
)
```

Catches `with effect from 1st August 2026`, `effective from August 1, 2026`, `w.e.f. 1 August 2026`. Returns the matched date string; downstream parses via `dateutil.parser.parse(strict=False)`.

**Edge case — future-dated effective dates.** A gazette published 2026-04-15 with effective date `2026-08-01` is normal; the system should not flag this as anomaly. The pipeline accepts `effective_date >= published_date` (with a 5-year ceiling).

### Field 3 — Penalty (multi-match)

The parent doc's §3.3 shows the single-match version. Production uses `re.finditer` and stores all matches:

```python
PENALTY_FINE_RE = re.compile(
    r"(?:fine|penalty|sum)\s+(?:of\s+)?(?:not exceeding\s+)?"
    r"(?:Rs\.?|LKR)\s*"
    r"([\d,]+(?:\.\d+)?(?:\s*[-–]\s*[\d,]+(?:\.\d+)?)?)"
    r"(?:\s*million)?",
    re.I,
)
IMPRISONMENT_RE = re.compile(
    r"imprisonment\s+(?:of either description\s+)?"
    r"(?:for a term\s+)?"
    r"(?:not exceeding\s+|up to\s+)?"
    r"(\d+)\s*(month|months|year|years)",
    re.I,
)
ALTERNATIVE_RE = re.compile(r"\bor\b|\beither\b", re.I)
```

The extractor:

```python
def extract_all_penalties(text: str) -> list[dict]:
    fines = [_parse_fine_match(m) for m in PENALTY_FINE_RE.finditer(text)]
    imprisonments = [_parse_imprisonment_match(m) for m in IMPRISONMENT_RE.finditer(text)]
    return _interleave_with_alternatives(fines, imprisonments, text)
```

`_interleave_with_alternatives` detects "X or Y" patterns — if a fine and an imprisonment are separated by ≤ 30 chars of text containing "or", they're merged into a single penalty row with `penalty_type='both'`.

### Field 4 — Principal act

```python
PRINCIPAL_ACT_RE = re.compile(
    r"(?:amend(?:s|ment to)?|amendment of|repeal(?:s|ing)?)\s+"
    r"(?:the\s+)?"
    r"([\w\s']+Act(?:\s*,?\s*No\.\s*\d+\s+of\s+\d{4})?)",
    re.I,
)
```

The capture group includes the act name + optional `No. X of YYYY` suffix.

**Edge case — repeal vs amendment.** Both verbs trigger the same regex. Disambiguate via the captured verb:

```python
def classify_amendment_type(text: str) -> Literal["amendment", "repeal", "new_act"]:
    if re.search(r"\b(repeal|repealed|repealing)\b", text, re.I):
        return "repeal"
    if re.search(r"\bamendment\b", text, re.I):
        return "amendment"
    return "new_act"
```

Stored in `m1_regulations.amendment_type` (a new column added by the BUILD_07 migration).

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| Regex (chosen) | Fast, transparent, locale-aware | ✅ All four fields fit comfortably in regex; ~1 ms per gazette | If field-extraction precision drops below 90 %. |
| Trained NER (e.g. spaCy `en_core_web_lg`) | Better recall on unusual phrasings | ❌ Sinhala/Tamil NER models are immature; English `en_core_web_lg` adds 500 MB for marginal gain | If the project expands to court-case NER (different problem). |
| LLM extraction | Best for novel patterns | ❌ Cost + latency; regex covers 95 % already | If we encounter a class of regulations the regex consistently misses. |
| `dateparser` for dates | Handles 90+ formats out-of-the-box | ✅ Used downstream after the regex anchors the date string | Always use it for parsing — `dateutil` is the same library family. |

## Worked example

Input — VAT amendment (`VAT_2024_AMD` excerpt):

```
"The Value Added Tax (Amendment) Act, No. 8 of 2024, amends the Value Added
Tax Act, No. 14 of 2002. The Act comes into operation on 1 January 2024.

Any person who fails to register at the threshold of LKR 80,000,000 shall
be guilty of an offence and on conviction shall be liable to a fine not
exceeding LKR 1,000,000 or to imprisonment of either description for a
term not exceeding 6 months or to both such fine and imprisonment."
```

Extraction:

```json
{
  "gazette_number": "2369/14",
  "effective_date": "2024-01-01",
  "principal_act_amended": "Value Added Tax Act, No. 14 of 2002",
  "amendment_type": "amendment",
  "penalties": [
    {"penalty_type": "both", "min_lkr": null, "max_lkr": 1000000,
     "imprisonment_months": 6,
     "context": "...fine not exceeding LKR 1,000,000 or to imprisonment..."}
  ]
}
```

The "or" + 0–30 char proximity merges the fine + imprisonment into a single `penalty_type='both'` row, matching the Sri Lankan legal convention.

## Failure modes & edge cases

- **Tiered penalties** ("first offence LKR 50k; subsequent LKR 500k") — extractor emits two separate rows; downstream UI groups by sequence number from the regulation text.
- **Sinhala/Tamil regulation text** — current regex is English-only; bilingual gazettes have an English column extracted by language routing ([04_M1_Preprocessing_Pipeline.md §3.2](04_M1_Preprocessing_Pipeline.md)) — the extractor runs on that.
- **Rupees vs millions** — `Rs. 1 million` and `Rs. 1,000,000` are different patterns. Mitigation: the regex captures an optional `million` suffix; `_parse_fine_match` multiplies by 10^6 when present.
- **Date with comma** — `August 1, 2026` vs `1 August 2026`. Both captured by the regex; `dateparser` handles both.
- **Multi-act amendment** — a single gazette amending multiple acts (rare but exists). The current regex returns the *first* match. Mitigation: a `finditer` pass on `PRINCIPAL_ACT_RE` is documented as a known future-work item.

## Validation & acceptance criteria

- **Per-field precision/recall** on a 100-gazette hand-validated sample: ≥ 95 % precision, ≥ 90 % recall for each field.
- **Multi-penalty handling.** Unit test asserts that a regulation with 3 penalty clauses produces 3 `m1_regulation_penalties` rows.
- **Date sanity check.** `effective_date >= gazette_published_date` and `effective_date <= gazette_published_date + 5 years`; outside that range, the field is set to NULL and `needs_review=true`.
- **Amendment-type coverage.** All 100 sample gazettes classified into amendment/repeal/new_act; no NULL.

## Cross-references

- Parent: [04_M1_Preprocessing_Pipeline.md](04_M1_Preprocessing_Pipeline.md) §3.3 (metadata)
- Related: [02_M1_Data_Requirements.md §2.8](02_M1_Data_Requirements.md) (`m1_regulation_penalties` schema)
- BUILD phase: BUILD_07 §Metadata extractor
- Code (when shipped): `ml/m1/preprocessing/metadata_extractor.py`
