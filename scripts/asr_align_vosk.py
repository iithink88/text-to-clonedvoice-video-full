#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用本地 Vosk (纯 C++ Kaldi) 对旁白音频做中文 ASR, 按给定句子列表对齐, 输出每句真实起止秒。

替代 asr_align.py (faster-whisper): 本机 faster-whisper 的 ctranslate2 会段错误, Vosk 无需 torch/云端, 稳定可用。

输入:
  --audio      旁白音频 (mp3/wav, 任意采样率, 脚本内部用 ffmpeg 转 16k mono)
  --sentences  每行一句纯文本的文件 (用于和识别结果做字符级匹配)
  --model      Vosk 中文模型目录 (默认读环境变量 VOSK_MODEL, 否则本机默认路径)
输出:
  --out  JSON: [{"i":0,"start":1.2,"end":3.4,"text":"..."}, ...]  (秒, 音频坐标系)

依赖: pip install vosk soundfile ; ffmpeg 在 PATH
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import wave

from vosk import Model, KaldiRecognizer, SetLogLevel

SetLogLevel(-1)  # 静音 vosk 日志

def resolve_vosk_model(explicit=None):
    """自动定位 Vosk 中文模型目录; 找不到则给出清晰指引并退出。"""
    if explicit and os.path.isdir(explicit):
        return explicit
    env = os.environ.get("VOSK_MODEL")
    if env and os.path.isdir(env):
        return env
    here = os.path.dirname(os.path.abspath(__file__))
    skill_root = os.path.dirname(here)
    for c in (os.path.expanduser(r"~\.cache\vosk-model-small-cn-0.22"),
              os.path.join(skill_root, "models", "vosk-model-small-cn-0.22"),
              r"C:\Users\lenovo\WorkBuddy\Claw\_vosk_model\vosk-model-small-cn-0.22"):
        if c and os.path.isdir(c):
            return c
    print("[!] 找不到 Vosk 中文模型 (vosk-model-small-cn-0.22)。请二选一:", file=sys.stderr)
    print("    1) 下载模型后, 设置环境变量 VOSK_MODEL 指向模型目录", file=sys.stderr)
    print("       下载: https://alphacephei.com/vosk/models (选 vosk-model-small-cn-0.22, 约 50MB)", file=sys.stderr)
    print("    2) 或把模型解压到技能目录 models/ 下: models/vosk-model-small-cn-0.22", file=sys.stderr)
    sys.exit(1)


def clean(s):
    return "".join(ch for ch in s if re.match(r"[\u4e00-\u9fffA-Za-z0-9]", ch))


def to_wav_16k_mono(src):
    """用 ffmpeg 把任意音频转成 16k mono s16le wav, 返回临时文件路径。"""
    fd, tmp = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    cmd = ["ffmpeg", "-y", "-i", src, "-ar", "16000", "-ac", "1",
           "-f", "wav", "-acodec", "pcm_s16le", tmp]
    r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if r.returncode != 0:
        print("ERROR: ffmpeg 转 wav 失败:\n" + r.stderr.decode("utf-8", "replace"),
              file=sys.stderr)
        sys.exit(1)
    return tmp


def recognize_words(wav_path, model_dir):
    """跑 Vosk, 返回词级列表 [{"word","start","end"}, ...]。"""
    if not os.path.isdir(model_dir):
        print(f"ERROR: 找不到 Vosk 模型目录: {model_dir}", file=sys.stderr)
        sys.exit(1)
    wf = wave.open(wav_path, "rb")
    if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
        print("ERROR: 音频必须是 16-bit mono wav", file=sys.stderr)
        sys.exit(1)
    rate = wf.getframerate()
    model = Model(model_dir)
    rec = KaldiRecognizer(model, rate)
    rec.SetWords(True)

    words = []

    def collect(res_json):
        try:
            res = json.loads(res_json)
        except Exception:
            return
        for w in res.get("result", []):
            words.append({
                "word": w.get("word", ""),
                "start": float(w.get("start", 0.0)),
                "end": float(w.get("end", 0.0)),
            })

    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            collect(rec.Result())
    collect(rec.FinalResult())
    wf.close()
    return words


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True, help="旁白音频路径")
    ap.add_argument("--sentences", required=True, help="每行一句纯文本(去标记)的文件")
    ap.add_argument("--out", default="asr_segments.json")
    ap.add_argument("--model", default=None, help="Vosk 中文模型目录 (默认可自动探测)")
    args = ap.parse_args()

    sentences = [l.strip() for l in open(args.sentences, encoding="utf-8") if l.strip()]
    if not sentences:
        print("ERROR: sentences 文件为空", file=sys.stderr)
        sys.exit(1)

    model_dir = resolve_vosk_model(args.model)
    print(f">> loading Vosk model: {model_dir}")
    wav_path = to_wav_16k_mono(args.audio)
    try:
        words = recognize_words(wav_path, model_dir)
    finally:
        try:
            os.remove(wav_path)
        except OSError:
            pass

    if not words:
        print("ERROR: Vosk 未识别到任何词, 无法对齐", file=sys.stderr)
        sys.exit(1)

    # 建字符级索引
    clean_chars = []
    char2word = []
    for wi, w in enumerate(words):
        for ch in w["word"]:
            if re.match(r"[\u4e00-\u9fffA-Za-z0-9]", ch):
                clean_chars.append(ch)
                char2word.append(wi)
    clean_text = "".join(clean_chars)

    pos = 0
    results = []
    for si, sent in enumerate(sentences):
        s = clean(sent)
        if not s:
            continue
        idx = clean_text.find(s, pos)
        if idx == -1 and len(s) >= 8:
            idx = clean_text.find(s[:8], pos)
        if idx == -1 and len(s) >= 4:
            idx = clean_text.find(s[:4], pos)
        if idx == -1:
            idx = pos
        cstart, cend = idx, min(idx + len(s), len(clean_text))
        if not char2word:
            break
        if cstart >= len(char2word):
            cstart = len(char2word) - 1
        if cend <= 0:
            cend = 1
        wi_s = char2word[cstart]
        wi_e = char2word[min(cend, len(char2word)) - 1]
        start = round(words[wi_s]["start"], 2)
        end = round(words[wi_e]["end"], 2)
        if end <= start:
            end = round(start + 0.4, 2)
        results.append({"i": si, "start": start, "end": end, "text": sent})
        pos = cend

    # 防重叠 + 兜底: 每句 end 不超过下一句 start - 0.05
    for i in range(len(results) - 1):
        nxt = results[i + 1]["start"]
        if results[i]["end"] > nxt - 0.05:
            results[i]["end"] = round(max(results[i]["start"] + 0.1, nxt - 0.05), 2)

    for r in results:
        print(f"[{r['i']:2d}] {r['start']:6.2f} -> {r['end']:6.2f}  {r['text']}")
    json.dump(results, open(args.out, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f">> saved {args.out} ({len(results)} segments)")


if __name__ == "__main__":
    # Windows GBK 控制台遇 Unicode 崩溃保险
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    main()
