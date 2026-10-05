#!/usr/bin/env python3
"""upload_release_assets.py — 建立 GitHub Release 並上傳 release_assets/ 全部檔案（可續傳）

用法: python3 tools/upload_release_assets.py [--tag kit-v1]
特性: 已存在且大小相符的 asset 會跳過（中斷後重跑即可續傳）；大檔分段顯示進度。
"""
import argparse
import http.client
import json
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT / "release_assets"
TOKEN = (ROOT / ".gh_token").read_text().strip()


def api(method, url, payload=None):
    req = urllib.request.Request(
        url, method=method,
        headers={"Authorization": f"Bearer {TOKEN}", "User-Agent": "kit",
                 "Accept": "application/vnd.github+json"},
        data=json.dumps(payload).encode() if payload else None,
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        body = r.read().decode()
        return json.loads(body) if body.strip() else {}


def upload_file(repo, release_id, fpath: Path):
    size = fpath.stat().st_size
    path = (f"/repos/{repo}/releases/{release_id}/assets?"
            + urllib.parse.urlencode({"name": fpath.name}))
    conn = http.client.HTTPSConnection("uploads.github.com", timeout=7200)
    conn.putrequest("POST", path)
    conn.putheader("Authorization", f"Bearer {TOKEN}")
    conn.putheader("User-Agent", "kit")
    conn.putheader("Content-Type", "application/octet-stream")
    conn.putheader("Content-Length", str(size))
    conn.endheaders()
    sent, t0, last = 0, time.time(), time.time()
    with open(fpath, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            conn.send(b)
            sent += len(b)
            if time.time() - last > 30:
                print(f"    ...{sent/1e6:.0f}/{size/1e6:.0f} MB "
                      f"({sent/1e6/max(time.time()-t0,.1):.2f} MB/s)", flush=True)
                last = time.time()
    r = conn.getresponse()
    body = r.read().decode()
    conn.close()
    if r.status not in (200, 201):
        raise RuntimeError(f"HTTP {r.status}: {body[:300]}")
    return sent, time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="kit-v1")
    ap.add_argument("--repo", default="caota985107/openvino-video-kit")
    args = ap.parse_args()

    rel_api = f"https://api.github.com/repos/{args.repo}/releases"
    try:
        rel = api("GET", f"{rel_api}/tags/{args.tag}")
        print("release 已存在:", rel["html_url"], flush=True)
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        rel = api("POST", rel_api, {
            "tag_name": args.tag,
            "name": "Models & Runtime (GitHub-only delivery)",
            "body": ("給無法使用 USB / HuggingFace 的環境：模型與執行環境由這裡下載。\n"
                     "用法：repo 內 `tools/company_fetch_and_setup.ps1`（或見 docs/COMPANY-DOWNLOAD.md）。\n"
                     "檔案皆有 CHECKSUMS.sha256 可驗證。"),
            "draft": False, "prerelease": False,
        })
        print("release 已建立:", rel["html_url"], flush=True)

    rid = rel["id"]
    existing = {a["name"]: a["size"] for a in api("GET", f"{rel_api}/{rid}/assets?per_page=100")}

    MAX_ASSET = 2 * 1024 * 1024 * 1024 - 65536  # GitHub 單檔 <2GB
    files = [p for p in sorted(ASSETS_DIR.iterdir())
             if p.is_file() and not p.name.startswith("_")
             and p.stat().st_size < MAX_ASSET]
    # 先傳小的（CHECKSUMS / manifest），讓公司端能立刻做連通性測試
    files.sort(key=lambda p: p.stat().st_size)

    for f in files:
        if f.name in existing and existing[f.name] == f.stat().st_size:
            print("skip (已在遠端):", f.name, flush=True)
            continue
        print(f"upload: {f.name} ({f.stat().st_size/1e6:.1f} MB) ...", flush=True)
        try:
            sent, dt = upload_file(args.repo, rid, f)
            print(f"  OK {sent/1e6:.1f} MB in {dt:.0f}s ({sent/1e6/max(dt,.1):.2f} MB/s)", flush=True)
        except Exception as e:
            print("  FAIL:", e, flush=True)
    print("UPLOAD DONE", flush=True)


if __name__ == "__main__":
    main()
