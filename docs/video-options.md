# 影片生成方案分析（CPU-only / OpenVINO / i5-13600K）

> 結論先講：**在純 CPU 上，「可行」的影片路線是 SVD（圖生影片）+ 投影片旁白影片**。
> 其他「文生影片」模型（LTX、Wan、ZeroScope）在 CPU 上不實用（小時~天級），故本 kit 不採用。
> 另外：你問過的 **SD3 notebook 是「圖像」模型**（不是影片）；本 kit 的圖像路線用 SD-Turbo / SDXL-Lightning 更快。

## 一、候選模型評估

| 模型 | 類型 | 官方 notebook | CPU 可行性 | 結論 |
|---|---|---|---|---|
| **SVD-XT + AnimateLCM（4-step）** | 圖 → 影片 | [stable-video-diffusion](https://github.com/openvinotoolkit/openvino_notebooks/tree/latest/notebooks/stable-video-diffusion) | ★★★☆ 數分鐘/2–4 秒片段；本 kit 主打 | ✅ 採用 |
| LTX-Video (2B DiT) | 文 → 影片 | [ltx-video](https://github.com/openvinotoolkit/openvino_notebooks/tree/latest/notebooks/ltx-video) | ★☆ GPU 上很快；CPU 上每支要很久（不划算） | ⛔ 不建議 |
| Wan2.1 (1.3B, CausVid 4-step) | 文 → 影片 | [wan2.1-text-to-video](https://github.com/openvinotoolkit/openvino_notebooks/tree/latest/notebooks/wan2.1-text-to-video) | ★☆ 1.3B + 4-step 理論可行，但 CPU 時間以「十分鐘~小時」計 | ⛔ 不建議 |
| Wan2.2 (5B MoE) | 文/圖 → 影片 | [wan2.2-text-image-to-video](https://github.com/openvinotoolkit/openvino_notebooks/tree/latest/notebooks/wan2.2-text-image-to-video) | ★ 連 GPU 都要權衡；CPU 免談 | ⛔ 不建議 |
| ZeroScope（舊型） | 文 → 影片 | [zeroscope-text2video](https://github.com/openvinotoolkit/openvino_notebooks/tree/latest/notebooks/zeroscope-text2video) | ★★ 量化後仍需很大 RAM（官方警告 24GB+） | ⛔ 不建議 |
| AnimateAnyone / DynamiCrafter | 人像/圖像動畫 | 同上 repo | ★★ 需姿態輸入、流程複雜 | ➖ 觀望 |

> 評估依據：官方 notebook 的記憶體警示與量化策略（NNCF weight compression）、以及本機對同級 CPU 的推理速度經驗。
> 精確時間請以本機實測為準（先跑 `--profile low` 的 SVD 量一次）。

## 二、為什麼是 SVD + AnimateLCM？

1. **4-step 蒸餾**：AnimateLCM 把去噪從 25+ 步降到 4 步（官方 notebook 標配），CPU 才跑得動。
2. **解析度友善**：512×320 / 576×320 訓練域，正好是 CPU 的舒適區。
3. **OpenVINO 官方支援**：notebook 完整（含轉檔、NNCF 量化、Gradio demo），helper 已 vendored 進本 repo。
4. **I2V 工作流更可控**：先用 SD 出一張好圖（快、可重跑），再讓它動起來；比直接文生影片可預期得多。

## 三、本 kit 的整合方式

```
[在家/有網]  tools/convert_svd.py     →  models/svd-ov/（IR：image_encoder / unet / vae_*）
[公司/離線]  scripts/07_svd_video.py  →  in.png → out.mp4（2–4 秒片段）
與主流程搭配：出圖（06_sd_image.py）→ 動起來（07）→ 穿插進投影片影片（05/run_lecture）
```

參數建議（13600K 級）：

| profile | 幀數 | 步數 | 解析度 | 用途 |
|---|---|---|---|---|
| low | 14（~2s @7fps） | 4 | 512×320 | 試水溫/草稿 |
| high | 25（~3.5s @7fps） | 6 | 512×320 | 成品片段 |

技巧：
- 動作不夠 → 提高 `--motion`（motion_bucket_id，40–127）；
- 想更像原圖 → 保持 `noise_aug_strength` 低（預設 0.01）；
- 一次生 2–4 秒就好，長片靠剪接拼接（`ffmpeg concat`）。

## 四、不採用路線的替代建議

- 想要「文生影片」品質 → 認命用 GPU（雲端不行就公司/家用有獨顯的機器），CPU 這代不現實。
- 需要動畫感的簡報 → 用「投影片 + Ken Burns 運鏡 + 旁白」就能很專業（見 README 主流程），成本近乎零。
