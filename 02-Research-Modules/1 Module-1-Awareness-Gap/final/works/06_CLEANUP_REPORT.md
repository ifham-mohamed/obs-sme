# Cleanup Report — Removable / Suspicious Files

**Generated:** 2026-07-15. Nothing has been deleted — review and remove manually.

## In `C:\Reasearch\xyz\` (repo root)

| Item | Size | Verdict |
|---|---|---|
| `readme/` (empty directory, next to `README.md`) | 0 | **Delete** — stray empty dir |
| `venv/` | 13 MB | **Delete** — uv manages envs per-workspace; root venv is redundant (ensure `.gitignore` covers it) |
| `mydata/` (Label Studio: `label_studio.sqlite3`, `media/`, `export/`, `test_data/`) | 1.6 MB | **KEEP but relocate/back up** — this is your live annotation instance data (Phase 3c). Untracked; add to `.gitignore`, and back it up before any cleanup |
| `storage/` | 126 MB | **Keep** — raw gazette PDFs (pipeline input). Consider moving to external storage if repo copies proliferate |
| `graphify-out/cache/`, `graphify-out/converted/` | — | **Regenerable** — safe to delete if space is needed; better: run `graphify update .` since the graph is stale (built at `94ae62d0`, 2026-05-23) |
| `ENIGMATRIX_FULL_CONTEXT_AND_M1_ANALYSIS.md` | 973 lines | **Superseded** — dated 2026-05-22, says Phases 3–5 "not started" (now code-complete). Replace with `01_MASTER_PROJECT_OVERVIEW.md` or archive |
| Line-ending churn: `git status` shows ~240 files "modified" in every submodule with equal insertions/deletions | — | **Not real changes** — CRLF noise. Fix once with `.gitattributes` (`* text=auto eol=lf`) + `git add --renormalize .` |

## In `E:\Obsidian\sme\` (vault)

| Item | Verdict |
|---|---|
| `Untitled/` and `Interim/` folders | **Review & delete** — `Untitled` contains `format/`, `m1/` scraps |
| `graphify-out/` inside the vault | **Delete or refresh** — duplicate of the repo's graph output; stale copy in a content vault |
| `note.md` at vault root | **Review** — likely scratch |
| `08-Findings-Log/plans/2026-06-28_M1_Phase3_Classifier_Plan/` | **Delete** — flagged in Session 62 as pollution (wrong date + colliding F-209–F-214 ids), stubbed but pending manual deletion |
| Stale `STATUS_2026-06-28…` report | **Delete** — same Session-62 flag |
| `03-Data-Sources/m1/raw/labeling/` | **Delete** — stray copy flagged in Session 62 |
| `05-Build-Status/*` headers say "As of 2026-05-20" | **Stale, not removable** — superseded by the 2026-07-15 addendum added this session |

## Duplicate vault problem
`C:\sme` is a divergent old copy of the vault (the frontend knowledge-portal sync historically pointed there). Decide: either retarget the frontend vault path to `E:\Obsidian\sme`, or set up a one-way sync E:→C:. Do **not** hand-edit `C:\sme`.

## Known security items (not files, but flagged)
- Railway build log PAT leak (Session 55) — rotate the token.
- `infra/docker-image-pin.txt` contains placeholder digests — pin real ones before relying on it.
