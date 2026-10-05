#!/usr/bin/env python3
"""rename_slides.py — 把手動匯出的投影片圖檔改名為 01.png、02.png…（不用 PowerShell 的路線用）

支援輸入檔名如「投影片1.PNG」「Slide1.PNG」「簡報3.png」；依檔名中的數字排序。
用法:
    python scripts/rename_slides.py work\\slides
"""
import re
import sys
from pathlib import Path


def main():
    d = Path(sys.argv[1] if len(sys.argv) > 1 else "slides")
    files = [f for f in d.iterdir()
             if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg")
             and re.search(r"\d+", f.stem)]
    files.sort(key=lambda f: int(re.search(r"\d+", f.stem).group()))
    if not files:
        sys.exit(f"在 {d} 找不到含數字檔名的圖片檔")

    tmp = []
    for i, f in enumerate(files, start=1):
        t = d / f"._tmp_{i:02d}{f.suffix.lower()}"
        f.rename(t)
        tmp.append((t, d / f"{i:02d}.png"))
    for t, target in tmp:
        if target.exists():
            target.unlink()
        t.rename(target)
    print(f"OK: 已改名 {len(tmp)} 張 → {d}/01.png … {len(tmp):02d}.png")


if __name__ == "__main__":
    main()
