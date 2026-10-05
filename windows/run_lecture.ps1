<#
    run_lecture.ps1 — 一鍵產出「投影片 + AI 旁白」影片
    用法（在 kit 根目錄）:
      powershell -ExecutionPolicy Bypass -File windows\run_lecture.ps1 -Pptx C:\path\deck.pptx -Profile high
    產物: work\slides.json / work\script.json / work\audio\NN.wav / work\slides\NN.png / work\final.mp4
#>
param(
    [Parameter(Mandatory = $true)][string]$Pptx,
    [ValidateSet("low", "high")][string]$Profile = "high",
    [string]$ScriptFile = "",     # 自備講稿（.txt）—公司已有講稿管道時用；給了就跳過本地 LLM
    [string]$Root = "",
    [string]$Ffmpeg = ""
)
$ErrorActionPreference = "Stop"
if (-not $Root) { $Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path }
Set-Location $Root
$Pptx = (Resolve-Path $Pptx).Path

$py = Join-Path $Root "python\python.exe"
if (-not (Test-Path $py)) {
    $py = Join-Path $Root ".venv\Scripts\python.exe"
    if (-not (Test-Path $py)) { $py = "python" }   # 開發模式 fallback
}
Write-Host "使用 Python: $py"
New-Item -ItemType Directory -Force "work" | Out-Null

Write-Host "`n=== [1/5] 抽取 PPT 文字 ==="
& $py "scripts\01_extract_ppt.py" $Pptx "work\slides.json"

if ($ScriptFile) {
    Write-Host "`n=== [2/5] 匯入外部講稿（公司管道）==="
    & $py "scripts\08_import_script.py" $ScriptFile "work\slides.json" "work\script.json"
} else {
    Write-Host "`n=== [2/5] 生成講稿（本地 LLM，profile=$Profile）==="
    & $py "scripts\02_generate_script.py" "work\slides.json" "work\script.json" --profile $Profile
}

Write-Host "`n=== [3/5] 旁白語音（Piper）==="
& $py "scripts\03_tts_piper.py" "work\script.json" "work\audio"

Write-Host "`n=== [4/5] 投影片 → PNG ==="
& (Join-Path $PSScriptRoot "slides_to_png.ps1") -Pptx $Pptx -Out "work\slides"

Write-Host "`n=== [5/5] 合成影片（ffmpeg）==="
& (Join-Path $PSScriptRoot "build_video.ps1") -Slides "work\slides" -Audio "work\audio" -Out "work\final.mp4" -Ffmpeg $Ffmpeg

Write-Host "`n完成 → work\final.mp4"
