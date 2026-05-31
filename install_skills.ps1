param(
    [string]$CodexHome = $(if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }),
    [string]$ProjectRoot = "",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SkillsSource = Join-Path $RepoRoot "skills"
$SkillsTarget = Join-Path $CodexHome "skills"
$SkillNames = @("shot-cutting-agent", "shot-text-excel", "scene-video-breakdown")

New-Item -ItemType Directory -Force -Path $SkillsTarget | Out-Null
$skillsTargetFull = [System.IO.Path]::GetFullPath($SkillsTarget)

foreach ($skill in $SkillNames) {
    $src = Join-Path $SkillsSource $skill
    $dst = Join-Path $SkillsTarget $skill
    $dstFull = [System.IO.Path]::GetFullPath($dst)
    if (-not $dstFull.StartsWith($skillsTargetFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to install outside the Codex skills directory: $dstFull"
    }
    if (Test-Path -LiteralPath $dst) {
        if (-not $Force) {
            throw "Skill already exists: $dst. Re-run with -Force to replace it."
        }
        Remove-Item -LiteralPath $dst -Recurse -Force
    }
    Copy-Item -LiteralPath $src -Destination $dst -Recurse
    Write-Host "Installed skill: $dst"
}

if ($ProjectRoot) {
    New-Item -ItemType Directory -Force -Path $ProjectRoot | Out-Null
    foreach ($name in @("shot_cutting_agent.py", "build_shot_text_excel_unified.py", "SHOT_CUTTING_AGENT_MODEL.md")) {
        Copy-Item -LiteralPath (Join-Path $RepoRoot $name) -Destination (Join-Path $ProjectRoot $name) -Force
    }
    Write-Host "Copied optional project scripts to: $ProjectRoot"
}

Write-Host "Done. Restart Codex to pick up the installed skills."
