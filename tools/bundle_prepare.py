#!/usr/bin/env python3
"""bundle_prepare.py — 在 Linux（或任何有 python3 的機器）準備「Windows USB 離線包」素材

做四件事（可重複執行，會跳過已完成項目）:
  A. 下載可攜 Python (Windows x64, 3.12) → assets/python-win-x86_64.tar.gz
  B. uv pip install --target bundle/pylibs （抓 Windows wheels；公司離線安裝用）
  C. 下載 uv.exe(Windows) → bundle/uv.exe（選配）
  D. 組裝 bundle/：複製程式碼、解 ffmpeg、放 piper 聲音

執行: python3 tools/bundle_prepare.py
日誌: bundle/_prepare.log（tee 到 stdout）
"""
import json
import re
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
import zipfile
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
BUNDLE = KIT / "bundle"
ASSETS = KIT / "assets"
LOG = BUNDLE / "_prepare.log"
H = {"User-Agent": "Mozilla/5.0 (bundle-prepare)"}


def log(*a):
    msg = " ".join(str(x) for x in a)
    print(msg, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def get(url, timeout=60):
    return urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=timeout).read()


def download(url, dest: Path, attempts=500, chunk=1 << 20):
    """可續傳下載（Range），慢速連線可用；中斷重跑即可。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    for i in range(attempts):
        try:
            pos = dest.stat().st_size if dest.exists() else 0
            req = urllib.request.Request(url, headers=dict(H))
            if pos:
                req.add_header("Range", f"bytes={pos}-")
            r = urllib.request.urlopen(req, timeout=45)
            if pos and r.status == 200:  # server 不支援續傳 → 重來
                pos = 0
                mode = "wb"
            else:
                mode = "ab"
            total = (int(r.headers.get("Content-Length") or 0)) + pos
            with open(dest, mode) as f:
                while True:
                    c = r.read(chunk)
                    if not c:
                        break
                    f.write(c)
                    pos += len(c)
            if total and pos < total:
                log(f"   ...{pos}/{total} bytes — 續傳重試 #{i+1}")
                continue
            return True
        except Exception as e:
            log(f"   download err #{i+1}: {type(e).__name__}: {str(e)[:90]}")
            time.sleep(2)
    return False


def find_python_url():
    try:
        base = "https://registry.npmmirror.com/-/binary/python-build-standalone/"
        items = json.loads(get(base, 30))
        for d in reversed([it for it in items if it.get("type") == "dir"]):
            try:
                sub = json.loads(get(d["url"], 30))
            except Exception:
                continue
            cand = [it["url"] for it in sub
                    if re.search(r"-x86_64-pc-windows-msvc-install_only\.tar\.gz$", it.get("name", ""))
                    and "3.12" in it.get("name", "")]
            if cand:
                return cand[0], "npmmirror"
    except Exception as e:
        log("  npmmirror 查詢失敗:", str(e)[:120])
    return None, None


def step_python():
    log("A. 可攜 Python (win64 3.12)")
    py = ASSETS / "python-win-x86_64.tar.gz"
    if py.exists() and py.stat().st_size > 20_000_000:
        try:
            with tarfile.open(py) as t:
                _ = t.getnames()
            log("   OK（已存在且完整）")
            return True
        except Exception:
            log("   既有檔不完整，重新下載")
            py.rename(py.with_suffix(".tar.gz.bad"))
    url, src = find_python_url()
    if not url:
        log("   找不到下載來源 — 跳過（之後可手動放 assets/python-win-x86_64.tar.gz）")
        return False
    log(f"   來源 {src}: {url}")
    ok = download(url, py)
    if ok:
        try:
            with tarfile.open(py) as t:
                _ = t.getnames()
            log(f"   OK {py.name} {py.stat().st_size/1e6:.1f}MB")
        except Exception as e:
            log("   tar 驗證失敗:", e)
            return False
    return ok


def step_pylibs():
    log("B. pylibs（Windows wheels → bundle/pylibs）")
    marker = BUNDLE / "pylibs" / "_DONE"
    if marker.exists():
        log("   OK（已完成）")
        return True
    req = KIT / "requirements-offline.txt"
    if not req.exists():
        req = KIT / "requirements.txt"
    uv = shutil.which("uv") or str(Path.home() / ".local" / "bin" / "uv")
    prev = BUNDLE / "pylibs"
    if prev.exists():
        shutil.rmtree(prev, ignore_errors=True)
    cmd = [uv, "pip", "install",
           "--target", str(prev),
           "--python-platform", "windows",
           "--python-version", "3.12",
           "--only-binary", ":all:",
           "-r", str(req)]
    log("   " + " ".join(cmd))
    r = subprocess.run(cmd)
    if r.returncode == 0:
        marker.write_text("ok")
        log("   OK")
        return True
    log("   FAIL rc=", r.returncode)
    return False


def step_uv_exe():
    log("C. uv.exe（Windows）")
    dst = BUNDLE / "uv.exe"
    if dst.exists() and dst.stat().st_size > 5_000_000:
        log("   OK（已存在）")
        return True
    try:
        meta = json.loads(get("https://pypi.org/pypi/uv/json", 30))
        ver = meta["info"]["version"]
        win = [u for u in meta["releases"][ver] if u["filename"].endswith("win_amd64.whl")]
        if not win:
            log("   PyPI 無 win wheel")
            return False
        tmp = ASSETS / "uv-win.whl"
        if not download(win[0]["url"], tmp):
            return False
        with zipfile.ZipFile(tmp) as z:
            exes = [n for n in z.namelist() if n.lower().endswith(".exe")]
            if exes:
                dst.write_bytes(z.read(exes[0]))
                log(f"   OK uv.exe {dst.stat().st_size} bytes")
                return True
    except Exception as e:
        log("   FAIL:", str(e)[:150])
    return False


def step_assemble():
    log("D. 組裝 bundle/")
    for d in ["scripts", "windows", "prompts", "notebooks", "tools", "configs", "docs"]:
        s = KIT / d
        if s.exists():
            shutil.copytree(s, BUNDLE / d, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
    for f in ["README.md", "requirements.txt", "requirements-offline.txt",
              "requirements-svd.txt", "LICENSE", "THIRD_PARTY.md"]:
        sf = KIT / f
        if sf.exists():
            shutil.copy2(sf, BUNDLE)
    vdst = BUNDLE / "models" / "piper"
    vdst.mkdir(parents=True, exist_ok=True)
    for f in (ASSETS / "piper").glob("*"):
        shutil.copy2(f, vdst / f.name)
    ff = BUNDLE / "ffmpeg"
    if not (ff / "bin" / "ffmpeg.exe").exists():
        z = ASSETS / "ffmpeg-release-essentials.zip"
        if z.exists():
            tmp = BUNDLE / "_ff_tmp"
            with zipfile.ZipFile(z) as zz:
                zz.extractall(tmp)
            inner = next(p for p in tmp.iterdir() if p.is_dir())
            (ff / "bin").mkdir(parents=True, exist_ok=True)
            for f in (inner / "bin").glob("*"):
                shutil.copy2(f, ff / "bin" / f.name)
            shutil.rmtree(tmp, ignore_errors=True)
            log("   ffmpeg 解壓 OK")
    # 清理殘留 .part
    for p in ASSETS.glob("*.part"):
        p.unlink()
        log("   清掉", p.name)
    log("   OK")
    return True


def main():
    BUNDLE.mkdir(exist_ok=True)
    log("=" * 64)
    log("bundle_prepare start", time.strftime("%Y-%m-%d %H:%M:%S"))
    a = step_python()
    b = step_pylibs()
    step_uv_exe()
    step_assemble()
    log(f"SUMMARY: python={a} pylibs={b}")
    log("ALL STEPS DONE", time.strftime("%Y-%m-%d %H:%M:%S"))


if __name__ == "__main__":
    main()
