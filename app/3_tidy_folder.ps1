# Tidy FlightAuditor folder: MOVES (never deletes) old files into _archive.
# Default = dry run (only shows what would move). Real move: powershell -File 3_tidy_folder.ps1 -Go
param([switch]$Go)
$root = $PSScriptRoot
$arch = Join-Path $root "_archive"
$patterns = @(
  "generate_site.py","add_flight_v2.py","count_flights.py","organize_files_by_year.py",
  "diagnose_broken_links_readonly.py","hc_download.py","build_hc_*.py","fix_hc_2016_test.py",
  "regen_hc_2016_index*.py","migration_state.json","broken_links_report*","orphans_report_*",
  "build_hc_*.log","*.log","HANDOFF_PROMPT_MASTER_V3.md"
)
$n = 0
foreach ($p in $patterns) {
  Get-ChildItem -LiteralPath $root -File -Filter $p -ErrorAction SilentlyContinue | ForEach-Object {
    $dest = Join-Path $arch $_.Name
    if (Test-Path -LiteralPath $dest) { Write-Host "SKIP (already in _archive): $($_.Name)"; return }
    if ($Go) {
      New-Item -ItemType Directory -Force -Path $arch | Out-Null
      Move-Item -LiteralPath $_.FullName -Destination $dest
      Write-Host "MOVED: $($_.Name)"
    } else { Write-Host "WOULD MOVE: $($_.Name)" }
    $n++
  }
}
if ($Go) { Write-Host "Done. Moved: $n. Nothing deleted. Folder: $arch" } else { Write-Host "Dry run. Would move: $n. To move for real run with -Go" }
