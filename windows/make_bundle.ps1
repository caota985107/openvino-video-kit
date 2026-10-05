<#
    make_bundle.ps1 — 打包「USB 離線包」到 dist\openvino-kit\
    內容: python(可攜) + pylibs(預抓 Windows 套件) + models + ffmpeg
          + scripts / windows / notebooks / tools / prompts / configs / docs + 文件
    前提: 先跑過 setup_home.ps1（有 .venv、models、ffmpeg）

    用法:
      powershell -ExecutionPolicy Bypass -File windows\make_bundle.ps1
      # 跳過 pylibs（包會變小，但公司端還需要套件才能跑）:
      #   ... -SkipPylibs
#>
param(
    [string]$Root = "",
    [switch]$SkipPylibs
)
$ErrorActionPreference = "Stop"
if (-not $Root) { $Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path }
Set-Location $Root

$dist = Join-Path $Root "dist\openvino-kit"
New-Item -ItemType Directory -Force $dist | Out-Null
Write-Host "目標: $dist"

Write-Host "`n=== [1/7] 專案檔案 ==="
foreach ($d in @("scripts", "windows", "prompts", "notebooks", "tools", "configs", "docs")) {
    if (Test-Path (Join-Path $Root $d)) {
        robocopy (Join-Path $Root $d) (Join-Path $dist $d) /E /NFL /NDL /NJH /NJS | Out-Null
    }
}
foreach ($f in @("README.md", "requirements.txt", "requirements-offline.txt",
                 "requirements-svd.txt", "LICENSE", "THIRD_PARTY.md")) {
    if (Test-Path (Join-Path $Root $f)) { Copy-Item (Join-Path $Root $f) $dist -Force }
}

Write-Host "`n=== [2/7] 模型（robocopy，大檔請耐心）==="
if (Test-Path (Join-Path $Root "models")) {
    robocopy (Join-Path $Root "models") (Join-Path $dist "models") /E /NFL /NDL /NJH /NJS | Out-Null
}

Write-Host "`n=== [3/7] 可攜 Python ==="
if (-not (Test-Path (Join-Path $dist "python\python.exe"))) {
    $pyTar = Join-Path $Root "assets\python-win-x86_64.tar.gz"
    if (-not (Test-Path $pyTar)) { throw "缺少 assets\python-win-x86_64.tar.gz（可先跑 tools\bundle_prepare.py 取得，見 README）" }
    New-Item -ItemType Directory -Force (Join-Path $dist "_py_tmp") | Out-Null
    tar -xf $pyTar -C (Join-Path $dist "_py_tmp")
    $inner = Get-ChildItem (Join-Path $dist "_py_tmp") -Directory | Select-Object -First 1
    Move-Item $inner.FullName (Join-Path $dist "python")
    Remove-Item (Join-Path $dist "_py_tmp") -Recurse -Force
}
& (Join-Path $dist "python\python.exe") --version

Write-Host "`n=== [4/7] uv.exe（選配）==="
if (Test-Path (Join-Path $Root "uv.exe")) { Copy-Item (Join-Path $Root "uv.exe") $dist -Force }
elseif (Test-Path (Join-Path $Root "assets\uv.exe")) { Copy-Item (Join-Path $Root "assets\uv.exe") $dist -Force }

Write-Host "`n=== [5/7] ffmpeg ==="
if (Test-Path (Join-Path $Root "ffmpeg")) {
    robocopy (Join-Path $Root "ffmpeg") (Join-Path $dist "ffmpeg") /E /NFL /NDL /NJH /NJS | Out-Null
}

Write-Host "`n=== [6/7] pylibs（公司離線安裝用）==="
if (-not $SkipPylibs) {
    $venvPy = Join-Path $Root ".venv\Scripts\python.exe"
    if (-not (Test-Path $venvPy)) { throw "找不到 .venv，請先跑 setup_home.ps1" }
    if (Test-Path (Join-Path $dist "pylibs")) { Remove-Item (Join-Path $dist "pylibs") -Recurse -Force }
    & $venvPy -m pip install --target (Join-Path $dist "pylibs") --only-binary=:all: -r (Join-Path $Root "requirements-offline.txt")
}

Write-Host "`n=== [7/7] 安裝腳本 ==="
Copy-Item (Join-Path $Root "windows\install_offline.ps1") $dist -Force
Copy-Item (Join-Path $Root "windows\install_offline.bat") $dist -Force

$size = (Get-ChildItem $dist -Recurse -File | Measure-Object Length -Sum).Sum / 1GB
Write-Host ("`n完成: {0}`n總大小: {1:N1} GB" -f $dist, $size)
Write-Host "→ 把『dist\openvino-kit』整個資料夾複製到 USB"
Write-Host "→ 公司電腦: 放任意位置 → 雙擊 install_offline.bat → 用 windows\run_lecture.ps1 產影片"
