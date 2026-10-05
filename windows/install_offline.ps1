<#
    install_offline.ps1 — 公司電腦（無網路）離線部署
    在 USB 包（openvino-kit）根目錄執行：
      powershell -ExecutionPolicy Bypass -File install_offline.ps1
        （或直接雙擊 install_offline.bat）
    - 把 pylibs\（預先抓好的 Windows 套件）複製進可攜 Python，不需要網路、不需要管理員權限
    - 做 import / OpenVINO device / ffmpeg 驗證
#>
param(
    [string]$Root = $PSScriptRoot
)
$ErrorActionPreference = "Stop"

$py = Join-Path $Root "python\python.exe"
if (-not (Test-Path $py)) { throw "找不到 python\python.exe — 請在完整的 openvino-kit USB 包根目錄執行本腳本" }
$src = Join-Path $Root "pylibs"
if (-not (Test-Path $src)) { throw "找不到 pylibs\（離線套件）— USB 包不完整或未帶到" }

$sp = Join-Path $Root "python\Lib\site-packages"
New-Item -ItemType Directory -Force $sp | Out-Null

Write-Host "=== [1/2] 安裝套件（robocopy pylibs -> python\Lib\site-packages）==="
robocopy $src $sp /E /NFL /NDL /NJH /NJS | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy 失敗 (exit code $LASTEXITCODE)" }

Write-Host "`n=== [2/2] 驗證 ==="
& $py -c "import openvino, openvino_genai, piper, pptx, numpy, PIL; print('imports OK')"
& $py -c "import openvino as ov; print('OpenVINO', ov.__version__); print('devices:', ov.Core().available_devices)"
if (Test-Path (Join-Path $Root "ffmpeg\bin\ffmpeg.exe")) {
    & (Join-Path $Root "ffmpeg\bin\ffmpeg.exe") -version | Select-Object -First 1
}
$svd = Test-Path (Join-Path $Root "models\svd-ov\model\unet.xml")
Write-Host ("SVD 模型: " + $(if ($svd) { "OK" } else { "未佈署（選配；在家跑 tools\convert_svd.py 後帶過來）" }))

Write-Host "`n完成。產影片:"
Write-Host "  powershell -ExecutionPolicy Bypass -File windows\run_lecture.ps1 -Pptx C:\path\deck.pptx -Profile high"
