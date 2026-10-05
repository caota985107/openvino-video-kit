#!/usr/bin/env python3
"""push_to_github.py — 用 GitHub Device Flow 推送到 GitHub（不需要 gh CLI）

流程（依序執行）:
    python tools/push_to_github.py auth-begin    # 印出一次性代碼 → 開 https://github.com/login/device 輸入
    python tools/push_to_github.py auth-finish   # 輪詢授權完成 → 儲存 token（.gh_token，不進版控）
    python tools/push_to_github.py create-repo   # 建立 repo（預設 openvino-video-kit）
    python tools/push_to_github.py push          # git push（token 只用在本次指令，不寫進 remote）

安全說明:
- token 只存在本機 .gh_token（chmod 600；已列入 .gitignore）
- 不需要任何密碼；授權隨時可在 GitHub Settings → Applications 撤銷
"""
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

CLIENT_ID = "178c6fc778ccc68e1d6a"  # GitHub CLI 的公開 client id（device flow 標準做法）
SCOPES = "repo"
ROOT = pathlib.Path(__file__).resolve().parent.parent
TOKEN_FILE = ROOT / ".gh_token"
PENDING_FILE = ROOT / ".gh_pending.json"
DEFAULT_REPO = "openvino-video-kit"


def _post(url, data):
    req = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(data).encode(),
        headers={"Accept": "application/json", "User-Agent": "openvino-video-kit"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def _api(method, path, token, payload=None):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "openvino-video-kit",
        },
        data=json.dumps(payload).encode() if payload else None,
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def auth_begin():
    d = _post("https://github.com/login/device/code", {"client_id": CLIENT_ID, "scope": SCOPES})
    PENDING_FILE.write_text(json.dumps({"device_code": d["device_code"], "interval": d.get("interval", 5)}))
    print("======================================================")
    print("  1) 開啟:  " + d["verification_uri"])
    print("  2) 輸入代碼:  " + d["user_code"])
    print(f"  （代碼 {d['expires_in']} 秒內有效；輸入後回來執行 auth-finish）")
    print("======================================================")


def auth_finish():
    p = json.loads(PENDING_FILE.read_text())
    interval = max(int(p.get("interval", 5)), 5)
    deadline = time.time() + 280
    while time.time() < deadline:
        try:
            r = _post(
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
                print("poll HTTPError", e.code)
                time.sleep(interval)
                continue
        if "access_token" in r:
            TOKEN_FILE.write_text(r["access_token"])
            os.chmod(TOKEN_FILE, 0o600)
            me = _api("GET", "/user", r["access_token"])
            print("授權成功:", me["login"])
            return
        err = r.get("error")
        if err == "authorization_pending":
            time.sleep(interval)
            continue
        print("授權失敗:", r)
        return
    print("還沒完成 — 在網頁輸入代碼後，再執行一次 auth-finish")


def create_repo(name=DEFAULT_REPO):
    token = TOKEN_FILE.read_text().strip()
    try:
        r = _api(
            "POST",
            "/user/repos",
            token,
            {
                "name": name,
                "description": "Windows-first offline AI video kit (OpenVINO, Intel CPU): PPT → 講稿 → TTS → MP4, low/high profiles, SVD video notebook.",
                "private": False,
                "has_issues": True,
            },
        )
        print("已建立:", r["html_url"])
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        if e.code == 422 and "already exists" in body:
            print("repo 已存在，跳過建立")
        else:
            raise
    me = _api("GET", "/user", token)
    print("帳號:", me["login"])


def push(name=DEFAULT_REPO, branch="main"):
    token = TOKEN_FILE.read_text().strip()
    login = _api("GET", "/user", token)["login"]
    remote_url = f"https://x-access-token:{token}@github.com/{login}/{name}.git"
    plain_url = f"https://github.com/{login}/{name}.git"
    subprocess.run(["git", "remote", "remove", "origin"], cwd=ROOT, capture_output=True)
    subprocess.run(["git", "remote", "add", "origin", remote_url], cwd=ROOT, check=True)
    try:
        subprocess.run(["git", "push", "-u", "origin", branch], cwd=ROOT, check=True)
    finally:
        subprocess.run(["git", "remote", "set-url", "origin", plain_url], cwd=ROOT, capture_output=True)
    print("push 完成: " + plain_url)


def main():
    cmds = {
        "auth-begin": auth_begin,
        "auth-finish": auth_finish,
        "create-repo": create_repo,
        "push": push,
    }
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        print(__doc__)
        sys.exit(1)
    cmds[sys.argv[1]]()


if __name__ == "__main__":
    main()
