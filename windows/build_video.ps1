<#
    build_video.ps1 — slides\NN.png + audio\NN.wav → final.mp4（1920×1080 H.264/AAC）
    ffmpeg 會優先用 kit 內的 ffmpeg\bin\ffmpeg.exe，找不到才用 PATH 上的 ffmpeg。

    用法: powershell -ExecutionPolicy Bypass -File windows\build_video.ps1 -Slides work\slides -Audio work\audio -Out work\final.mp4
#>
param(
    [string]$Slides = "slides",
    [string]$Audio = "audio",
    [string]$Out = "final.mp4",
    [string]$Ffmpeg = ""
)
$ErrorActionPreference = "Stop"
if (-not $Ffmpeg) {
    $local = Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..")).Path "ffmpeg\bin\ffmpeg.exe"
    $Ffmpeg = if (Test-Path $local) { $local } else { "ffmpeg" }
}
& $Ffmpeg -version | Select-Object -First 1

$tmp = Join-Path ((Get-Location).Path) "_buildvideo_tmp"
New-Item -ItemType Directory -Force $tmp | Out-Null
$list = Join-Path $tmp "list.txt"
if (Test-Path $list) { Remove-Item $list -Force }

$count = 0
Get-ChildItem (Join-Path $Audio "*.wav") | Sort-Object Name | ForEach-Object {
    $n = $_.BaseName
    $png = Join-Path $Slides "$n.png"
    if (Test-Path $png) {
        & $Ffmpeg -y -loglevel error -loop 1 -i $png -i $_.FullName `
            -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" `
            -c:v libx264 -tune stillimage -pix_fmt yuv420p -r 30 `
            -c:a aac -b:a 192k -ar 44100 -shortest (Join-Path $tmp "seg_$n.mp4")
        Add-Content -Path $list -Value "file 'seg_$n.mp4'" -Encoding Ascii
        Write-Host "[$n] ok"
        $count++
    } else {
        Write-Host "skip ${n}: missing $png"
    }
}

if ($count -eq 0) { throw "沒有任何可合成的頁面（檢查 $Slides 與 $Audio 的檔名配對）" }
& $Ffmpeg -y -loglevel error -f concat -safe 0 -i $list -c copy $Out
Write-Host "OK -> $Out（$count 頁）"
