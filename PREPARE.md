# PREPARE.md — 從你的 PPT 產生「講稿.txt」（給 Claude Code 的工作說明）

> **怎麼用（一句話）**：把「這份 PREPARE.md ＋ 你的簡報.pptx」交給 Claude Code，說：
> 「請照 PREPARE.md 把簡報轉成講稿.txt」。它會完成下面所有步驟。
>
> 適用兩種環境：
> - 已裝好 kit（有 `python\python.exe`）→ 用「步驟 1A」
> - 任何裝了 Python 3 的電腦（不需套件）→ 用「步驟 1B」（兩者輸出相同）

## 一、最終產物（唯一交付檔案）

檔名 **`講稿.txt`**：純文字、UTF-8（不加 BOM），每一頁投影片一段旁白。

### 硬性格式（完成前逐項核對）
1. 段落順序 = 投影片順序，一頁一段。
2. 段與段之間用**獨立一行 `---`** 分隔（開頭/結尾多放也可以；中間不要出現空白段）。
3. **段落數必須等於投影片頁數**（例：10 頁 → 10 段）。
4. 每段是「可直接朗讀的話」：
   - 不要任何前綴/標記：「第 3 頁」「3.」「#3」「Page 3」都不要；不要 Markdown（清單符號、粗體、標題）。
   - 不要註解、不要括號補充說明——要唸出來的只有內文。
5. 每一頁都要有內容；封面、目錄、謝謝頁也各寫 1–2 句。
6. 除分隔線外，內文不要出現連續三個以上的「-」。

### 內容規範（朗讀品質）
- 繁體中文、口語自然，像講者在台上說話；投影片的列點要改寫成完整句子（「效率 +30%」→「效率提升了三成」）。
- **忠於投影片與備忘稿**：可以補連接詞、轉場與一句白話解釋；不要編造數字、事實、承諾。不確定處留 `【待確認：…】` 給人工補。
- 圖片／圖表頁：依標題與備忘稿寫 1–3 句概述，不臆測數據。
- 長度：中文語音約每秒 4–5 個字；一般頁 **80–150 字**（約 20–35 秒），封面/結尾 1–2 句即可。
- 數字盡量用中文（「一千二百」比「1,200」唸得穩）；英文專有名詞可保留，但避免整句英文。
- 投影片備忘稿（notes）若有現成內容，優先以它為底稿改寫。

## 二、Claude Code 執行步驟

### 0. 抽取每頁文字
- **1A（有 kit）**：
  ```
  python\python.exe scripts\01_extract_ppt.py "簡報.pptx" work\slides.json
  ```
  → 讀 `work\slides.json`（title / bullets / notes）。
- **1B（任何 Python 3，不需套件）**：把本文件「三、附錄」的 `extract_pptx_text.py` 存成檔案後執行：
  ```
  python extract_pptx_text.py "簡報.pptx" slides.json
  ```
  → 讀 `slides.json`（lines / notes）。
  （此腳本本 kit 也有：`scripts/extract_pptx_text.py`）

### 1. 逐頁撰寫旁白
依「一、」的硬性格式與內容規範，把每一頁都寫滿。

### 2. 寫出 `講稿.txt`
格式示意（直接照這個長相干）：
```
本頁是封面，主題是＿＿＿。
---
各位好，今天要跟大家介紹三件事……
---
第一件事是……
```
存檔：UTF-8、無 BOM。

### 3. 自我檢查（必做，全部通過才交件）
- 段落數檢查：把下面存成 `check.py` 執行——
  ```python
  import re
  t = open("講稿.txt", encoding="utf-8").read()
  parts = [p.strip() for p in re.split(r"(?m)^\s*-{3,}\s*$", t.strip()) if p.strip()]
  print("段落數:", len(parts))
  for i, p in enumerate(parts, 1):
      print(f"[{i}] {p[:30]}…")
  ```
  段落數必須等於頁數；不符就修到符為止（常見原因：漏寫某頁、多放了分隔線、段落中間有空行被當成新段）。
- 確認檔案第一個字不是 BOM（開頭直接是文字）。
- （有 kit 時）加驗：
  ```
  python\python.exe scripts\08_import_script.py 講稿.txt work\slides.json work\script.json
  ```
  看到「分頁方式: 分隔線(---)｜段落數 N｜投影片頁數 N」且沒有 ⚠️ 就是通過；可打開它產生的 `script.md` 逐頁對照檢查。

### 4. 交件後的產影片指令（給使用者參考）
```
powershell -ExecutionPolicy Bypass -File windows\run_lecture.ps1 -Pptx "簡報.pptx" -ScriptFile "講稿.txt"
```
成品：`work\final.mp4`。
（不想碰 PowerShell 的路線：見 `docs/COMPANY-DOWNLOAD.md` 的「不用 PowerShell 的替代路線」。）

## 三、附錄：extract_pptx_text.py（純標準庫，任何 Python 3 可跑）

```python
#!/usr/bin/env python3
"""extract_pptx_text.py — 用標準庫抽取 PPTX 每頁文字（含備忘稿）

用法: python extract_pptx_text.py 簡報.pptx [slides.json]
不需要安裝任何套件；輸出 [{"slide":N, "lines":[...], "notes":"..."}]
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
```
