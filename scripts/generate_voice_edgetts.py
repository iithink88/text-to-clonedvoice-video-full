#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 edge-tts (微软免费在线 TTS) 生成旁白 mp3。

无需任何 API 密钥, 走微软在线语音合成服务。中文默认女声 XiaoxiaoNeural。
长文本会自动按句子切分、逐段合成后用 ffmpeg 拼接, 规避单次请求长度上限。

用法:
  python generate_voice_edgetts.py --text 文案.txt --voice zh-CN-XiaoxiaoNeural --out narration_edge.mp3
"""
import argparse
import asyncio
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# 常用中文音色 (voice name -> 说明)
VOICE_PRESETS = {
    "1": ("zh-CN-XiaoxiaoNeural", "晓晓 · 温柔女声 (默认推荐)"),
    "2": ("zh-CN-YunxiNeural", "云希 · 活力男声"),
    "3": ("zh-CN-XiaoyiNeural", "晓伊 · 知性女声"),
    "4": ("zh-CN-YunyangNeural", "云扬 · 男声 (偏新闻播报)"),
    "5": ("zh-CN-liaoning-XiaomengNeural", "辽宁 · 晓梦 · 东北女声"),
}

MAX_CHUNK = 1500  # 每段最大字符数, 避免单次 SSML 过长


def read_text(p):
    return Path(p).read_text(encoding="utf-8-sig").strip()


def split_sentences(text):
    """按中文/英文句末标点切句, 保留标点。"""
    import re
    # 切分但不丢弃标点
    parts = re.split(r"(?<=[。！？；!?;…\n])", text)
    sents = [s.strip() for s in parts if s and s.strip()]
    return sents


def chunk_text(sents, max_chunk=MAX_CHUNK):
    """把句子拼成 <=max_chunk 字符的块, 尽量不切断句子。"""
    chunks, cur = [], ""
    for s in sents:
        if len(cur) + len(s) <= max_chunk:
            cur += s
        else:
            if cur:
                chunks.append(cur)
            # 单句超长, 强制按 max_chunk 截断
            while len(s) > max_chunk:
                chunks.append(s[:max_chunk])
                s = s[max_chunk:]
            cur = s
    if cur:
        chunks.append(cur)
    return chunks


async def synth_chunk(text, voice, tmp_path):
    import edge_tts
    comm = edge_tts.Communicate(text, voice)
    await comm.save(tmp_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True, help="旁白文本文件(txt, UTF-8)")
    ap.add_argument("--out", default="narration_edge.mp3", help="输出 mp3 路径")
    ap.add_argument("--voice", default="", help="语音名, 留空则交互选择; 或用 1-5 选预设")
    ap.add_argument("--rate", default="+0%", help="语速, 如 +20% / -10% (edge-tts 格式)")
    args = ap.parse_args()

    text = read_text(args.text)
    if not text:
        print("[!] 旁白文本为空")
        sys.exit(1)

    voice = args.voice
    if not voice:
        print("选择中文音色 (方案B 免费声):")
        for k, (vn, desc) in VOICE_PRESETS.items():
            print(f"  [{k}] {desc}  ({vn})")
        choice = input("输入 1-5 (默认 1): ").strip() or "1"
        voice = VOICE_PRESETS.get(choice, VOICE_PRESETS["1"])[0]
    elif voice in VOICE_PRESETS:
        voice = VOICE_PRESETS[voice][0]

    rate = args.rate if args.rate else None
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    chunks = chunk_text(split_sentences(text))
    print(f">> edge-tts 合成: voice={voice} 段落数={len(chunks)}")

    tmp_files = []
    try:
        for i, ch in enumerate(chunks):
            tmp = out.parent / f".edgetts_tmp_{i}.mp3"
            asyncio.run(synth_chunk(ch, voice, str(tmp)))
            tmp_files.append(tmp)
        if len(tmp_files) == 1:
            os.replace(tmp_files[0], out)
        else:
            # ffmpeg concat
            list_path = out.parent / ".edgetts_list.txt"
            with open(list_path, "w", encoding="utf-8") as f:
                for t in tmp_files:
                    f.write(f"file '{t.as_posix()}'\n")
            r = subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                 "-i", str(list_path), "-c", "copy", str(out)],
                capture_output=True, text=True, encoding="utf-8")
            if r.returncode != 0:
                print("[!] ffmpeg 拼接失败:\n", r.stderr[-500:])
                sys.exit(1)
            list_path.unlink()
        # 清理临时
        for t in tmp_files:
            try:
                t.unlink()
            except OSError:
                pass
    except Exception as e:
        print(f"[!] edge-tts 合成失败: {e}")
        sys.exit(1)

    print(f"[ok] 已生成 {out} (voice={voice})")


if __name__ == "__main__":
    main()
