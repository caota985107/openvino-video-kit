<#
    setup_home.ps1 — 在家（有網路的 Windows）一鍵準備
    1) 準備 uv（根目錄 uv.exe，或自動下載）
    2) 安裝 Python 3.12 + venv + Python 依賴
    3) 下載模型（low / high / both）
    4) 佈署 piper 聲音、解開 ffmpeg
    完成後 → 跑 make_bundle.ps1 打包成 USB 離線包

    用法:
      powershell -ExecutionPolicy Bypass -File windows\setup_home.ps1 -Profile both
#>
param(
    [ValidateSet("low", "high", "both")][string]$Profile = "both",
    [string]$Root = ""
)
$ErrorActionPreference = "Stop"
if (-not $Root) { $Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path }
Set-Location $Root
Write-Host "專案根目錄: $Root"

Write-Host "`n=== [1/6] uv ==="
$uv = Join-Path $Root "uv.exe"
if (-not (Test-Path $uv)) {
    $uvCmd = Get-Command uv -ErrorAction SilentlyContinue
    if ($uvCmd) {
        $uv = $uvCmd.Source
        Write-Host "使用系統 uv: $uv"
    } else {
        $uvZip = Join-Path $Root "assets\uv-x86_64-pc-windows-msvc.zip"
        if (-not (Test-Path $uvZip)) {
            Write-Host "下載 uv ..."
            Invoke-WebRequest "https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip" -OutFile (Join-Path $Root "uv.zip")
            $uvZip = Join-Path $Root "uv.zip"
        }
        Expand-Archive $uvZip -DestinationPath (Join-Path $Root "_uv_tmp") -Force
        $found = Get-ChildItem (Join-Path $Root "_uv_tmp") -Recurse -Filter uv.exe | Select-Object -First 1
        Copy-Item $found.FullName $uv -Force
        Remove-Item (Join-Path $Root "_uv_tmp") -Recurse -Force
        if (Test-Path (Join-Path $Root "uv.zip")) { Remove-Item (Join-Path $Root "uv.zip") }
    }
}
& $uv --version

Write-Host "`n=== [2/6] Python 3.12 ==="
& $uv python install 3.12

Write-Host "`n=== [3/6] venv + 依賴 ==="
& $uv venv ".venv" --python 3.12
& $uv pip install --python ".venv\Scripts\python.exe" -r requirements.txt
& $uv pip install --python ".venv\Scripts\python.exe" pip
$py = ".venv\Scripts\python.exe"

Write-Host "`n=== [4/6] 模型下載（$Profile，總量約 5–10GB，可中斷重跑）==="
if ($Profile -eq "both") { & $py "tools\fetch_models.py" --set all --dest models }
else { & $py "tools\fetch_models.py" --set $Profile --dest models }

Write-Host "`n=== [5/6] piper 聲音 → models\piper ==="
New-Item -ItemType Directory -Force "models\piper" | Out-Null
Copy-Item "assets\piper\*" "models\piper\" -Force

Write-Host "`n=== [6/6] ffmpeg 解壓 ==="
if (Test-Path "assets\ffmpeg-release-essentials.zip") {
    Expand-Archive "assets\ffmpeg-release-essentials.zip" -DestinationPath "_ff_tmp" -Force
    $ffdir = Get-ChildItem "_ff_tmp" -Directory | Select-Object -First 1
    New-Item -ItemType Directory -Force "ffmpeg" | Out-Null
    Copy-Item (Join-Path $ffdir.FullName "bin") "ffmpeg\bin" -Recurse -Force
    Remove-Item "_ff_tmp" -Recurse -Force
    & "ffmpeg\bin\ffmpeg.exe" -version | Select-Object -First 1
} else {
    Write-Host "警告: 找不到 assets\ffmpeg-release-essentials.zip（稍後 make_bundle 會檢查）"
}

Write-Host "`n完成。下一步: powershell -ExecutionPolicy Bypass -File windows\make_bundle.ps1"
