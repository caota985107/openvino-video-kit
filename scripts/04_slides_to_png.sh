#!/usr/bin/env bash
# 04_slides_to_png.sh — PPTX → slides/NN.png (1920x1080)
# 需要: LibreOffice (soffice) + poppler (pdftoppm)
# 若公司只有 PowerPoint：改用「檔案→匯出→變更檔案類型→PNG」逐頁匯出，
# 再把檔名改成 01.png, 02.png... 放進 slides/ 即可。
#
# 用法: bash scripts/04_slides_to_png.sh deck.pptx [slides/]
set -euo pipefail

PPTX="${1:-deck.pptx}"
OUT="${2:-slides}"

command -v soffice >/dev/null 2>&1 || { echo "缺少 soffice（LibreOffice）"; exit 1; }
command -v pdftoppm >/dev/null 2>&1 || { echo "缺少 pdftoppm（poppler-utils）"; exit 1; }

mkdir -p "$OUT" "$(dirname "$PPTX")/build"
soffice --headless --convert-to pdf --outdir build "$PPTX"
PDF="build/$(basename "${PPTX%.*}").pdf"
[ -f "$PDF" ] || { echo "PDF 轉檔失敗: $PDF"; exit 1; }

pdftoppm -png -scale-to-x 1920 -scale-to-y 1080 "$PDF" "$OUT/slide"

# slide-01.png → 01.png
cd "$OUT"
for f in slide-*.png; do
  mv -f "$f" "${f#slide-}"
done

echo "OK → $OUT/ (01.png ... 對應 audio/NN.wav)"
