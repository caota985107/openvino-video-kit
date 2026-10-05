<#
    slides_to_png.ps1 — PPTX → slides\NN.png（1920×1080）
    用 PowerPoint COM 匯出（公司電腦有 Office 就能用，不需額外安裝）。
    沒有 PowerPoint 時改用: LibreOffice 路線（scripts\04_slides_to_png.sh）
    或手動「檔案 → 匯出 → 變更檔案類型 → PNG」。

    用法: powershell -ExecutionPolicy Bypass -File windows\slides_to_png.ps1 -Pptx deck.pptx -Out work\slides
#>
param(
    [Parameter(Mandatory = $true)][string]$Pptx,
    [string]$Out = "slides"
)
$ErrorActionPreference = "Stop"
$Pptx = (Resolve-Path $Pptx).Path
New-Item -ItemType Directory -Force $Out | Out-Null
$OutAbs = (Resolve-Path $Out).Path

try {
    $ppt = New-Object -ComObject PowerPoint.Application
} catch {
    throw "無法啟動 PowerPoint（未安裝或 COM 被封鎖）。改用 LibreOffice 或手動匯出 PNG。"
}
$pres = $null
try {
    $pres = $ppt.Presentations.Open($Pptx, $true, $false, $false)   # ReadOnly, Untitled, WithWindow=false
    $pres.Export($OutAbs, "PNG", 1920, 1080)
} finally {
    if ($pres) { $pres.Close() | Out-Null }
    $ppt.Quit() | Out-Null
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ppt) | Out-Null
}

# 改名: 「投影片1.PNG」→ 01.png（依檔名數字排序）
$files = Get-ChildItem $OutAbs -File | Where-Object { $_.Name -match '\.(png|PNG|jpg|JPG)$' }
$i = 0
foreach ($f in ($files | Sort-Object { [int]([regex]::Match($_.BaseName, '\d+').Value) })) {
    $i++
    Rename-Item $f.FullName -NewName ("{0:D2}.png" -f $i) -Force
}
Write-Host "OK -> $OutAbs（$i 張）"
