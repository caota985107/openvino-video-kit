# openvino-video-kit 🎬

**Windows-first「全離線」AI 影片工具箱**（Intel CPU / OpenVINO，i5-13600K 級即可）：

> PPT → 講稿（本地 LLM）→ 中文旁白（Piper TTS）→ 影片（ffmpeg）
> 外加：Stable Diffusion 出圖（低配/高配）、SVD 圖生影片（OpenVINO notebook + 腳本）

- ✅ **全程不碰雲端、不需要 GPU**：OpenVINO 在 CPU 上跑
- ✅ **公司無網路可用**：在家把 USB 包做好 → 公司插上就能跑（免管理員權限）
- ✅ **低配 low / 高配 high 兩種模式**，都是「分鐘級」可行（不是跑一個禮拜的那種）

---

## 兩種模式（low / high）

| 用途 | 低配 low | 高配 high |
|---|---|---|
| 講稿生成（LLM） | Qwen3-4B-int4（2.3GB） | Qwen3-8B-int4（4.9GB） |
| 出圖（SD） | SD-Turbo：512²、**1 step、約 2–5 秒/張** | SDXL-Lightning：768²、2 step、約 10–12 秒/張 |
| 圖生影片（SVD） | 14 幀 / 4 step | 25 幀 / 6 step |
| 旁白 TTS | Piper zh_CN-huayan-medium（兩者相同） | 同左 |

> 出圖時間為 FastSD CPU 官方於 i7-12700 的實測級距（13600K 相近）；SVD 為估算，第一次請先跑 low 量實際時間。
>
> **只做影片、講稿走公司管道？** 日常主力就是 `sd_low`（SD-Turbo）與 `sd_high`（SDXL-Lightning）兩顆；`models\Qwen*` 只有「本地生成講稿」才需要（可刪，省 7GB）。
> 自備講稿：`python scripts/08_import_script.py 講稿.txt work\slides.json work\script.json`，或直接 `run_lecture.ps1 -Pptx deck.pptx -ScriptFile 講稿.txt`。跑不動的模型（LTX-Video、Wan）完全沒有放進本包。

---

## 快速開始

### 路線 A：有網路的 Windows（推薦）

```powershell
# 0) 下載本 repo（zip 或 git clone），進入資料夾
# 1) 一鍵準備（裝依賴、抓模型 ~17GB、解 ffmpeg）
powershell -ExecutionPolicy Bypass -File windows\setup_home.ps1 -Profile both
# 2) 打成 USB 離線包（dist\openvino-kit）
powershell -ExecutionPolicy Bypass -File windows\make_bundle.ps1
```

把 `dist\openvino-kit` 複製到 USB。

### 路線 B：用 Linux 備料

```bash
python3 tools/fetch_models.py --set all --dest models   # 抓模型（HuggingFace）
python3 tools/bundle_prepare.py                          # 抓可攜 Python + Windows wheels、組裝 bundle/
# 完成後：bundle/ 就是 USB 包內容（複製到 USB）
```

### 公司端（不能 USB、不能 HuggingFace → 全部走 GitHub）

適用：公司電腦只能連 GitHub（免登入可讀）。
```powershell
# 1) repo 頁「Code → Download ZIP」→ 解壓（例：D:\openvino-kit）
# 2) 一鍵抓模型＋執行環境（來源＝GitHub Releases，約 10.6GB，可中斷重跑）
powershell -ExecutionPolicy Bypass -File tools\company_fetch_and_setup.ps1
# 3) 產影片
powershell -ExecutionPolicy Bypass -File windows\run_lecture.ps1 -Pptx C:\簡報.pptx -ScriptFile C:\講稿.txt
# 成品：work\final.mp4
```
連通性測試與疑難排解：[docs/COMPANY-DOWNLOAD.md](docs/COMPANY-DOWNLOAD.md)。
（備用）若哪天能用 USB：`install_offline.bat` 走既有離線包流程。

**產影片流程**：①抽 PPT 文字 → ②講稿（公司管道提供，或加 `--profile high` 讓本地 LLM 生成）→ ③Piper 中文旁白 → ④投影片轉 PNG（PowerPoint COM）→ ⑤ffmpeg 合成。講稿記得審一遍（2 分鐘）。

---

## SVD 圖生影片（進階）

> **模型分析**（為什麼選 SVD、LTX/Wan 為何不建議）：見 [docs/video-options.md](docs/video-options.md)

| 檔案 | 用途 |
|---|---|
| `notebooks/upstream_stable-video-diffusion.ipynb` | 官方 OpenVINO notebook 原文（Apache-2.0） |
| `notebooks/video_svd_offline.ipynb` | **離線特化版**（載入已轉好的 IR，只做推理、輸出 mp4） |
| `tools/convert_svd.py` | **在家**把 SVD 轉成 OpenVINO IR（第一次，需網路 + RAM ≥16GB） |
| `scripts/07_svd_video.py` | **公司離線**一行指令：`python scripts/07_svd_video.py in.png out.mp4 --profile low` |

第一次在家：`python tools/convert_svd.py --dest models/svd-ov`
（下載 SVD-XT ~9.5GB + AnimateLCM LoRA 並轉檔；一組件一組件進行、可中斷重跑。）
13600K 上一支 2–4 秒短片（4-step、512×320）為數分鐘級 → 建議只做片頭/過場 2–3 段。

---

## 目錄結構

```
openvino-video-kit/
├─ README.md / LICENSE / THIRD_PARTY.md
├─ prompts/             # ①「PPT→講稿」②「講稿→分鏡/SD prompt」模板
├─ scripts/             # 01 抽PPT｜02 講稿(LLM)｜03 TTS｜06 出圖｜07 SVD影片｜（Linux: 04 轉圖、05 合成）
├─ windows/             # setup_home｜make_bundle｜install_offline｜run_lecture｜slides_to_png｜build_video（PowerShell）
├─ tools/               # fetch_models｜bundle_prepare｜convert_svd｜push_to_github｜SVD helper(vendored)
├─ notebooks/           # SVD 官方 notebook + 離線版
├─ configs/models.json  # 低/高配模型清單（HF repo id、大小、用途）
└─ docs/video-options.md# 影片方案分析（SVD vs LTX vs Wan vs ZeroScope）
```

## 模型清單（`tools/fetch_models.py`）

| key | 模型 | 大小 | 用途 |
|---|---|---|---|
| llm_low | OpenVINO/Qwen3-4B-int4-ov | 2.3GB | 講稿（快） |
| llm_high | OpenVINO/Qwen3-8B-int4-ov | 4.9GB | 講稿（好） |
| sd_low | rupeshs/sd-turbo-openvino | 5.2GB | 出圖 512 / 1 step |
| sd_high | rupeshs/SDXL-Lightning-2steps-openvino-int8 | 4.8GB | 出圖 768 / 2 steps |
| （SVD） | 由 `tools/convert_svd.py` 產出 | ~7GB | 圖生影片 |

> ⚠️ 授權提醒（公司使用前請確認）：SD-Turbo「研究用途為主」、SDXL-Lightning 與 SVD 商用有條件。詳見 THIRD_PARTY.md。

## 常見問題

- **公司電腦裝不了東西？** 本包全走可攜：Python、套件、模型、ffmpeg 都在同一資料夾，複製就能跑、免管理員權限。
- **USB 格式**：請用 exFAT / NTFS（模型有單檔超過 4GB，FAT32 放不下）。
- **公司沒有 PowerPoint？** `slides_to_png.ps1` 走 PowerPoint COM；沒有就改用 LibreOffice 路線（`scripts/04_slides_to_png.sh`）或手動「另存 PNG」。
- **講稿風格想改？** 改 `prompts/01_ppt_to_script.md` 規則段，或 `scripts/02_generate_script.py` 的 SYSTEM 常數。
- **RAM 不夠？** 出圖/影片都用 low 配置（SD 1-step、SVD 14 幀）；建議 ≥16GB。
- **公司資安/網路政策**：本包執行期完全不需網路；唯一連網是「在家準備」那一步。

## 為什麼模型不在 GitHub repo 裡？（實測結論）

- Git LFS 免費額度 **10GiB 儲存 / 10GiB 月流量** → 本包模型合計 ~17GB **放不下**（只放一半也會讓 clone 流量超額）。
- 實測本機線路：GitHub Releases 下載僅 ~20KB/s（對比 HuggingFace 6MB/s）→ 即使付費 LFS，上傳/回抓時間也不合理。
- 因此模型走：`tools/fetch_models.py`（在家抓）+ USB bundle 交付。repo 只放程式碼、notebook 與文件。
- 若你仍要遠端存模型：GitHub Releases（不佔 LFS 配額）或公司 NAS 都是更好的選擇。

## Credits

- [openvino_notebooks](https://github.com/openvinotoolkit/openvino_notebooks)（Apache-2.0）：SVD notebook 與 helper 來源
- [FastSD CPU](https://github.com/rupeshs/fastsdcpu)：低/高配 SD 模型（OpenVINO IR）
- [Piper](https://github.com/OHF-Voice/piper1-gpl)：本地 TTS
