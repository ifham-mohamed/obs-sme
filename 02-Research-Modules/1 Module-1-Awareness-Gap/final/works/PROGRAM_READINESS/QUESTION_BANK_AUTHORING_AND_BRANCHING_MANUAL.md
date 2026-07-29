# Question Bank — Authoring & Branching Manual

> Group: `PROGRAM_READINESS`. Companion to `M1_NON_CODING_TASKS_AND_GOLIVE_READINESS_PLAN.md`.
> **Purpose.** The operator manual for `/admin/questions` — what every field on the authoring form means, why it exists, what the branching engine does with it, and how to author a correct question without reading the source. Written 2026-07-29 against the reworked form.
> **Audience.** Researcher / research assistant authoring the instrument. No coding required.

---

## 0. The one-paragraph mental model

Every awareness, knowledge and vulnerability question lives in **one table** — `survey_questions`. A question is not a standalone object: it carries (a) *identity* — where it sits in the instrument, (b) *linkage* — which regulation, domain and sector it is about, (c) *content* — the prompt in three languages, (d) *an answer space* — what a valid answer looks like, and (e) *optionally, routing* — which question comes next given the answer. The survey engine walks this table at runtime. It never reads a hard-coded questionnaire; the table **is** the questionnaire.

---

## 1. Section 01 — Identity

### 1.1 Question code — *now automatic, no longer typed*

**What changed.** The field used to be a free-text input pre-filled with a guess. Two admins authoring at once could pick the same code, and a typo produced a code that no seed script or analysis notebook could find. It is now **derived and displayed read-only**.

**The format.**

```
awareness.pdpa.q01
   │        │    └── sequence, zero-padded, next free number IN THIS SECTION
   │        └─────── instrument section, slugified (lowercase, underscores)
   └──────────────── module: awareness | knowledge | vulnerability
```

**Rules the allocator follows:**

| Rule | Reason |
|---|---|
| Numbering is **per section**, not per module | `awareness.pdpa.q01` and `awareness.mrp.q01` can coexist. Adding a PDPA question never renumbers the MRP block. |
| Uses **max + 1**, never count + 1 | Archiving `q07` must not cause the next question to also become `q07` and collide with the archived row. |
| Allocated **server-side at save time** | The form only *previews* the code. Two admins saving simultaneously get `q04` and `q05`, not two `q04`s. |
| Version is **not** in the code | Bumping the instrument v1 → v2 would otherwise renumber every code and break every downstream join. The version lives in its own column. |

> [!note] Legacy codes still work
> Rows seeded before this change (`Q-A-DPDPA-1-v1`, `VAT_FACT_001`) keep their codes. The allocator only governs *new* questions. Nothing needs migrating.

### 1.2 Module — **required**

Which of the three instruments this question belongs to.

| Value | Instrument | What it measures |
|---|---|---|
| M1 — Awareness | awareness | *Does the SME know this rule exists?* |
| M2 — Knowledge | knowledge | *Do they know its content correctly?* — has a scoreable answer key |
| M3 — Vulnerability | vulnerability | *Does their behaviour expose them to risk?* — feeds the risk model |

Module also decides which extra sections the form shows: M2 reveals *Knowledge type* and the correct-answer controls; M3 reveals *Risk-signal mapping*.

### 1.3 Format — **required**

Defines the shape of a valid answer. **Changing it clears the options and any branching rules**, because a rule written against the old answer values can no longer match. The form warns when this happens.

| Format | What the respondent does | Stored as |
|---|---|---|
| Yes / No | picks one of two | text (`yes` / `no`) |
| MCQ (single) | picks one option | text (the option value) |
| MCQ (multi) | picks several | comma-joined text |
| Likert scale | picks a point on 1–5 | **number** |
| Numeric | types a number | **number** |
| Date | picks a date | date |
| Short text | one line | text |
| Open response | free paragraph | text, not auto-scored |
| Scenario response | paragraph answering a scenario | text, rubric-scored |
| Ordered steps | drags steps into order | ordered id list |

The text/number distinction matters for branching — see §5.3.

### 1.4 Instrument section — **required** *(this is the field that drives the code)*

A short grouping label: `pdpa`, `mrp`, `slsi`, `history`, `behaviour`. It does three jobs:

1. **Forms the middle segment of the question code.**
2. **Groups questions for ordering.** The engine finishes a section before moving to the next.
3. **Gives the linear fallback its scope** — "next question" means "next in *this* section", not "next in the whole bank".

The input suggests sections already in use for the selected module. Reuse one where possible; a new section starts a new numbering series and a new ordering block.

### 1.5 Sort order — **hidden, auto-assigned**

Position within the section. Now assigned automatically as `(highest in section) + 10`.

**Why it exists:** it is the entire linear path. When no branching rule matches — the common case — the engine picks the next active question in the same section with a **higher sort order**. Without it, ordering falls back to insertion order, which is not stable enough for a research instrument.

**Why steps of 10:** leaves gaps so a question can later be slotted between two existing ones (set it to 25 to sit between 20 and 30) without renumbering the block. Editable on the edit page when you need that.

### 1.6 Version — **hidden, defaults to `v1`**

Labels which revision of the instrument a question belongs to. The point is **comparability**: once fieldwork starts, freeze v1. Substantive changes to wording or options create v2 questions, so responses collected under different wordings are never silently pooled. Nothing in the runtime engine reads it — it is a research-integrity marker, exposed on the edit page.

### 1.7 The three flags

| Flag | Default | What it actually does |
|---|---|---|
| **Required** | on | Respondent cannot advance without answering. Turn **off** for sensitive or optional items (income bands, open-ended comments) where forcing an answer causes drop-off or fabricated data. |
| **Branching root** | off | Marks this question as a valid **entry point**. `start_flow()` picks the lowest-sorted branching root in scope. Typically **exactly one per section**. If none is marked, the engine falls back to the first question by sort order — so it is a safety net, not a hard requirement. |
| **Active** | on | Soft on/off. Unchecking retires the question from all future surveys **without deleting it**, so responses already collected stay valid and analysable. Prefer this over archiving mid-fieldwork. |

> [!warning] Never hard-delete a question that has responses
> `survey_responses` references the question code. Uncheck **Active** instead.

---

## 2. Section 02 — Linkage

### 2.1 Linked regulation

The regulation this question is about. Two effects: the SME sees a **context card** with the regulation summary before the question, and the awareness-gap analysis can group responses by regulation.

Optional. A question with no regulation is a *baseline* question — a general item asked regardless of which regulations are active.

### 2.2 Domain & Sector — **now auto-filled**

**What changed.** These were blank dropdowns the author had to remember to fill, which meant a PDPA question could end up tagged `VAT` — silently corrupting the domain breakdown in the analysis.

They now inherit from the selected regulation:

- **Domain** ← the regulation's `domain_code`.
- **Sector** ← the regulation's sector, **only when the regulation targets exactly one**. A multi-sector regulation leaves Sector blank, which the engine reads as *applies to all sectors*.

Auto-fill only writes into **empty** fields — deliberate narrowing is never overwritten. Both remain editable: set Sector manually to ask a general regulation's question of retailers only.

### 2.3 Knowledge type — M2 only

`factual` / `procedural` / `application` / `exception`. Drives the M2 sub-score breakdown so a low knowledge score can be attributed ("they know the rule exists but not the procedure").

### 2.4 Ground-truth source — **removed**

**Why.** It was a free-text field duplicating information the linked regulation already holds authoritatively (`source_url`, `document_number`, `principal_act_amended`). Two copies of a citation drift apart; the regulation record is the one that gets verified by the CA. Provenance now comes from the link, in one place.

The column still exists for legacy rows and is shown read-only on the edit page. Nothing was deleted.

---

## 3. Section 03 — Localised content

Unchanged. Prompt in **EN** (required), **සිං** Sinhala, **த** Tamil.

**Needs translation** flags the row for the translation queue. Leave it **on** while SI/TA are empty or machine-drafted; clear it once a human has reviewed both. The SME-side renderer falls back to English and records `language_fallback_used` — so an unfinished translation degrades gracefully but is measurable.

---

## 4. Section 04 — Answers & options

The builder now renders **only** the controls that make sense for the chosen format, and shows a one-line explainer of what it expects.

| Format | What you configure |
|---|---|
| Yes / No | Nothing — a `yes` / `no` pair is seeded automatically, labels editable in all three languages |
| MCQ single / multi | One row per option: a machine **value** plus EN / SI / TA labels |
| Likert | min, max, and a label for each endpoint |
| Numeric | min, max, unit (LKR, days, staff) |
| Ordered steps | one row per step; correct order as a comma-separated id list |
| Short text / Open / Scenario | max length only |
| Date | nothing |

### 4.1 Option values — the rule that matters most

The **value** is the token stored in `survey_responses.answer_text` and the token branching predicates match against. The **label** is what the respondent reads and can be freely reworded or translated.

**Keep values short, lowercase, no spaces:** `yes`, `no`, `not_sure`, `within_30_days`.

The builder now warns on the four failure modes that silently break branching later:

- an option with a **blank value**
- **two options sharing a value** — ambiguous match
- a value containing **spaces or punctuation** — brittle string comparison
- an option with **no English label** — respondent sees a blank choice

These are warnings, not blocks; you can still save. But a rule pointing at a value that no option defines will never fire.

### 4.2 Correct answer — M2 only

Appears as a radio (single) / checkbox (multi) / range (Likert, Numeric) next to the options. M1 and M3 have no answer key by design — awareness and vulnerability are *measured*, not *graded*.

---

## 5. Section 05 — Branching rules

### 5.1 Why branching exists

A fixed questionnaire asks everyone everything. That is wasteful and, worse, it produces meaningless data: asking "when did you first learn that selling above MRP is an offence?" of someone who *just told you they didn't know it was an offence* yields a fabricated answer.

Branching makes the instrument **adaptive**: the answer just given decides what is worth asking next. For an awareness-gap study this is the core measurement device — the *path* a respondent takes through the instrument is itself data.

### 5.2 The paradigm — how the engine actually decides

When an answer is submitted, `next_question()` runs this sequence:

```
answer submitted
   │
   ├─ 1. Walk this question's rules TOP TO BOTTOM.
   │       First rule whose condition matches wins. Stop testing.
   │       → jump to that rule's target
   │
   ├─ 2. No rule matched (or no rules at all)?
   │       → LINEAR FALLBACK: next active question in the same
   │         instrument_section with a higher sort_order
   │       → section exhausted? next section, then next module (1→2→3)
   │
   ├─ 3. Regulation scope check
   │       Running a regulation-scoped survey? A target outside that
   │       regulation is treated as if the rule didn't match, and the
   │       engine continues linearly WITHIN scope.
   │
   ├─ 4. Skip-answered
   │       Already answered this code in a previous session? Skip forward.
   │       (Resume policy — a cycle guard stops infinite loops.)
   │
   └─ 5. Nothing left → instrument complete
```

Five properties follow from this, and they explain almost every "why did it do that?" question:

1. **Order matters.** Put the most specific rule first. A broad rule above a narrow one makes the narrow one dead.
2. **There is always an implicit `Otherwise`.** You never have to write a catch-all. The form now renders this terminal branch explicitly so it is visible rather than inferred.
3. **Rules are optional.** No rules = a straight-line question. Most questions should have none.
4. **A bad target is survivable.** A target that is archived, out of scope, or nonexistent degrades to linear next rather than crashing the survey.
5. **Branching is advisory at save time.** The backend soft-warns on cycles and forward references but does not block. The form now catches the mechanical errors *before* you save.

### 5.3 The four predicates — and which formats they work with

| Predicate | Fires when | Reads | Valid for |
|---|---|---|---|
| `answer_eq` | answer is **exactly** one value | text | all formats |
| `answer_in` | answer is **any of** several values | text | choice formats; for multi-select, matches if **any** selected value is in the list |
| `answer_lt` | answer is **less than** a number | number | Likert, Numeric **only** |
| `answer_gt` | answer is **greater than** a number | number | Likert, Numeric **only** |

> [!important] Why `answer_lt` / `answer_gt` are hidden for text formats
> They read `answer_numeric`, a column only populated for Likert and Numeric answers. On a Yes/No question that column is null, so the comparison can never be true — the rule is dead on arrival. The dropdown now offers only the predicates the engine can actually evaluate for the chosen format.

Exactly **one** predicate per rule. Compound conditions ("A and B") are expressed by chaining questions, not by one rule.

### 5.4 What the editor now catches

| Message | Meaning |
|---|---|
| *This predicate can never fire for the chosen answer format* | numeric comparison on a text answer |
| *No value set* | empty predicate — never matches |
| *The value isn't one of the options defined above* | typo or a value deleted from §4 |
| *Points at this same question* | self-loop; respondent would be stuck |
| *Target isn't in the currently loaded list* | tick **Search all questions** to confirm it exists |
| *An earlier rule has the same condition* | unreachable — evaluation stopped before reaching it |

Each rule also shows a **plain-English restatement** — "If the answer is exactly *No* → go to `awareness.mrp.q04`" — so a rule can be proof-read without decoding JSON.

### 5.5 Visual vs JSON

Same data, two views. **Visual** for authoring. **JSON** for bulk paste, review, or copying a rule set between questions — edit, then **Apply JSON**. The stored shape:

```json
[
  { "when": { "answer_eq": "no" },            "goto_question_code": "awareness.mrp.q04" },
  { "when": { "answer_in": ["si", "ta"] },    "goto_question_code": "awareness.mrp.q03" },
  { "when": { "answer_lt": 3 },               "goto_question_code": "knowledge.vat.q01" }
]
```

---

## 6. Worked example — MRP enforcement (real regulation, real flow)

**Background.** Selling a product above its printed Manufacturer's Recommended Price is an offence in Sri Lanka. The research question is not just *do SMEs comply* but **where the awareness gap sits**: do they not know the rule, or know it and misunderstand its scope?

Four questions in section `mrp`, module M1, all linked to regulation `MRP_ENFORCEMENT_2026`. Domain and sector auto-fill from that link.

### The questions

| Code | Sort | Format | Prompt (EN) |
|---|---|---|---|
| `awareness.mrp.q01` | 10 | Yes / No | Are you aware that selling any product above its printed MRP label is an offence? |
| `awareness.mrp.q02` | 20 | MCQ single | When did you first learn that selling above MRP is a legal offence? |
| `awareness.mrp.q03` | 30 | MCQ single | Where did you learn about the MRP rule? |
| `awareness.mrp.q04` | 40 | MCQ single | If you were unaware — what would have helped you find out? |

`q01` is the **Branching root** for this section.

### The rules on `q01`

Options on q01: `yes` / `no`.

| # | Condition | Goto | Why |
|---|---|---|---|
| 1 | `answer_eq` = `no` | `awareness.mrp.q04` | Unaware — skip "when did you learn" and "where did you learn"; both are unanswerable. Jump to the channel-gap question, which is the *useful* item for an unaware respondent. |
| 2 | — | *(no second rule)* | Aware → **Otherwise** applies: linear next = `q02`. |

One rule. That is the whole configuration.

### Two respondents, traced

**Respondent A — a grocery retailer who knows the rule**

```
q01  "Are you aware…?"          → yes
      rule 1: answer_eq "no"?   ✗ no match
      Otherwise → linear next in section `mrp`, sort > 10
q02  "When did you first learn…?"  → "before_2024"
      no rules → linear next
q03  "Where did you learn…?"       → "supplier"
      no rules → linear next
q04  "What would have helped…?"    → answered
      section exhausted → next section / module
```

Path: `q01 → q02 → q03 → q04`. Four questions. Yields *depth* of awareness.

**Respondent B — a small textile shop that has never heard of it**

```
q01  "Are you aware…?"          → no
      rule 1: answer_eq "no"?   ✓ MATCH → goto awareness.mrp.q04
q04  "What would have helped…?"    → "supplier_notice"
      section exhausted → next section / module
```

Path: `q01 → q04`. Two questions — `q02` and `q03` were never rendered.

### Why this is the correct design

- Respondent B is never asked *when* they learned something they don't know. No fabricated data enters the dataset.
- B's survey is shorter, which reduces drop-off in exactly the group the study most needs to hear from.
- The **path itself is the measurement**: `q01 = no` is the awareness gap; `q04` says which channel would have closed it. That is a directly actionable policy finding, and it comes from one branching rule.

### Adding a third path

Say you want unaware respondents in the **food** sector routed to an SLSI certification question instead. Two changes:

1. Add rule **above** the current one:
   `answer_eq` = `no` → `awareness.slsi.q01`
2. Scope it by setting **Sector** = `food` on `awareness.slsi.q01`.

The sector filter runs inside the engine's visibility check, so a non-food respondent skips it and falls through to `q04`. Order matters: place the new rule first, or the existing `no → q04` rule matches and the SLSI rule becomes unreachable — which the editor now flags as *"An earlier rule has the same condition"*.

---

## 7. Authoring checklist

Before saving a new question:

- [ ] **Module** correct — it decides which extra sections appear
- [ ] **Instrument section** picked from the suggestions where one fits (new section = new numbering block)
- [ ] Code preview looks right (`awareness.<section>.qNN`)
- [ ] **Format** chosen *before* writing options — changing it later clears them
- [ ] **Linked regulation** set; confirm Domain / Sector auto-filled sensibly
- [ ] **Prompt EN** written; *Needs translation* left on until SI + TA are human-reviewed
- [ ] Option **values** short and lowercase; no builder warnings
- [ ] M2 only: correct answer marked
- [ ] M3 only: risk-signal mapping set, or deliberately left blank for informational items
- [ ] Branching: rules ordered most-specific-first; no red errors; previews read correctly
- [ ] Exactly one **Branching root** per section
- [ ] Verified by a CA before fieldwork (list view → **Verify selected**)

---

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Regulation dropdown empty; `422` on `/m1/regulations?size=200` | list endpoint capped page size at 100 | **Fixed** — cap raised to 500 |
| A label shows as `questions.fields.xyz` | stale front-end build after adding i18n keys | restart the dev server (`.next` cache) |
| Branching rule never fires | value isn't one of the declared options, or a numeric predicate on a text format | check §4 option values; the editor now flags both |
| Respondent skipped a question you expected | an earlier rule matched first, or the question is inactive / out of sector scope | check rule order and the Active + Sector flags |
| Survey starts at the wrong question | no branching root in that section, so it fell back to lowest sort order | mark the intended entry point as **Branching root** |
| Two questions share a code | pre-existing legacy rows; new codes are allocated server-side and cannot collide | rename the legacy row via duplicate + archive |

---

## 9. What changed in this revision (2026-07-29)

| Area | Before | After |
|---|---|---|
| Question code | free-text input, collision-prone | derived `module.section.qNN`, allocated server-side, shown read-only |
| Sort order | manual field | auto `max + 10` within section; editable on edit page |
| Version | manual field | hidden, defaults `v1`; on edit page |
| Instrument section | optional free text | **required**, suggests existing sections, drives the code |
| Domain / Sector | manual, easy to mis-tag | auto-filled from linked regulation, still overridable |
| Ground-truth source | free-text duplicate of the regulation citation | removed from the form; inherited from the link |
| Answers & options | generic builder | format-aware, seeded defaults, value-hygiene warnings |
| Branching | four predicates always offered, no feedback | format-restricted predicates, plain-English previews, six inline checks, explicit *Otherwise* branch |
| Regulations list | `422` at `size=200` | cap raised to 500 |

---

## Related

- `M1_NON_CODING_TASKS_AND_GOLIVE_READINESS_PLAN.md` — where this sits in go-live sequencing
- `05_MANUAL_TESTING_GUIDE.md` — end-to-end survey walkthroughs
- `04_API_AND_PAGES_REFERENCE.md` — the admin endpoints behind this form
