<#
  Reorganize the Module-1 `final\works\` folder into a consistent, grouped-by-phase
  numbering scheme, and rewrite the [[wikilinks]] inside the docs to match.

  - Files 01–08 (overview docs) are left untouched.
  - The phase analyses + their plans are renumbered 09–22, grouped by phase.
  - The cross-cutting Activity-Log docs become 23–24.
  - Every [[link]] target inside the works/*.md files is updated to the new name.

  SAFE TO RE-RUN: skips any source that's already been renamed. Nothing is deleted.
  Run it from anywhere — it operates on its own folder ($PSScriptRoot).

  Usage (PowerShell):
      cd "E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\final\works"
      # optional dry run first:
      .\_REORGANIZE_works.ps1 -WhatIfLinks
      # then for real:
      .\_REORGANIZE_works.ps1
#>

[CmdletBinding()]
param(
    [switch]$WhatIfLinks  # preview link edits without writing files
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
if (-not $root) { $root = (Get-Location).Path }

# BOM-less UTF-8 writer so we don't prepend a BOM to the markdown on Windows PS 5.1.
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

# old-basename (no .md)  ->  new-basename (no .md)
$map = [ordered]@{
    'PHASE1_FOUNDATION_ANALYSIS'              = '09_PHASE1_FOUNDATION_ANALYSIS'
    'PHASE1_GAP_CLOSURE_PLAN'                 = '10_PHASE1_GAP_CLOSURE_PLAN'
    'PHASE2_INGEST_EXTRACTION_ANALYSIS'       = '11_PHASE2_INGEST_EXTRACTION_ANALYSIS'
    'PHASE2_GAP_CLOSURE_PLAN'                 = '12_PHASE2_GAP_CLOSURE_PLAN'
    'PHASE2_CHUNK_CONTRACT_PLAN'              = '13_PHASE2_CHUNK_CONTRACT_PLAN'
    'PHASE2_METADATA_CONFIDENCE_PLAN'         = '14_PHASE2_METADATA_CONFIDENCE_PLAN'
    'PHASE2_QUALITY_MONITORING_PLAN'          = '15_PHASE2_QUALITY_MONITORING_PLAN'
    'PHASE2_RUNTIME_DEPS_PLAN'                = '16_PHASE2_RUNTIME_DEPS_PLAN'
    'PHASE2_TRILINGUAL_AUTOCHAIN_PLAN'        = '17_PHASE2_TRILINGUAL_AUTOCHAIN_PLAN'
    'PHASE3_ANNOTATION_CLASSIFICATION_ANALYSIS' = '18_PHASE3_ANNOTATION_CLASSIFICATION_ANALYSIS'
    'PHASE3_GAP_CLOSURE_PLAN'                 = '19_PHASE3_GAP_CLOSURE_PLAN'
    'PHASE4_SCHEDULERS_ALERTS_ANALYSIS'       = '20_PHASE4_SCHEDULERS_ALERTS_ANALYSIS'
    'PHASE4_GAP_CLOSURE_PLAN'                 = '21_PHASE4_GAP_CLOSURE_PLAN'
    'PHASE5_RESEARCH_FINDINGS_ANALYSIS'       = '22_PHASE5_RESEARCH_FINDINGS_ANALYSIS'
    '14_ACTIVITY_LOG_ANALYSIS'                = '23_ACTIVITY_LOG_ANALYSIS'
    '15_ACTIVITY_LOG_GAP_CLOSURE_PLAN'        = '24_ACTIVITY_LOG_GAP_CLOSURE_PLAN'
}

# ---- 1. Rewrite [[wikilinks]] in every .md in the folder --------------------
# Matches an old basename only when it is a link target: preceded by '[' or '/'
# and followed by ']', '|', or '#'. This safely handles [[Name]], [[Name|alias]],
# [[Name#heading]], and path-style [[.../works/Name]] while leaving already-
# numbered names (e.g. 09_PHASE1_...) untouched.
Write-Host "== Rewriting wikilinks ==" -ForegroundColor Cyan
Get-ChildItem -Path $root -Filter *.md | ForEach-Object {
    $file = $_.FullName
    $text = Get-Content -LiteralPath $file -Raw
    $orig = $text
    foreach ($old in $map.Keys) {
        $new = $map[$old]
        $pattern = "(?<=[\[/])" + [regex]::Escape($old) + "(?=[\]\|#])"
        $text = [regex]::Replace($text, $pattern, $new)
    }
    if ($text -ne $orig) {
        if ($WhatIfLinks) {
            Write-Host ("  would update links in: " + $_.Name) -ForegroundColor Yellow
        } else {
            [System.IO.File]::WriteAllText($file, $text, $utf8NoBom)
            Write-Host ("  updated links in: " + $_.Name) -ForegroundColor Green
        }
    }
}

if ($WhatIfLinks) {
    Write-Host "`n(dry run — no files renamed, no links written)" -ForegroundColor Yellow
    return
}

# ---- 2. Rename the files ----------------------------------------------------
# All target names are unique and none pre-exist, so a single pass is safe.
Write-Host "`n== Renaming files ==" -ForegroundColor Cyan
foreach ($old in $map.Keys) {
    $src = Join-Path $root ($old + '.md')
    $dstName = $map[$old] + '.md'
    $dst = Join-Path $root $dstName
    if (Test-Path -LiteralPath $dst) {
        Write-Host ("  skip (already exists): " + $dstName) -ForegroundColor DarkGray
        continue
    }
    if (Test-Path -LiteralPath $src) {
        Rename-Item -LiteralPath $src -NewName $dstName
        Write-Host ("  " + $old + ".md  ->  " + $dstName) -ForegroundColor Green
    } else {
        Write-Host ("  skip (source missing): " + $old + ".md") -ForegroundColor DarkGray
    }
}

Write-Host "`nDone. Review with:  Get-ChildItem | Sort-Object Name" -ForegroundColor Cyan
