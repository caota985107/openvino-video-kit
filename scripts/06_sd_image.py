#!/usr/bin/env python3
"""06_sd_image.py — 單張出圖（OpenVINO，CPU）+ 計時

用法:
    python scripts/06_sd_image.py "a serene night market in taiwan, cinematic" out.png --profile low
    python scripts/06_sd_image.py "modern office, morning light" out.png --profile high

--profile low  → configs/models.json 的 sd_low （SD-Turbo，512²，1 step，約 2–5 秒）
--profile high → sd_high（SDXL-Lightning，2 steps，約 10–12 秒）
模型先下載: python tools/fetch_models.py --set low --dest models
"""
import argparse
import json
import time
from pathlib import Path

import openvino_genai as ov_genai
from PIL import Image

PROFILE_DEFAULTS = {
    "low": {"steps": 1, "width": 512, "height": 512},
    "high": {"steps": 2, "width": 768, "height": 768},
}


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def resolve_model_dir(profile: str, models_root: Path) -> Path:
    cfg = json.loads((project_root() / "configs" / "models.json").read_text(encoding="utf-8"))
    key = "sd_high" if profile == "high" else "sd_low"
    return (models_root / cfg[key]["dir"]).resolve()


def main():
    ap = argparse.ArgumentParser(description="Stable Diffusion 出圖（OpenVINO / CPU）")
    ap.add_argument("prompt", nargs="?", default="a serene taiwanese night market, cinematic lighting")
    ap.add_argument("out", nargs="?", default="out.png")
    ap.add_argument("--profile", choices=["low", "high"], default="high")
    ap.add_argument("--models-root", default="models")
    ap.add_argument("--steps", type=int, default=None, help="覆寫步數")
    ap.add_argument("--width", type=int, default=None)
    ap.add_argument("--height", type=int, default=None)
    args = ap.parse_args()

    defaults = PROFILE_DEFAULTS[args.profile]
    steps = args.steps or defaults["steps"]
    width = args.width or defaults["width"]
    height = args.height or defaults["height"]

    model_dir = resolve_model_dir(args.profile, Path(args.models_root))
    if not model_dir.exists():
        raise SystemExit(
            f"找不到模型: {model_dir}\n"
            f"先執行: python tools/fetch_models.py --set {args.profile} --dest models"
        )

    print(f"[profile={args.profile}] 載入 {model_dir} ...")
    pipe = ov_genai.Text2ImagePipeline(str(model_dir), "CPU")

    t0 = time.perf_counter()
    try:
        tensor = pipe.generate(args.prompt, num_inference_steps=steps, width=width, height=height)
    except TypeError:
        # 某些模型/版本不支援 width/height 參數
        tensor = pipe.generate(args.prompt, num_inference_steps=steps)
    dt = time.perf_counter() - t0

    image = Image.fromarray(tensor.data[0])
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    image.save(args.out)
    print(f"{dt:.1f}s → {args.out}（{image.size[0]}x{image.size[1]}, {steps} steps, profile={args.profile}）")


if __name__ == "__main__":
    main()
