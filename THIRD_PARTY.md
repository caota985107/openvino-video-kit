# THIRD_PARTY.md — 第三方元件與授權

本 kit 自行撰寫的部分為 MIT（見 LICENSE）。以下為相依／內含的第三方元件：

## 內含（vendored）原始碼
| 檔案 | 來源 | 授權 |
|---|---|---|
| notebooks/upstream_stable-video-diffusion.ipynb | [openvino_notebooks](https://github.com/openvinotoolkit/openvino_notebooks) stable-video-diffusion notebook | Apache-2.0 |
| notebooks/ov_stable_video_diffusion_helper.py、tools/ov_stable_video_diffusion_helper.py | 同上（notebook 資料夾內 helper） | Apache-2.0 |
| tools/lcm_scheduler.py | 同上 | Apache-2.0 |

## 內含二進位／資產
| 檔案 | 說明 | 授權 |
|---|---|---|
| assets/ffmpeg-release-essentials.zip | Windows ffmpeg 建置（gyan.dev） | ffmpeg LGPL/GPL（此建置含 GPL 元件，如 x264） |
| assets/piper/zh_CN-huayan-medium.onnx(.json) | Piper 中文聲音（源自 rhasspy/piper-voices，訓練自 HuaYan TTS） | 見來源 repo（CC/自訂，商用前請確認） |

## 執行時安裝的套件
- openvino、openvino-genai、openvino-tokenizers：Apache-2.0（Intel）
- piper-tts：GPL（OHF-Voice/piper1-gpl）
- python-pptx、huggingface_hub、numpy、Pillow：各自開源授權
- （選配）torch、diffusers、transformers：BSD/Apache

## 模型
| 模型 | 授權備註 |
|---|---|
| Qwen3-4B / Qwen3-8B（int4 OpenVINO 轉換） | Apache-2.0 |
| SD-Turbo（rupeshs 轉 OpenVINO） | **研究用途為主**（原模型限制），商用請評估 |
| SDXL-Lightning（2-step, int8 OpenVINO） | 依 SDXL 系列授權（openrail++ 等，商用需確認） |
| Stable Video Diffusion (SVD-XT) | Stability AI Community License：**商用有條件**，公司用途請確認條款 |
| AnimateLCM-SVD-xt LoRA | 見 wangfuyun/AnimateLCM-SVD-xt |

> 提醒：公司內部使用前，請就「模型授權」與「產出內容」確認公司政策（尤其 SVD 與 SD-Turbo 的商用條款）。
