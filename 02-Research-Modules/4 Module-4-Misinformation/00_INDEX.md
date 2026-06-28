---
tags: [meta, module-4, index]
source: synthesised
layer: meta
module: m4
---

# Module 4 — Misinformation Classification (Index)

> 9-class classifier distinguishing authentic regulatory information from 8 misinformation patterns: rumour, false-attribution, outdated-recycled, fabricated-source, partial-truth, sarcasm-misread, premature-leak, scam.

## Contents

| # | File | What it covers |
|---|---|---|
| 01 | [01_Module4_Misinformation_Architecture](01_Module4_Misinformation_Architecture.md) | Research methodology — taxonomy, dataset, model, evaluation, Perplexity verification layer |
| 02 | [02_BUILD_Module4_Misinformation](02_BUILD_Module4_Misinformation.md) | Engineering build plan — classifier service, verification API, reporting UI |
| 03 | [03_Module4_Data_Collection](03_Module4_Data_Collection.md) | Sourcing strategy: social media, news, government counters |
| 04 | [04_Module4_SriLankan_Sources](04_Module4_SriLankan_Sources.md) | Sri Lankan-specific outlets, fact-check organisations, language coverage |
| 05 | [05_Module4_Perplexity_Prompt](05_Module4_Perplexity_Prompt.md) | Perplexity-API verification prompt template (also linked from [09-Prompts](../../09-Prompts/02_Module4_Perplexity_Prompt.md)) |
| 06 | [06_Data_Architecture_M1_M4](06_Data_Architecture_M1_M4.md) | Shared data architecture for Modules 1 + 4 (regulation truth records, claim-to-regulation links) |

## Research questions

- **RQ-M4.1** — Can a 9-class classifier distinguish authentic regulatory information from 8 misinformation patterns with macro F1 ≥ 0.78 on Sri Lankan social-media data?
- **RQ-M4.2** — Does a Perplexity-API verification layer reduce false-positive flagging on legitimate regulatory news?

## Status

🔲 Data sources catalogued; Perplexity verification prompt drafted; classifier not yet trained.

## See also

- [Module 1 — Regulation Truth Records](../1%20Module-1-Awareness-Gap/02_M1_Data_Requirements.md)
- [09-Prompts](../../09-Prompts/00_Prompts_Index.md) — full prompts library
- [Research Master Index](../../00-Meta/Research_Master_Index.md)
