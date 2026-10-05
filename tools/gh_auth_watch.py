#!/usr/bin/env python3
"""gh_auth_watch.py — 背景輪詢 GitHub Device Flow 授權，一完成就把 token 存到 .gh_token

用途：先執行 `push_to_github.py auth-begin` 取得代碼，再背景執行本檔；
      使用者在 https://github.com/login/device 輸入代碼後，token 會自動落地，
      不需要再手動觸發 auth-finish。
最多輪詢 ~14 分鐘（device code 壽命 15 分鐘）。
"""
import json
import os
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLIENT_ID = "178c6fc778ccc68e1d6a"
PENDING_FILE = ROOT / ".gh_pending.json"
TOKEN_FILE = ROOT / ".gh_token"


def post(url, data):
    req = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(data).encode(),
        headers={"Accept": "application/json", "User-Agent": "openvino-video-kit"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    p = json.loads(PENDING_FILE.read_text())
    interval = max(int(p.get("interval", 5)), 5)
    deadline = time.time() + 850
    print("watching for GitHub authorization...", flush=True)
    while time.time() < deadline:
        try:
            r = post(
                "https://github.com/login/oauth/access_token",
                {
                    "client_id": CLIENT_ID,
                    "device_code": p["device_code"],
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
            )
        except urllib.error.HTTPError as e:
            try:
                r = json.loads(e.read().decode())
            except Exception:
                time.sleep(interval)
                continue
        except Exception:
            time.sleep(interval)
            continue
        if "access_token" in r:
            TOKEN_FILE.write_text(r["access_token"])
            os.chmod(TOKEN_FILE, 0o600)
            print("TOKEN SAVED", flush=True)
            return
        err = r.get("error")
        if err in ("authorization_pending", "slow_down"):
            time.sleep(interval)
            continue
        print("stopped:", r, flush=True)
        return
    print("watch timeout (not authorized within 15 min)", flush=True)


if __name__ == "__main__":
    main()
