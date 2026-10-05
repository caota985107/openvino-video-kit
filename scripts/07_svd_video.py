#!/usr/bin/env python3
"""07_svd_video.py — 圖片 → 短片（Stable Video Diffusion + OpenVINO，CPU 可跑）

來源：改編自 openvinotoolkit/openvino_notebooks（Apache-2.0）。
模型：先在家跑 tools/convert_svd.py 產生 IR（models/svd-ov/），公司離線只需推理。

用法:
    python scripts/07_svd_video.py input.png out.mp4 --profile low
    python scripts/07_svd_video.py input.png out.mp4 --profile high --fps 7

--profile low : 14 幀（約 2 秒 @7fps）、4 step → 較快
--profile high: 25 幀（約 3.5 秒 @7fps）、6 step → 較好

備註:
- 輸入圖會先縮到 512×320（CPU 友善；想更清晰可改 --width/--height，時間會等比增加）
- 只輸出 mp4（用 kit 內 ffmpeg 編碼，不需要額外套件）
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import openvino as ov
import torch

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from lcm_scheduler import AnimateLCMSVDStochasticIterativeScheduler  # noqa: E402
from ov_stable_video_diffusion_helper import OVStableVideoDiffusionPipeline  # noqa: E402
from transformers import CLIPImageProcessor  # noqa: E402
from diffusers.utils import load_image  # noqa: E402

PRESETS = {
    "low": {"num_frames": 14, "num_inference_steps": 4, "decode_chunk_size": 7},
    "high": {"num_frames": 25, "num_inference_steps": 6, "decode_chunk_size": 8},
}


def find_ffmpeg() -> str:
    env = os.environ.get("FFMPEG")
    if env and Path(env).exists():
        return env
    for cand in (ROOT / "ffmpeg" / "bin" / "ffmpeg.exe", ROOT / "ffmpeg" / "bin" / "ffmpeg"):
        if cand.exists():
            return str(cand)
    found = shutil.which("ffmpeg")
    if found:
        return found
    raise SystemExit("找不到 ffmpeg（設定環境變數 FFMPEG 或放到 ffmpeg/bin/）")


def save_mp4(frames, out_path: Path, fps: int):
    tmp = Path(tempfile.mkdtemp(prefix="svd_frames_"))
    try:
        for i, frame in enumerate(frames):
            frame.save(tmp / f"{i:04d}.png")
        cmd = [
            find_ffmpeg(), "-y", "-loglevel", "error",
            "-framerate", str(fps),
            "-i", str(tmp / "%04d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
            str(out_path),
        ]
        subprocess.run(cmd, check=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description="SVD 圖生影片（OpenVINO / CPU）")
    ap.add_argument("image", help="輸入圖片（建議 16:9）")
    ap.add_argument("out", nargs="?", default="svd_out.mp4")
    ap.add_argument("--profile", choices=["low", "high"], default="low")
    ap.add_argument("--model-dir", default="models/svd-ov", help="convert_svd.py 的輸出目錄")
    ap.add_argument("--device", default="CPU")
    ap.add_argument("--width", type=int, default=512)
    ap.add_argument("--height", type=int, default=320)
    ap.add_argument("--fps", type=int, default=7)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--motion", type=int, default=80, help="motion_bucket_id：越大動作越大")
    args = ap.parse_args()

    model_root = Path(args.model_dir).resolve()
    model_dir = model_root / "model"
    if not (model_dir / "unet.xml").exists():
        raise SystemExit(
            f"找不到 SVD IR: {model_dir}\n先在家執行: python tools/convert_svd.py --dest {args.model_dir}"
        )

    preset = PRESETS[args.profile]
    print(f"載入 SVD IR（{args.profile}: {preset['num_frames']}幀 / {preset['num_inference_steps']} step）...")
    core = ov.Core()
    vae_encoder = core.compile_model(model_dir / "vae_encoder.xml", args.device)
    image_encoder = core.compile_model(model_dir / "image_encoder.xml", args.device)
    unet = core.compile_model(model_dir / "unet.xml", args.device)
    vae_decoder = core.compile_model(model_dir / "vae_decoder.xml", args.device)
    scheduler = AnimateLCMSVDStochasticIterativeScheduler.from_pretrained(model_root / "scheduler")
    feature_extractor = CLIPImageProcessor.from_pretrained(model_root / "feature_extractor")

    pipe = OVStableVideoDiffusionPipeline(
        vae_encoder, image_encoder, unet, vae_decoder, scheduler, feature_extractor
    )

    image = load_image(args.image).resize((args.width, args.height))
    generator = torch.Generator(device="cpu").manual_seed(args.seed)

    t0 = time.perf_counter()
    frames = pipe(
        image,
        width=args.width,
        height=args.height,
        num_frames=preset["num_frames"],
        num_inference_steps=preset["num_inference_steps"],
        decode_chunk_size=preset["decode_chunk_size"],
        motion_bucket_id=args.motion,
        fps=args.fps,
        generator=generator,
        output_type="pil",
    ).frames[0]
    dt = time.perf_counter() - t0

    out_path = Path(args.out)
    save_mp4(frames, out_path, args.fps)
    print(f"{dt/60:.1f} 分鐘 → {out_path}（{len(frames)} 幀 @ {args.fps}fps，profile={args.profile}）")


if __name__ == "__main__":
    main()
