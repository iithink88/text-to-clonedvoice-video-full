# 流水线详解 · 文案转克隆声视频

## 端到端数据流

```
script.txt (文案, **高亮**)
   │  parse_segments()  拆句 + 提取高亮
   ▼
(sentences.txt 纯文本, 用于 ASR 匹配)
   │  generate_clone_voice.py  →  MiniMax TTS
   ▼
narration_clone.mp3 ──ffmpeg atempo──▶ narration_sped.mp3
   │  ffprobe 拿 TOTAL 时长
   ▼
asr_align.py (faster-whisper, word_timestamps)
   │  字符级匹配 sentences.txt ↔ 识别结果
   ▼
asr_segments.json  [{i,start,end,text}]  ← 真实朗读时间戳(秒)
   │  与原文句子顺序一一对应
   ▼
build_video.py 生成 index.html
   │  GROUPS = [{t:start, e:end, html:带高亮}]
   │  SCENE_START = 每 4 句一个转场点
   │  data-duration = TOTAL + 1.5
   ▼
hyperframes render → final.mp4
```

关键点：**GROUPS 的 t/e 直接用 ASR 真实秒，不再用 SCALE 估算**。
字幕出现/消失严格等于那句话被念出来的区间，因此音频和字幕天然重合。

---

## 依赖安装

### 1. Hyperframes（视频合成）
```bash
npx --yes hyperframes@latest --help     # 首次自动下载
# 依赖: Chrome(无头) + ffmpeg，通常本机已有
hyperframes doctor                       # 自检依赖
```

### 2. ffmpeg
```bash
# macOS
brew install ffmpeg
# 验证
ffmpeg -version && ffprobe -version
```

### 3. Python + faster-whisper（ASR 对齐）
```bash
python3 -m venv venv
venv/bin/pip install faster-whisper
# 首次运行 asr_align.py 会自动下载中文 base 模型(~150MB)
# 想要更准可改 --model small / medium（更慢）
```

### 4. MiniMax 克隆声凭证
私有 JSON 配置示例（`~/.codex/skills/jiajia-digital-human-video/private/config.json`）：
```json
{
  "minimax": {
    "group_id": "",
    "voice_id": "你的声音ID（克隆后回填）",
    "token_plan_api_key": "sk-xxx",
    "balance_api_key": "sk-api-xxx",
    "preferred_model": "speech-2.8-turbo"
  }
}
```
`generate_clone_voice.py` 默认自动定位该文件；否则 `--voice-config` 或环境变量 `MINIMAX_CONFIG` 指定。

---

## 排错清单

| 现象 | 原因 | 解决 |
|------|------|------|
| 字幕上一句没读完下一句就出 | 用了估算时间轴 | 必须走 ASR 对齐（asr_segments.json 真实秒） |
| 中文字幕成方块 | 渲染机缺中文字体 | CSS `:root --cn` 补 `PingFang SC`/`Hiragino Sans GB`，或装字体 |
| MiniMax 401 | key/group_id 错 | 检查私有配置 `token_plan_api_key` 与 `voice_id` |
| MiniMax 返回 audio 为空 | 文本过长/含不支持字符 | 缩短单段，或分句调用 |
| faster-whisper `w.word` 报错 | 存入列表后是 dict | 用 `w["word"]` |
| ASR 某句时间戳错位 | 识别字与原文差异大 | 调 `--model small`；或句子里补 **专有名词** 帮助锚定 |
| 渲染极慢(逐帧) | 无头 Chrome 逐帧抓取 | 正常，66s 视频约 15-20 分钟；勿中途 kill |

---

## 扩展点

### 换视觉风格
编辑 `scripts/build_video.py` 的 `TEMPLATE` 常量：
- CSS 变量集中在 `:root`（`--accent` 主色、`--accent2` 辅色）
- 背景层 `.glow` / `.grid` / `.ghost` 可换形状/颜色
- 转场逻辑在 `buildTimeline()` 的 `SCENE_START.forEach`

### 更精细的分镜
当前为"字幕驱动通用场景"。若要按内容生成图示分镜（如流程图/对比卡），
可在 `--input` 文案里用分段标记（如 `## 场景:流程图`），让 `parse_segments()`
识别并生成对应区块——这属于进阶定制。

### 不用克隆声、用占位声
把 `generate_clone_voice.py` 换成 `hyperframes tts`（自带 Kokoro 中文声 `zf_xiaobei`），
适合先出样片再换克隆声。

### 竖版 / 其他尺寸
改 TEMPLATE 里 `width/height` 与 `data-width/height`，并把字幕区 `#captions` 尺寸调小。
