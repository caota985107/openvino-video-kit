#!/usr/bin/env python3
"""extract_pptx_text.py — 用標準庫抽取 PPTX 每頁文字（含備忘稿）

用法: python scripts/extract_pptx_text.py 簡報.pptx [slides.json]
不需要安裝任何套件；輸出 [{"slide":N, "lines":[...], "notes":"..."}]
（與 PREPARE.md 附錄同一支腳本）
"""
import json
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def para_lines(xml_bytes):
    """回傳 XML 中所有 <a:p> 的文字行（已去空白）。"""
    root = ET.fromstring(xml_bytes)
    out = []
    for p in root.iter(A + "p"):
        line = "".join(t.text or "" for t in p.iter(A + "t")).strip()
        if line:
            out.append(line)
    return out


def slide_order(z):
    """依簡報播放順序回傳每頁的 xml 路徑（處理過頁序調換也正確）。"""
    rels = ET.fromstring(z.read("ppt/_rels/presentation.xml.rels"))
    rid2t = {r.get("Id"): r.get("Target") for r in rels}
    order = []
    pres = ET.fromstring(z.read("ppt/presentation.xml"))
    for s in pres.iter(P + "sldId"):
        t = rid2t.get(s.get(R + "id"), "")
        if t:
            order.append("ppt/" + (t[3:] if t.startswith("../") else t))
    return order


def notes_file(z, slide_name):
    """找某頁的備忘稿檔（ppt/slides/slideN.xml → ppt/notesSlides/notesSlideM.xml）。"""
    rp = slide_name.replace("slides/", "slides/_rels/") + ".rels"
    if rp not in z.namelist():
        return None
    rels = ET.fromstring(z.read(rp))
    for r in rels:
        t = r.get("Target") or ""
        if "notesSlide" in t:
            return "ppt/" + (t[3:] if t.startswith("../") else t)
    return None


def main():
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "deck.pptx")
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "slides.json")
    z = zipfile.ZipFile(src)
    slides = []
    for i, name in enumerate(slide_order(z), start=1):
        lines = para_lines(z.read(name)) if name in z.namelist() else []
        notes = ""
        nf = notes_file(z, name)
        if nf and nf in z.namelist():
            notes = "\n".join(para_lines(z.read(nf)))
        slides.append({"slide": i, "lines": lines, "notes": notes})
    out.write_text(json.dumps(slides, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: {len(slides)} 頁 → {out}")


if __name__ == "__main__":
    main()
