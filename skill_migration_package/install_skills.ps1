param(
    [string]$CodexHome = "$env:USERPROFILE\.codex",
    [string]$ProjectRoot = ""
)

$ErrorActionPreference = "Stop"

$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SkillsSource = Join-Path $PackageRoot "skills"
$ProjectScripts = Join-Path $PackageRoot "project_scripts"
$SkillsTarget = Join-Path $CodexHome "skills"

New-Item -ItemType Directory -Force -Path $SkillsTarget | Out-Null
foreach ($skill in @("shot-cutting-agent", "shot-text-excel", "scene-video-breakdown", "audio-subtitle-transcript")) {
    $src = Join-Path $SkillsSource $skill
    $dst = Join-Path $SkillsTarget $skill
    if (Test-Path -LiteralPath $dst) {
        Remove-Item -LiteralPath $dst -Recurse -Force
    }
    Copy-Item -LiteralPath $src -Destination $dst -Recurse
    Write-Host "Installed skill: $dst"
}

if ($ProjectRoot) {
    New-Item -ItemType Directory -Force -Path $ProjectRoot | Out-Null
    Copy-Item -LiteralPath (Join-Path $ProjectScripts "shot_cutting_agent.py") -Destination (Join-Path $ProjectRoot "shot_cutting_agent.py") -Force
    Copy-Item -LiteralPath (Join-Path $ProjectScripts "build_shot_text_excel_unified.py") -Destination (Join-Path $ProjectRoot "build_shot_text_excel_unified.py") -Force
    Copy-Item -LiteralPath (Join-Path $ProjectScripts "SHOT_CUTTING_AGENT_MODEL.md") -Destination (Join-Path $ProjectRoot "SHOT_CUTTING_AGENT_MODEL.md") -Force
    Write-Host "Project scripts copied to: $ProjectRoot"
}
Write-Host "Done."
