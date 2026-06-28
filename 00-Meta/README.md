---
tags: [meta, vault-overview]
source: enigmatrix-docs/README.md
layer: meta
module: shared
---

# Enigmatrix Vault — README

This Obsidian vault is the research-side workspace for the **Enigmatrix SME Regulatory Intelligence Platform** — a four-module system that ingests Sri Lankan Official Gazette publications, classifies them into SME-relevant categories, measures the information lag between publication and SME awareness, and delivers structured alerts to registered SMEs.

The vault mirrors the canonical engineering documentation at `c:\Reasearch\xyz\enigmatrix-docs\` (which builds the MkDocs site). This is the personal, browsable, Obsidian-native copy.

## Start here

- [MOC-Root](MOC-Root.md) — top-level map of the vault
- [Research_Master_Index](Research_Master_Index.md) — academic / research documents
- [SETUP_Master_Index](SETUP_Master_Index.md) — onboarding & developer guides
- [BUILD_Master_Index](BUILD_Master_Index.md) — engineering build plan
- [Tag-Index](Tag-Index.md) — tag vocabulary used in front-matter

## Modules

| # | Module | Folder |
|---|---|---|
| 1 | Regulatory Awareness Gap (Module 1) | [1 Module-1-Awareness-Gap](../02-Research-Modules/1%20Module-1-Awareness-Gap/00_INDEX.md) |
| 2 | Knowledge Hub (Module 2) | [2 Module-2-Knowledge-Hub](../02-Research-Modules/2%20Module-2-Knowledge-Hub/00_README_Master_Index.md) |
| 3 | Risk Scoring (Module 3) | [3 Module-3-Risk](../02-Research-Modules/3%20Module-3-Risk/00_INDEX.md) |
| 4 | Misinformation Classification (Module 4) | [4 Module-4-Misinformation](../02-Research-Modules/4%20Module-4-Misinformation/00_INDEX.md) |

## Stack reference

| Domain | Vault location | Purpose |
|---|---|---|
| Backend | [04-Technology-Stack/backend/](../04-Technology-Stack/backend/) | FastAPI + SQLAlchemy + Alembic |
| Frontend | [04-Technology-Stack/frontend/](../04-Technology-Stack/frontend/) | Next.js 14 App Router + Tailwind |
| Infra | [04-Technology-Stack/infra/](../04-Technology-Stack/infra/) | Docker Compose + CI/CD + observability |
| ML | [04-Technology-Stack/ml/](../04-Technology-Stack/ml/) | XLM-R, XGBoost, ChromaDB RAG |
| Shared | [04-Technology-Stack/shared/](../04-Technology-Stack/shared/) | Architecture, testing, next-steps |

## Working log

- [Findings Index](../08-Findings-Log/00_Findings_Index.md) — research findings, sessions, change log, feature tracker
- [Timeline](../06-Timeline/00_Timeline_Overview.md) — phase plan + Module 1 roadmap
- [Prompts Library](../09-Prompts/00_Prompts_Index.md) — Claude & Perplexity prompt templates
