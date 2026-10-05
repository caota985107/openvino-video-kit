@echo off
REM 05_build_video.bat — slides\NN.png + audio\NN.wav -> final.mp4 (Windows)
REM 需要: ffmpeg 在 PATH 中
REM 用法: scripts\05_build_video.bat slides audio final.mp4
setlocal enabledelayedexpansion

set "SLIDES=%~1"
if "%SLIDES%"=="" set "SLIDES=slides"
set "AUDIO=%~2"
if "%AUDIO%"=="" set "AUDIO=audio"
set "OUT=%~3"
if "%OUT%"=="" set "OUT=final.mp4"

set "TMP=%CD%\_buildvideo_tmp"
mkdir "%TMP%" 2>nul
if exist "%TMP%\list.txt" del "%TMP%\list.txt"

for %%F in ("%AUDIO%\*.wav") do (
  set "N=%%~nF"
  if exist "%SLIDES%\!N!.png" (
    ffmpeg -y -loglevel error -loop 1 -i "%SLIDES%\!N!.png" -i "%%F" ^
      -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" ^
      -c:v libx264 -tune stillimage -pix_fmt yuv420p -r 30 ^
      -c:a aac -b:a 192k -ar 44100 -shortest "%TMP%\seg_!N!.mp4"
    echo file 'seg_!N!.mp4'>> "%TMP%\list.txt"
    echo [!N!] ok
  ) else (
    echo skip !N!: missing %SLIDES%\!N!.png
  )
)

ffmpeg -y -loglevel error -f concat -safe 0 -i "%TMP%\list.txt" -c copy "%OUT%"
del "%TMP%\seg_*.mp4" 2>nul
del "%TMP%\list.txt" 2>nul
rmdir "%TMP%" 2>nul
echo OK -^> %OUT%
