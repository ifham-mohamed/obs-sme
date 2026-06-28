# 14_M1_9 — Category × Sector Workflows (cross-cutting reference)

> Companion to [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md) — covers the cross-cutting reference **X9: how the 12 categories + 10 sectors flow through every M1 surface**.
> **Implementation status:** Reference doc — describes existing conventions across the 8 tracking surfaces (A1–A4, S1–S4). The 12 categories + 10 sectors are shipped in the schema + admin form; the badge colour conventions documented here are shipped via `components/ui/`.

## Purpose

The M1 taxonomy has 12 mutually-exclusive **categories** (single-label) + 10 **sectors** (multi-label), defined in [m1/09_M1_Annotation_Guidelines.md §2 + §3](09_M1_Annotation_Guidelines.md). Each appears on dozens of frontend surfaces — admin filters, badges on cards, columns in tables, chips in URL state, accent colours on per-module shells. Without a single reference, naming + colour drifts across surfaces ("Manufacturing" vs "manufacturing" vs "Mfg"; tax-blue vs slate). This doc is the lookup table — what each value is, where it appears, what colour + label it carries.

## Detailed process

### Category convention table

| Code | Label (EN) | Badge variant | Where it appears |
|---|---|---|---|
| `TAX_RATE_CHANGE` | Tax rate change | `<DomainBadge variant="domain-tax">` (slate) | Admin list filter, regulation card, survey context card |
| `LABOUR_LAW` | Labour law | `<DomainBadge variant="domain-labour">` | same |
| `EPF_ETF_CHANGE` | EPF / ETF change | `<DomainBadge variant="domain-epf">` | same |
| `PRODUCT_STANDARD` | Product standard | `<DomainBadge variant="domain-product">` | same |
| `BUSINESS_REGISTRATION` | Business registration | `<DomainBadge variant="domain-business">` | same |
| `IMPORT_EXPORT` | Import / export | `<DomainBadge variant="domain-trade">` | same |
| `FINANCIAL_REGULATION` | Financial regulation | `<DomainBadge variant="domain-finance">` | same |
| `SECTOR_SPECIFIC` | Sector-specific | `<DomainBadge variant="domain-sector">` | same |
| `ENVIRONMENTAL` | Environmental | `<DomainBadge variant="domain-env">` | same |
| `PENALTY_ENFORCEMENT` | Penalty enforcement | `<DomainBadge variant="domain-penalty">` | same |
| `DEADLINE_EXTENSION` | Deadline extension | `<DomainBadge variant="domain-deadline">` | same |
| `NO_SME_IMPACT` | No SME impact | `<DomainBadge variant="domain-none">` (muted grey) | Admin-only — SMEs never see these |

Labels render in EN by default; SI/TA via next-intl message keys `m1.category.{code}`. Trilingual parity is a CI-tested invariant.

### Sector convention table

| Code | Label (EN) | Badge | Affects (sample) |
|---|---|---|---|
| `manufacturing` | Manufacturing | `<SectorBadge>` (uniform colour; sector identity isn't colour-coded, only label) | VAT, EPF, OSH |
| `retail` | Retail | same | VAT, Product standards, Imports |
| `services` | Services | same | VAT, Labour |
| `agriculture` | Agriculture | same | Subsidies, Land |
| `construction` | Construction | same | Labour, OSH |
| `it_bpo` | IT / BPO | same | Data protection, Labour |
| `hospitality` | Hospitality | same | Tourism, Labour |
| `transport` | Transport | same | Customs, Vehicle |
| `healthcare` | Healthcare | same | Pharmaceutical, Labour |
| `finance` | Finance | same | CBSL regulations |

> Categories use **colour** as a primary identity cue (12 distinct hues); sectors use **label only** (10 uniform-coloured chips). The asymmetry is intentional — categories are more numerous than colours-distinguishable, but the design constraint is that an admin filter rail can hold 12 coloured filter chips without becoming a rainbow soup.

### Where these values appear across the 8 surfaces

| Surface | Category usage | Sector usage |
|---|---|---|
| A1 (Pipeline-state) | Filter column on `/admin/regulations` | Filter column on `/admin/regulations` |
| A2 (Review queue) | Category dropdown in the override drawer | Sector multi-select in the override drawer |
| A3 (Verification) | Read-only badge on the detail page | Read-only chip list on the detail page |
| A4 (Lag analytics) | Cross-tab dimension (lag-by-category) | Cross-tab dimension (lag-by-sector) |
| S1 (Discovery) | Filter chip on `/regulations` | Filter chip + applicability badge |
| S2 (Survey) | Survey is partitioned per-regulation (categories are read-only on the context card) | Sector-tailored regulation selection (7 sector regulations + 2 universal) |
| S3 (Compliance tracker) | Status pill on the row + category badge | Sector chips on the row |
| S4 (Deadlines + alerts) | Category badge in the alert-history table | n/a (alerts already filtered to SME's sector at send time) |

The cross-cutting concern: **the same enum value must render identically on every surface**. The `<DomainBadge>` component is the single source of truth — every surface imports it; nobody hand-rolls a coloured pill.

### URL-state convention

When categories or sectors land in URL state, they use lowercase enum codes (NOT labels), comma-separated:

```
/admin/regulations?change_category=TAX_RATE_CHANGE,EPF_ETF_CHANGE
/regulations?sector=manufacturing,retail
```

Multi-value: comma. Negation: leading `!` (e.g. `change_category=!NO_SME_IMPACT`). Date-range and other filters follow the same lowercase + comma + `!` convention.

### Sort orderings

Default sort across surfaces uses `(severity_level DESC, effective_date ASC)` — most-severe-soonest-first. Categories + sectors are alphabetised in their filter dropdowns by code (not label, so the order is stable across locales).

### Accessibility considerations

- Every badge has both colour AND a label — colour is never the sole carrier of information.
- Badge variants use the WCAG AA contrast ratio (4.5:1) on both light + dark themes — verified by the project's existing axe-core CI.
- Trilingual labels are mandatory; CI fails any PR that adds a new category/sector without `m1.{category|sector}.{code}` translations in `messages/{en,si,ta}.json`.

## Technology choices

This is a reference doc; the conventions are shipped, not designed-from-scratch. The choices captured:

| Convention | Locked at | Why |
|---|---|---|
| 12 categories single-label | [m1/09_M1_Annotation_Guidelines.md §2](09_M1_Annotation_Guidelines.md) | Mutually exclusive in the data model — UI mirrors |
| 10 sectors multi-label | Same | Multi-label in the data model — UI mirrors |
| `<DomainBadge>` per-category colour | `frontend/components/ui/domain-badge.tsx` | One component owns the colour map |
| Sector chips uniform colour | `frontend/components/ui/sector-badge.tsx` | Avoids the "rainbow soup" problem |
| Lowercase enum + comma URL state | Existing pattern across `/admin/regulations`, `/admin/questions` | Consistency across admin surfaces |
| Trilingual labels via next-intl | Project-wide convention | EN/SI/TA is the project's scope |

## Worked example

An admin filter on `/admin/regulations`:

```
URL: /admin/regulations?change_category=TAX_RATE_CHANGE,EPF_ETF_CHANGE&sector=manufacturing&page=1

Filter rail (left):
  Category
    [✓] Tax rate change         (slate badge)
    [ ] Labour law
    [✓] EPF / ETF change        (purple badge)
    [ ] Product standard
    ... 8 more
  Sector
    [✓] Manufacturing
    [ ] Retail
    [ ] Services
    ... 7 more

Result table renders 18 rows.
Each row's category column shows the same coloured <DomainBadge> as the filter rail.
Sector column shows multi-chip stack — sectors alphabetised.
```

The SME-side mirror (intended):

```
URL: /regulations?sector=retail&applicable=true

Filter chip bar (top):
  [Sector: Retail ×]  [Applicable to me ×]

Result: 12 cards, each showing:
  <DomainBadge variant="domain-tax">   for a VAT regulation
  <SectorBadge>retail</SectorBadge>   <SectorBadge>services</SectorBadge>
  <ApplicabilityBadge level="100%">applicable</ApplicabilityBadge>
```

## Failure modes & edge cases

- **New category added.** Adding a 13th category requires: schema migration (per [m1/09_M1_Annotation_Guidelines.md §2](09_M1_Annotation_Guidelines.md)) + new `<DomainBadge>` variant (new CSS class + colour) + trilingual labels in `messages/*.json` + CI translation test pass. The convention freezes new categories until the next quarterly review — taxonomy drift is documented as a risk in [m1/01_M1_Research_Problem.md §10](01_M1_Research_Problem.md).
- **Renamed enum.** Renaming an existing enum (e.g. `EPF_ETF_CHANGE` → `EPF_CONTRIBUTION_CHANGE`) breaks every URL ever shared. Mitigation: never rename; deprecate + add new.
- **Locale-missing label.** A new category landed without SI/TA. CI fails the PR — translation must land with the enum.
- **Colour-blind users.** Categories rely on colour; mitigated by always-present labels. Plus the `<DomainBadge>` uses distinguishable hue + saturation pairs.
- **URL state parsing errors.** Unknown enum value in URL (e.g. someone hand-typed `?sector=manufaturing`). Mitigation: filter falls back to "no filter" + toast warns "Unknown filter value; showing all".

## Validation & acceptance criteria

- **Single source of truth for badges.** No surface re-implements category/sector rendering. CI grep: `class.*tax|class.*epf` outside `domain-badge.tsx` → fail.
- **Trilingual parity.** Every category/sector code has en + si + ta translations. CI test: `Object.keys(messages.en.m1.category) === Object.keys(messages.si.m1.category) === Object.keys(messages.ta.m1.category)`.
- **WCAG AA contrast.** All badge variants pass axe-core's contrast check on both themes.
- **URL state round-trip.** A shared URL with filters renders the same view in any session.
- **Sort stability.** Sorting by category renders the same order regardless of locale (sort by code, not label).

## Cross-references

- Parent: [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md)
- Backend taxonomy: [09_M1_Annotation_Guidelines.md §2 + §3](09_M1_Annotation_Guidelines.md)
- Worked examples per category: [09_M1_1_Category_Taxonomy_Examples.md](09_M1_1_Category_Taxonomy_Examples.md)
- Frontend component primitives: [12_UI_Screens_and_Loading.md §4](../frontend/SETUP/12_UI_Screens_and_Loading.md)
- Code: `frontend/components/ui/domain-badge.tsx`, `frontend/components/ui/sector-badge.tsx`, `frontend/components/ui/severity-badge.tsx`, `frontend/components/ui/module-badge.tsx`
- Translation keys: `frontend/messages/{en,si,ta}.json` under `m1.category.*` + `m1.sector.*`
