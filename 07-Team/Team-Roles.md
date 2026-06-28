---
tags: [meta, team]
source: 01-Project-Overview/SME_Research_Proposal_Enigmatrix.md §11
layer: meta
module: shared
---

# Team — Individual Member Responsibilities

> Four-member team, each owning one module and one individual research question, all feeding the unified Enigmatrix platform.

| Member ID | Name | Module | Individual Research Question | Novel Dataset |
|---|---|---|---|---|
| **215075J** | Mohamed M.R.I (Ifham) | **Module 1 — Awareness Gap** | What is the information lag between gazette publication and SME awareness? | Regulatory change lag timeline dataset |
| **215007F** | Ahamadh M.S.A | **Module 2 — Knowledge Gap** | How accurate is the compliance guidance Sri Lankan SMEs receive? | Compliance Q&A benchmark dataset |
| **215008J** | Ahamed T.I | **Module 3 — Risk Gap** | Which SME characteristics predict compliance failure before it occurs? | SME vulnerability & violation dataset |
| **215019T** | Cader Z.R | **Module 4 — Misinformation Gap** | How does tax misinformation spread through Sri Lankan SME networks? | Annotated misinformation corpus |

## How each module fits

- **Module 1 (Ifham)** anchors the platform — produces the labelled gazette corpus and the lag dataset that downstream modules consume.
- **Module 2 (Ahamadh)** builds the retrieval-augmented Q&A layer over the M1 corpus + a wider regulatory KB.
- **Module 3 (Ahamed)** uses M1 alert-engagement signals + sector/size features to predict per-SME risk.
- **Module 4 (Cader)** classifies social-media regulatory claims, cross-referencing M1 truth records.

The four datasets and four models share one identity model, one taxonomy, and one survey engine — see [Unified-Platform](../01-Project-Overview/Unified-Platform.md).

## See also

- [Project-Overview](../01-Project-Overview/Project-Overview.md)
- [Research-Question](../01-Project-Overview/Research-Question.md) — RQs per module
- [Timeline](../06-Timeline/00_Timeline_Overview.md) — six-phase schedule
- [Findings-Log/FEATURES](../08-Findings-Log/FEATURES.md) — live tracker of who delivered what
