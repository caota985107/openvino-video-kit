# 公司端下載與安裝（無 USB、無 HuggingFace，只走 GitHub）

> 適用：公司電腦**不能插 USB**、**連不上 HuggingFace/其他模型來源**，但可以開 GitHub。
> 所有內容都放在 GitHub：程式碼在 repo、模型與執行環境在 **Releases（kit-v1）**。

## 0. 先做連通性測試（30 秒）

用公司電腦瀏覽器依序開：

1. `https://github.com/caota985107/openvino-video-kit` ← repo 頁
2. `https://github.com/caota985107/openvino-video-kit/releases` ← Releases 頁
3. 下載測試小檔：
   `https://github.com/caota985107/openvino-video-kit/releases/download/kit-v1/REACHABILITY_TEST.txt`

判讀：

| 情況 | 意思 | 處理 |
|---|---|---|
| 3 可下載 | ✅ 全套可行 | 照下面 §1–§3 |
| 1 不通 | github.com 被擋 | 請 IT 放行 github.com |
| 1、2 通、3 不通 | 檔案 CDN（release assets）被擋 | 請 IT 放行 `*.githubusercontent.com`、`objects.githubusercontent.com`；否則無法取檔 |

## 1. 取得程式碼

- **方法 A（推薦）**：repo 頁 → `Code` → `Download ZIP` → 解壓到例如 `D:\openvino-kit`
- **方法 B**：`git clone https://github.com/caota985107/openvino-video-kit.git`（公開庫、免登入）
- **方法 C（都擋時的土法）**：逐一開檔 → 右上「Download raw file」→ 照原目錄結構存（可行但麻煩）

## 2. 一鍵抓模型＋執行環境

在 `D:\openvino-kit` 開 PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File tools\company_fetch_and_setup.ps1
```

- 會從 Releases 下載：**2 個 SD 模型（分卷）約 9.9GB＋pylibs 套件包＋ffmpeg＋可攜 Python**（全部約 10.6GB）
- **可中斷重跑**：已下載的會跳過；SHA256 不符會自動重抓
- 只要環境（不抓模型）：加 `-SkipModels`；只要模型：加 `-SkipExtras`

## 3. 產影片

```powershell
powershell -ExecutionPolicy Bypass -File windows\run_lecture.ps1 -Pptx C:\簡報.pptx -ScriptFile C:\講稿.txt
```

成品：`work\final.mp4`（中間產物：`work\slides.json`、`work\script.json`、`work\audio\`、`work\slides\`）

講稿格式：純文字，一段一頁（空行分段，或每段前後加 `---`；也可用 `1.`「第1頁」標記）。

## 疑難排解

- **下載很慢/斷線**：直接重跑腳本（會續傳）；BITS 失敗時會自動改用 WebClient。
- **手動下載替代**：Releases 頁每個檔案都可直接點。分卷檔（`.part00．part01…`）必須**全部**下載後合併：
  ```cmd
  copy /b sd-turbo-openvino.zip.part00+sd-turbo-openvino.zip.part01+sd-turbo-openvino.zip.part02 sd-turbo-openvino.zip
  ```
  解壓前可用 `CHECKSUMS.sha256` 驗證（PowerShell：`Get-FileHash 檔名 -Algorithm SHA256`）。
- **SSL/憑證錯誤**（公司 proxy）：請 IT 處理，或先用手機熱點驗證流程。
- **python 無法啟動**：安裝 Microsoft VC++ Redistributable 2015–2022。
- **只想先玩出圖**：裝好環境後 `python\python.exe scripts\06_sd_image.py "prompt" out.png --profile low`。
