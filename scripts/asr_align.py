#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用本地 faster-whisper 对旁白音频做中文 ASR, 按给定句子列表对齐, 输出每句真实起止秒。

输入:
  --audio   旁白音频 (mp3/wav)
  --sentences  每行一句纯文本的文件 (用于和识别结果做字符级匹配)
输出:
  --out  JSON: [{"i":0,"start":1.2,"end":3.4,"text":"..."}, ...]  (秒, 音频坐标系)

依赖: pip install faster-whisper  (首次运行会下载模型)
"""
import argparse
import json
import re
import sys

from faster_whisper import WhisperModel


def clean(s):
    return "".join(ch for ch in s if re.match(r"[\u4e00-\u9fffA-Za-z0-9]", ch))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True, help="旁白音频路径")
    ap.add_argument("--sentences", required=True, help="每行一句纯文本(去标记)的文件")
    ap.add_argument("--out", default="asr_segments.json")
    ap.add_argument("--model", default="base", help="faster-whisper 模型, base/small/medium")
    args = ap.parse_args()

    sentences = [l.strip() for l in open(args.sentences, encoding="utf-8") if l.strip()]
    if not sentences:
        print("ERROR: sentences 文件为空", file=sys.stderr)
        sys.exit(1)

    print(f">> loading model ({args.model}, int8, cpu) ...")
    model = WhisperModel(args.model, device="cpu", compute_type="int8")
    segs, _ = model.transcribe(args.audio, word_timestamps=True, language="zh")

    words = []
    for s in segs:
        for w in s.words:
            if isinstance(w, dict):
                words.append({
                    "word": w.get("word", ""),
                    "start": w.get("start", 0.0),
                    "end": w.get("end", 0.0),
                })
            else:
                words.append({"word": w.word, "start": w.start, "end": w.end})

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
        if idx == -1:
            idx = pos
        cstart, cend = idx, min(idx + len(s), len(clean_text))
        if cstart >= len(char2word):
            cstart = len(char2word) - 1
        wi_s = char2word[cstart]
        wi_e = char2word[cend - 1] if cend > 0 else char2word[cstart]
        start = round(words[wi_s]["start"], 2)
        end = round(words[wi_e]["end"], 2)
        results.append({"i": si, "start": start, "end": end, "text": sent})
        pos = cend

    # 防重叠: 每句 end 不超过下一句 start - 0.05
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
    main()
