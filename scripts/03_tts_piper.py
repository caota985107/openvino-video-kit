#!/usr/bin/env python3
"""03_tts_piper.py — script.json → audio/NN.wav（Piper 本地中文 TTS，CPU）

用法:
    python scripts/03_tts_piper.py script.json audio/
    python scripts/03_tts_piper.py script.json audio/ --voice models/piper/zh_CN-huayan-medium.onnx

聲音取得（repo assets 已附；也可自行下載）:
    python -m piper.download_voices zh_CN-huayan-medium --data-dir models/piper
"""
import argparse
import json
import sys
import wave
from pathlib import Path

from piper import PiperVoice

DEFAULT_VOICE = "models/piper/zh_CN-huayan-medium.onnx"
SAMPLE_RATE_DEFAULT = 22050


def synth_to_wav(voice, text: str, out_path: Path, sample_rate: int):
    """相容 piper1-gpl 兩種 API：synthesize_wav（直接寫 wave）或 synthesize（產生器）。"""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if hasattr(voice, "synthesize_wav"):  # 新 API
        with wave.open(str(out_path), "wb") as wav_file:
            voice.synthesize_wav(text, wav_file)
        return

    # 替代 API：synthesize 產生 AudioChunk（audio_float_array, float32, [-1,1]）
    import numpy as np

    chunks = [c.audio_float_array for c in voice.synthesize(text)]
    audio = np.concatenate(chunks) if chunks else np.zeros(1, dtype="float32")
    pcm = (audio.clip(-1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(out_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm.tobytes())


def main():
    ap = argparse.ArgumentParser(description="script.json → audio/NN.wav（Piper TTS）")
    ap.add_argument("script", nargs="?", default="script.json")
    ap.add_argument("outdir", nargs="?", default="audio")
    ap.add_argument("--voice", default=DEFAULT_VOICE, help="Piper onnx 模型路徑")
    args = ap.parse_args()

    items = json.loads(Path(args.script).read_text(encoding="utf-8"))
    out_dir = Path(args.outdir)

    onnx_path = Path(args.voice)
    if not onnx_path.exists():
        sys.exit(
            f"找不到聲音模型 {onnx_path}\n"
            "先執行: python -m piper.download_voices zh_CN-huayan-medium --data-dir models/piper"
        )

    print(f"載入 Piper 聲音 {onnx_path} ...")
    voice = PiperVoice.load(str(onnx_path))

    sample_rate = SAMPLE_RATE_DEFAULT
    cfg = getattr(voice, "config", None)
    if cfg is not None and getattr(cfg, "sample_rate", None):
        sample_rate = int(cfg.sample_rate)

    made = 0
    for item in items:
        n = int(item["slide"])
        text = (item.get("narration") or "").strip()
        if not text:
            print(f"[{n:>3}] 空講稿，跳過")
            continue
        wav_path = out_dir / f"{n:02d}.wav"
        synth_to_wav(voice, text, wav_path, sample_rate)
        print(f"[{n:>3}] → {wav_path}")
        made += 1

    print(f"OK → {out_dir}/（{made} 個檔案，檔名對應 slides/NN.png）")


if __name__ == "__main__":
    main()
