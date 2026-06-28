# 01 — AI/ML Fundamentals

> Goal of this document: give you a clear, no-hand-waving understanding of what model training actually is, what data it needs, and whether to train from scratch or fine-tune. By the end you should be able to explain these concepts to your supervisor.

---

## 1. What is a Machine Learning Model, Really?

A model is a **mathematical function** with a very large number of internal numbers called **parameters** (also called **weights**). For example:

- A small linear regression model might have 5 parameters.
- A medium neural network might have 1 million parameters.
- BERT-base has about 110 million parameters.
- XLM-R-base (which you will use) has about 270 million parameters.
- GPT-4-class models have hundreds of billions.

The model takes an input (e.g. a sentence), pushes it through layers of math involving these parameters, and produces an output (e.g. a category label, a translation, a probability).

**Training = finding the values of those parameters that make the input → output mapping as accurate as possible on your data.**

That is it. Every other detail (loss functions, optimizers, learning rates, gradient descent, backpropagation) is just engineering machinery to do that one thing efficiently.

---

## 2. What Happens Internally During Training (Step by Step)

Take one training example: an input `x` and the correct answer `y`.

1. **Forward pass.** Push `x` through the model. The model produces a prediction `ŷ`.
2. **Loss calculation.** Compare `ŷ` with `y` using a *loss function* (e.g. cross-entropy for classification). The loss is a single number — how wrong the model was.
3. **Backward pass (backpropagation).** Calculate, for each parameter, how much it contributed to the loss. This is done using calculus (gradients).
4. **Parameter update.** Nudge each parameter slightly in the direction that would reduce the loss. The size of the nudge is the *learning rate*.
5. Repeat for the next example. After seeing the whole dataset once, you have completed one *epoch*. Most models train for several epochs.

After many millions of these tiny updates, the parameters settle into values that make the model produce reasonable predictions on inputs it has never seen before.

**That generalization to unseen inputs is the entire point.** A model that memorizes the training data but fails on new examples is useless. This is called overfitting.

---

## 3. Train From Scratch vs Fine-Tune — The Single Most Important Decision

| Aspect | Train From Scratch | Fine-Tune Pretrained Model |
|--------|--------------------|-----------------------------|
| **What it means** | Initialize all parameters randomly, train the entire model on your data | Take a model that someone else already trained on a huge general dataset, then train only further on your domain data |
| **Data needed** | Millions to billions of labeled examples | Hundreds to a few thousand labeled examples |
| **Compute needed** | Weeks to months on multi-GPU clusters; costs thousands to millions of dollars | Hours to a few days on a single GPU; can be done on Google Colab or Kaggle for free |
| **Time** | Months of engineering | Days |
| **When appropriate** | Genuinely new architecture research, or a domain where no pretrained model exists | Almost every applied research project — including yours |
| **Risk** | Likely to fail because you do not have enough data or compute | Low; the pretrained model already knows language — you only teach it your specific task |
| **Novelty for research** | Novelty is in the architecture | Novelty is in your data, your task, your evaluation, your findings |

### Verdict for Enigmatrix

**Fine-tune. Every module fine-tunes existing models.** Your novelty is not "we trained a new transformer" — your novelty is the dataset, the measurements, the application to Sri Lankan SME compliance, and the cross-lingual evaluation. The model is your *instrument*, not your contribution.

Trying to train from scratch with your data would produce a worse model than fine-tuning, and it would consume the months you should be spending on data collection and analysis.

---

## 4. What is "Pretrained"?

A pretrained model is one that has already learned a general task on a massive dataset, before you ever touch it.

**Examples relevant to Enigmatrix:**

- **XLM-R (XLM-RoBERTa)** — pretrained on 2.5 TB of text in 100 languages including Sinhala and Tamil. It already understands sentence structure, vocabulary, and semantics in your three target languages.
- **mBERT (multilingual BERT)** — similar idea, smaller, supports 104 languages.
- **LaBSE** — sentence-embedding model, very strong for cross-lingual semantic search.
- **MarianMT / NLLB-200** — translation models, useful for Sinhala/Tamil ↔ English.

When you fine-tune XLM-R on your regulatory classification task, you are saying: "You already know how language works in 100 languages. I just need you to learn that *this* sentence means VAT-rate-change and *that* sentence means EPF-deadline-extension." The model only has to learn the new categorization, not the language itself.

---

## 5. What Type of Data Do You Need?

This depends on the task. For Enigmatrix:

### Classification tasks (Modules 1, 4)
You need **labeled examples**: pairs of `(text, category)`. For example:

```
"Notice is hereby given that VAT rate shall be revised to 18% with effect from..."
→ category: "TAX_RATE_CHANGE"

"The Commissioner General hereby extends the deadline for filing..."
→ category: "DEADLINE_EXTENSION"
```

You will manually label 500–1500 examples per classifier. This is the most time-consuming and most important step.

### RAG / Question-answering (Module 2)
You need a **knowledge base** (your verified compliance documents) plus an **evaluation set** of `(question, ground-truth-answer)` pairs.

### Regression / risk prediction (Module 3)
You need **feature vectors** with **outcome labels**: rows describing an SME (sector, age, size, region, history) plus a binary label (compliant / non-compliant).

### Misinformation detection (Module 4)
You need **annotated claims**: text claim + label (accurate / partially accurate / misleading / false) + ideally the source it came from.

---

## 6. How Does the Model "Learn From the Data"?

Concretely:

- For **classification**, the model adjusts weights so that for each labeled example, the probability it assigns to the correct category goes up and the probability it assigns to wrong categories goes down.
- For **regression**, the model adjusts weights so that its predicted number gets closer to the true number.
- For **RAG**, no weight adjustment happens — instead, the system retrieves relevant documents and an LLM reads them. Your "training" here is curating the knowledge base and tuning retrieval.

The crucial point: a model only learns patterns that are present in your training data. If you never label a "deadline-extension" example, the model will never learn to recognize one. **The quality of your labels caps the quality of your model.**

---

## 7. Adapting Existing Models to Your Domain — Three Levels

There is a spectrum of how much you change a pretrained model. From cheapest to most expensive:

### Level 1 — Zero-shot / few-shot prompting (no training)
Use an instruction-tuned LLM (GPT-4, Claude, Gemini, Llama-3-Instruct) and give it the task in the prompt. No training needed.

- **Pros:** Fastest, no data collection needed.
- **Cons:** API cost, less control, no novel research contribution.
- **Use case for you:** Baseline for comparison, or for low-volume tasks.

### Level 2 — RAG (Retrieval-Augmented Generation)
Don't change the model. Instead, retrieve relevant documents from your knowledge base and inject them into the prompt. Used heavily in Module 2.

- **Pros:** No training, knowledge base updates instantly, citations are natural.
- **Cons:** Quality depends on retrieval quality.
- **Use case for you:** Module 2 (compliance Q&A), Module 4 (claim verification).

### Level 3 — Full fine-tuning
Update the pretrained model's weights using your labeled data. Used for classifiers in Modules 1 and 4.

- **Pros:** Best accuracy on your specific task, becomes your IP, runs locally.
- **Cons:** Needs labeled data, needs GPU, needs evaluation.
- **Use case for you:** Module 1 regulatory-change classifier, Module 4 misinformation classifier.

### Level 4 — Parameter-Efficient Fine-Tuning (LoRA, QLoRA, adapters)
A modern compromise. Only train a small percentage of the parameters (~1%). Almost as accurate as full fine-tuning but 10× faster and uses less GPU memory.

- **Pros:** Cheap, fast, runs on consumer GPUs.
- **Cons:** Slight accuracy drop on some tasks.
- **Use case for you:** Recommended approach if you have GPU constraints.

---

## 8. The Mental Model You Should Carry Forward

Whenever you see a model task in your research, ask in this order:

1. Can a rule-based or keyword approach solve this acceptably? (Often yes, and that is your baseline — never skip this.)
2. Can RAG plus a general LLM solve this? (Yes for QA-style tasks.)
3. Do I need a fine-tuned classifier? (Yes for high-volume, low-latency, structured-output tasks.)
4. Do I need to train something from scratch? (Almost certainly no.)

Your final model choice for each module will be a **stack of approaches** — usually a baseline (Level 1/2) plus a fine-tuned model (Level 3) — and your research finding includes the comparison.

---

## 9. Common Mistakes to Avoid

| Mistake                                               | Why it hurts                                                                          | Fix                                                                                                             |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Reporting only the fine-tuned model's accuracy        | No baseline to compare against — reviewers will reject                                | Always report at least one rule-based baseline AND the pretrained zero-shot baseline AND your fine-tuned result |
| Training and evaluating on the same data              | Inflated accuracy, model has memorized                                                | Strict train / validation / test split (e.g. 70 / 15 / 15) — test set seen ONLY at the end                      |
| Using accuracy on imbalanced data                     | Misleading — 95% accuracy on 95-positive data is achieved by always saying "positive" | Report precision, recall, F1, confusion matrix, and macro-F1                                                    |
| Labeling everything yourself with no second annotator | Cannot measure label reliability                                                      | Have at least 2 annotators for ≥ 10% of data, report Cohen's Kappa                                              |
| Skipping a held-out test set                          | Cannot honestly claim generalization                                                  | Lock the test set away until the final evaluation                                                               |

---

## 10. Summary in One Paragraph

You will not train models from scratch. You will fine-tune existing multilingual models (XLM-R is your default) on small labeled datasets that you carefully construct. You will compare each fine-tuned model against simple baselines so the improvement is measurable. Your novelty is in the data you collect and the questions you answer — not in the model architecture. The technical steps (data → preprocessing → fine-tuning → evaluation) are well-trodden; the research contribution is the *measurement* of phenomena nobody has measured before in the Sri Lankan SME context.
