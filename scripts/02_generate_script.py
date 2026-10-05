#!/usr/bin/env python3
"""02_generate_script.py — slides.json → script.json（本地 LLM，OpenVINO，CPU）

用法:
    python scripts/02_generate_script.py slides.json script.json --profile high
    python scripts/02_generate_script.py slides.json script.json --profile low

--profile low  → configs/models.json 的 llm_low （Qwen3-4B，較快）
--profile high → llm_high（Qwen3-8B，品質較好）
模型先下載: python tools/fetch_models.py --set high --dest models
"""
import argparse
import json
import re
import time
from pathlib import Path

import openvino_genai as ov_genai

SYSTEM = (
    "你是資深企業講師與簡報教練。任務：把投影片內容改寫成「影片旁白講稿」。\n"
    "規則：\n"
    "1. 使用台灣繁體中文，口語但專業，適合影片旁白。\n"
    "2. 每頁講稿 60–120 字（約 20–40 秒）；標題頁與結尾頁 40–80 字。\n"
    "3. 只根據提供的標題、內容、備忘稿撰寫；不得新增原文沒有的數據、名稱或事實。\n"
    "4. 數字與專有名詞照抄原文。\n"
    "5. 第一頁之外不要罐頭開場；不要 emoji、不要 markdown 符號。\n"
    '6. 只輸出 JSON：{"slide": N, "narration": "..."}'
)


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def resolve_model_dir(profile: str, models_root: Path) -> Path:
    cfg = json.loads((project_root() / "configs" / "models.json").read_text(encoding="utf-8"))
    key = "llm_high" if profile == "high" else "llm_low"
    return (models_root / cfg[key]["dir"]).resolve()


def build_prompt(slide: dict, total: int) -> str:
    bullets = "\n".join(f"- {b}" for b in slide.get("bullets", [])) or "（無）"
    notes = slide.get("notes") or "（無）"
    return (
        f"<投影片資料>\n"
        f"第 {slide['slide']} 頁（共 {total} 頁）\n"
        f"標題：{slide.get('title') or '（無）'}\n"
        f"內容：\n{bullets}\n"
        f"講者備忘：{notes}\n"
        f"</投影片資料>\n\n"
        f"請輸出第 {slide['slide']} 頁的旁白講稿（JSON）。/no_think"
    )


def strip_think(text: str) -> str:
    return re.sub(r" thinking.*?<｜end▁of▁thinking｜>", "", text, flags=re.S).strip()


def extract_narration(text: str) -> str:
    """優先抓 JSON 的 narration 欄位；抓不到就把清理後全文當講稿。"""
    text = strip_think(text)
    m = re.search(r"\{.*?\}", text, flags=re.S)
    if m:
        try:
            obj = json.loads(m.group(0))
            narration = str(obj.get("narration", "")).strip()
            if narration:
                return narration
        except json.JSONDecodeError:
            pass
    return text


def main():
    ap = argparse.ArgumentParser(description="slides.json → script.json（本地 LLM / OpenVINO）")
    ap.add_argument("slides", nargs="?", default="slides.json")
    ap.add_argument("out", nargs="?", default="script.json")
    ap.add_argument("--profile", choices=["low", "high"], default="high", help="low=較快 / high=較好")
    ap.add_argument("--models-root", default="models", help="模型根目錄")
    ap.add_argument("--max-tokens", type=int, default=400)
    args = ap.parse_args()

    slides = json.loads(Path(args.slides).read_text(encoding="utf-8"))
    model_dir = resolve_model_dir(args.profile, Path(args.models_root))
    if not model_dir.exists():
        raise SystemExit(
            f"找不到模型: {model_dir}\n"
            f"先執行: python tools/fetch_models.py --set {args.profile} --dest models"
        )

    print(f"[profile={args.profile}] 載入模型 {model_dir}（第一次載入較慢）...")
    pipe = ov_genai.LLMPipeline(str(model_dir), "CPU")

    cfg = ov_genai.GenerationConfig()
    cfg.max_new_tokens = args.max_tokens
    cfg.apply_chat_template = False  # 我們自行套 Qwen chat 格式

    results = []
    for slide in slides:
        prompt = build_prompt(slide, len(slides))
        chat = (
            f"<|im_start|>system\n{SYSTEM}<|im_end|>\n"
            f"<|im_start|>user\n{prompt}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )
        t0 = time.perf_counter()
        raw = str(pipe.generate(chat, cfg))
        narration = extract_narration(raw)
        dt = time.perf_counter() - t0
        print(f"[{slide['slide']:>3}] {dt:5.1f}s  {narration[:40]}...")
        results.append({"slide": slide["slide"], "narration": narration})

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    md = out_path.with_suffix(".md")
    lines = []
    for slide, res in zip(slides, results):
        lines.append(f"## 第 {res['slide']} 頁：{slide.get('title') or ''}\n")
        lines.append(res["narration"] + "\n")
    md.write_text("\n".join(lines), encoding="utf-8")
    print(f"OK → {out_path} / {md}（記得人工審稿）")


if __name__ == "__main__":
    main()
