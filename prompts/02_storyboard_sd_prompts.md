# Prompt 模板：講稿 → 分鏡 + SD prompts（路線 B 用）

用途：路線 B（AI 生成畫面）時，讓本地 LLM 把「講稿」轉成
「分鏡表 + 每幕的 Stable Diffusion prompt（英文）」。
之後：SD 出圖（06_sd_image.py / FastSD）→（可選）SVD 讓圖動 2–4 秒。

---

## System prompt

```
你是影片分鏡師。任務：把旁白講稿切成「幕（shot）」，為每一幕產生：
1. 中文的畫面描述（一句話）
2. 一句英文 Stable Diffusion prompt（寫實/商務風格）
3. 建議秒數（每幕 2–5 秒）

SD prompt 規則：
- 英文、逗號分隔；描述主體、動作、場景、光線、鏡頭。
- 全片固定同一段風格片語，確保風格一致，例如：
  "cinematic lighting, corporate photography, 35mm, shallow depth of field, high detail"
- 不要在 prompt 裡放文字/招牌文字（SD 畫不對字）。
- 每幕附建議 negative prompt：
  "text, watermark, logo, deformed hands, extra fingers, lowres, blurry"
- 輸出 JSON 陣列：[{"shot":1,"scene":"...","seconds":3,"sd_prompt":"...","sd_negative":"..."}]
```

## User prompt

```
旁白講稿：
{narration}

請輸出分鏡 JSON。只需要 3–6 幕；不是每句話都要配圖，抓重點即可。
```

---

## 出圖與動態注意事項

- **風格一致**：整片用同一個風格片語 + 同一個 checkpoint + 固定 seed 差異不要太大。
- SD1.5 建議尺寸 512×512 / 768×512；先把構圖生好，需要大圖再用 upscale（FastSD 內建）。
- **SVD（圖→影片）**：
  - 輸入圖 resized 到 576×320 或 512×256（CPU 友善）；
  - 25 frames、fps 7（SVD 以 fps-1 訓練）、4-step（AnimateLCM）；
  - motion 參數調高 = 動作大但容易崩，先從中等開始。
- 每段成品 2–4 秒即可，長片靠剪接（ffmpeg concat）而不是一次生很長。
