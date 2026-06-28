---
tags: [meta, timeline, index]
source: synthesised
layer: meta
module: shared
---

# 06 — Timeline (Overview)

> Project timeline at three resolutions: phase plan (research), engineering layers (build), and Module 1 roadmap (delivery).

## Phase plan — six research phases

| Phase  | Window         | Focus                                                           | Output                                               |
| ------ | -------------- | --------------------------------------------------------------- | ---------------------------------------------------- |
| **P1** | Feb 2026       | Problem framing & proposal                                      | Submitted proposal (✅ done)                          |
| **P2** | Mar – Apr 2026 | Data collection (gazette corpus + SME survey instrument design) | 800+ gazettes ingested; survey piloted               |
| **P3** | May – Jun 2026 | Module 1 model training + evaluation                            | XLM-R + LoRA at macro F1 ≥ 0.92 on held-out test set |
| **P4** | Jul 2026       | Deployment + lag-measurement instrumentation                    | Pipeline live; `m1_propagation_events` populating    |
| **P5** | Jul – Aug 2026 | Lag dataset analysis + SME awareness survey at scale            | ≥ 100 SME respondents; published lag distribution    |
| **P6** | Aug 2026       | Thesis write-up + modules 2/3/4 partial integration             | Submitted thesis                                     |

## Engineering layers

The engineering side is sequenced by [01_Engineering_Layers_Timeline](01_Engineering_Layers_Timeline.md) (`BUILD_00_INDEX` from enigmatrix-docs). The 17 BUILD documents are grouped into three layers:

- **Layer 1 — Foundation** (BUILD_01–04): project init, folder structure, backend API, database & storage
- **Layer 2 — Platform** (BUILD_05–08): frontend, auth, M1 awareness, M2 knowledge
- **Layer 3 — Intelligence** (BUILD_09–17): M3 risk, M4 misinformation, ML training, ingestion/scheduling, admin, deployment, observability, progress tracker, prompts library

## Module 1 roadmap

See [02_Module1_Roadmap](02_Module1_Roadmap.md) — five-phase delivery roadmap for the Module 1 deep-dive (data → model → deploy → measure → report).

## Progress tracking

- [03_Progress_Tracker_Template](03_Progress_Tracker_Template.md) — template for weekly progress notes
- Live tracker entries: [08-Findings-Log/FEATURES](../08-Findings-Log/FEATURES.md) · [SESSIONS](../08-Findings-Log/SESSIONS.md) · [CHANGES](../08-Findings-Log/CHANGES.md)

## See also

- [Project-Overview](../01-Project-Overview/Project-Overview.md)
- [Team-Roles](../07-Team/Team-Roles.md)
