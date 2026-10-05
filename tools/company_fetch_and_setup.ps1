<#
    company_fetch_and_setup.ps1 — 公司端（無 USB、無 HuggingFace，只能走 GitHub）
    在「repo 內容」根目錄執行：
      powershell -ExecutionPolicy Bypass -File tools\company_fetch_and_setup.ps1
    流程：從 GitHub Releases 下載 模型分卷 / pylibs / ffmpeg / python
          → 合併分卷 → 就地組出可直接使用的資料夾結構
    之後即可：windows\run_lecture.ps1 -Pptx 簡報.pptx -ScriptFile 講稿.txt
    支援中斷重跑（已下載檔案會跳過；SHA256 不符會重抓）。

    參數：
      -SkipModels   只裝環境（python/pylibs/ffmpeg），不抓模型
      -SkipExtras   只抓模型，不裝環境
#>
param(
    [string]$Root = "",
    [switch]$SkipModels,
    [switch]$SkipExtras
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
if (-not $Root) { $Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path }
Set-Location $Root
$REL = "https://github.com/caota985107/openvino-video-kit/releases/download/kit-v1"
$DL = Join-Path $Root "_dl"
New-Item -ItemType Directory -Force $DL | Out-Null

Write-Host "=== 連通性測試 ==="
try {
    Invoke-WebRequest -Uri $REL/assets_manifest.json -OutFile (Join-Path $DL "assets_manifest.json") -UseBasicParsing | Out-Null
    Write-Host "GitHub Releases 可連線 OK"
} catch {
    Write-Host "⚠ 無法從 GitHub Releases 下載。請先用瀏覽器測試："
    Write-Host "   $REL/REACHABILITY_TEST.txt"
    Write-Host "   （可下載=網路OK；不行=需要請 IT 放行，或參考 docs/COMPANY-DOWNLOAD.md 的手動路線）"
    throw
}

function Get-ReleaseFile([string]$name) {
    $out = Join-Path $DL $name
    if ((Test-Path $out) -and (Get-Item $out).Length -gt 0) { Write-Host "  skip $name"; return }
    Write-Host "  download $name ..."
    $url = "$REL/$([uri]::EscapeDataString($name))"
    for ($i = 1; $i -le 3; $i++) {
        try {
            try { Start-BitsTransfer -Source $url -Destination $out -ErrorAction Stop }
            catch { (New-Object System.Net.WebClient).DownloadFile($url, $out) }
            return
        } catch {
            Write-Host "   retry $i ($($_.Exception.Message))"
            Start-Sleep -Seconds 3
            if (Test-Path $out) { Remove-Item $out -Force }
        }
    }
    throw "下載失敗: $name"
}

function Join-Parts([string[]]$parts, [string]$outZip) {
    if (Test-Path $outZip) { Remove-Item $outZip -Force }
    $out = [System.IO.File]::Create($outZip)
    try {
        foreach ($p in $parts) {
            $in = [System.IO.File]::OpenRead((Join-Path $DL $p))
            try { $in.CopyTo($out) } finally { $in.Close() }
        }
    } finally { $out.Close() }
}

function Check-SHA([string]$file, [string]$expect) {
    if (-not $expect) { return }
    $h = (Get-FileHash $file -Algorithm SHA256).Hash.ToLower()
    if ($h -ne $expect.ToLower()) { throw "SHA256 不符: $file（重新執行本腳本會自動重抓）" }
    Write-Host "  sha256 OK: $(Split-Path $file -Leaf)"
}

$m = Get-Content (Join-Path $DL "assets_manifest.json") -Raw | ConvertFrom-Json

if (-not $SkipModels) {
    Write-Host "`n=== [1/3] 模型（分卷下載 → 合併 → 解壓，約 10GB）==="
    New-Item -ItemType Directory -Force (Join-Path $Root "models") | Out-Null
    foreach ($model in $m.models) {
        Write-Host "[$($model.name)]"
        $target = Join-Path $Root "models\$($model.dir)"
        if ($model.parts.Count -gt 0) {
            foreach ($p in $model.parts) { Get-ReleaseFile $p }
            $zip = Join-Path $DL "$($model.name).zip"
            if (-not (Test-Path $target)) {
                Write-Host "  合併分卷 ..."
                Join-Parts $model.parts $zip
                Check-SHA $zip $model.zip_sha256
                Write-Host "  解壓 ..."
                Expand-Archive -Path $zip -DestinationPath (Join-Path $Root "models") -Force
            } else {
                Write-Host "  已存在 models\$($model.dir)（跳過）"
            }
        } else {
            Get-ReleaseFile "$($model.name).zip"
            $zip = Join-Path $DL "$($model.name).zip"
            Check-SHA $zip $model.zip_sha256
            if (-not (Test-Path $target)) { Expand-Archive -Path $zip -DestinationPath (Join-Path $Root "models") -Force }
        }
    }
}

if (-not $SkipExtras) {
    Write-Host "`n=== [2/3] 可攜 Python ==="
    $pyT = $m.extras | Where-Object { $_.name -eq "python-win-x86_64.tar.gz" }
    if ($pyT) { Get-ReleaseFile $pyT.name; Check-SHA (Join-Path $DL $pyT.name) $pyT.sha256 }
    if (-not (Test-Path (Join-Path $Root "python\python.exe"))) {
        New-Item -ItemType Directory -Force (Join-Path $Root "_pytmp") | Out-Null
        tar -xf (Join-Path $DL "python-win-x86_64.tar.gz") -C (Join-Path $Root "_pytmp")
        $inner = Get-ChildItem (Join-Path $Root "_pytmp") -Directory | Select-Object -First 1
        Move-Item $inner.FullName (Join-Path $Root "python")
        Remove-Item (Join-Path $Root "_pytmp") -Recurse -Force
    }
    & (Join-Path $Root "python\python.exe") --version

    Write-Host "`n=== [3/3a] pylibs → python\Lib\site-packages ==="
    $pl = $m.extras | Where-Object { $_.name -eq "pylibs-win64-cp312.zip" }
    if ($pl) { Get-ReleaseFile $pl.name; Check-SHA (Join-Path $DL $pl.name) $pl.sha256 }
    $sp = Join-Path $Root "python\Lib\site-packages"
    New-Item -ItemType Directory -Force $sp | Out-Null
    if (-not (Test-Path (Join-Path $sp "openvino"))) {
        $ex = Join-Path $DL "pylibs_x"
        if (Test-Path $ex) { Remove-Item $ex -Recurse -Force }
        Expand-Archive -Path (Join-Path $DL "pylibs-win64-cp312.zip") -DestinationPath $ex -Force
        $srcDir = Join-Path $ex "pylibs"
        if (-not (Test-Path $srcDir)) { $srcDir = (Get-ChildItem $ex -Directory | Select-Object -First 1).FullName }
        robocopy $srcDir $sp /E /NFL /NDL /NJH /NJS | Out-Null
        Remove-Item $ex -Recurse -Force
    } else { Write-Host "  site-packages 已有 openvino（跳過）" }

    Write-Host "`n=== [3/3b] ffmpeg ==="
    $ff = $m.extras | Where-Object { $_.name -eq "ffmpeg-release-essentials.zip" }
    if ($ff) { Get-ReleaseFile $ff.name; Check-SHA (Join-Path $DL $ff.name) $ff.sha256 }
    if (-not (Test-Path (Join-Path $Root "ffmpeg\bin\ffmpeg.exe"))) {
        $ex = Join-Path $DL "ff_x"
        if (Test-Path $ex) { Remove-Item $ex -Recurse -Force }
        Expand-Archive -Path (Join-Path $DL "ffmpeg-release-essentials.zip") -DestinationPath $ex -Force
        $inner = Get-ChildItem $ex -Directory | Select-Object -First 1
        New-Item -ItemType Directory -Force (Join-Path $Root "ffmpeg") | Out-Null
        Copy-Item (Join-Path $inner.FullName "bin") (Join-Path $Root "ffmpeg\bin") -Recurse -Force
        Remove-Item $ex -Recurse -Force
    }
}

Write-Host "`n=== 驗證 ==="
$py = Join-Path $Root "python\python.exe"
& $py -c "import openvino, openvino_genai, piper, pptx, numpy, PIL; print('imports OK')"
& $py -c "import openvino as ov; print('OpenVINO', ov.__version__); print('devices:', ov.Core().available_devices)"
if (Test-Path (Join-Path $Root "ffmpeg\bin\ffmpeg.exe")) { & (Join-Path $Root "ffmpeg\bin\ffmpeg.exe") -version | Select-Object -First 1 }

Write-Host "`n完成！產影片:"
Write-Host "  powershell -ExecutionPolicy Bypass -File windows\run_lecture.ps1 -Pptx C:\簡報.pptx -ScriptFile C:\講稿.txt"
Write-Host "（下載的原始檔在 _dl\，可留著重裝用；要省空間可自行刪除）"
