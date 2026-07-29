# Survey Builder & Question Assignment — Manual

> Group: `PROGRAM_READINESS`. Companion to `QUESTION_BANK_AUTHORING_AND_BRANCHING_MANUAL.md`.
> **Purpose.** How to assemble a survey out of the question bank — creating it, setting its scope, and picking the questions SMEs will actually be served. Covers the scope-resolution rules that decide what appears in the bank and what a respondent receives at runtime. Written 2026-07-29 against the rebuilt assigner.
> **Audience.** Researcher / research assistant. No coding required.

---

## 0. Two objects, one distinction worth getting straight

| | **Question bank** (`/admin/questions`) | **Survey** (`/admin/surveys`) |
|---|---|---|
| What it is | Every question that exists, across all modules | A *selection* of those questions, ordered, aimed at an audience |
| Analogy | The library | A reading list |
| Reused? | One question can appear in many surveys | A survey is a specific study instrument |
| Deleting | Retires the question everywhere | Only removes it from that one survey |

Assigning a question to a survey **copies nothing**. It creates a link. Edit the question's wording later and every survey using it updates — which is exactly what you want mid-study, and exactly why you should bump the **version** rather than silently rewrite a question already in the field.

---

## 1. Creating a survey — `/admin/surveys/new`

### 1.1 Survey identity

Title and description in **EN / SI / TA**. Title (English) is required; the other two are optional and fall back to English for respondents whose locale isn't filled in.

This is respondent-facing text. "Awareness of 2026 pricing regulations — grocery retail" beats "Test survey 3".

### 1.2 Module — **required**

| Option | Bank shows | Use when |
|---|---|---|
| **Unified — All Modules** | M1 + M2 + M3 | One sitting covering awareness → knowledge → vulnerability |
| **M1 — Awareness** | awareness only | Measuring the awareness gap on its own |
| **M2 — Knowledge** | knowledge only | Scored knowledge test |
| **M3 — Vulnerability** | vulnerability only | Risk-profile intake |

> [!warning] This was broken until 2026-07-29
> A survey saved as **Unified** was silently narrowed to M1 on the assign page — the code read `module_number ?? 1`, so a null (Unified) module became module 1. You could create a Unified survey and never be shown a single M2 or M3 question. Fixed: Unified now passes all three modules through.

### 1.3 Sector

Tick the study sectors this survey targets. **Leave all unticked = every sector.**

| Sector | Covers |
|---|---|
| Grocery / Food Retail | kade, mini-marts, small supermarkets |
| Food Service | restaurants, cafés, bakeries, take-aways |
| General-Goods Retail | textile/apparel, electronics/mobile, hardware |

Sector does two things: it filters what you can assign, and it decides which SMEs are served this survey at runtime (§4).

> [!warning] Also fixed on 2026-07-29
> The form has always written the **multi-sector** list, but two other places only read the older **single-sector** column. Consequences: the assign page filtered by neither, and the runtime resolver treated any multi-sector survey as *general* — so a grocery-only survey was served to restaurants and hardware shops alike. Both now read the multi-sector list, falling back to the legacy column.

### 1.4 Active

Unticked surveys are never served. Use it to stage a survey while you assemble questions, then flip it on when the instrument is final.

Saving takes you straight to **Manage questions**.

---

## 2. Manage questions — the assigner

Two panels. **Left: assigned questions** (this survey, in order). **Right: the question bank** (what you may add).

### 2.1 The scope banner

Above the bank sits a banner stating the survey's scope — module and sectors — plus the sentence *"Questions tagged All sectors always qualify."*

It exists to answer one question before you ask it: **"why is the bank empty / why can't I find that question?"** Nine times out of ten the survey's own Module or Sector is excluding it, and the banner says so without you having to open the edit page.

### 2.2 What "in scope" means

Two independent tests, both must pass:

**Module test** — the question's module must be one the survey covers. Unified covers all three.

**Sector test** — a question qualifies if **either**:

- its sector is one of the survey's sectors, **or**
- it has **no sector at all** ("All sectors").

The second half is the important one. A general question like *"How do you usually hear about new regulations?"* applies to every SME, so it appears in a grocery survey, a food-service survey and an all-sector survey alike. Without that rule you would have to author three near-identical copies of every general question — and then reconcile three sets of responses at analysis time.

#### The matrix, worked out

Bank contents:

| Question | Module | Sector |
|---|---|---|
| A | M1 | grocery_retail |
| B | M1 | *(none — all sectors)* |
| C | M2 | grocery_retail |
| D | M2 | *(none — all sectors)* |
| E | M3 | food_service |
| F | M1 | general_retail |

What each survey shows:

| Survey | Module | Sectors | Bank shows |
|---|---|---|---|
| Unified, all sectors | — | — | A B C D E F |
| Unified, grocery + food service | — | grocery, food | A B C D E |
| M1 only, all sectors | M1 | — | A B F |
| M1 only, grocery | M1 | grocery | A B |
| M2 only, grocery | M2 | grocery | C D |

Read row 2: **F is excluded** — it is general-retail-only and this survey targets grocery + food service. **B and D are included** despite having no sector, because "no sector" means "everyone".

Read the last row against row 4: same sector, different module, completely different question set. That is the module filter doing its job.

### 2.3 The four filters

Scope is fixed by the survey. These four narrow *within* scope, and every one is a **searchable dropdown** — type to filter, click to select, click the × to clear.

| Filter | Narrows to | Reach for it when |
|---|---|---|
| **Regulation** | questions linked to one regulation | Building a regulation-specific instrument — "everything we ask about MRP enforcement" |
| **Domain** | a regulatory area (VAT, EPF, PDPA, MRP) | You want the whole area regardless of which act each question cites |
| **Instrument section** | one authoring block (`pdpa`, `mrp`, `slsi`) | Pulling in a coherent, already-ordered block in one go |
| **Format** | Yes/No, MCQ, Likert… | Assembling a fast screening survey out of binary questions only |

They **stack** — Regulation `MRP_ENFORCEMENT_2026` + Format `Yes / No` gives every binary MRP question. A counter shows how many are active, and **Clear filters** resets all four at once without touching search or scope.

Free-text **search** runs alongside them, matching question code and English prompt, debounced so it doesn't fire a request per keystroke.

### 2.4 Adding and ordering

- **+** adds a question to the end of the assigned list.
- **Add all N** adds every unassigned question on the current page — the fast path after narrowing with filters.
- Already-assigned questions stay visible in the bank, dimmed and marked **Already assigned**, so you can see coverage rather than watching rows vanish.
- **▲ ▼** on the left panel reorder. Order in that panel is the order SMEs see.
- **−** removes from this survey. The question itself is untouched.

Adds, removes and reorders apply **optimistically** — the UI updates immediately and reconciles with the server behind it. If a call fails the row snaps back and an error toast appears, so you are never left believing a change stuck when it didn't.

### 2.5 Pagination

Bottom of the bank: **Showing 1–15 of 87**, a page-size selector (10 / 15 / 25 / 50) and prev/next. Page resets to 1 whenever a filter, the search box, or the page size changes — otherwise you would land on page 4 of a 1-page result and see an empty list.

During a refetch the list dims rather than collapsing to skeletons, so rows don't jump under the cursor.

---

## 3. Ordering: assigned order vs. branching

Two different mechanisms, and it is worth being precise about which wins.

| | **Assigned order** (this page) | **Branching rules** (question form) |
|---|---|---|
| Scope | one survey | the question itself, everywhere |
| Decides | the default sequence | jumps, conditional on the answer |
| Precedence | fallback | **wins when a rule matches** |

The engine, on every answer: test that question's branching rules top-to-bottom → first match jumps → **no match, fall back to the next question in order**.

So assigned order is the spine; branching is the shortcut. A survey with no branching anywhere runs exactly top to bottom.

> [!tip] Check branching targets are actually assigned
> If `awareness.mrp.q01` has a rule jumping to `awareness.mrp.q04` but you never added q04 to this survey, the jump can't land and the engine falls through to linear next. Assign both ends of every branch.

---

## 4. Runtime — which survey does an SME actually get?

When an SME starts a module, the resolver runs:

```
SME opens module M, sector S
   │
   ├─ 1. Active survey for module M targeting sector S?          → use it
   │       (matches the multi-sector list OR the legacy column)
   ├─ 2. Active GENERAL survey for module M?                     → use it
   │       (general = BOTH sector columns empty)
   ├─ 3. Repeat 1–2 for the Unified survey (module = null)       → use it
   └─ 4. Nothing configured → fall back to the raw question bank
```

Three consequences worth internalising:

1. **Sector-specific beats general.** A grocery survey and a general survey can coexist for the same module; grocery SMEs get the specific one, everyone else the general.
2. **Module-specific beats Unified.** A dedicated M1 survey overrides a Unified one for awareness.
3. **"General" now means genuinely general.** Before the fix, a survey with sectors ticked had a null legacy column and was misread as general — so a grocery instrument went to every SME. Now a survey only counts as general when *both* sector columns are empty.

> [!important] Only one active survey per (module, sector)
> Nothing stops you creating two. The resolver takes the most recent, but which one that is isn't obvious from the list view. Keep one active per combination and use **Active** to switch between them.

---

## 5. Worked example — MRP enforcement, grocery retail

**Research goal.** Measure awareness of the MRP rule among grocery retailers, and for those who are aware, test whether they understand its scope. One sitting, two modules.

### Step 1 — create

| Field | Value |
|---|---|
| Title (EN) | MRP awareness & knowledge — grocery retail, 2026 Q3 |
| Description (EN) | Baseline instrument for the awareness-gap study. |
| Module | **Unified — All Modules** |
| Sector | ☑ Grocery / Food Retail |
| Active | ☐ *(off while assembling)* |

Unified because we need M1 and M2 in one sitting. Sector grocery because that is the study population for this wave.

### Step 2 — what the bank now shows

Scope banner: **All modules · Grocery / Food Retail**.

Of the 87 questions in the bank, the bank shows those that are M1/M2/M3 **and** (grocery **or** no sector). Food-service-only and general-retail-only questions are gone. General questions like *"How did you first learn about regulatory changes?"* remain, correctly.

### Step 3 — pull in the MRP block

Set **Regulation** = `MRP_ENFORCEMENT_2026`. The bank drops to four questions. **Add all 4**.

Assigned:

```
1. awareness.mrp.q01  Are you aware that selling above MRP is an offence?
2. awareness.mrp.q02  When did you first learn it was an offence?
3. awareness.mrp.q03  Where did you learn about the MRP rule?
4. awareness.mrp.q04  What would have helped you find out?
```

### Step 4 — add the knowledge follow-up

Clear the regulation filter. Set **Domain** = `MRP` and **Format** = `MCQ (single)`. Two M2 questions appear — scope-of-rule items. Add both.

```
5. knowledge.mrp.q01  Which of these products is MRP labelling required on?
6. knowledge.mrp.q02  Who enforces the MRP rule?
```

### Step 5 — add the general context question

Clear filters. Search `first learn`. `awareness.general.q01` appears — no sector, so in scope. Add it and move it to **position 1** with ▲, so respondents start with an easy general question before the specific ones.

Final order:

```
1. awareness.general.q01   How did you first learn about regulatory changes?
2. awareness.mrp.q01       Are you aware selling above MRP is an offence?     ← branching root
3. awareness.mrp.q02       When did you first learn?
4. awareness.mrp.q03       Where did you learn?
5. awareness.mrp.q04       What would have helped?
6. knowledge.mrp.q01       Which products require MRP labelling?
7. knowledge.mrp.q02       Who enforces it?
```

### Step 6 — two respondents, traced

`awareness.mrp.q01` carries one branching rule: `answer_eq: no → awareness.mrp.q04`.

**Kamal — grocery SME who knows the rule**

```
1  general.q01   → "supplier"        no rules → next in order
2  mrp.q01       → yes               rule needs "no" ✗ → next in order
3  mrp.q02       → "before_2024"     → next
4  mrp.q03       → "supplier"        → next
5  mrp.q04       → answered          → next
6  knowledge.mrp.q01 → answered      → next
7  knowledge.mrp.q02 → answered      → complete
```

Seven questions. Yields depth of awareness **and** a knowledge score.

**Nadeeka — grocery SME who has never heard of it**

```
1  general.q01   → "never really"    → next in order
2  mrp.q01       → no                rule matches ✓ → jump to mrp.q04
5  mrp.q04       → "supplier_notice" → next in order
6  knowledge.mrp.q01 → guessed       → next
7  knowledge.mrp.q02 → guessed       → complete
```

Five questions. `mrp.q02` and `mrp.q03` skipped — she cannot say *when* or *where* she learned something she doesn't know.

### Step 7 — activate

Tick **Active** on the survey. Grocery SMEs now resolve to this instrument. Food-service and general-retail SMEs do **not** — they fall through to whatever general or Unified survey exists, or to the raw bank.

### What the study gets out of it

- `mrp.q01 = no` → the raw awareness gap, per sector.
- `mrp.q04` on the unaware → which channel would have closed the gap. Directly actionable.
- `knowledge.mrp.*` on the aware → whether awareness translates into correct understanding, which is the more interesting finding: an SME who knows the rule exists but not its scope is a *different* policy problem from one who has never heard of it.
- Path length itself is data — Nadeeka answered 5, Kamal 7, and the difference is the measurement.

---

## 6. Checklist

Before activating a survey:

- [ ] Title (EN) is descriptive enough to identify in the list six months from now
- [ ] **Module** matches the study design — Unified only if you genuinely want all three
- [ ] **Sector** ticked deliberately; unticked means *everyone*
- [ ] Scope banner on the assign page reads as expected
- [ ] Every intended question assigned — check the count
- [ ] Order reviewed; general/warm-up questions early
- [ ] Every branching **target** is also assigned to this survey
- [ ] Exactly one **Branching root** among the assigned M1 questions
- [ ] No competing active survey for the same (module, sector)
- [ ] Questions CA-verified where the design requires it
- [ ] **Active** ticked last, once the instrument is final

---

## 7. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Bank empty, no filters set | No question matches the survey's module + sector | Author one for this scope, or widen the survey's config |
| Unified survey shows only M1 questions | The `?? 1` bug | **Fixed 2026-07-29** — pull the latest build |
| Multi-sector survey shows everything / nothing | Assigner read the legacy single-sector column | **Fixed 2026-07-29** |
| Grocery survey served to restaurants | Resolver classified any multi-sector survey as *general* | **Fixed 2026-07-29** — general now requires both sector columns empty |
| A known question won't appear | Wrong module, wrong sector, or `is_active` off | Check its Module / Sector / Active on the question form |
| Respondent skipped a question you assigned | A branching rule jumped past it | Review rules on the preceding question |
| Branch jumps nowhere | Target isn't assigned to this survey | Assign the target too |
| Two surveys fight for the same audience | Both active for the same (module, sector) | Deactivate one |
| Search feels laggy | Debounced 300 ms by design | — |

---

## 8. What changed in this revision (2026-07-29)

| Area | Before | After |
|---|---|---|
| Unified surveys | coerced to M1, hiding M2 + M3 | all three modules in scope |
| Multi-sector surveys | assigner read the legacy single column | reads the multi-sector list, legacy fallback |
| Runtime resolver | any multi-sector survey counted as *general* | general requires both sector columns empty; sector membership matched properly |
| Unified at runtime | not resolvable | module-specific first, Unified as fallback |
| Bank filters | search only | + Regulation, Domain, Section, Format — all searchable, stackable, with a clear-all |
| Pagination | prev/next, fixed 15 | range counts, page-size selector, auto-reset on filter change |
| Add / remove | full refetch per action | optimistic with rollback; **Add all** for a filtered page |
| Scope visibility | one static hint line | banner naming the survey's actual module + sectors, and why the bank is limited |
| Bank rows | prompt + code | + module, section, format and sector badges |
| Backend list API | scalar module + sector only | repeatable `module_numbers` / `sector_codes`, plus section and format filters |

---

## Related

- `QUESTION_BANK_AUTHORING_AND_BRANCHING_MANUAL.md` — authoring the questions this page assigns
- `M1_NON_CODING_TASKS_AND_GOLIVE_READINESS_PLAN.md` — go-live sequencing
- `05_MANUAL_TESTING_GUIDE.md` — end-to-end survey walkthroughs
