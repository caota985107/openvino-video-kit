#!/usr/bin/env python3
"""fetch_models.py — 下載模型包（HuggingFace）

用法（在家、有網路的機器上跑）:
    uv run --no-project --with huggingface_hub python tools/fetch_models.py --set low
    uv run --no-project --with huggingface_hub python tools/fetch_models.py --set high
    uv run --no-project --with huggingface_hub python tools/fetch_models.py --set all
    # 自訂組合: --set llm_high,sd_low
    # 指定位置: --dest D:\\openvino-kit\\models

--set 可選: low | high | all | 逗號分隔的 key（見 configs/models.json）
下載有斷點續傳，中斷後重跑即可。
"""
import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/models.json")
    ap.add_argument("--dest", default="models", help="模型存放資料夾（bundle 內）")
    ap.add_argument("--set", default="all", help="low|high|all|<key1,key2>")
    args = ap.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.exists():
        # 允許從任一 cwd 執行：以本檔位置為準
        cfg_path = Path(__file__).resolve().parent.parent / "configs" / "models.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

    want = args.set.strip().lower()
    if want == "all":
        keys = [k for k, v in cfg.items() if isinstance(v, dict) and "repo" in v]
    elif want in ("low", "high"):
        keys = [k for k, v in cfg.items()
                if isinstance(v, dict) and v.get("tier") == want and "repo" in v]
    else:
        keys = [k.strip() for k in want.split(",") if k.strip()]

    if not keys:
        raise SystemExit(f"沒有符合的模型 key: {args.set}")

    from huggingface_hub import snapshot_download  # 延後 import，錯誤訊息較友善

    dest_root = Path(args.dest).expanduser()
    for k in keys:
        m = cfg[k]
        target = dest_root / m.get("dir", k)
        print(f"== [{k}] {m['repo']}  →  {target}", flush=True)
        snapshot_download(repo_id=m["repo"], local_dir=str(target))
        print(f"   done: {k}", flush=True)

    print("ALL DONE")
    print(f"模型位置: {dest_root.resolve()}")


if __name__ == "__main__":
    main()
