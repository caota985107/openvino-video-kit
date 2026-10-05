#!/usr/bin/env python3
"""convert_svd.py — 在家（有網路、RAM ≥16GB 建議）把 Stable Video Diffusion 轉成 OpenVINO IR

來源：改編自 openvinotoolkit/openvino_notebooks 的 stable-video-diffusion notebook
     （Apache-2.0；ov_stable_video_diffusion_helper.py 原封不動 vendored 在 tools/）。

產出（公司離線推理用）:
    models/svd-ov/model/{image_encoder,unet,vae_encoder,vae_decoder}.xml(.bin)
    models/svd-ov/scheduler/、models/svd-ov/feature_extractor/

用法:
    uv run --no-project --with torch --with diffusers --with safetensors --with huggingface_hub \
        --with openvino --with transformers python tools/convert_svd.py --dest models/svd-ov

注意:
- 需要先下載 PyTorch 版 SVD-XT（~9.5GB，腳本會自動抓）+ AnimateLCM LoRA。
- 轉檔是「一組件一組件」進行，中斷重跑會跳過已完成的檔案。
- 這裡不做 NNCF 量化（保持簡單）；fp16 IR 較大，但 13600K 上 4-step/512×320 是可行的。
"""
import argparse
import gc
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default="models/svd-ov", help="輸出資料夾（含 model/scheduler/feature_extractor）")
    args = ap.parse_args()

    dest = Path(args.dest).expanduser().resolve()
    model_dir = dest / "model"
    model_dir.mkdir(parents=True, exist_ok=True)

    # 依賴檢查（torch / diffusers / openvino 等在匯入 helper 時就會用到）
    try:
        import torch  # noqa: F401
        import diffusers  # noqa: F401
        import openvino  # noqa: F401
    except ImportError as e:
        sys.exit(
            f"缺少套件: {e}\n"
            "請先安裝（在家、有網路時）:\n"
            "  pip install torch --index-url https://download.pytorch.org/whl/cpu\n"
            "  pip install diffusers transformers safetensors huggingface_hub openvino\n"
        )

    sys.path.insert(0, str(TOOLS))
    import ov_stable_video_diffusion_helper as helper

    # 覆寫 helper 的模組層級 MODEL_DIR，讓產出落在指定資料夾
    helper.MODEL_DIR = model_dir
    helper.IMAGE_ENCODER_PATH = model_dir / "image_encoder.xml"
    helper.VAE_ENCODER_PATH = model_dir / "vae_encoder.xml"
    helper.VAE_DECODER_PATH = model_dir / "vae_decoder.xml"
    helper.UNET_PATH = model_dir / "unet.xml"

    print(f"轉檔目標: {model_dir}")
    print("（第一次會下載 stabilityai/stable-video-diffusion-img2vid-xt ~9.5GB 與 AnimateLCM 權重）")
    helper.convert_stable_video_diffusion()
    gc.collect()

    ok = all(p.exists() for p in [
        model_dir / "image_encoder.xml",
        model_dir / "unet.xml",
        model_dir / "vae_encoder.xml",
        model_dir / "vae_decoder.xml",
        dest / "scheduler",
        dest / "feature_extractor",
    ])
    if ok:
        total = sum(f.stat().st_size for f in dest.rglob("*") if f.is_file())
        print(f"完成 → {dest}（{total/1e9:.2f} GB）")
        print("把整個 models/svd-ov 資料夾帶去公司即可離線生成影片。")
    else:
        print("部分檔案缺失，請重跑本腳本（已完成的部分會自動跳過）")


if __name__ == "__main__":
    main()
