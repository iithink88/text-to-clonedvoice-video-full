#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图形界面启动器: 文案 -> 短视频。双击「启动.bat」会打开本窗口。

若系统没有 tkinter 图形库, 自动回退到命令行交互模式(run_video.py)。
"""
import os
import sys
import subprocess
import threading
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, scrolledtext
except ImportError:
    # 无图形库 -> 回退命令行交互(仅在 python.exe 调用时有效)
    sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))
    import run_video
    run_video.main()
    sys.exit(0)

SKILL_DIR = Path(__file__).resolve().parent
SCRIPTS = SKILL_DIR / "scripts"
RUN = SCRIPTS / "run_video.py"
INPUT_DEFAULT = SKILL_DIR / "input" / "文案.txt"

VOICE_LIST = [
    ("1", "晓晓 · 温柔女声 (默认推荐)"),
    ("2", "云希 · 活力男声"),
    ("3", "晓伊 · 知性女声"),
    ("4", "云扬 · 男声 (偏新闻播报)"),
    ("5", "辽宁 · 晓梦 · 东北女声"),
]


class App:
    def __init__(self, root):
        self.root = root
        root.title("文案转短视频 · 启动器")
        root.geometry("700x620")
        root.resizable(True, True)

        tk.Label(root, text="把口播文案变成带配音 + 字幕的短视频",
                 font=("Microsoft YaHei", 13, "bold")).pack(pady=(10, 2))
        tk.Label(root, text="声音引擎：A = 克隆你的声线(需配 MiniMax)   B = 微软免费声(默认)",
                 fg="#555").pack()

        frm = ttk.LabelFrame(root, text="参数", padding=10)
        frm.pack(fill="x", padx=12, pady=8)

        ttk.Label(frm, text="文案文件").grid(row=0, column=0, sticky="w", pady=3)
        self.var_input = tk.StringVar(value=str(INPUT_DEFAULT))
        ttk.Entry(frm, textvariable=self.var_input, width=52).grid(row=0, column=1, padx=5)
        ttk.Button(frm, text="浏览", command=self.browse).grid(row=0, column=2)

        ttk.Label(frm, text="声音引擎").grid(row=1, column=0, sticky="w", pady=3)
        self.var_backend = tk.StringVar(value="B")
        ttk.Radiobutton(frm, text="B 免费声(推荐)", variable=self.var_backend,
                        value="B").grid(row=1, column=1, sticky="w")
        ttk.Radiobutton(frm, text="A 克隆声", variable=self.var_backend,
                        value="A").grid(row=1, column=2, sticky="w")

        ttk.Label(frm, text="免费声音色").grid(row=2, column=0, sticky="w", pady=3)
        self.var_voice = tk.StringVar(value="1")
        voice_cb = ttk.Combobox(frm, textvariable=self.var_voice,
                                values=[f"{k} {d}" for k, d in VOICE_LIST],
                                state="readonly", width=42)
        voice_cb.current(0)
        voice_cb.grid(row=2, column=1, columnspan=2, sticky="w", padx=5)

        ttk.Label(frm, text="加速倍数").grid(row=3, column=0, sticky="w", pady=3)
        self.var_speed = tk.StringVar(value="1.3")
        ttk.Entry(frm, textvariable=self.var_speed, width=12).grid(row=3, column=1, sticky="w", padx=5)

        ttk.Label(frm, text="标题(可选)").grid(row=4, column=0, sticky="w", pady=3)
        self.var_title = tk.StringVar()
        ttk.Entry(frm, textvariable=self.var_title, width=40).grid(row=4, column=1, columnspan=2, sticky="w", padx=5)

        ttk.Label(frm, text="产品名(可选)").grid(row=5, column=0, sticky="w", pady=3)
        self.var_product = tk.StringVar()
        ttk.Entry(frm, textvariable=self.var_product, width=40).grid(row=5, column=1, columnspan=2, sticky="w", padx=5)

        btn_frm = ttk.Frame(root)
        btn_frm.pack(pady=8)
        ttk.Button(btn_frm, text="开始生成", command=self.start_generate).pack(side="left", padx=8)
        ttk.Button(btn_frm, text="一键示例出片", command=self.start_auto).pack(side="left", padx=8)

        ttk.Label(root, text="运行日志").pack(anchor="w", padx=12)
        self.log = scrolledtext.ScrolledText(root, height=14, state="disabled",
                                             font=("Consolas", 9))
        self.log.pack(fill="both", expand=True, padx=12, pady=(2, 10))

        self.running = False

    def browse(self):
        p = filedialog.askopenfilename(title="选择文案 txt",
                                       filetypes=[("文本", "*.txt"), ("所有", "*.*")])
        if p:
            self.var_input.set(p)

    def log_write(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def run_cmd(self, cmd, label):
        if self.running:
            messagebox.showwarning("提示", "正在生成中，请稍候。")
            return
        self.running = True
        self.log_write(f"\n=== {label} ===\n")

        def worker():
            try:
                proc = subprocess.Popen(cmd, cwd=str(SKILL_DIR),
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT,
                                        text=True, encoding="utf-8",
                                        errors="replace", bufsize=1)
                for line in proc.stdout:
                    self.root.after(0, self.log_write, line)
                proc.wait()
                self.root.after(0, self.log_write,
                                f"\n=== 结束 (returncode={proc.returncode}) ===\n")
                ok = proc.returncode == 0
                self.root.after(0, lambda: messagebox.showinfo(
                    "完成" if ok else "失败",
                    ("视频已生成，请到桌面查看 克隆声视频_*.mp4" if ok
                     else "生成失败，请看上方日志。")))
            except Exception as e:
                self.root.after(0, self.log_write, f"[异常] {e}\n")
                self.root.after(0, lambda: messagebox.showerror("异常", str(e)))
            finally:
                self.running = False

        threading.Thread(target=worker, daemon=True).start()

    def start_generate(self):
        backend = self.var_backend.get()
        if backend == "A":
            messagebox.showinfo(
                "提示",
                "选了 A(克隆声)，请先按「新手安装指导.md」配置 private/config.json。\n"
                "也可改用 B 免费声直接出片。")
        voice = self.var_voice.get().split()[0] if self.var_voice.get() else "1"
        cmd = [sys.executable, str(RUN),
               "--backend", backend, "--voice", voice,
               "--speed", self.var_speed.get() or "1.3",
               "--title", self.var_title.get(),
               "--product", self.var_product.get(),
               "--input", self.var_input.get()]
        self.run_cmd(cmd, f"生成 (引擎={backend}, 音色={voice})")

    def start_auto(self):
        self.run_cmd([sys.executable, str(RUN), "--auto"], "一键示例出片")


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
