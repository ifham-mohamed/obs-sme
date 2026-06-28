---
tags: [meta, tag-vocabulary]
source: synthesised
layer: meta
module: shared
---

# Tag Index

Front-matter convention used across the vault. Use this tag vocabulary when creating new notes so the Obsidian tag pane stays coherent.

## Front-matter schema

```yaml
---
tags: [<one-or-more from the lists below>]
source: <path in enigmatrix-docs if mirrored, or "synthesised">
layer: <research | build | setup | tracker | meta>
module: <m1 | m2 | m3 | m4 | shared>
---
```

## Tag families

### Module

- `module-1` — Regulatory Awareness Gap
- `module-2` — Knowledge Hub
- `module-3` — Risk Scoring
- `module-4` — Misinformation Classification
- `cross-module` — content spanning two or more modules

### Layer

- `research` — academic content (problem framing, methodology, lit review, findings)
- `build` — engineering build specs (the BUILD_NN files)
- `setup` — developer onboarding & operating guides
- `tracker` — engineering activity log (sessions, changes, features)
- `meta` — indices, MOCs, templates

### Topic

- `data` — data sources, schema, ingestion, preprocessing
- `model` — ML architecture, training, evaluation
- `deployment` — packaging, infra, monitoring
- `annotation` — labelling, taxonomy, IAA
- `nlp` — language handling, OCR, Sinhala/Tamil
- `api` — REST/HTTP interfaces
- `ui` — frontend screens, admin console
- `survey` — SME questionnaires, awareness measurement
- `compliance` — deadlines, regulatory alerts

### Stack

- `backend` · `frontend` · `infra` · `ml` · `shared`

### Status (use sparingly)

- `wip` · `blocked` · `done` · `deferred`

## Examples

```yaml
# Module 1 deep-dive on PDF extraction
tags: [module-1, research, data, nlp]
layer: research
module: m1
```

```yaml
# Backend SETUP doc for auth & roles
tags: [backend, setup, api]
layer: setup
module: shared
```

```yaml
# Findings session entry
tags: [tracker, module-3, model]
layer: tracker
module: m3
```
