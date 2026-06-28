# 04 — Technology Stack Justification Guide

> Goal: for every technology in your stack, give you the answer to "why this and not the alternative" so you can defend each choice in viva.

---

## 1. The Defense Pattern

For every technology, you should be able to answer five questions:

1. **What** does it do?
2. **Why** is it appropriate for our project?
3. **What is the alternative** we considered?
4. **Why did we not choose the alternative?**
5. **What are its limitations?**

This document provides those answers for each technology in the proposal stack.

---

## 2. Programming Language: Python

**What:** General-purpose interpreted language with the strongest ecosystem for ML, data science, NLP, and rapid backend development.

**Why for this project:**
- Every ML/NLP library you need is Python-first (HuggingFace, PyTorch, TensorFlow, scikit-learn, spaCy).
- FastAPI (your backend) is Python.
- Data processing pipelines (Pandas, PyMuPDF, BeautifulSoup) are Python.
- Single-language stack across data, ML, and API reduces context-switching.

**Alternatives considered:**
- **R** — strong statistics, weaker NLP / production ecosystem.
- **JavaScript / Node** — fine for backend + scraping, but ML support is significantly weaker (TensorFlow.js, ONNX runtime exist but are second-class).
- **Java** — solid backend, almost no modern NLP ecosystem.

**Why not those:** Having to translate between an ML language (Python) and a backend language (Java/Node) doubles the integration work. Python + FastAPI keeps everything in one language.

**Limitations:**
- Slower than compiled languages — irrelevant for our use case because the heavy work happens in C-backed libraries.
- GIL limits true multithreading — we use multiprocessing or async IO instead.

**Cite:** Pedregosa et al. (scikit-learn), Wolf et al. (HuggingFace transformers), van Rossum (Python language).

---

## 3. ML Framework: PyTorch (with HuggingFace Transformers)

**What:** PyTorch is a deep learning library. HuggingFace Transformers is a high-level API on top of PyTorch (and TensorFlow) that gives access to thousands of pretrained models.

**Why for this project:**
- HuggingFace is the de-facto standard in NLP research — almost every modern model is published with HuggingFace weights.
- PyTorch is dominant in research (~80% of NLP papers) → easier to follow and adapt published methods.
- Built-in `Trainer` API handles training loop boilerplate.
- `pipeline()` API allows zero-shot use for baselines without writing training code.

**Alternative considered: TensorFlow / Keras**
- Equally capable.
- Stronger industrial deployment story (TF Serving, TFLite).
- More complex API.

**Why PyTorch over TensorFlow:** Research velocity matters more than deployment polish for a 6-month project. HuggingFace works on both, but PyTorch backend is the default and better-documented path.

**Limitations:**
- Memory-hungry for large models — mitigated by using `XLM-R-base` (270M parameters) instead of large.
- Production deployment (TorchServe, ONNX) is less polished than TF Serving — mitigated by simply wrapping with FastAPI.

**Cite:** Paszke et al. 2019 (PyTorch), Wolf et al. 2020 (HuggingFace Transformers).

---

## 4. Specific Models

### XLM-RoBERTa (XLM-R)

**What:** A multilingual transformer pretrained on 100 languages including Sinhala and Tamil.

**Why:** You have data in three languages. Single-model multilingual support eliminates needing separate models per language. XLM-R consistently outperforms mBERT on low-resource South Asian benchmarks.

**Alternatives:**
- **mBERT** — older, weaker on low-resource languages.
- **IndicBERT** — South Asian focus, smaller, less coverage of Sinhala.
- **LaBSE** — sentence embedding only, not for classification.

**Cite:** Conneau et al. 2020 ("Unsupervised Cross-lingual Representation Learning at Scale").

### XGBoost

**What:** Gradient-boosted decision tree library.

**Why for Module 3:** Tabular data with mixed categorical / numerical features, often class-imbalanced — exactly XGBoost's strength. Fast, interpretable (feature importance), works well on small datasets.

**Alternative:** LightGBM (similar performance, faster training), Random Forest (simpler, slightly weaker).

**Cite:** Chen & Guestrin 2016.

### LSTM (TensorFlow / Keras)

**What:** Recurrent neural network for sequential data.

**Why for Module 3:** If you have time-series of SME behavior (filings over time, payment history), LSTM captures temporal patterns that XGBoost on aggregate features cannot.

**Alternative:** Transformer-based time-series models (TST), 1D CNN.

---

## 5. RAG Stack: LangChain + ChromaDB / FAISS

**What:**
- **LangChain** orchestrates: load documents → split → embed → store → retrieve → prompt LLM.
- **ChromaDB** is an open-source vector database — stores embeddings and supports similarity search.
- **FAISS** is a Facebook-built similarity search library — faster, less feature-rich than Chroma.

**Why for Modules 2, 4:** RAG is the standard pattern for grounding LLM answers in a verified knowledge base. LangChain reduces boilerplate. ChromaDB has a simple Python API and persists to disk.

**Alternatives:**
- **LlamaIndex** — equally good RAG framework, slightly more focused.
- **Pinecone / Weaviate** — managed vector DBs, paid, faster at scale.
- **pgvector** — PostgreSQL extension for vector storage. Single-database simplicity but slower at scale.

**For your project size** (KB of a few thousand documents), ChromaDB on a single machine is more than sufficient.

**Cite:** Lewis et al. 2020 (RAG paper), LangChain documentation, Chroma documentation.

---

## 6. Backend: FastAPI

**What:** Modern, async Python web framework optimized for building APIs.

**Why for this project:**
- Native Python type hints → automatic request/response validation via Pydantic.
- Auto-generated OpenAPI / Swagger documentation — saves you writing API docs.
- Async-friendly — handles concurrent requests well, important when serving model inference and database queries.
- Minimal boilerplate.
- Same language as your ML code → no inter-process bridges needed.

**Alternatives:**
- **Flask** — simpler but synchronous, no auto-validation, no auto-docs. You would write more code.
- **Django** — heavyweight, opinionated, REST framework requires extra setup. Overkill for an API.
- **Node.js (Express / NestJS)** — fine, but introduces a second language to your stack.

**Limitations:**
- Newer than Flask/Django — less Stack Overflow content.
- Requires understanding of async/await for advanced use.

**Cite:** Ramirez (FastAPI documentation), Pydantic project.

---

## 7. Frontend: Next.js (React + TypeScript)

**What:** A React framework that adds server-side rendering, file-based routing, API routes, and production-ready defaults.

**Why for this project:**
- React is the dominant frontend ecosystem → vast component library, hiring pool, documentation.
- Next.js handles routing, building, optimization out of the box → faster development.
- Server-side rendering useful for SEO if any public pages.
- TypeScript catches integration bugs at compile time — important when calling APIs whose contract is changing.
- Tailwind CSS pairs naturally with Next.js for fast UI development.

**Alternatives:**
- **Plain React** (Vite) — lighter, fewer features, more setup.
- **Vue / Nuxt** — fine, smaller ecosystem.
- **Svelte / SvelteKit** — modern, very productive, smaller community.
- **Streamlit** — Python-based, perfect for quick demos, terrible for production UX.

**Recommendation:** Use **Streamlit** for quick research prototypes and internal demos (e.g. classifier preview). Use **Next.js** for the actual SME-facing platform.

**Cite:** Next.js documentation, React documentation.

---

## 8. Database: PostgreSQL

**What:** Open-source relational database with strong consistency, JSON support, full-text search, and extensions like pgvector.

**Why for this project:**
- All your data is fundamentally relational (SMEs, regulations, surveys, classifications, training records have keys and foreign keys).
- ACID transactions ensure your trained-status flag updates atomically with training records.
- JSON column type handles flexible fields without schema explosion.
- Full-text search (`tsvector`) good for searching gazette text.
- pgvector extension adds vector embedding storage if you want a single database.
- Mature ecosystem (psycopg, SQLAlchemy, Alembic for migrations).

**Alternatives:**
- **MySQL / MariaDB** — comparable, slightly weaker on advanced features (CTEs, window functions, JSON).
- **MongoDB** — document store, fine for unstructured data, weaker for relational queries you need (joining survey responses to SME profiles).
- **SQLite** — great for prototyping, not for concurrent multi-user.

**Why PostgreSQL over MongoDB:** Your data is relational. Survey responses join to SME profiles join to regulations. Forcing this into MongoDB would mean either denormalizing (data duplication) or doing application-side joins (slow, error-prone).

**Limitations:**
- More schema discipline required than NoSQL — but this is actually a *benefit* for research data integrity.

**Cite:** PostgreSQL documentation, Stonebraker (relational model foundation).

---

## 9. Vector Database: ChromaDB

Already covered in §5. Note: you can also use **pgvector** (PostgreSQL extension) to keep one database. For a research project, ChromaDB is simpler. For long-term production, pgvector consolidates.

---

## 10. Web Scraping: Scrapy + BeautifulSoup + Playwright

**What:**
- **Scrapy** — full scraping framework with concurrent requests, retry logic, pipelines.
- **BeautifulSoup** — HTML parser for one-off scraping scripts.
- **Playwright** — browser automation for JavaScript-heavy sites.

**Why this combination:**
- Use **BeautifulSoup + requests** for simple static pages (news archives).
- Use **Scrapy** when you need to scrape many pages with rate limiting, retries, polite crawling.
- Use **Playwright** when the site renders content via JavaScript (some news sites, some social platforms).

**Alternatives:**
- **Selenium** — older browser automation, slower than Playwright.
- **Puppeteer** — Node.js-based, similar to Playwright.

**Cite:** Scrapy documentation, BeautifulSoup documentation, Playwright documentation.

---

## 11. PDF Parsing: PyMuPDF (fitz) + pdfplumber

**What:**
- **PyMuPDF** (`fitz`) — fast, accurate text and layout extraction from native PDFs.
- **pdfplumber** — high-level API specifically good at table extraction and detailed layout analysis.

**Why both:** PyMuPDF is faster for bulk text extraction; pdfplumber is better when you need positional precision (for tables in regulations). Most pipelines use PyMuPDF first; fall back to pdfplumber for problematic pages.

**Alternatives:**
- **PyPDF2 / pypdf** — works but extraction quality is poor.
- **pdfminer.six** — basis of pdfplumber, lower-level.
- **OCR (Tesseract / EasyOCR)** — necessary when the PDF is scanned (image-only).

**For Module 1 you will use:** PyMuPDF as the default, pdfplumber for tables, Tesseract OCR for scanned older gazettes.

**Cite:** PyMuPDF documentation, pdfplumber GitHub.

---

## 12. NLP: spaCy + HuggingFace Transformers

**What:**
- **spaCy** — fast, production-grade pipeline for tokenization, NER, dependency parsing in 70+ languages including Sinhala (community model) and Tamil (limited).
- **HuggingFace Transformers** — already covered.

**When to use which:**
- **spaCy** for: tokenization, sentence segmentation, fast NER, rule-based pattern matching, when you need millisecond latency on millions of documents.
- **Transformers** for: classification, semantic similarity, embeddings, when accuracy matters more than speed.

**Cite:** Honnibal & Montani (spaCy), Wolf et al. (Transformers).

---

## 13. Annotation: Label Studio

**What:** Open-source data labeling platform supporting text classification, NER, image annotation, etc.

**Why:** Web-based UI, multi-user support, exports to standard formats, supports inter-annotator agreement workflows.

**Alternatives:**
- **Doccano** — simpler, lighter, less feature-rich.
- **Prodigy** — paid, excellent active-learning features.

**For Enigmatrix:** Label Studio is the right balance.

---

## 14. Synthetic Data: SDV / CTGAN / Faker

**What:**
- **SDV** (Synthetic Data Vault) — high-level library for synthetic tabular data generation that preserves statistical properties.
- **CTGAN** — GAN-based tabular generator, used inside SDV.
- **Faker** — generates fake names, addresses, phone numbers — useful for placeholder fields.

**Why for Module 3:** Real defaulter records are limited. Synthetic data calibrated against public population statistics (sector distribution, business age distribution from CBSL) lets you train risk models without privacy concerns.

**Critical:** Synthetic data must be **clearly labeled as synthetic** in every figure and table, and you must report performance separately on real-only vs combined data.

**Cite:** Patki et al. 2016 (SDV), Xu et al. 2019 (CTGAN).

---

## 15. Translation: Google Translate API / NLLB-200

**What:**
- **Google Translate API** — paid managed service, broad language support including Sinhala and Tamil.
- **NLLB-200** (No Language Left Behind, Meta) — open-source 200-language translation model.

**Why:** Module 4 collects Sinhala/Tamil social posts; you need them in English for cross-language analysis (or to use English-only baseline models).

**Choice:** Use Google Translate for survey-volume work (cheap, easy). Use NLLB-200 self-hosted if you have privacy concerns or large volumes.

**Critical:** Always keep the original-language text alongside the translation. Do all final analysis on the original where possible. Translation introduces errors you must report.

**Cite:** NLLB Team 2022 (No Language Left Behind paper).

---

## 16. Evaluation: RAGAS, Cohen's Kappa, scikit-learn metrics

**What:**
- **RAGAS** — RAG-specific evaluation framework: faithfulness, answer relevance, context precision, context recall.
- **Cohen's Kappa** — inter-annotator agreement metric.
- **scikit-learn metrics** — precision, recall, F1, ROC-AUC, etc.

**Why:** Each metric is the standard for its task. RAGAS is required to defensibly evaluate Module 2's RAG system.

**Cite:** Es et al. 2023 (RAGAS), Cohen 1960 (Kappa), Pedregosa et al. (scikit-learn).

---

## 17. Visualization: Plotly + Matplotlib + Seaborn

**What:**
- **Matplotlib** — foundational, every plot type.
- **Seaborn** — statistical plotting on top of Matplotlib (cleaner API).
- **Plotly** — interactive plots for dashboards and reports.

**Recommendation:** Use **Seaborn** for thesis figures (publication quality, simple API). Use **Plotly** for the web dashboard (interactivity).

---

## 18. Model Interpretability: SHAP

**What:** Shapley-value-based feature attribution. Tells you which features drove each prediction.

**Why for Module 3:** Examiners (and SMEs) will demand explanations for risk scores. SHAP provides per-prediction explanations and global feature importance.

**Cite:** Lundberg & Lee 2017.

---

## 19. Decision Summary Table

| Layer | Tech chosen | Main alternative | Why we chose ours |
|-------|-------------|-------------------|--------------------|
| Language | Python | Node.js | Single-language stack with ML libraries |
| ML Framework | PyTorch + HF | TensorFlow + Keras | Research-dominant, faster iteration |
| LLM (small) | XLM-R | mBERT | Better Sinhala/Tamil support |
| Tabular ML | XGBoost | LightGBM | Mature, interpretable, fast |
| RAG framework | LangChain | LlamaIndex | Bigger community, more docs |
| Vector DB | ChromaDB | pgvector | Simple, persistable, project-scale |
| Backend | FastAPI | Flask / Django | Async, type-safe, auto-docs |
| Frontend | Next.js | Plain React / Streamlit | Production quality + SEO + routing |
| Database | PostgreSQL | MongoDB | Relational data integrity |
| PDF parsing | PyMuPDF + pdfplumber | PyPDF2 | Better text + table extraction |
| Scraping | Scrapy + Playwright | Selenium | Scrapy is faster + Playwright is modern |
| Annotation | Label Studio | Doccano | More features, multi-user |
| Synthetic data | SDV | DataSynthesizer | Easier API, better calibration |
| Translation | Google Translate / NLLB | DeepL | Sinhala/Tamil coverage |
| Eval (RAG) | RAGAS | Manual only | Standard, automated |
| Interpretability | SHAP | LIME | More principled, more popular |
| Viz | Seaborn + Plotly | ggplot (R) | Single-language stack |

---

## 20. How to Cite Technology Choices in Your Thesis

Use this template sentence for the methodology chapter:

> "The classification component was implemented using HuggingFace Transformers (Wolf et al., 2020) with the XLM-RoBERTa base model (Conneau et al., 2020), which has been shown to outperform mBERT on low-resource South Asian language tasks. Training was performed in PyTorch (Paszke et al., 2019) on a single NVIDIA T4 GPU via Google Colab. Hyperparameters (Table M) were selected via grid search on the validation set."

This sentence pattern, repeated for each layer, makes your stack defensible.

---

## Summary

Every technology in your stack is a mainstream, well-justified choice. The defenses above are sufficient to handle examiner questions. Build a **stack-decision document** in your thesis appendix using the table in §19 and short justification paragraphs from this guide.
