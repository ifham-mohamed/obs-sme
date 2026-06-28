# Technology Selection & Justification Guide
## Enigmatrix | SME Regulatory Intelligence Platform | University of Moratuwa 2026

---

## Why Every Technology Choice Needs Justification in Research

In a research paper, every technology choice must answer four questions:
1. **What** does it do?
2. **Why** is it better than the alternatives for THIS specific problem?
3. **What are its limitations** in this context?
4. **Where is it used** in your system (which module, which step)?

---

## Core Technologies — Full Justification

### Python
| Attribute | Detail |
|---|---|
| **What it is** | General-purpose programming language dominant in data science |
| **Why use it** | Largest ML/AI ecosystem; HuggingFace, scikit-learn, Pandas all Python-native |
| **Benefits** | Rapid prototyping, extensive libraries, readable syntax |
| **Limitations** | Slower than C++ for raw compute; GIL limits true multi-threading |
| **Used in** | All modules — data processing, model training, API backend |
| **Research citation** | Standard in field; cite HuggingFace, scikit-learn papers |

---

### TensorFlow / Keras
| Attribute | Detail |
|---|---|
| **What it is** | Google's deep learning framework with Keras high-level API |
| **Why use it** | Production-ready, TFLite for mobile deployment, TFX for pipelines |
| **Benefits** | Strong deployment ecosystem, SavedModel format, TensorBoard |
| **Limitations** | More verbose than PyTorch; harder to debug dynamic computation |
| **Used in** | Module 3 if LSTM temporal model is implemented |
| **vs PyTorch** | TensorFlow better for production; PyTorch better for research experimentation |

---

### PyTorch
| Attribute | Detail |
|---|---|
| **What it is** | Facebook/Meta's dynamic computation graph deep learning framework |
| **Why use it** | HuggingFace Transformers default framework; easier custom model development |
| **Benefits** | Pythonic API, dynamic graphs, easier debugging, dominant in NLP research |
| **Limitations** | Deployment pipeline less mature than TensorFlow |
| **Used in** | Modules 1, 2, 4 via HuggingFace Transformers (XLM-R fine-tuning) |
| **Research citation** | Paszke et al. (2019) "PyTorch: An Imperative Style, High-Performance Deep Learning Library" |

---

### HuggingFace Transformers
| Attribute | Detail |
|---|---|
| **What it is** | Library providing pretrained transformer models and fine-tuning APIs |
| **Why use it** | XLM-R, mBERT available out-of-the-box; unified training API |
| **Benefits** | 200,000+ pretrained models; unified Trainer API; multilingual support |
| **Limitations** | Large model sizes; requires GPU for efficient fine-tuning |
| **Used in** | Modules 1, 2, 4 for XLM-R fine-tuning |
| **Research citation** | Wolf et al. (2020) "Transformers: State-of-the-Art Natural Language Processing" |

---

### XLM-RoBERTa (XLM-R)
| Attribute | Detail |
|---|---|
| **What it is** | Multilingual transformer pretrained on 100 languages including Sinhala |
| **Why use it** | Sri Lankan context requires Sinhala + Tamil + English support in one model |
| **Benefits** | Cross-lingual transfer learning; no need for separate Sinhala model |
| **Limitations** | 1.1GB model size; slower inference than distilled models |
| **vs mBERT** | XLM-R consistently outperforms mBERT on low-resource languages |
| **Research citation** | Conneau et al. (2020) "Unsupervised Cross-lingual Representation Learning at Scale" |

---

### FastAPI
| Attribute | Detail |
|---|---|
| **What it is** | Modern async Python web framework for building REST APIs |
| **Why use it** | Auto-generates OpenAPI docs; async support for ML inference; fastest Python framework |
| **Benefits** | Type hints via Pydantic, auto validation, async endpoints for model serving |
| **Limitations** | Newer ecosystem; fewer plugins than Django |
| **vs Django** | FastAPI: lightweight, async, API-first. Django: full-stack, slower, heavier |
| **vs Node.js** | FastAPI: Python-native (same language as ML code). Node.js: requires cross-language calls |
| **Used in** | All modules — REST API layer connecting ML models to frontend |

---

### Node.js
| Attribute | Detail |
|---|---|
| **What it is** | JavaScript runtime for building scalable server-side applications |
| **Why use it** | If team prefers JavaScript, strong async I/O for non-ML services |
| **Benefits** | Same language as Next.js frontend; large NPM ecosystem; strong WebSocket support |
| **Limitations** | Not Python-native — requires API calls to Python ML services |
| **Recommendation** | Use FastAPI for ML services; Node.js only if needed for real-time notification service |

---

### Next.js
| Attribute | Detail |
|---|---|
| **What it is** | React-based full-stack framework for web applications |
| **Why use it** | Server-side rendering, API routes, TypeScript support, excellent for dashboards |
| **Benefits** | SEO-friendly, fast page loads, built-in routing, Vercel deployment |
| **Limitations** | JavaScript/TypeScript — separate language from Python ML backend |
| **Used in** | Frontend for data collection forms, SME dashboards, compliance chatbot UI |
| **vs Django Templates** | Next.js: modern SPA experience. Django templates: simpler but less interactive |

---

### PostgreSQL
| Attribute | Detail |
|---|---|
| **What it is** | Open-source relational database with strong JSON and full-text search support |
| **Why use it** | Structured SME survey data, training status tracking, relational integrity |
| **Benefits** | ACID compliance, JSON columns for flexible data, pg_vector for embeddings |
| **Limitations** | Not designed for vector search at scale (use ChromaDB/FAISS for vectors) |
| **Used in** | All modules — survey storage, training records, module-wise data management |
| **vs MongoDB** | PostgreSQL: relational integrity, better for structured survey data. MongoDB: better for unstructured logs |

---

### LangChain
| Attribute | Detail |
|---|---|
| **What it is** | Framework for building LLM-powered applications with RAG, agents, chains |
| **Why use it** | Module 2 RAG pipeline: connects document chunks → vector store → LLM → answer |
| **Benefits** | Modular chains, built-in FAISS/ChromaDB connectors, prompt templating |
| **Limitations** | Rapid API changes; abstraction can hide errors; debugging is harder |
| **Used in** | Module 2 compliance Q&A, Module 4 claim verification |

---

### FAISS / ChromaDB
| Attribute | Detail |
|---|---|
| **What they are** | Vector similarity search libraries for finding semantically similar text chunks |
| **Why use them** | RAG systems need to retrieve the top-k most relevant document chunks for a query |
| **FAISS** | Facebook AI; fast, in-memory, best for large-scale search |
| **ChromaDB** | Persistent storage, easier to use, better for development |
| **Recommendation** | Use ChromaDB for development/prototyping; migrate to FAISS for production scale |

---

### XGBoost
| Attribute | Detail |
|---|---|
| **What it is** | Gradient boosting framework optimized for tabular data |
| **Why use it** | Module 3 risk prediction uses tabular SME features; XGBoost consistently wins on structured data |
| **Benefits** | Handles missing values, fast training, built-in regularization, SHAP compatible |
| **Limitations** | Not suitable for raw text or image data |
| **Research citation** | Chen & Guestrin (2016) "XGBoost: A Scalable Tree Boosting System" |

---

### SHAP
| Attribute | Detail |
|---|---|
| **What it is** | SHapley Additive exPlanations — model-agnostic explainability library |
| **Why use it** | Required for research: must explain WHICH SME features predict non-compliance |
| **Benefits** | Works with any ML model; provides both global and local explanations |
| **Limitations** | Computationally expensive for large datasets; exact SHAP values require exponential computation |
| **Used in** | Module 3 — feature importance for compliance risk prediction |

---

### scikit-learn
| Attribute | Detail |
|---|---|
| **What it is** | Python library for traditional ML algorithms and preprocessing |
| **Why use it** | Baseline models (Logistic Regression, Random Forest), preprocessing, metrics |
| **Benefits** | Simple API, extensive documentation, fast for small-medium datasets |
| **Limitations** | Not designed for deep learning; limited GPU support |
| **Used in** | All modules — train_test_split, metrics, baseline models, SMOTE (imbalanced-learn) |

---

### Label Studio
| Attribute | Detail |
|---|---|
| **What it is** | Open-source data annotation tool supporting text, images, audio |
| **Why use it** | Module 4 needs human annotation of social media posts as accurate/misleading/false |
| **Benefits** | Free, self-hosted, supports multiple annotators, exports to JSON/CSV |
| **Limitations** | Requires server setup; UI can be slow with large datasets |
| **Used in** | Module 4 misinformation corpus annotation |

---

## Technology Stack Summary by Module

| Module | Data Tools | ML/NLP Tools | Evaluation | Storage |
|---|---|---|---|---|
| M1 — Awareness | PyMuPDF, Scrapy, Google Forms | XLM-R (HuggingFace), scikit-learn | F1, Kruskal-Wallis | PostgreSQL |
| M2 — Knowledge | spaCy, Google Forms | LangChain, FAISS, XLM-R | RAGAS, Cohen's Kappa | ChromaDB + PostgreSQL |
| M3 — Risk | SDV/CTGAN, imbalanced-learn | XGBoost, SHAP, scikit-learn | AUC-ROC, F1 | PostgreSQL |
| M4 — Misinfo | Label Studio, Translate API | XLM-R, RAG, GPT API | Cohen's Kappa, F1 | PostgreSQL + ChromaDB |

**Shared across all modules:** Python, Pandas, NumPy, FastAPI, Next.js, PostgreSQL, Plotly/Seaborn

---
*Generated by Perplexity AI for Enigmatrix Research Group — University of Moratuwa 2026*
