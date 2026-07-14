#!/usr/bin/env python3
"""Generate narration with MiniMax cloned voice for Hyperframes videos.

Reads a private JSON config that contains minimax credentials and voice_id,
posts to MiniMax TTS v2, and writes the resulting MP3 + response metadata.

Example:
    python3 generate_clone_voice.py --config ~/.codex/.../config.json \
        --text narration.txt --out narration_clone.mp3
"""
import argparse
import binascii
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def fatal(msg):
    print("ERROR: " + msg, file=sys.stderr)
    sys.exit(1)


def resolve_config(path):
    if path:
        p = Path(path)
        if p.exists():
            return p
        fatal(f"指定的配置不存在: {path}")
    # Fallback: 依次查找常见私有配置位置。
    skill_dir = Path(__file__).resolve().parent.parent  # 技能根目录
    candidates = [
        os.environ.get("MINIMAX_CONFIG", ""),
        str(skill_dir / "private" / "config.json"),                        # 本机首选: 技能目录下 private/config.json
        str(Path.home() / ".workbuddy" / "skills" / "text-to-clonedvoice-video-full" / "private" / "config.json"),
        str(Path.home() / ".codex" / "skills" / "jiajia-digital-human-video" / "private" / "config.json"),
    ]
    for c in candidates:
        c = c.strip() if isinstance(c, str) else c
        if not c:
            continue
        p = Path(c)
        if p.exists():
            return p
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="Path to private JSON config with minimax credentials")
    parser.add_argument("--text", default="narration.txt", help="Input narration text file")
    parser.add_argument("--out", default="narration_clone.mp3", help="Output MP3 path")
    parser.add_argument("--billing", choices=["token", "balance"], default="token")
    args = parser.parse_args()

    cfg_path = resolve_config(args.config)
    if not cfg_path or not cfg_path.exists():
        fatal("找不到 MiniMax 私有配置。请用 --config 指定，或设置 MINIMAX_CONFIG 环境变量")

    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception as e:
        fatal(f"读取配置失败: {e}")

    mm = cfg.get("minimax", {})
    group_id = mm.get("group_id", "")
    voice_id = mm.get("voice_id")
    key = mm.get("token_plan_api_key") if args.billing == "token" else mm.get("balance_api_key")
    model = mm.get("preferred_model", "speech-2.8-turbo")
    if not key:
        fatal("配置中缺少对应 billing 的 API key")
    if not voice_id:
        fatal("配置中缺少 voice_id")

    text_path = Path(args.text)
    try:
        text = text_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        fatal(f"找不到旁白文件 {text_path}")
    if not text:
        fatal("旁白文本为空")

    out_mp3 = Path(args.out)
    out_json = out_mp3.with_suffix(".response.json")
    out_dur = out_mp3.with_suffix(".duration.txt")

    query = f"?GroupId={urllib.parse.quote(group_id)}" if group_id else ""
    body = {
        "model": model,
        "text": text,
        "stream": False,
        "voice_setting": {
            "voice_id": voice_id,
            "speed": 1.0,
            "vol": 1.0,
            "pitch": 0,
        },
        "audio_setting": {
            "sample_rate": 32000,
            "bitrate": 128000,
            "format": "mp3",
            "channel": 1,
        },
    }
    req = urllib.request.Request(
        f"https://api.minimax.chat/v1/t2a_v2{query}",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )

    print(">> 请求 MiniMax 克隆声 TTS ...", flush=True)
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        fatal(f"HTTP {e.code}: {detail}")
    except Exception as e:  # noqa
        fatal(f"请求失败: {e}")

    base = result.get("base_resp", {})
    if base.get("status_code", -1) != 0:
        fatal(f"MiniMax 返回错误: {base.get('status_msg')} | {json.dumps(result, ensure_ascii=False)[:500]}")

    audio_hex = (result.get("data") or {}).get("audio")
    if not audio_hex:
        fatal("返回结果中缺少 data.audio")

    audio_bytes = binascii.unhexlify(audio_hex)
    out_mp3.write_bytes(audio_bytes)
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        dur = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(out_mp3)]
        ).decode().strip()
    except Exception:
        dur = "unknown"
    out_dur.write_text(dur, encoding="utf-8")
    print(f"OK 生成 {out_mp3} ({len(audio_bytes)} bytes, 时长 {dur}s)")


if __name__ == "__main__":
    main()
