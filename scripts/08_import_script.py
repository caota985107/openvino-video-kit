#!/usr/bin/env python3
"""08_import_script.py — 外部講稿 → script.json（自備講稿流程）

公司已有講稿管道時：把純文字講稿切成一頁一段 → 直接餵給 03_tts_piper.py。

用法:
    python scripts/08_import_script.py 講稿.txt [slides.json] [script.json]

分頁方式（自動判斷）:
    A. 一行 `---` 當分隔線
    B. 行首標記：`1.` `1、` `(1)` `第1頁` `Page 1` `#1`
    C. 空行分段
段落數必須等於投影片頁數（slides.json 的頁數）；不符時列出每段開頭供檢查（可 --force 硬對齊）。
"""
import argparse
import json
import re
import sys
from pathlib import Path

MARK = re.compile(r"(?m)^\s*(?:第\s*\d+\s*[頁页]|Page\s*\d+|#\d+|\d+\s*[.、)]\s)")


def split_parts(text: str):
    t = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if re.search(r"(?m)^\s*-{3,}\s*$", t):
        parts = re.split(r"(?m)^\s*-{3,}\s*$", t)
        mode = "分隔線(---)"
    else:
        marks = list(MARK.finditer(t))
        if len(marks) >= 2:
            parts = []
            for i, m in enumerate(marks):
                end = marks[i + 1].start() if i + 1 < len(marks) else len(t)
                parts.append(t[m.start():end])
            mode = "行首編號"
        else:
            parts = re.split(r"\n\s*\n+", t)
            mode = "空行分段"
    cleaned = []
    for p in parts:
        p = re.sub(r"(?m)^\s*(?:第\s*\d+\s*[頁页]|Page\s*\d+|#\d+|\d+\s*[.、)]\s*)", "", p.strip())
        p = p.strip()
        if p:
            cleaned.append(p)
    return cleaned, mode


def main():
    ap = argparse.ArgumentParser(description="外部講稿 → script.json")
    ap.add_argument("script_txt", help="純文字講稿檔")
    ap.add_argument("slides", nargs="?", default="work/slides.json")
    ap.add_argument("out", nargs="?", default="script.json")
    ap.add_argument("--force", action="store_true", help="段落數不符時硬對齊（裁切/補空）")
    args = ap.parse_args()

    text = Path(args.script_txt).read_text(encoding="utf-8")
    parts, mode = split_parts(text)
    slides = json.loads(Path(args.slides).read_text(encoding="utf-8"))
    n = len(slides)
    print(f"分頁方式: {mode}｜段落數: {len(parts)}｜投影片頁數: {n}")

    if len(parts) != n:
        print("⚠️ 段落數與頁數不符，各段開頭如下：")
        for i, p in enumerate(parts, 1):
            print(f"  [{i}] {p[:36]}...")
        if not args.force:
            sys.exit("請調整講稿（用 --- 分隔線最好對），或加 --force 硬對齊")
        if len(parts) > n:
            parts = parts[:n]
        else:
            parts = parts + [""] * (n - len(parts))

    results = [{"slide": i + 1, "narration": parts[i]} for i in range(n)]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    md = out.with_suffix(".md")
    lines = []
    for s, r in zip(slides, results):
        lines.append(f"## 第 {r['slide']} 頁：{s.get('title') or ''}\n")
        lines.append((r["narration"] or "") + "\n")
    md.write_text("\n".join(lines), encoding="utf-8")
    print(f"OK → {out} / {md}（可打開 script.md 檢查，再接 03 TTS → 05 合成）")


if __name__ == "__main__":
    main()
