#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交互式一键启动器: 文案 -> 克隆声/免费声横版短视频 (Vosk 字幕对齐)。

双击 "启动.bat" 会调用本脚本。所有中文交互在 Python 内完成(UTF-8 稳定)。
声音引擎二选一:
  [A] MiniMax 云端克隆声: 真实克隆你的声音, 需 API 凭证(首次克隆 9.9 元),
       按 private/config.json 里的 voice_id 合成。要克隆声音时选这个。
  [B] edge-tts 免费声: 微软在线 TTS, 零配置零费用, 音色固定(晓晓等),
       对声音没要求时选这个(默认推荐, 立即可用)。
输出到桌面。
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL_DIR / "scripts"
CONFIG = SKILL_DIR / "private" / "config.json"
INPUT_DIR = SKILL_DIR / "input"
DESKTOP = Path.home() / "Desktop"

PLACEHOLDER_HINTS = ("在这里填", "如果用", "填第", "你的", "克隆后")


def line(c="="):
    print(c * 60)


def ask(prompt, default=""):
    try:
        v = input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\n已取消。")
        sys.exit(0)
    return v or default


def check_config():
    """返回 (config_path, billing)。config 无效则打印指引并退出。"""
    if not CONFIG.exists():
        line()
        print("[!] 选了 A(克隆声) 但还没配置 MiniMax 凭据。")
        print(f"    请复制模板并填写:")
        print(f"    模板: {SKILL_DIR / 'private' / 'config.example.json'}")
        print(f"    目标: {CONFIG}")
        print("    需要填: voice_id + (balance_api_key 或 token_plan_api_key)")
        print("    详细步骤见: " + str(SKILL_DIR / "新手安装指导.md"))
        line()
        sys.exit(1)
    try:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[!] config.json 解析失败: {e}")
        sys.exit(1)
    mm = cfg.get("minimax", {})

    def filled(v):
        if not v or not str(v).strip():
            return False
        return not any(h in str(v) for h in PLACEHOLDER_HINTS)

    if not filled(mm.get("voice_id")):
        print("[!] config.json 里的 voice_id 还没填(或还是占位文字)。请先克隆声音并回填。")
        sys.exit(1)
    bal = filled(mm.get("balance_api_key"))
    tok = filled(mm.get("token_plan_api_key"))
    if not bal and not tok:
        print("[!] config.json 里 balance_api_key / token_plan_api_key 都没填。至少填一个。")
        sys.exit(1)
    billing = "balance" if bal else "token"
    print(f"[ok] 凭据已就绪 (计费方式: {billing})")
    return CONFIG, billing


def get_script_text():
    """返回文案文件路径。优先 input/文案.txt; 否则交互输入。"""
    default_txt = INPUT_DIR / "文案.txt"
    if default_txt.exists() and default_txt.read_text(encoding="utf-8").strip():
        print(f"[ok] 使用文案文件: {default_txt}")
        return str(default_txt)
    print("没有找到默认文案文件 input/文案.txt。")
    print("请选择: [1] 输入一个 txt 文件路径   [2] 直接粘贴文案")
    choice = ask("输入 1 或 2 (默认 2): ", "2")
    if choice == "1":
        p = ask("txt 文件完整路径: ").strip('"')
        if not os.path.exists(p):
            print("[!] 文件不存在。")
            sys.exit(1)
        return p
    print("请粘贴文案，输入完成后单独敲一行 END 回车结束：")
    lines = []
    while True:
        try:
            l = input()
        except (EOFError, KeyboardInterrupt):
            break
        if l.strip() == "END":
            break
        lines.append(l)
    text = "\n".join(lines).strip()
    if not text:
        print("[!] 文案为空。")
        sys.exit(1)
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    default_txt.write_text(text, encoding="utf-8")
    print(f"[ok] 文案已存到 {default_txt}")
    return str(default_txt)


def run_edgetts(input_txt, speed, product, title, out_path):
    """edge-tts 免费声 -> mp3 -> build_video.py --audio (零配置)。"""
    mp3 = str(SKILL_DIR / "input" / "narration_edge.mp3")
    gen_cmd = [sys.executable, str(SCRIPTS / "generate_voice_edgetts.py"),
               "--text", input_txt, "--out", mp3]
    line("-")
    print("正在用 edge-tts 免费声合成旁白(微软在线, 约几秒)……")
    line("-")
    r = subprocess.run(gen_cmd)
    if r.returncode != 0:
        print("[失败] edge-tts 旁白生成失败, 把报错发给助手排查。")
        sys.exit(1)

    build_cmd = [sys.executable, str(SCRIPTS / "build_video.py"),
                 "--audio", mp3, "--asr", "vosk",
                 "--speed", speed, "--output", str(out_path)]
    if product:
        build_cmd += ["--product", product]
    if title:
        build_cmd += ["--title", title]
    line("-")
    print("旁白已生成, 开始画面渲染(较慢, 请勿关闭窗口)……")
    line("-")
    return subprocess.run(build_cmd)


def main():
    line()
    print("  文案 -> 横版短视频  (Vosk 字幕对齐版)")
    line()

    input_txt = get_script_text()

    speed = ask("音频加速倍数 (回车默认 1.3): ", "1.3")
    try:
        float(speed)
    except ValueError:
        speed = "1.3"

    product = ask("产品/工具名 (回车用默认): ", "")
    title = ask("标题卡大字 (回车用默认, 可含 <br>): ", "")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = DESKTOP / f"克隆声视频_{ts}.mp4"

    print()
    print("声音引擎:")
    print("  [A] MiniMax 克隆声  —— 真实克隆你的声音, 需 API 凭证(首次克隆 9.9 元)")
    print("  [B] edge-tts 免费声 —— 微软在线 TTS, 零配置零费用, 音色固定(默认推荐)")
    backend = ask("选 A 或 B (默认 B): ", "B").upper()

    if backend == "A":
        cfg_path, billing = check_config()
        cmd = [
            sys.executable, str(SCRIPTS / "build_video.py"),
            "--input", input_txt,
            "--asr", "vosk",
            "--billing", billing,
            "--voice-config", str(cfg_path),
            "--speed", speed,
            "--output", str(out_path),
        ]
        if product:
            cmd += ["--product", product]
        if title:
            cmd += ["--title", title]
        line("-")
        print("开始生成(克隆声需联网, 渲染较慢, 请勿关闭窗口)……")
        line("-")
        r = subprocess.run(cmd)
        line()
        if r.returncode == 0:
            print(f"[完成] 视频已生成: {out_path}")
        else:
            print("[失败] 生成中断，请把上面的报错发给助手排查。")
    else:
        r = run_edgetts(input_txt, speed, product, title, out_path)
        line()
        if r.returncode == 0:
            print(f"[完成] 视频已生成: {out_path}")
        else:
            print("[失败] 生成中断，请把报错发给助手排查。")
    line()


if __name__ == "__main__":
    main()
