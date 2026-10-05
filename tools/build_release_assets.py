#!/usr/bin/env python3
"""build_release_assets.py — 打包 GitHub Release 用的檔案（模型分卷 / pylibs / ffmpeg / python）

產物在 release_assets/（可重複執行、已完成的會跳過）：
  sd-turbo-openvino.zip(.partNN …)       SDXL-Lightning-2steps-openvino-int8.zip(.partNN …)
  pylibs-win64-cp312.zip                 ffmpeg-release-essentials.zip
  python-win-x86_64.tar.gz               CHECKSUMS.sha256
  assets_manifest.json                   ← 給公司端腳本用（分卷清單 + 雜湊）
"""
import hashlib
import json
import shutil
import subprocess
import time
import zipfile
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
OUT = KIT / "release_assets"
PART = 1900 * 1024 * 1024  # 每卷上限（< 2GB GitHub 限制）
LOG = OUT / "_build.log"


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(s + "\n")


def sha256_of(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(8 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def zip_dir(src: Path, zpath: Path, store: bool):
    if zpath.exists() and zpath.stat().st_size > 0:
        log("skip zip (exists):", zpath.name)
        return
    t0 = time.time()
    log(f"zip {src.name} -> {zpath.name} ({'store' if store else 'deflate'}) ...")
    if shutil.which("zip"):
        subprocess.run(
            ["zip", "-r", "-q", "-0" if store else "-1", str(zpath), src.name],
            cwd=str(src.parent), check=True,
        )
    else:
        mode = zipfile.ZIP_STORED if store else zipfile.ZIP_DEFLATED
        with zipfile.ZipFile(zpath, "w", mode) as z:
            for f in sorted(src.rglob("*")):
                if f.is_file():
                    z.write(f, f.relative_to(src.parent))
    log(f"  done {zpath.name} {zpath.stat().st_size/1e9:.2f} GB in {time.time()-t0:.0f}s")


def split_file(zpath: Path):
    if list(OUT.glob(zpath.name + ".part*")):
        log("skip split (exists):", zpath.name)
        return
    if zpath.stat().st_size <= PART:
        return
    t0 = time.time()
    log("split:", zpath.name)
    if shutil.which("split"):
        subprocess.run(["split", "-b", str(PART), "-d", "-a", "2",
                        str(zpath), str(zpath) + ".part"], check=True)
    else:
        with open(zpath, "rb") as f:
            i = 0
            while True:
                chunk = f.read(PART)
                if not chunk:
                    break
                (Path(str(zpath) + f".part{i:02d}")).write_bytes(chunk)
                i += 1
    log(f"  -> {len(list(OUT.glob(zpath.name + '.part*')))} parts in {time.time()-t0:.0f}s")


def main():
    OUT.mkdir(exist_ok=True)
    log("=" * 60)
    log("build_release_assets", time.strftime("%Y-%m-%d %H:%M:%S"))

    targets = [
        (KIT / "bundle" / "models" / "sd-turbo-openvino", "sd-turbo-openvino.zip", True),
        (KIT / "bundle" / "models" / "SDXL-Lightning-2steps-openvino-int8",
         "SDXL-Lightning-2steps-openvino-int8.zip", True),
        (KIT / "bundle" / "pylibs", "pylibs-win64-cp312.zip", False),
    ]
    for src, zname, store in targets:
        if not src.exists():
            log("MISSING:", src)
            continue
        z = OUT / zname
        zip_dir(src, z, store)
        if z.exists():
            split_file(z)

    for src, name in [
        (KIT / "assets" / "ffmpeg-release-essentials.zip", "ffmpeg-release-essentials.zip"),
        (KIT / "assets" / "python-win-x86_64.tar.gz", "python-win-x86_64.tar.gz"),
    ]:
        dst = OUT / name
        if src.exists() and not dst.exists():
            log("copy", name)
            shutil.copy2(src, dst)

    # checksums + manifest
    log("checksums ...")
    files = sorted(p for p in OUT.iterdir() if p.is_file() and not p.name.startswith("_"))
    lines = []
    for p in files:
        lines.append(f"{sha256_of(p)}  {p.name}")
    (OUT / "CHECKSUMS.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {"tag": "kit-v1",
                "base_url": "https://github.com/caota985107/openvino-video-kit/releases/download/kit-v1",
                "models": [], "extras": []}
    for name, mdir in [("sd-turbo-openvino", "sd-turbo-openvino"),
                       ("SDXL-Lightning-2steps-openvino-int8", "SDXL-Lightning-2steps-openvino-int8")]:
        parts = sorted(p.name for p in OUT.glob(name + ".zip.part*"))
        zp = OUT / (name + ".zip")
        manifest["models"].append({
            "name": name, "dir": mdir,
            "parts": parts,
            "zip_sha256": sha256_of(zp) if zp.exists() else None,
            "zip_size": zp.stat().st_size if zp.exists() else None,
        })
    for e in ["pylibs-win64-cp312.zip", "ffmpeg-release-essentials.zip", "python-win-x86_64.tar.gz"]:
        p = OUT / e
        if p.exists():
            manifest["extras"].append({"name": e, "sha256": sha256_of(p), "size": p.stat().st_size})
    (OUT / "assets_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    log("ALL DONE", time.strftime("%Y-%m-%d %H:%M:%S"))


if __name__ == "__main__":
    main()
