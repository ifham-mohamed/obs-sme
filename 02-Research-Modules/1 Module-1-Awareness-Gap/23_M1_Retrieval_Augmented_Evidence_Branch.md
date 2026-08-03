# 23 — Module 1: Branch C — Retrieval-Augmented Evidence Branch

> [!success] Implementation status — 2026-08-03 (Session 74)
> **Phases 1–4 and 8 are built and tested** in `enigmatrix-ml`. Phases 0, 5, 6, 7 remain open. Every leakage rule in §7 and every kill criterion in §8 is enforced in code, not left to discipline. `linearsvc_v6_primary` verified byte-identical (14/14 SHA-256) after every run.
>
> **No real Branch C numbers exist yet** — the implementation was verified on synthetic data with an offline encoder. See [[2026-08-03_Branch_C_Retrieval_Evidence_Implementation|2026-08-03_Branch_C_Retrieval_Evidence_Implementation]] for what was built, what was found, and §11 below for the phase-by-phase status.

> **Design assessment and build plan.** Whether a retrieval branch is worth adding alongside Branch A (TF-IDF + LinearSVC) and Branch B (XLM-R + LoRA), what it can and cannot be claimed to prove, and how to build it without invalidating the result.
>
> The frozen `linearsvc_v6_primary` is **not modified**. Branch C is additive, in the same sense [[20_M1_Multitask_Classifier_Upgrade|V7]] is additive.
>
> Companion to [[05_M1_Model_Architecture|05_M1_Model_Architecture]] (branch design) · [[06_M1_Training_Evaluation|06_M1_Training_Evaluation]] (protocol and gates) · [[18_M1_Dataset_And_Model_Lineage|18_M1_Dataset_And_Model_Lineage]] (lineage) · [[20_M1_Multitask_Classifier_Upgrade|20_M1_Multitask_Classifier_Upgrade]] (the three-output head this feeds) · [[10_M1_Sinhala_Tamil_NLP|10_M1_Sinhala_Tamil_NLP]] (cross-lingual retrieval).

---

## 0. Verdict up front

**Build it — but not as a performance play.**

A retrieval branch is the right next component, for reasons that have nothing to do with beating 0.947 macro-F1. It is the only one of the three branches that can actually produce **Output 4**, which today does not exist: `LinearSVCGazetteInference` returns `confidence=None` by design, because LinearSVC decision margins are not calibrated probabilities. Branch A answers Outputs 1–3 well and Output 4 not at all.

The accuracy framing is the weak one, and §1.2 shows why with the arithmetic. It is still worth running the comparison — but as a reported curve with honest confidence intervals, not as the headline claim.

| Framing | Verdict | Where it lands |
|---|---|---|
| **Output 4 / explainability** | Strong. Fills a real, documented gap. Measurable on its own terms (ECE, risk-coverage, expert agreement) without depending on test-set size. | Headline contribution |
| **Rare-class rescue** | Strong and plausible. Retrieval is known to help most where supervision is thinnest, and `EPF_ETF_CHANGE` has 8 training rows. | Secondary claim, per-class evidence |
| **Beat A and B on accuracy** | Weak — not because Branch C won't help, but because the test split **cannot detect it**. Report it; do not stake the thesis on it. | Exploratory, reported with CIs |

---

## 1. The honest assessment

### 1.1 What the baseline actually is

From `models/m1/linearsvc_v6_primary/model_registry.json` and `runs/`:

| Model | Split | Macro-F1 | Accuracy | Errors |
|---|---|---|---|---|
| `linearsvc_v6_primary` (Branch A) | test (167 rows) | **0.9472** | 0.9581 | **7** |
| `linearsvc_v6_primary` | validation (166 rows) | 0.9245 | 0.9458 | 9 |
| tfidf_linsvc, 5-fold CV (v5) | CV | 0.9009 ± 0.0392 | — | — |
| tfidf_logreg, 5-fold CV (v5) | CV | 0.8506 ± 0.0545 | — | — |
| XLM-R + LoRA, category-only (Branch B) | Kaggle test (121) | 0.6415 | — | `gate_pass: false` |
| XLM-R + LoRA multitask V7, 3-seed e8 | test | 0.0936 | — | Rejected |
| XLM-R + LoRA V7 weighted, seed 42 | **validation only** | 0.8999 | — | Below 0.92 gate |

Two things follow immediately.

**Branch B is not currently a competitive branch.** Its best honest number (0.8999) is validation-only, single-seed, and still under the gate. Framing Branch C as "better than A and B" is partly a comparison against something that has not yet cleared its own bar. Fix or caveat that framing in the write-up.

**Branch A has 7 errors of headroom.** That is the entire target.

### 1.2 The power problem

With 167 test rows and 7 errors, the 95% Wilson interval on accuracy 0.9581 is **[0.9160, 0.9796]** — 6.35 percentage points wide. Any Branch C improvement smaller than that is invisible.

McNemar's exact test, where *b* = errors Branch C fixes and *c* = correct predictions Branch C breaks:

| C fixes | C breaks | Net errors | McNemar *p* | Significant? |
| ------- | -------- | ---------- | ----------- | ------------ |
| 7       | 0        | 0          | 0.0156      | ✅            |
| 6       | 0        | 1          | 0.0312      | ✅            |
| 5       | 0        | 2          | 0.0625      | ❌            |
| 6       | 1        | 2          | 0.1250      | ❌            |
| 4       | 0        | 3          | 0.1250      | ❌            |
| 5       | 1        | 3          | 0.2188      | ❌            |
| 3       | 0        | 4          | 0.2500      | ❌            |

> [!warning] Branch C must fix **at least 6 of 7 errors and break none** to reach *p* < 0.05.
> Fixing 5 and breaking 0 — a genuinely excellent result, a 29% relative error reduction — lands at *p* = 0.0625 and is not significant. The test set is too small for the claim, not the method too weak.

There is a second, sharper problem. **Macro-F1 is noise-dominated at the tail.** `EPF_ETF_CHANGE` has exactly **1** test row. Flipping that single row moves its class F1 from 1.0 to 0.0, which moves macro-F1 by **12.5 percentage points** — larger than the entire gap between Branch A and Branch B's best run. Any macro-F1 comparison on this split is, to a meaningful degree, a report on one document.

### 1.3 What to do about it

Three options, in order of preference:

1. **Report the accuracy comparison with bootstrap CIs and McNemar, and state plainly that the split lacks power.** Pre-register this before running. An examiner who sees you identify your own power limit trusts the rest of the document; one who catches it themselves does not.
2. **Add a second evaluation axis that does not depend on 167 rows** — retrieval Recall@k is measured per-query with k neighbours each, expert agreement on evidence is measured per-annotation. Both give you real *n*. This is §6.
3. **Grow the test set** before making accuracy claims. Not free, but the honest fix if accuracy must be the headline.

---

## 2. Why build it anyway

### 2.1 Output 4 does not currently exist

From `m1/model/inference.py`:

```python
class LinearSVCGazetteInference:
    """...LinearSVC decision scores are not calibrated probabilities, so this
    adapter returns confidence=None and exposes the decision margin
    separately."""
```

The four-output contract promises **confidence + evidence snippet**. The production model delivers neither. This is not a performance gap to be squeezed — it is an unimplemented output, and Branch C is the natural implementation:

- **Confidence** = neighbour-agreement mass. If 8 of 10 nearest expert-labeled gazettes carry `SECTOR_SPECIFIC`, that is 0.8, and it is calibrated by construction in a way a hinge-loss margin is not. Validate with a reliability diagram, ECE, and Brier score.
- **Evidence** = the retrieved precedents themselves, with gazette ID, date, expert label, similarity, and matched span.

Reporting "Branch A provides no confidence signal; Branch C provides one with ECE = *x*" is a complete, defensible result that never touches the 167-row problem.

### 2.2 Evidence as precedent, not as heatmap

This is the strongest conceptual argument and it deserves a section in the thesis.

A TF-IDF coefficient ("the token *cess* contributed +0.42") or an attention weight is an explanation of the *model*. A retrieved precedent — *"classified `TAX_RATE_CHANGE` because it closely resembles Gazette 2481/16, which a domain expert labeled `TAX_RATE_CHANGE`"* — is an explanation in the *user's and the expert's* vocabulary.

For a system whose users are SME owners and whose correction loop is expert routing (see the Stage-D/E hold-and-release pipeline, Session 108), precedent-based evidence is the only explanation type that both audiences can act on. The expert can accept or reject the precedent directly; that judgement becomes new labeled data. **The explanation and the feedback mechanism become the same object.**

### 2.3 Rare-class rescue

Training distribution — `m1_regulations_v6_1110_clean_fixedsplit`, the split the frozen primary was trained on (777 / 166 / 167). `SECTOR_SPECIFIC` is 61% of training data:

| Category | Train rows | Test rows |
|---|---|---|
| SECTOR_SPECIFIC | 474 | 102 |
| IMPORT_EXPORT | 78 | 17 |
| TAX_RATE_CHANGE | 58 | 12 |
| LABOUR_LAW | 52 | 11 |
| PENALTY_ENFORCEMENT | 46 | 10 |
| PRODUCT_STANDARD | 36 | 8 |
| BUSINESS_REGISTRATION | 25 | 6 |
| **EPF_ETF_CHANGE** | **8** | **1** |

A discriminative classifier cannot learn a decision boundary from 8 examples; it learns `class_weight="balanced"` and a prayer. A retrieval index does not need a boundary — it needs those 8 documents to be findable. This is precisely the regime where retrieval augmentation is documented to help ([Retrieval-augmented Multi-label Text Classification](https://arxiv.org/pdf/2305.13058) reports gains concentrated in limited-data and long-document settings).

Expect Branch C's gains to land on the ≤36-row classes and expect it to be neutral-to-slightly-worse on `SECTOR_SPECIFIC`. **Report per-class, not just macro.** If the story is "retrieval helps exactly where supervision is thinnest," that is a finding — and it is robust to the macro-F1 noise problem in a way the aggregate number is not.

### 2.4 Operational payoffs

- **Zero-retrain corpus growth.** Every newly expert-labeled gazette enters the index immediately. Branch A requires retrain → revalidate → promote. For a system ingesting gazettes continuously, this is a substantial deployment argument.
- **Reuse.** [[00-Meta/BUILD_Master_Index|BUILD_08]] (M2 Knowledge Hub) already specifies ChromaDB + a RAG Q&A endpoint over the M1 corpus, and BUILD_10 (M4 misinformation verifier) specifies the M1 corpus as RAG ground truth. **Branch C's index is that index.** Building it now buys M2 and M4 their retrieval layer and lets the thesis claim architectural coherence rather than three unrelated modules.

---

## 3. Novelty — what you cannot claim, and what you can

> [!danger] Do not write "we propose a novel retrieval-augmented classifier."
> The prior work is dense and a reviewer will find it in minutes.

**Established prior art:**

- kNN-LM — Khandelwal et al., 2020 — interpolating a parametric model with nearest-neighbour retrieval
- RAG — Lewis et al., 2020
- [KRA: K-Nearest Neighbor Retrieval Augmented Model for Text Classification](https://www.mdpi.com/2079-9292/13/16/3237) — exactly the C1/C2 design, across CNN/LSTM/BERT/RoBERTa
- [Retrieval-augmented Multi-label Text Classification](https://arxiv.org/pdf/2305.13058) — legal and biomedical domains, limited-data regime
- [Mind Your Neighbours: Leveraging Analogous Instances for Rhetorical Role Labeling for Legal Documents](https://arxiv.org/pdf/2404.01344) — neighbour-based methods on legal text
- Retrieval-based in-context example selection for LLM classification

**What is defensibly claimable, strongest first:**

1. **Cross-lingual precedent retrieval for a low-resource regulatory language pair.** A Sinhala or Tamil gazette retrieving English-labeled precedents through a shared multilingual space, with measured cross-lingual Recall@k. Sinhala/Tamil legal NLP is genuinely thin, this connects to existing work in [[10_M1_Sinhala_Tamil_NLP|10_M1_Sinhala_Tamil_NLP]], and it is a real empirical question rather than an engineering restatement. **This is the best novelty angle you have.**

2. **First benchmark and baseline suite for Sri Lankan Government Gazette regulation classification.** `m1/model/baselines.py` already states the position: *"the comparison is itself a research finding, since no prior baseline exists for Sri Lankan regulatory text."* A three-branch comparison — sparse discriminative, dense fine-tuned, retrieval — over a newly annotated corpus with published splits and a documented leakage audit is a contribution. **The contribution is the corpus and the comparison, not any single branch.**

3. **The evidence contract.** The claim that regulatory classification for SME compliance must carry a retrievable, expert-auditable precedent — evaluated by expert agreement on whether the retrieved precedent justifies the assigned label. Nobody has this for this domain, and it is a human-subjects result, not an algorithmic one.

4. **Selective prediction tied to expert routing.** Risk-coverage curves that translate directly into human-review load: *"at 85% coverage the system is 99% accurate; the 15% it abstains on route to an expert."* Deployment-relevant, uses the confidence Branch C provides, and connects to the hold/release pipeline that already exists.

The reframe: **novelty lives in the domain, the languages, and the evidence/abstention contract — not in the retrieval algorithm.** That is standard and entirely respectable positioning for an applied dissertation. Claiming algorithmic novelty here is the one move that would damage the work.

---

## 4. Architecture

Three variants. Build C1 and C2; treat C3 as an optional extra baseline.

```text
gazette text
     │
     ├──────────────► Branch A: TF-IDF → LinearSVC ──► margins ──┐
     │                                                            │
     └──► embed ──► hybrid retrieval over TRAIN-ONLY index        │
                    (BM25 + dense, RRF-fused)                     │
                         │                                        │
                         ├──► top-k labeled precedents            │
                         │         │                              │
                         │         ├──► similarity-weighted vote ─┤
                         │         │         = C1                 │
                         │         │                              ▼
                         │         │                    λ-interpolation = C2
                         │         │                              │
                         │         └──► LLM prompt = C3           ▼
                         │                              Output 1: domain
                         └──────────────────────────►   Output 2: sectors
                                    evidence snippets   Output 3: relevance
                                                        Output 4: confidence + evidence
```

**C1 — pure retrieval classifier.** Embed → retrieve top-k from the train-only index → similarity-weighted vote over neighbour labels. A standalone branch, directly comparable to A and B. Multi-label sectors fall out of the same neighbours by thresholding weighted sector mass.

**C2 — score fusion (recommended primary).** `p_final = λ · softmax(margin_A / T) + (1 − λ) · p_kNN`, with temperature *T* and mixing weight *λ* fitted on validation. This is the kNN-LM recipe. It is cheap, it is the variant most likely to actually move the number, and it lets retrieval rescue rare classes without disturbing `SECTOR_SPECIFIC`, where Branch A is already at 0.96 F1. **Side benefit worth reporting: fitting *T* also gives Branch A the calibrated confidence it currently lacks**, which means your confidence comparison is A-with-temperature vs. C2, a fairer and more interesting contrast than A-with-nothing.

**C3 — retrieval-augmented in-context learning.** Retrieve k labeled examples → construct prompt → LLM classifies. Highest ceiling, but it costs API budget, adds latency, complicates reproducibility, and overlaps the zero-shot LLM baseline already planned in `baselines.py`. Worth one run as an upper-bound probe; not worth making load-bearing.

### 4.1 Embedding model

> [!important] Do **not** reuse `xlm-roberta-base` CLS embeddings.
> Untuned XLM-R CLS vectors are known-poor for similarity, and this is plausibly part of why Branch B underperformed. An encoder trained for classification is not an encoder trained for retrieval.

Candidates to evaluate:

| Model | Why | Watch for |
|---|---|---|
| **LaBSE** | Strongest Sinhala/Tamil↔English sentence alignment; built for cross-lingual retrieval | 512-token limit; sentence-level, needs chunking |
| **BGE-M3** | Multilingual, long-document (8k), and emits dense + sparse + multi-vector in one pass — hybrid retrieval for free | Heavier; verify Sinhala/Tamil coverage empirically |
| **multilingual-e5-large** | Strong general multilingual retrieval baseline | Requires `query:`/`passage:` prefixes; easy to get wrong |

Evaluate all three on **Recall@k for cross-lingual retrieval specifically**, not just monolingual. That measurement is itself a reportable result for §3 claim 1.

### 4.2 Hybrid retrieval is likely to win

Branch A reaches 0.947 with TF-IDF alone — sparse legal-keyword matching is doing most of the work on this corpus. A purely dense retriever discards the signal you have the most evidence for. Run **BM25 + dense, fused with Reciprocal Rank Fusion**, and ablate all three (BM25-only, dense-only, hybrid). The ablation is cheap and the BM25-only arm doubles as a strong, hard-to-criticise retrieval baseline.

---

## 5. Build phases

### Phase 0 — Pre-register the evaluation (before any code)

Write down, and commit, before running anything:

- Primary claim: Output 4 quality (ECE, Brier, risk-coverage, expert agreement)
- Secondary claim: per-class F1 on the ≤36-train-row categories
- Exploratory: aggregate macro-F1 vs. Branch A, reported with bootstrap CI and McNemar, **with the §1.2 power limitation stated**
- Test split touched **once**, at the end. All k / λ / T / threshold selection on validation only.

This phase costs an hour and is the single highest-value item in the document.

### Phase 1 — Build the index

- Corpus = **train split only** — 777 rows if indexing against `m1_regulations_v6_1110_clean_fixedsplit` (what the frozen primary uses), or 773 if against the `..._multitask_noleak` variant. Pick one and state it; do not mix. See §7 — this is not optional.
- Store per row: text, chunk spans, `category`, `sectors`, gazette ID, publication date, language.
- Chunk long gazettes (many exceed 512 tokens); index at chunk level, aggregate to document by max-similarity.
- FAISS **flat/exact** index — 773 vectors is trivially small, and exact search removes ANN recall as a confound.
- Parallel BM25 index over the same corpus.
- Persist through the Chroma path that BUILD_08 will consume, so M2 inherits it.

### Phase 2 — C1, pure retrieval classifier

- Sweep k ∈ {1, 3, 5, 10, 20} on validation.
- Similarity-weighted vote → distribution over 8 categories; weighted sector mass → multi-label sectors via tuned threshold.
- Report validation macro-F1, per-class F1, and **Recall@k** (fraction of queries where ≥1 retrieved neighbour carries the gold label). Recall@k is your high-*n* metric — it does not suffer the §1.2 problem.

### Phase 3 — C2, fusion

- Fit *T* (temperature on Branch A margins) and *λ* on validation.
- Sweep λ ∈ [0, 1] in 0.05 steps; plot macro-F1 vs λ. **The curve is the result**, even if its peak is not significantly above λ = 1. A curve that rises then falls demonstrates that retrieval carries complementary signal; a flat curve demonstrates it does not. Both are publishable findings.

### Phase 4 — Output 4: the confidence and evidence contract

The core deliverable.

- **Confidence:** fused probability. Reliability diagram, ECE, Brier score. Compare A-uncalibrated (no signal) / A-temperature-scaled / C1 / C2.
- **Evidence:** top-3 precedents per prediction — gazette ID, date, expert label, similarity, matched span. Define the JSON contract now; it becomes an API response shape.
- **Risk-coverage:** sort test predictions by confidence, plot accuracy vs. coverage, report the operating point meeting the product's accuracy bar and the resulting human-review load. This connects directly to the existing expert-routing/hold pipeline.

### Phase 5 — Human evaluation of evidence

Small, and the most defensible result in the document.

Sample ~50 test predictions, show each retrieved precedent to domain experts (2 annotators), ask: *"Does this precedent justify the assigned label?"* Report agreement and Cohen's κ. You already have Label Studio configured and κ is already in the evaluation stack. **No test-set-size objection touches this result**, because *n* is the number of annotations, not the number of test rows.

### Phase 6 — Rare-class analysis

Per-class F1 for `EPF_ETF_CHANGE`, `BUSINESS_REGISTRATION`, `PRODUCT_STANDARD` across A / B / C1 / C2, with per-class bootstrap CIs. This is where the rare-class framing gets its evidence.

### Phase 7 — Cross-lingual retrieval

Query in Sinhala and Tamil against the English-labeled index and vice versa. Report Recall@k broken out by language pair, across the three embedding models. Feeds §3 claim 1 and [[10_M1_Sinhala_Tamil_NLP|10_M1_Sinhala_Tamil_NLP]].

### Phase 8 — Verification

- Leakage audit — assert no test/val ID or near-duplicate is in the index (§7)
- Bootstrap CIs on all headline numbers
- McNemar, A vs C1 and A vs C2
- 5-fold CV with the index **rebuilt per fold**
- Write results to the truth-ledger evidence JSON, matching the `M1_OPERATING_EVIDENCE_*.json` convention

---

## 6. Evaluation summary

| Metric | Effective *n* | Robust to §1.2? | Reports on |
|---|---|---|---|
| Recall@k | 167 queries × k | ✅ | Retrieval quality |
| Cross-lingual Recall@k | queries × k × pairs | ✅ | Novelty claim 1 |
| ECE / Brier | 167 predictions, binned | ✅ | Output 4 confidence |
| Risk-coverage curve | full curve | ✅ | Abstention / routing |
| Expert agreement + κ | ~50 × 2 annotators | ✅ | Novelty claim 3 |
| Per-class F1 (rare) | 1–8 rows/class | ⚠️ report CIs | Rare-class claim |
| Aggregate macro-F1 | 167 | ❌ underpowered | Exploratory only |

The top five rows are where the thesis should live.

---

## 7. Leakage — the failure that will silently invalidate everything

> [!danger] The index must contain **training rows only**.
> If all 1110 rows are indexed and then evaluated on test, every test row retrieves itself at similarity 1.0 and the result is ~100% accuracy and completely worthless. For cross-validation the index must be **rebuilt inside each fold**. This is the most common way this specific experiment gets quietly invalidated, and it looks like a spectacular result right up until someone asks.

The Step-41 audit already found this corpus is vulnerable: **8 within-split duplicate-text rows and 6 train–val overlap rows** in V6, cleaned to 1103 rows / 773-163-167 splits.

That audit checked **exact** text. Retrieval is broken by **near**-duplicates, which are far more common here — gazettes are formulaic, and successive amendments to the same ordinance share most of their boilerplate. Required additions:

1. **Near-duplicate audit before indexing.** Compute cosine similarity of every val/test row against every train row. Flag pairs > 0.95. Manually inspect. A test row whose nearest train neighbour is a 0.98-similar amendment of the same ordinance is not a fair evaluation item, and it will inflate Branch C specifically while leaving Branch A's number untouched — producing an apparent Branch C win that is pure artifact.
2. **Report the near-duplicate distribution** as a dataset-card addition in [[18_M1_Dataset_And_Model_Lineage|18_M1_Dataset_And_Model_Lineage]]. This is a genuine limitation of any gazette corpus and disclosing it strengthens the work.
3. **Temporal consistency.** V6 is a fixed temporal split. For deployment realism, a test gazette should not retrieve a precedent published after it. Train-only indexing gives you this for free on the current split; state it explicitly rather than leaving it implied.

---

## 8. Risks and kill criteria

| Risk | Signal | Response |
|---|---|---|
| Near-duplicate inflation | C1 ≥ 0.99 accuracy, or Recall@1 ≈ 1.0 | Stop. Run §7.1 audit before believing anything. |
| Retrieval adds no complementary signal | λ-curve is flat or monotone toward λ=1 | Legitimate negative result. Report it — a measured "retrieval does not help here, and here is why" is publishable and honest. |
| Embeddings fail on Sinhala/Tamil | Cross-lingual Recall@k near chance | Fall back to BM25 over translated text; report the failure as a low-resource NLP finding. |
| Branch C degrades `SECTOR_SPECIFIC` | Per-class F1 drops on the 474-row class | Expected and acceptable at small λ. Tune λ on validation; report the trade-off curve. |
| Scope creep into M2 | Building a full Q&A pipeline | Branch C needs the index, not the generation layer. Stop at retrieval + vote + fusion. |

**Kill criterion:** if after Phase 3 the λ-curve is flat *and* Recall@k is below ~0.7, retrieval is not finding useful precedents on this corpus. Write it up as a negative result with the diagnostic evidence and stop — do not proceed to Phases 5–7.

---

## 9. Effort and sequencing

| Phase | Effort | Blocking? |
|---|---|---|
| 0 — Pre-register | 1 hour | Blocks everything |
| 1 — Index + near-duplicate audit | 1–2 days | Blocks 2–7 |
| 2 — C1 | 1 day | |
| 3 — C2 fusion | 1 day | |
| 4 — Output 4 metrics | 2 days | Headline result |
| 5 — Expert evaluation | 1 day work, ~1 week wall-clock | Long pole — start recruiting during Phase 1 |
| 6 — Rare-class analysis | 0.5 day | |
| 7 — Cross-lingual | 1 day | |
| 8 — Verification | 1 day | |

**~2–3 weeks wall-clock**, with expert availability as the critical path. Start Phase 5 recruitment during Phase 1.

New code is additive and small: `m1/model/retrieval.py` (index build, kNN vote, fusion), `m1/model/calibration.py` (temperature, ECE, reliability), `scripts/audit_near_duplicates.py`. `linearsvc_v6_primary` stays frozen; Branch C reads its margins through the existing inference adapter and never writes to it.

---

## 10. One-paragraph summary

Branch C is worth building, but the reason is not the one in the original framing. Branch A is at 0.947 macro-F1 with 7 errors on 167 test rows, which means no accuracy improvement Branch C could plausibly deliver is statistically detectable on the current split — it would need to fix 6 of 7 errors and break none to reach *p* < 0.05, and a single `EPF_ETF_CHANGE` row is worth 12.5 points of macro-F1. What Branch C uniquely provides is **Output 4**, which does not exist today: `LinearSVCGazetteInference` returns `confidence=None` because hinge margins are not probabilities, and there is no evidence snippet at all. Neighbour agreement gives calibrated confidence; retrieved precedents give evidence that a domain expert can audit and that doubles as the correction loop. Retrieval also plausibly rescues the ≤36-training-row categories where a discriminative boundary cannot be learned, and the index it requires is the same index BUILD_08 and BUILD_10 already need. Claim novelty in the **cross-lingual Sinhala/Tamil precedent retrieval**, the **first gazette-classification benchmark**, and the **expert-auditable evidence contract** — never in the retrieval algorithm, which is well-established prior art. Build C1 and C2, guard obsessively against near-duplicate leakage, pre-register the evaluation, and let the human evaluation of evidence quality carry the contribution rather than a macro-F1 delta the data cannot support.

---

## 11. Implementation status — 2026-08-03 (Session 74)

Full session record: [[2026-08-03_Branch_C_Retrieval_Evidence_Implementation|2026-08-03_Branch_C_Retrieval_Evidence_Implementation]].

### Phase status

| Phase | Status | Where it lives |
|---|---|---|
| 0 — Pre-register the evaluation | 🔲 **not done** | must precede the first real run; the sweeps are coded but the commitment is not written down |
| 1 — Index + near-duplicate audit | 🟢 built | `scripts/build_m1_retrieval_index.py` · `scripts/audit_near_duplicates.py` |
| 2 — C1 pure retrieval classifier | 🟢 built | `RetrievalClassifier` in `m1/model/retrieval.py` |
| 3 — C2 fusion | 🟢 built | `m1/model/calibration.py` + the λ sweep in the evaluator |
| 4 — Output 4 contract + metrics | 🟢 built | `build_evidence_contract` · ECE / Brier / risk–coverage |
| 5 — Human evaluation of evidence | 🔲 blocked on expert availability | — |
| 6 — Rare-class analysis | 🟡 scaffolded | `c1_rare_class` block in the results JSON (support ≤ 10) |
| 7 — Cross-lingual retrieval | 🔲 not done | LaBSE default + Sinhala/Tamil tokenizer fixed, but no cross-lingual Recall@k measured |
| 8 — Verification | 🟢 done | 132 tests; all three CLIs run end-to-end |

### Deviations from the plan in §4–§5, and why

| Plan said | Built instead | Reason |
|---|---|---|
| Chunk with the XLM-R tokenizer | Character windows (1200 / 200 overlap) with char spans retained | A 1.1 GB SentencePiece download is not an acceptable dependency for an index build, and the dense encoder tokenises internally anyway. Char spans are what the evidence contract needs to quote a source span. |
| `rank_bm25` for sparse | Pure-Python BM25-Okapi, ~40 lines | Avoids a dependency, and made the Sinhala/Tamil tokenizer inspectable — which is how the mark-stripping defect below was found. |
| FAISS for dense | FAISS flat → sklearn cosine → NumPy matmul, in that order | All three exact. On ~800 rows the difference is milliseconds, so FAISS is optional rather than required. |
| Cosine > 0.95 audit | Cosine audit **plus** a hash-based exact-duplicate check | An encoder can score a verbatim duplicate at 0.93 and slip under the threshold. Hashing cannot miss. |
| — | Row-level collapse before voting | Without it, one long multi-chunk gazette occupies all *k* slots and casts *k* votes for its own label. `k` now means "k precedent documents", which is what an expert reading the evidence expects. |

### Two findings that change how §7 and §8 should be read

**A tokenizer defect was masquerading as §8's "embeddings fail on Sinhala/Tamil" risk.** `re.findall(r"\w+", …)` drops Unicode combining marks, so `බදු` tokenised as `බද` — Sinhala/Tamil vowel signs were being stripped and words split at each one. Sparse retrieval on both target languages would have been silently degraded, and the natural misdiagnosis is the embedding model. Fixed with explicit script ranges + a regression test. **Add "Unicode mark handling" to the §8 risk table** — it is a distinct failure mode from encoder quality, and it is cheap to test for.

**§7's Step-41 finding reproduces exactly, and the de-leaked split is not canonical.** 8 duplicate-text groups, 3 of them train↔val (6 rows) — matching Step-41's "8 within-split duplicate-text rows and 6 train–val overlap rows". But the cleaned 1103-row split exists only in the rejected **V7-W** lineage ([[22_M1_Data_Usage_and_Row_Count_Register|22_M1_Data_Usage_and_Row_Count_Register]]), not in `datasets/`. So:

- `linearsvc_v6_primary` is frozen against the **1110-row split that still contains the 6 overlap rows**.
- **Validation 0.9245 is optimistic** (3/166 rows = 1.8% are verbatim train copies). Magnitude of the bias is unquantified.
- **Test 0.9472 is unaffected** — no train↔test text duplication. Keep quoting the test number.

§7.3's temporal-consistency point holds and is now free: train-only indexing on a fixed temporal split means a test gazette cannot retrieve a precedent published after it.

### Kill criteria — instrumented

§8's leakage signal is no longer a thing to remember. `leakage_alarm` fires at C1 accuracy ≥ 0.99 or Recall@1 ≥ 0.99, prints the §8 STOP text, and the evaluator **exits 5**. Verified on a synthetic corpus constructed to trip it. The λ-flatness kill criterion is reported (full curve, both endpoints) but deliberately not automated — that judgement stays human.

### Before the first real run

1. Write Phase 0. The code will happily sweep k, sector threshold, T and λ; only a pre-registration stops that from becoming selection on validation dressed as a protocol.
2. `make dataset-inventory` on Windows — the 5 parquet-only versions under `enigmatrix-ml/datasets/` are still unread.
3. Decide the V6 leakage disposition (caveat the validation number, or rebuild 1103 as canonical and re-measure Branch A — the second invalidates 0.9245 and needs a re-freeze).

---

*Sources for prior-art positioning: [Retrieval-augmented Multi-label Text Classification](https://arxiv.org/pdf/2305.13058) · [KRA: K-Nearest Neighbor Retrieval Augmented Model for Text Classification](https://www.mdpi.com/2079-9292/13/16/3237) · [Mind Your Neighbours: Leveraging Analogous Instances for Rhetorical Role Labeling for Legal Documents](https://arxiv.org/pdf/2404.01344)*

---

## 12. Delivered — Branch C inside Gazette-SME-RA-HMT (2026-08-03)

This document specified Branch C. It is now **built, measured and integrated** as one of three
branches in the hybrid classifier. The full system write-up is
[[24_M1_RAHMT_Hybrid_Architecture]]; this section records only what the design predicted
versus what shipped.

### What was delivered as specified

| Specified here | Delivered |
|---|---|
| Additive alongside the frozen Branch A | Yes. `M1_CLASSIFIER_BACKEND` still defaults to `linearsvc`; the frozen artifact is untouched |
| Index = train rows only | Enforced in `branch_c_retrieval.py`. 777 rows, 768-dim, L2-normalised |
| Leave-one-out retrieval for train queries | Enforced (`exclude_self=True` on the train split) — without it the train features are perfect and fusion learns to over-trust retrieval |
| Precedent vote over top-k neighbours (C1) | `label_distribution()`, top-k 10, softmax over similarity/τ at τ = `0.05` |
| λ-fusion with Branch A (C2) | Generalised to a 4-way simplex fusion over A, B, C and a rule prior, weights grid-searched on **validation** |
| **Output 4 — the whole argument of this document** | **Delivered.** Calibrated confidence (domain ECE `0.0319`) plus an evidence snippet on **167/167** test records. `LinearSVCGazetteInference` still returns `confidence=None`, exactly as §2 said it must |

### What the power arithmetic predicted, and what happened

§1 argued that with 167 test rows and 7 Branch-A errors, a new branch would have to fix 6 of 7
and break none to reach *p* < 0.05 — so the branch must be argued on Output 4, not accuracy.

**Confirmed.** The full hybrid reached domain macro-F1 `0.9351` against Branch A's `0.9197`:
paired bootstrap `+0.0155`, 95% CI `[−0.0411, +0.0767]`, **`p = 0.548`**. The accuracy framing
was correctly abandoned before the run rather than after it.

### Measured contribution

Branch C standalone on the test split: domain macro-F1 **`0.8590`**, sectors `0.8675`,
relevance `0.9020`, joint exact-match `0.8443`, ECE `0.0564`. It earned a validation-fitted
fusion weight of **`0.30`** — the second largest of four, ahead of the transformer branch at
`0.15`. For a mechanism with no discriminative training at all, that is the strongest
available evidence that exemplar memory is a real evidence source rather than a garnish.

None of the §8 kill criteria fired.

### Deviations from this design, and why

| Design here | Shipped | Why |
|---|---|---|
| Hybrid **BM25 + LaBSE** retrieval | Dense-only `intfloat/multilingual-e5-base` | e5 is trained with explicit `query: ` / `passage: ` prefixes and is stronger out-of-the-box on this corpus size. **The consequence is honest: no lexical-hybrid ablation was run, so the "hybrid retrieval beats dense-only here" claim is unmade, not disproved.** Tracked as a `[~]` gate in [[final/works/03_FEATURE_CHECKLIST\|03_FEATURE_CHECKLIST]] §23 |
| Branch C as a bolt-on to the frozen Branch A | Branch C as one of three branches in a jointly-fitted fusion | The multi-task upgrade made a joint fit the cleaner design; the frozen artifact is still not modified, so the additive constraint holds |

### One correction found while integrating

`label_distribution()` accumulated its similarity-weighted vote in `float32`. Ten float32
weights summing to 1.0 leave a ~1e-7 residue, producing probabilities such as `1.000000119`.
`fusion.apply_temperature` takes `log()` of those and `metrics.expected_calibration_error`
bins them into `[0, 1]`, so an out-of-range value corrupts calibration and can move a record
into the wrong abstention rung. Now accumulated in float64, nan/inf-scrubbed, clipped to
`[0, 1]`, and renormalised onto the simplex before casting back to float32.

**The encoder is not a swappable choice.** `index_train.npz` holds vectors produced by
`multilingual-e5-base`; a different encoder produces a different vector space in which every
cosine similarity against the index is meaningless. The runtime encoder name is pinned in
`branch_c_report.json` and its commit hash in `results/_huggingface_repos.json`.
