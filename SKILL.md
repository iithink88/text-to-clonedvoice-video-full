---
name: text-to-clonedvoice-video-full
description: 文案转横版短视频（完整分镜画面版）。支持两种声音引擎：① MiniMax 云端克隆声（真实克隆你的声音，需 API 凭证，首次克隆 9.9 元）；② edge-tts 微软免费声（零配置、零费用，音色固定）。输入口播文案，自动生成带配音、字幕严格对齐、分镜画面的深色科技风横版视频（1920x1080）。
---

# 文案 → 横版短视频（完整分镜版 / 有画面）

你把一段口播文案丢进来，它自动出一条：带配音（可克隆你的声音，也可用微软免费声）、字幕严格卡在真实朗读节奏上、且带完整分镜画面的深色科技风横版短视频（1920×1080）。

## 画面包含
标题卡 → 产品卡 → 代码窗/URL → 终端命令 → 对比卡 → 五步流程卡 → 后端/工具接入 → 结尾卡。场景切换按字幕进度自动均分到 8 个 scene。

## 触发场景
- 用户给一段产品/工具介绍口播文案，要做一个"有画面、有分镜"的短视频
- 想要统一深色科技风、分镜式画面的短视频效果

## 新手必读（第一次用先看这）
- 📌 完整注册、充值、拿 API Key、克隆你的声音流程，看 **[新手安装指导.md](新手安装指导.md)**。
- 💰 价格速览：**克隆一个声音 9.9 元/个**（首次合成时扣，永久可用）；**生成音频 2 元/万字符**（turbo 默认）/ 3.5 元/万字符（hd），1 汉字=2 字符，一条 300 字口播配音才约 0.1 元。

## 快速开始（双击即用）
> 本技能已针对 Windows 适配：字幕对齐用 **Vosk**（稳定，绕开 faster-whisper 段错误），声音引擎在双击时二选一。
1. **放文案**：把口播文案写进 `input/文案.txt`（支持 `**关键词**` 高亮）。也可双击运行时直接粘贴。
2. **双击 `启动.bat`**：
   - 选 **[B] edge-tts 免费声**（默认推荐）：零配置、零费用，微软在线 TTS，音色固定（晓晓等），立即可出片。
   - 选 **[A] MiniMax 克隆声**：真实克隆你的声音，需先按 [新手安装指导.md](新手安装指导.md) 配好 `private/config.json`（voice_id + API Key，首次克隆声 9.9 元）。
   - 再选加速倍数 / 产品名 / 标题，成片输出到桌面 `克隆声视频_时间戳.mp4`。

> 预算与效果对照：**要克隆你自己/他人的声音 → 选 A（花约 10 元，永久可用）**；**对音色没要求、想免费马上出片 → 选 B（edge-tts，音色是微软自带，不是克隆）**。

## 首次安装依赖（朋友分享版 · 装一次即可）
1. **Node.js（必需，渲染用）**：到 https://nodejs.org 下载 LTS 版安装，装完重启一次。脚本用 `npx hyperframes` 渲染，首次会自动下载 Chromium。
2. **ffmpeg / ffprobe（必需）**：推荐 `winget install ffmpeg`（或 Chocolatey `choco install ffmpeg`），也可下载静态包把 `bin/` 加进 PATH。
3. **Python 依赖（必需）**：本技能用 WorkBuddy 自带的托管 Python（`启动.bat` 会自动定位），在该 Python 下执行：
   ```
   "<WorkBuddy托管Python>\Scripts\python.exe" -m pip install -r requirements.txt
   ```
   `requirements.txt` 含 `edge-tts vosk soundfile`。若不用 WorkBuddy，也可改用任意 Python 3.11+，把 `启动.bat` 里的 Python 路径改掉即可。
4. **Vosk 中文模型（必需，约 50MB）**：到 https://alphacephei.com/vosk/models 下载 `vosk-model-small-cn-0.22.zip` 并解压，二选一：
   - 放到技能目录 `models/vosk-model-small-cn-0.22`；或
   - 设置环境变量 `VOSK_MODEL` 指向解压目录。
   脚本会自动探测，找不到会给出提示。
5. **（可选）MiniMax 克隆声**：仅选 A 时需要。按 [新手安装指导.md](新手安装指导.md) 注册、充值、克隆声音、填 `private/config.json`。

## 依赖说明
- **声音引擎（二选一）**：
  - **[B] edge-tts 免费声（默认，零配置）**：微软在线 TTS，无需任何凭证，音色固定（晓晓 / 云希 等）。
  - **[A] MiniMax 克隆声（需凭证）**：首次克隆声音 9.9 元/个（永久可用），生成音频按字符计费。需配 `private/config.json`（见新手安装指导.md）。
- **字幕对齐**：**Vosk**（默认 `--asr vosk`）+ 中文模型 `vosk-model-small-cn-0.22`（见上方安装第 4 步）。⚠️ faster-whisper（`--asr whisper`）在本机 ctranslate2 段错误，勿用。
- **渲染**：`npx hyperframes@latest`（需 Node.js，首次自动下载 Chromium）。
- **音频处理**：ffmpeg / ffprobe（需装）。

## 用法
```bash
# 最简：给文案文件，自动生成配音 + 加速1.3x + 渲染
python scripts/build_video.py --input 文案.txt --speed 1.3 --output 成片.mp4

# 已有旁白音频，跳过 TTS，直接套 full 画面
python scripts/build_video.py --audio voice.mp3 --input 文案.txt --output 成片.mp4

# 指定分镜内容（不传则用通用默认）
python scripts/build_video.py --input 文案.txt --speed 1.3 \
  --title "用大白话，<br>生成<span class='hl'>能跑的应用</span>？" \
  --product "Lovable" --subtitle "用大白话生成能跑能部署的全栈应用" \
  --url "https://lovable.dev" --command "做一个带登录的投票应用" \
  --steps "理解需求/自然语言描述|生成界面/响应式组件|接入数据/数据库后端|实时预览/热更新调试|一键部署/直接上线" \
  --editors "GitHub|Supabase|Vercel|等十几种开发工具" \
  --before "你盯着 AI 写代码" --after "派给开发助手" \
  --code_tags "AI|Fullstack|App" --vs_bad "手写需求文档|反复调试报错" --vs_good "一句话生成|自动跑测试|一键部署" \
  --output 成片.mp4
```

## 参数
- `--input` / `--text`：文案（支持 `**关键词**` 标橙高亮）
- `--audio`：已有旁白音频，跳过 TTS（直接套分镜画面）
- `--speed`：音频加速倍数（默认 1.0；常用 1.3）
- `--title`：标题卡大字（可含 `<br>` 与 `<span class='hl'>`）
- `--product` / `--subtitle`：产品卡名称与副标题
- `--url` / `--command`：代码窗 URL、终端演示命令（prompt）
- `--steps`：`标题/描述|标题/描述|...` 最多 5 步
- `--editors`：`a|b|c` 后端/工具列表
- `--before` / `--after`：结尾对比（旧做法 vs 现在）
- `--outro`：结尾大字
- `--s1_kick` ~ `--s7_kick`：各场景左上角角标文案
- `--code_tags`：代码窗标签，`a|b|c`，默认 `Agent|Code|Console`
- `--code_btn`：代码窗按钮文字，默认 `开始 ↧`
- `--term_title` / `--term_hint` / `--term_status`：终端标题、提示、状态文案
- `--vs_bad` / `--vs_good`：对比卡左右侧内容，`a|b|c`
- `--audience`：scene 7 底部受众文案
- `--foot` / `--float_meta`：结尾左下角 pill 和右上角浮动 meta
- `--asr`：字幕对齐引擎，`vosk`（默认，稳定）/ `whisper`（段错误，勿用）
- `--vosk-model`：Vosk 中文模型目录（默认自动探测：环境变量 VOSK_MODEL 或 `models/` 子目录）
- `--billing`：MiniMax 计费，`balance`（按量，新手推荐）/ `token`（订阅套餐）

## 注意
- 字幕时间轴由本地 **Vosk**（Kaldi）从音频真实识别，绝不重叠错位；faster-whisper 会段错误，已默认改用 Vosk。
- 最省事的方式是双击 `启动.bat`（自动定位 Python）。手动跑命令请用 `python`（不是 `python3`）。
- 代码窗标签、终端文案、对比卡内容已全部参数化，可随主题替换；若需更深度改造画面结构，修改 `scripts/build_video.py` 中 `TEMPLATE_FULL` 即可。
