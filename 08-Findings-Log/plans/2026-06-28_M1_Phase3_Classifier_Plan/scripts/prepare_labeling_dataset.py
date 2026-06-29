#!/usr/bin/env python3
"""
M1 Phase 3 — Slice 1: prepare an annotation-ready labeling dataset.

Turns the existing *silver* (LLM/regex) classified gazette rows into:
  1. a deduped, stratified first annotation batch (batch_01.csv),
  2. a Label Studio import file WITH the silver labels as pre-annotations
     (so human annotation becomes *correction*, not labeling-from-scratch),
  3. a before-snapshot of the silver category distribution.

Stdlib only (csv/json/random/argparse) — runs anywhere Python 3.9+ exists.
Deterministic (seeded) so re-runs reproduce the same batch.

Usage:
  python prepare_labeling_dataset.py \
      --csv-dir "C:/sme/03-Data-Sources/m1/raw/csv" \
      --out-dir "C:/sme/03-Data-Sources/m1/raw/labeling" \
      --batch-size 250 --seed 42
"""
from __future__ import annotations
import argparse, csv, glob, json, os, random, re, sys
from collections import Counter, defaultdict

CURATED_GLOBS = ["m1_regulations.csv", "m1_regulations_next50.csv",
                 "m1_regulations_next50_batch*.csv"]
# v2..v6 snapshots are deliberately excluded (noisy cumulative working copies).

KEY_FIELDS = ["gazette_number", "title_en", "summary_en", "principal_act_amended",
              "gazette_published_date", "domain_code", "change_category",
              "raw_pdf_path", "source_url", "raw_text"]
RARE_CAP = 20  # categories with <= this many rows are "rare" → include all of them


def load_curated(csv_dir: str) -> list[dict]:
    rows: list[dict] = []
    seen_files: list[str] = []
    for pat in CURATED_GLOBS:
        for f in sorted(glob.glob(os.path.join(csv_dir, pat))):
            seen_files.append(os.path.basename(f))
            with open(f, encoding="utf-8", errors="ignore", newline="") as fh:
                for r in csv.DictReader(fh):
                    r["__src"] = os.path.basename(f)
                    rows.append(r)
    print(f"  loaded {len(rows)} rows from {len(seen_files)} curated files: {seen_files}")
    return rows


def completeness(r: dict) -> int:
    return sum(1 for k in KEY_FIELDS if (r.get(k) or "").strip())


def dedupe(rows: list[dict]) -> list[dict]:
    best: dict[str, dict] = {}
    for r in rows:
        g = (r.get("gazette_number") or r.get("regulation_short_code") or "").strip()
        if not g:
            continue
        if g not in best or completeness(r) > completeness(best[g]) or (
            completeness(r) == completeness(best[g])
            and len(r.get("raw_text") or "") > len(best[g].get("raw_text") or "")
        ):
            best[g] = r
    return list(best.values())


def quarter(dstr: str) -> str:
    m = re.match(r"\s*(\d{4})-(\d{2})", dstr or "")
    if not m:
        return "unknown"
    y, mo = int(m.group(1)), int(m.group(2))
    return f"{y}-Q{(mo - 1)//3 + 1}"


def cat_of(r: dict) -> str:
    return (r.get("change_category") or "").strip() or "unlabeled"


def stratified_batch(rows: list[dict], size: int, rng: random.Random) -> list[dict]:
    """All rows from rare categories + quarter-diversified fill from common ones."""
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_cat[cat_of(r)].append(r)
    rare = {c: rs for c, rs in by_cat.items() if len(rs) <= RARE_CAP}
    common = {c: rs for c, rs in by_cat.items() if len(rs) > RARE_CAP}

    picked: list[dict] = []
    for c, rs in rare.items():                       # include every rare-class row
        picked.extend(rs)

    remaining = max(0, size - len(picked))
    if remaining and common:
        # round-robin across common categories, quarter-diversified within each
        buckets: dict[str, list[dict]] = {}
        for c, rs in common.items():
            by_q: dict[str, list[dict]] = defaultdict(list)
            for r in rs:
                by_q[quarter(r.get("gazette_published_date", ""))].append(r)
            order: list[dict] = []
            qkeys = sorted(by_q)
            for qk in qkeys:
                rng.shuffle(by_q[qk])
            i = 0
            while any(by_q[qk] for qk in qkeys):       # interleave quarters
                qk = qkeys[i % len(qkeys)]
                if by_q[qk]:
                    order.append(by_q[qk].pop())
                i += 1
            buckets[c] = order
        cats = sorted(buckets)
        i = 0
        while remaining > 0 and any(buckets[c] for c in cats):
            c = cats[i % len(cats)]
            if buckets[c]:
                picked.append(buckets[c].pop(0))
                remaining -= 1
            i += 1
    rng.shuffle(picked)
    return picked


def task_text(r: dict) -> str:
    parts = []
    if (r.get("title_en") or "").strip():
        parts.append("TITLE: " + r["title_en"].strip())
    if (r.get("principal_act_amended") or "").strip():
        parts.append("ACT: " + r["principal_act_amended"].strip())
    if (r.get("summary_en") or "").strip():
        parts.append("SUMMARY: " + r["summary_en"].strip())
    rt = (r.get("raw_text") or "").strip()
    if rt and rt.count("(cid:") < 5:          # skip cid-garbled Sinhala dumps
        parts.append("TEXT: " + rt[:1500])
    return "\n".join(parts) or "(no extracted text — open the PDF at pdf_path)"


def to_label_studio(rows: list[dict]) -> list[dict]:
    tasks = []
    for i, r in enumerate(rows, 1):
        silver_cat = (r.get("change_category") or "").strip()
        silver_sec = (r.get("domain_code") or "").strip()
        preds = []
        result = []
        if silver_cat:
            result.append({"from_name": "category", "to_name": "text",
                           "type": "choices", "value": {"choices": [silver_cat]}})
        if silver_sec:
            result.append({"from_name": "sector", "to_name": "text",
                           "type": "choices", "value": {"choices": [silver_sec]}})
        if result:
            preds.append({"model_version": "silver_v0", "result": result})
        tasks.append({
            "id": i,
            "data": {
                "gazette_number": r.get("gazette_number", ""),
                "pdf_path": r.get("raw_pdf_path", ""),
                "source_url": r.get("source_url", ""),
                "gazette_published_date": r.get("gazette_published_date", ""),
                "silver_category": silver_cat,
                "silver_sector": silver_sec,
                "text": task_text(r),
            },
            "predictions": preds,
        })
    return tasks


def main() -> int:
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    default_csv = os.path.normpath(os.path.join(here, "..", "..", "..", "..",
                                   "03-Data-Sources", "m1", "raw", "csv"))
    ap.add_argument("--csv-dir", default=default_csv)
    ap.add_argument("--out-dir", default=os.path.join(os.path.dirname(default_csv), "labeling"))
    ap.add_argument("--batch-size", type=int, default=250)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    rng = random.Random(a.seed)

    print(f"[1/4] loading curated silver CSVs from: {a.csv_dir}")
    rows = load_curated(a.csv_dir)
    if not rows:
        print("  ERROR: no curated rows found — check --csv-dir", file=sys.stderr)
        return 2
    deduped = dedupe(rows)
    print(f"[2/4] deduped to {len(deduped)} distinct gazettes")

    dist = Counter(cat_of(r) for r in deduped)
    os.makedirs(a.out_dir, exist_ok=True)
    with open(os.path.join(a.out_dir, "category_distribution_before.csv"), "w",
              encoding="utf-8", newline="") as fh:
        w = csv.writer(fh); w.writerow(["change_category", "count"])
        for c, n in dist.most_common():
            w.writerow([c, n])

    batch = stratified_batch(deduped, a.batch_size, rng)
    bdist = Counter(cat_of(r) for r in batch)
    cols = [c for c in (rows[0].keys()) if c != "__src"] + ["__quarter"]
    with open(os.path.join(a.out_dir, "batch_01.csv"), "w",
              encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in batch:
            r = dict(r); r["__quarter"] = quarter(r.get("gazette_published_date", ""))
            w.writerow(r)

    tasks = to_label_studio(batch)
    with open(os.path.join(a.out_dir, "label_studio_import.json"), "w",
              encoding="utf-8") as fh:
        json.dump(tasks, fh, ensure_ascii=False, indent=2)

    print(f"[3/4] full-corpus silver distribution: {dict(dist.most_common())}")
    print(f"[4/4] batch_01 = {len(batch)} tasks; per-category: {dict(bdist.most_common())}")
    print(f"  wrote: {a.out_dir}/batch_01.csv")
    print(f"  wrote: {a.out_dir}/label_studio_import.json ({len(tasks)} tasks, "
          f"{sum(1 for t in tasks if t['predictions'])} with pre-annotations)")
    print(f"  wrote: {a.out_dir}/category_distribution_before.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
