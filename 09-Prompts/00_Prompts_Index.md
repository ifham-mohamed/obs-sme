---
tags: [meta, prompts, index]
source: synthesised
layer: meta
module: shared
---

# 09 — Prompts (Index)

> Library of LLM prompts used in the project: Claude prompts for engineering/research workflows, Perplexity prompts for misinformation verification (Module 4), and saved chat transcripts.

## Contents

| File | What it is |
|---|---|
| [01_Claude_Prompts_Library](01_Claude_Prompts_Library.md) | Reusable Claude prompts: research workflow, code review, doc-writing, annotation guidance |
| [02_Module4_Perplexity_Prompt](02_Module4_Perplexity_Prompt.md) | Perplexity-API verification prompt for Module 4 misinformation classifier |
| [claude-chats/](claude-chats/) | Saved Claude chat transcripts (research conversations, debugging sessions) |

## Conventions

- Each saved prompt has a header explaining: **purpose**, **inputs**, **expected output**, **model + parameters**, **last tested date**.
- Prompts that produce structured output (JSON, table, citations) include a schema example.
- Prompts that have been retired but kept for history are tagged `#retired` in their front-matter.

## See also

- [Module 4 — Misinformation](../02-Research-Modules/4%20Module-4-Misinformation/00_INDEX.md) — primary consumer of Perplexity prompt
- [Findings-Log/SESSIONS](../08-Findings-Log/SESSIONS.md) — chat-driven debug sessions are often referenced here
