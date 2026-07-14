#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文案 -> MiniMax 克隆声横版短视频 一键流水线。

流程:
  1. 解析文案(支持 **关键词** 高亮标记), 拆句
  2. 生成克隆声 (MiniMax) 或复用 --audio
  3. 可选 ffmpeg 加速 (--speed)
  4. ASR 对齐: 用 faster-whisper 拿到每句真实起止秒
  5. 生成 Hyperframes index.html (深色科技风 + 关键词高亮 + 字幕同步 + 转场)
  6. 渲染 MP4 (+ 可选抽帧验证)

模板:
  --template lite : 纯字幕浮层 + 深色氛围背景(轻量)
  --template full : 完整分镜框架(标题卡/产品卡/代码窗/终端/对比/五步卡/编辑器/结尾卡),
                     内容用参数或默认值填充, 画面与成片同款

用法:
  python3 build_video.py --input script.txt --speed 1.3 --kicker "AI TOOL"
  python3 build_video.py --input script.txt --template full --title "复制一个网站<br>最快能<span class='hl'>有多快</span>？" --product "XX 工具"
  python3 build_video.py --audio voice.mp3 --input script.txt --template full
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Lite 模板: 纯字幕浮层 + 深色氛围背景
# ---------------------------------------------------------------------------
TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"/>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
:root{
  --bg:#0a0e14; --fg:#eaf0f7; --muted:#9aa6b8;
  --accent:#ff6a2c; --accent2:#5be8c4;
  --cn:"Hiragino Sans GB","PingFang SC","STHeiti",sans-serif;
  --mono:"JetBrains Mono","Hiragino Sans GB",monospace;
}
*{box-sizing:border-box;}
html,body{margin:0;width:1920px;height:1080px;overflow:hidden;background:var(--bg);
  font-family:var(--cn);color:var(--fg);}
#main{position:relative;width:1920px;height:1080px;background:var(--bg);}
.layer{position:absolute;inset:0;pointer-events:none;}
.glow{position:absolute;border-radius:50%;filter:blur(120px);}
.glow.a{width:760px;height:760px;left:-140px;top:-160px;
  background:radial-gradient(circle,var(--accent),transparent 70%);opacity:.32;}
.glow.b{width:680px;height:680px;right:-120px;bottom:-160px;
  background:radial-gradient(circle,var(--accent2),transparent 70%);opacity:.28;}
.grid{background-image:linear-gradient(rgba(255,255,255,.035) 1px,transparent 1px),
  linear-gradient(90deg,rgba(255,255,255,.035) 1px,transparent 1px);
  background-size:80px 80px;
  mask-image:radial-gradient(circle at 50% 45%,#000 30%,transparent 80%);}
.ghost{position:absolute;font-family:var(--mono);color:rgba(255,255,255,.045);
  font-weight:800;letter-spacing:-.04em;white-space:nowrap;font-size:520px;
  left:40px;bottom:-170px;}
.kicker{position:absolute;top:54px;left:60px;z-index:40;font-family:var(--mono);
  font-size:22px;letter-spacing:.32em;color:var(--accent2);text-transform:uppercase;opacity:.85;}
.kw{color:var(--accent);font-weight:800;}
#captions{position:absolute;left:0;right:0;top:0;bottom:0;z-index:50;
  display:flex;justify-content:center;align-items:center;pointer-events:none;}
.cap-group{position:absolute;width:1640px;text-align:center;font-size:56px;
  font-weight:700;line-height:1.4;color:var(--fg);text-shadow:0 4px 18px rgba(0,0,0,.55);
  opacity:0;visibility:hidden;padding:0 20px;}
</style>
</head>
<body>
<div id="main" data-composition-id="main" data-width="1920" data-height="1080" data-start="0" data-duration="__DURATION__">
  <div class="layer grid"></div>
  <div class="layer glow a" id="glowA"></div>
  <div class="layer glow b" id="glowB"></div>
  <div class="ghost">__GHOST__</div>
  <div class="kicker">__KICKER__</div>
  <div id="captions"></div>
  <audio id="voice" data-start="0" data-track-index="2" src="__AUDIO__" data-volume="1"></audio>
</div>
<script>
window.__timelines = window.__timelines || {};
(function(){
  var dur = parseFloat('__DURATION__');
  var GROUPS = __GROUPS__;
  var SCENE_START = __SCENE_START__;

  var capRoot = document.getElementById('captions');
  GROUPS.forEach(function(g,i){
    var el = document.createElement('div');
    el.className='cap-group'; el.id='cg-'+i; el.innerHTML=g.html;
    capRoot.appendChild(el);
  });

  function buildTimeline(){
    var tl = gsap.timeline();
    GROUPS.forEach(function(g,i){
      var el = document.getElementById('cg-'+i);
      tl.set(el,{opacity:0,visibility:'visible'}, g.t);
      tl.to(el,{opacity:1,duration:0.25,ease:'power2.out',overwrite:'auto'}, g.t);
      tl.to(el,{opacity:0,duration:0.2,ease:'power2.in',overwrite:'auto'}, g.e-0.2);
      tl.set(el,{opacity:0,visibility:'hidden'}, g.e);
    });
    tl.to('#glowA',{scale:1.15,duration:5,ease:'sine.inOut',yoyo:true,repeat:Math.ceil(dur/5)},0);
    tl.to('#glowB',{scale:1.18,duration:6,ease:'sine.inOut',yoyo:true,repeat:Math.ceil(dur/6)},0);
    SCENE_START.forEach(function(ts,idx){
      if(idx===0) return;
      tl.to('#main',{scale:1.02,duration:0.25,ease:'power2.out',overwrite:'auto'}, ts);
      tl.to('#main',{scale:1,duration:0.45,ease:'power2.inOut',overwrite:'auto'}, ts+0.25);
      tl.to('#glowA',{opacity:0.42,duration:0.6,ease:'power1.inOut',overwrite:'auto'}, ts);
      tl.to('#glowB',{opacity:0.20,duration:0.6,ease:'power1.inOut',overwrite:'auto'}, ts);
    });
    return tl;
  }
  window.__timelines['main'] = buildTimeline();
})();
</script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# Full 模板: 完整分镜框架(成片同款画面)
#   场景切换时机按字幕进度自动均分到 8 个 scene, 字幕 GROUPS 用 ASR 真实秒驱动
# ---------------------------------------------------------------------------
TEMPLATE_FULL = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
  :root {
    --bg: #0a0e14; --bg2: #121823; --bg3: #0f1521;
    --fg: #eaf0f7; --muted: #9aa6b8;
    --accent: #ff6a2c; --accent2: #5be8c4; --danger: #ff5470;
    --line: rgba(255, 255, 255, 0.08);
    --cn: "Hiragino Sans GB", "PingFang SC", "STHeiti", sans-serif;
    --mono: "JetBrains Mono", "Hiragino Sans GB", monospace;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; width: 1920px; height: 1080px; overflow: hidden;
    background: var(--bg); font-family: var(--cn); color: var(--fg); }
  #main { position: relative; width: 1920px; height: 1080px; background: var(--bg); }
  .scene { position: absolute; inset: 0; width: 1920px; height: 1080px; overflow: hidden; }
  .scene-content { position: relative; width: 100%; height: 100%; padding: 90px 130px;
    display: flex; flex-direction: column; justify-content: center; gap: 30px;
    box-sizing: border-box; z-index: 2; }
  .glow { position: absolute; border-radius: 50%; filter: blur(120px); z-index: 0; pointer-events: none; }
  .grid { position: absolute; inset: 0; z-index: 0; pointer-events: none;
    background-image: linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,.035) 1px, transparent 1px);
    background-size: 80px 80px;
    mask-image: radial-gradient(circle at 50% 45%, #000 30%, transparent 80%); }
  .ghost { position: absolute; font-family: var(--mono); color: rgba(255,255,255,.04);
    z-index: 0; pointer-events: none; font-weight: 800; letter-spacing: -0.04em; white-space: nowrap; }
  .kicker { font-family: var(--mono); font-size: 22px; letter-spacing: 0.32em;
    color: var(--accent2); text-transform: uppercase; }
  .kw { color: var(--accent); font-weight: 800; }
  .hl { color: var(--accent); }
  .mono { font-family: var(--mono); }
  .rule { height: 3px; width: 220px; background: linear-gradient(90deg, var(--accent), transparent); border-radius: 2px; }

  #scene1 { z-index: 1; background: var(--bg); }
  #scene1 .headline { font-size: 104px; font-weight: 800; line-height: 1.12; letter-spacing: -0.02em; }
  #scene1 .ghost-q { font-family: var(--mono); font-size: 720px; right: -60px; top: -180px; color: rgba(255,106,44,0.07); }

  #scene2 { z-index: 2; background: var(--bg); opacity: 0; }
  .card-product { display: flex; align-items: center; gap: 38px; padding: 46px 54px;
    background: linear-gradient(135deg, rgba(255,106,44,0.10), rgba(91,232,196,0.06));
    border: 2px solid rgba(255,106,44,0.5); border-radius: 26px; box-shadow: 0 0 60px rgba(255,106,44,0.18); }
  .logo-mark { width: 116px; height: 116px; flex: 0 0 auto; border-radius: 24px; background: var(--accent);
    color: #1a0c04; font-family: var(--mono); font-weight: 800; font-size: 58px;
    display: flex; align-items: center; justify-content: center; }
  .card-product .name { font-family: var(--mono); font-size: 64px; font-weight: 700; letter-spacing: -0.01em; }
  .card-product .sub { margin-top: 12px; font-size: 34px; color: var(--muted); }
  .scanlines { position: absolute; inset: 0; z-index: 1; pointer-events: none;
    background: repeating-linear-gradient(0deg, rgba(91,232,196,0.05) 0px, rgba(91,232,196,0.05) 2px, transparent 2px, transparent 9px);
    mask-image: radial-gradient(circle at 40% 50%, #000 10%, transparent 70%); }

  #scene3 { z-index: 3; background: var(--bg); opacity: 0; }
  .flow { display: flex; align-items: stretch; gap: 46px; }
  .urlbar { flex: 1 1 0; background: var(--bg2); border: 2px solid var(--line); border-radius: 22px; padding: 40px 44px;
    display: flex; flex-direction: column; gap: 26px; }
  .urlbar .bar { display: flex; align-items: center; gap: 18px; background: #0a0f18; border: 1px solid var(--line);
    border-radius: 14px; padding: 22px 26px; font-family: var(--mono); font-size: 34px; color: var(--fg); }
  .urlbar .dot { width: 16px; height: 16px; border-radius: 50%; background: var(--accent); flex: 0 0 auto; }
  .btn { align-self: flex-start; background: var(--accent); color: #1a0c04; font-weight: 800; font-size: 32px;
    padding: 16px 40px; border-radius: 14px; }
  .arrow { align-self: center; font-family: var(--mono); font-size: 90px; color: var(--accent2); flex: 0 0 auto; }
  .codewin { flex: 1.1 1 0; background: var(--bg3); border: 2px solid rgba(91,232,196,0.4); border-radius: 22px; overflow: hidden; }
  .codewin .titlebar { display: flex; gap: 12px; padding: 18px 24px; background: rgba(255,255,255,0.04); border-bottom: 1px solid var(--line); }
  .codewin .titlebar i { width: 16px; height: 16px; border-radius: 50%; display: inline-block; }
  .codewin .body { padding: 30px 34px; display: flex; flex-direction: column; gap: 22px; }
  .tags { display: flex; gap: 16px; flex-wrap: wrap; }
  .tag { font-family: var(--mono); font-size: 26px; font-weight: 700; padding: 8px 20px; border-radius: 999px;
    border: 1px solid var(--accent2); color: var(--accent2); }
  .code-line { font-family: var(--mono); font-size: 28px; color: var(--muted); display: flex; gap: 16px; }
  .code-line .k { color: var(--accent); }
  .code-line .v { color: var(--accent2); }

  #scene4 { z-index: 4; background: var(--bg); opacity: 0; }
  .terminal { background: #070b11; border: 2px solid var(--line); border-radius: 22px; overflow: hidden; max-width: 1180px; }
  .terminal .titlebar { display: flex; gap: 12px; align-items: center; padding: 20px 26px;
    background: rgba(255,255,255,0.05); border-bottom: 1px solid var(--line); }
  .terminal .titlebar i { width: 16px; height: 16px; border-radius: 50%; display: inline-block; }
  .terminal .tt { margin-left: 14px; font-family: var(--mono); font-size: 24px; color: var(--muted); }
  .terminal .body { padding: 40px 44px; display: flex; flex-direction: column; gap: 22px; font-family: var(--mono); font-size: 32px; }
  .terminal .line { display: flex; gap: 14px; }
  .terminal .p { color: var(--accent); }
  .terminal .green { color: var(--accent2); }
  .terminal .dim { color: var(--muted); }
  .cursor { display: inline-block; width: 16px; height: 34px; background: var(--accent2); animation: blink 1s steps(1) infinite; }
  @keyframes blink { 50% { opacity: 0; } }

  #scene5 { z-index: 5; background: var(--bg); opacity: 0; }
  .vs { display: flex; align-items: stretch; gap: 40px; }
  .panel { flex: 1 1 0; border-radius: 24px; padding: 44px 48px; display: flex; flex-direction: column; gap: 24px; }
  .panel.bad { background: rgba(255,84,112,0.06); border: 2px solid rgba(255,84,112,0.4); }
  .panel.good { background: rgba(91,232,196,0.07); border: 2px solid rgba(91,232,196,0.55); box-shadow: 0 0 50px rgba(91,232,196,0.15); }
  .panel .pt { font-size: 40px; font-weight: 800; }
  .panel.bad .pt { color: var(--danger); }
  .panel.good .pt { color: var(--accent2); }
  .panel .row { font-size: 34px; color: var(--fg); display: flex; gap: 16px; align-items: center; }
  .panel.bad .row { color: var(--muted); }
  .panel .x { color: var(--danger); font-weight: 800; }
  .panel .chk { color: var(--accent2); font-weight: 800; }
  .vs-mid { align-self: center; font-family: var(--mono); font-size: 64px; color: var(--accent); }

  #scene6 { z-index: 6; background: var(--bg); opacity: 0; }
  .steps { display: flex; align-items: flex-start; gap: 22px; margin-top: 10px; }
  .step { flex: 1 1 0; background: var(--bg2); border: 2px solid var(--line); border-radius: 20px; padding: 30px 26px;
    display: flex; flex-direction: column; gap: 18px; position: relative; }
  .step .num { width: 64px; height: 64px; border-radius: 16px; background: var(--accent); color: #1a0c04;
    font-family: var(--mono); font-weight: 800; font-size: 36px; display: flex; align-items: center; justify-content: center; }
  .step .sl { font-size: 28px; font-weight: 700; line-height: 1.3; }
  .step .sd { font-size: 22px; color: var(--muted); line-height: 1.35; }
  .connector { position: absolute; top: 215px; left: 150px; right: 150px; height: 3px;
    background: linear-gradient(90deg, var(--accent), var(--accent2)); z-index: 0; border-radius: 2px; }

  #scene7 { z-index: 7; background: var(--bg); opacity: 0; }
  .chips { display: flex; gap: 18px; flex-wrap: wrap; max-width: 1500px; }
  .chip { font-family: var(--mono); font-size: 30px; font-weight: 700; padding: 16px 30px; border-radius: 14px;
    background: var(--bg2); border: 1px solid var(--line); color: var(--fg); }
  .chip.hot { border-color: var(--accent); color: var(--accent); }
  .chip.more { border-color: var(--accent2); color: var(--accent2); }
  .audience { margin-top: 6px; font-size: 40px; font-weight: 800; line-height: 1.4; }
  .audience .hl { color: var(--accent); }

  #scene8 { z-index: 8; background: var(--bg); opacity: 0; }
  .beforeafter { display: flex; align-items: center; gap: 40px; }
  .ba { flex: 1 1 0; border-radius: 20px; padding: 34px 40px; font-size: 34px; font-weight: 700; line-height: 1.4; }
  .ba.old { background: rgba(255,255,255,0.04); border: 1px solid var(--line); color: var(--muted);
    text-decoration: line-through; text-decoration-color: var(--danger); }
  .ba.new { background: rgba(255,106,44,0.10); border: 2px solid var(--accent); color: var(--fg); }
  .ba .lab { display: block; font-family: var(--mono); font-size: 22px; letter-spacing: 0.2em; margin-bottom: 10px; color: var(--accent2); }
  .bigclose { font-size: 92px; font-weight: 800; line-height: 1.12; letter-spacing: -0.02em; margin-top: 8px; }
  .bigclose .hl { color: var(--accent); }
  .footer { margin-top: 18px; font-family: var(--mono); font-size: 26px; color: var(--muted); display: flex; gap: 18px; align-items: center; }
  .footer .pill { color: var(--accent); border: 1px solid var(--accent); border-radius: 999px; padding: 6px 18px; }

  #captions { position: absolute; left: 0; right: 0; bottom: 70px; z-index: 50;
    display: flex; justify-content: center; pointer-events: none; }
  .cap-group { position: absolute; width: 1680px; text-align: center; font-size: 52px; font-weight: 700;
    line-height: 1.42; color: var(--fg); text-shadow: 0 4px 18px rgba(0,0,0,0.55); opacity: 0; visibility: hidden; }
  .float-meta { position: absolute; top: 54px; right: 60px; z-index: 40; font-family: var(--mono);
    font-size: 20px; letter-spacing: 0.22em; color: rgba(173,184,201,0.9); }
</style>
</head>
<body>
  <div id="main" data-composition-id="main" data-width="1920" data-height="1080" data-start="0" data-duration="__DURATION__">
    <!-- SCENE 1 -->
    <div id="scene1" class="scene">
      <div class="grid"></div>
      <div class="glow" style="width:760px;height:760px;right:-120px;top:-160px;background:rgba(255,106,44,0.18);"></div>
      <div class="ghost ghost-q">?</div>
      <div class="scene-content">
        <div class="kicker" id="s1-kick">__S1_KICK__</div>
        <div class="headline" id="s1-title">__S1_TITLE__</div>
        <div class="rule" id="s1-rule"></div>
      </div>
    </div>
    <!-- SCENE 2 -->
    <div id="scene2" class="scene">
      <div class="grid"></div>
      <div class="scanlines"></div>
      <div class="glow" style="width:680px;height:680px;left:-160px;bottom:-200px;background:rgba(91,232,196,0.14);"></div>
      <div class="scene-content">
        <div class="kicker" id="s2-kick">__S2_KICK__</div>
        <div class="card-product" id="s2-card">
          <div class="logo-mark">&lt;/&gt;</div>
          <div>
            <div class="name">__PRODUCT__</div>
            <div class="sub">__SUBTITLE__</div>
          </div>
        </div>
      </div>
    </div>
    <!-- SCENE 3 -->
    <div id="scene3" class="scene">
      <div class="grid"></div>
      <div class="glow" style="width:700px;height:700px;right:-160px;top:-160px;background:rgba(255,106,44,0.14);"></div>
      <div class="scene-content">
        <div class="kicker" id="s3-kick">__S3_KICK__</div>
        <div class="flow" id="s3-flow">
          <div class="urlbar">
            <div class="bar"><span class="dot"></span><span>__URL__</span></div>
            <div class="btn">__CODE_BTN__</div>
          </div>
          <div class="arrow">→</div>
          <div class="codewin">
            <div class="titlebar"><i style="background:#ff5f56"></i><i style="background:#ffbd2e"></i><i style="background:#27c93f"></i></div>
            <div class="body">
              <div class="tags">__CODE_TAGS__</div>
              <div class="code-line"><span class="k">export</span> <span class="v">default</span> function App() {</div>
              <div class="code-line">&nbsp;&nbsp;<span class="k">return</span> &lt;Layout /&gt;</div>
              <div class="code-line">}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <!-- SCENE 4 -->
    <div id="scene4" class="scene">
      <div class="grid"></div>
      <div class="glow" style="width:680px;height:680px;left:-160px;top:-160px;background:rgba(91,232,196,0.12);"></div>
      <div class="scene-content">
        <div class="kicker" id="s4-kick">__S4_KICK__</div>
        <div class="terminal" id="s4-term">
          <div class="titlebar"><i style="background:#ff5f56"></i><i style="background:#ffbd2e"></i><i style="background:#27c93f"></i><span class="tt">__TERM_TITLE__</span></div>
          <div class="body">
            <div class="line"><span class="p">$</span><span class="green">__COMMAND__</span></div>
            <div class="line dim">__TERM_HINT__</div>
            <div class="line"><span class="p">&gt;</span> __URL__</div>
            <div class="line"><span class="green">__TERM_STATUS__</span><span class="cursor"></span></div>
          </div>
        </div>
      </div>
    </div>
    <!-- SCENE 5 -->
    <div id="scene5" class="scene">
      <div class="grid"></div>
      <div class="glow" style="width:700px;height:700px;right:-160px;bottom:-200px;background:rgba(255,84,112,0.10);"></div>
      <div class="scene-content">
        <div class="kicker" id="s5-kick">__S5_KICK__</div>
        <div class="vs" id="s5-vs">
          <div class="panel bad">
            <div class="pt">❌ 不是这样</div>
            __VS_BAD_ROWS__
          </div>
          <div class="vs-mid">VS</div>
          <div class="panel good">
            <div class="pt">✅ 是这样的</div>
            __VS_GOOD_ROWS__
          </div>
        </div>
      </div>
    </div>
    <!-- SCENE 6 -->
    <div id="scene6" class="scene">
      <div class="grid"></div>
      <div class="glow" style="width:700px;height:700px;left:-160px;top:-160px;background:rgba(255,106,44,0.12);"></div>
      <div class="scene-content" style="padding-top:120px;">
        <div class="kicker" id="s6-kick">__S6_KICK__</div>
        <div class="connector" id="s6-conn"></div>
        <div class="steps" id="s6-steps">__STEPS_HTML__</div>
      </div>
    </div>
    <!-- SCENE 7 -->
    <div id="scene7" class="scene">
      <div class="grid"></div>
      <div class="glow" style="width:700px;height:700px;right:-160px;top:-160px;background:rgba(91,232,196,0.12);"></div>
      <div class="scene-content">
        <div class="kicker" id="s7-kick">__S7_KICK__</div>
        <div class="chips" id="s7-chips">__CHIPS_HTML__</div>
        <div class="audience" id="s7-aud">__AUDIENCE__</div>
      </div>
    </div>
    <!-- SCENE 8 -->
    <div id="scene8" class="scene">
      <div class="grid"></div>
      <div class="glow" style="width:820px;height:820px;left:-160px;bottom:-220px;background:rgba(255,106,44,0.16);"></div>
      <div class="scene-content">
        <div class="beforeafter" id="s8-ba">
          <div class="ba old"><span class="lab">BEFORE</span>__S8_BEFORE__</div>
          <div class="ba new"><span class="lab">NOW</span>__S8_AFTER__</div>
        </div>
        <div class="bigclose" id="s8-big">__S8_TITLE__</div>
        <div class="footer" id="s8-foot"><span class="pill">OPEN SOURCE</span>__S8_FOOT__</div>
      </div>
    </div>

    <!-- CAPTIONS -->
    <div id="captions"></div>
    <div class="float-meta">__FLOAT_META__</div>

    <!-- AUDIO -->
    <audio id="voice" data-start="0" data-track-index="2" src="__AUDIO__" data-volume="1"></audio>
  </div>

  <script>
    window.__timelines = window.__timelines || {};
    var GROUPS = __GROUPS__;
    var N = GROUPS.length;
    var SCENE_COUNT = 8;
    // 场景切换时机: 按字幕进度均分到 8 个 scene (真实秒)
    var SCENE_START = [];
    for (var i = 0; i < SCENE_COUNT; i++) {
      if (i === 0) { SCENE_START.push(0); }
      else {
        var idx = Math.min(N - 1, Math.floor(i * N / SCENE_COUNT));
        SCENE_START.push(Math.max(SCENE_START[i - 1] + 0.6, GROUPS[idx].t));
      }
    }

    var capRoot = document.getElementById("captions");
    GROUPS.forEach(function (g, i) {
      var el = document.createElement("div");
      el.className = "cap-group"; el.id = "cg-" + i; el.innerHTML = g.html;
      capRoot.appendChild(el);
    });

    var tl = gsap.timeline({ paused: true });

    // ---- Scene 1 ----
    tl.from("#s1-kick", { y: 24, opacity: 0, duration: 0.5, ease: "power3.out" }, SCENE_START[0] + 0.2);
    tl.from("#s1-title", { x: -80, opacity: 0, duration: 0.7, ease: "expo.out" }, SCENE_START[0] + 0.45);
    tl.from("#s1-rule", { scaleX: 0, opacity: 0, duration: 0.6, ease: "power2.out", transformOrigin: "left center" }, SCENE_START[0] + 1.0);
    tl.from(".ghost-q", { scale: 0.8, opacity: 0, duration: 1.0, ease: "power2.out" }, SCENE_START[0] + 0.3);

    function transition(outId, inId, t) {
      tl.to(outId, { opacity: 0, scale: 1.08, duration: 0.5, ease: "power2.in", overwrite: "auto" }, t);
      tl.set(inId, { opacity: 1 }, t);
      tl.fromTo(inId, { scale: 0.95 }, { scale: 1, duration: 0.6, ease: "power2.out", overwrite: "auto" }, t);
    }

    // ---- Scene 2 ----
    transition("#scene1", "#scene2", SCENE_START[1] - 0.15);
    tl.from("#s2-kick", { y: 20, opacity: 0, duration: 0.5, ease: "power3.out" }, SCENE_START[1]);
    tl.from("#s2-card", { y: 60, opacity: 0, scale: 0.96, duration: 0.7, ease: "back.out(1.4)" }, SCENE_START[1] + 0.15);

    // ---- Scene 3 ----
    transition("#scene2", "#scene3", SCENE_START[2] - 0.15);
    tl.from("#s3-kick", { y: 20, opacity: 0, duration: 0.5, ease: "power3.out" }, SCENE_START[2]);
    tl.from("#s3-flow", { y: 50, opacity: 0, duration: 0.7, ease: "power3.out" }, SCENE_START[2] + 0.15);
    tl.from(".arrow", { x: -30, opacity: 0, duration: 0.5, ease: "power2.out" }, SCENE_START[2] + 0.4);

    // ---- Scene 4 ----
    transition("#scene3", "#scene4", SCENE_START[3] - 0.15);
    tl.from("#s4-kick", { y: 20, opacity: 0, duration: 0.5, ease: "power3.out" }, SCENE_START[3]);
    tl.from("#s4-term", { y: 50, opacity: 0, scale: 0.97, duration: 0.7, ease: "power3.out" }, SCENE_START[3] + 0.15);

    // ---- Scene 5 ----
    transition("#scene4", "#scene5", SCENE_START[4] - 0.15);
    tl.from("#s5-kick", { y: 20, opacity: 0, duration: 0.5, ease: "power3.out" }, SCENE_START[4]);
    tl.from(".panel.bad", { x: -50, opacity: 0, duration: 0.6, ease: "power3.out" }, SCENE_START[4] + 0.15);
    tl.from(".vs-mid", { scale: 0, opacity: 0, duration: 0.5, ease: "back.out(2)" }, SCENE_START[4] + 0.3);
    tl.from(".panel.good", { x: 50, opacity: 0, duration: 0.6, ease: "power3.out" }, SCENE_START[4] + 0.35);

    // ---- Scene 6 ----
    transition("#scene5", "#scene6", SCENE_START[5] - 0.15);
    tl.from("#s6-kick", { y: 20, opacity: 0, duration: 0.5, ease: "power3.out" }, SCENE_START[5]);
    tl.from("#s6-conn", { scaleX: 0, opacity: 0, duration: 0.7, ease: "power2.out", transformOrigin: "left center" }, SCENE_START[5] + 0.15);
    tl.from(".step", { y: 50, opacity: 0, duration: 0.55, ease: "power3.out", stagger: 0.12 }, SCENE_START[5] + 0.25);

    // ---- Scene 7 ----
    transition("#scene6", "#scene7", SCENE_START[6] - 0.15);
    tl.from("#s7-kick", { y: 20, opacity: 0, duration: 0.5, ease: "power3.out" }, SCENE_START[6]);
    tl.from(".chip", { y: 40, opacity: 0, duration: 0.5, ease: "back.out(1.5)", stagger: 0.08 }, SCENE_START[6] + 0.15);
    tl.from("#s7-aud", { y: 40, opacity: 0, duration: 0.6, ease: "power3.out" }, SCENE_START[6] + 0.7);

    // ---- Scene 8 ----
    transition("#scene7", "#scene8", SCENE_START[7] - 0.15);
    tl.from("#s8-ba", { y: 50, opacity: 0, duration: 0.7, ease: "power3.out" }, SCENE_START[7]);
    tl.from("#s8-big", { y: 60, opacity: 0, duration: 0.8, ease: "expo.out" }, SCENE_START[7] + 0.4);
    tl.from("#s8-foot", { opacity: 0, duration: 0.6, ease: "power2.out" }, SCENE_START[7] + 0.9);

    // ---- Captions (真实秒, 无 SCALE) ----
    GROUPS.forEach(function (g, i) {
      var el = document.getElementById("cg-" + i);
      tl.set(el, { opacity: 0, visibility: "visible" }, g.t);
      tl.to(el, { opacity: 1, duration: 0.25, ease: "power2.out", overwrite: "auto" }, g.t);
      tl.to(el, { opacity: 0, duration: 0.2, ease: "power2.in", overwrite: "auto" }, g.e - 0.2);
      tl.set(el, { opacity: 0, visibility: "hidden" }, g.e);
    });

    // Ambient motion
    tl.to(".glow", { scale: 1.12, duration: 4.6, ease: "sine.inOut", yoyo: true, repeat: 14 }, 0);
    tl.to(".ghost-q", { rotation: 6, duration: 6.2, ease: "sine.inOut", yoyo: true, repeat: 10 }, 0);
    tl.to(".grid", { backgroundPosition: "80px 80px", duration: 7.7, ease: "none", repeat: 8 }, 0);

    window.__timelines["main"] = tl;
  </script>
</body>
</html>
"""


def fatal(msg):
    print("ERROR: " + msg, file=sys.stderr)
    sys.exit(1)


def parse_segments(text):
    """拆句 + 提取 **高亮**。返回 [(html, plain), ...]。"""
    parts = re.split(r"(?<=。)|(?<=！)|(?<=？)|(?<=\n)|(?<=;)|\|", text)
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        html = re.sub(r"\*\*(.+?)\*\*", r"<span class='kw'>\1</span>", p)
        plain = re.sub(r"\*\*(.+?)\*\*", r"\1", p)
        out.append((html, plain))
    return out


def _resolve_npx():
    """Windows 下 Python subprocess 不走 shell, 必须拿到 npx.cmd 绝对路径。
    优先 PATH 查找, 再退回已知 nodejs 安装位置。"""
    if os.name != "nt":
        return "npx"
    # shutil.which 会带上 PATHEXT, 能找到 npx.cmd
    for name in ("npx.cmd", "npx.exe", "npx"):
        p = shutil.which(name)
        if p:
            return p
    # 退回本机已知路径
    for cand in (
        r"C:\Program Files\nodejs\npx.cmd",
        os.path.expandvars(r"%APPDATA%\npm\npx.cmd"),
        os.path.expanduser(r"~\.workbuddy\binaries\node\versions\22.22.2\npx.cmd"),
    ):
        if os.path.isfile(cand):
            return cand
    return "npx.cmd"  # 最后交给 shell 兜底


_NPX = None


def run(cmd, **kw):
    global _NPX
    cmd = list(cmd)
    if cmd and cmd[0] == "npx":
        if _NPX is None:
            _NPX = _resolve_npx()
        cmd[0] = _NPX
    print(">> " + " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run(cmd, **kw)


def build_steps_html(steps_arg):
    """steps_arg: '标题/描述|标题/描述|...' 最多5步。"""
    if not steps_arg:
        steps_arg = ("侦查 · 分析源站/抓取结构、资源与路由|"
                     "提取规范 · 生成组件/字体 / 颜色 / 样式|"
                     "多 Agent 并行构建/不同区块同时开工|"
                     "合并代码/统一拼装成项目|"
                     "视觉对比 · QA/像素级校验还原度")
    items = [s.strip() for s in steps_arg.split("|") if s.strip()][:5]
    parts = []
    for i, it in enumerate(items):
        if "/" in it:
            sl, sd = it.split("/", 1)
        else:
            sl, sd = it, ""
        parts.append(
            f'<div class="step"><div class="num">{i+1}</div>'
            f'<div class="sl">{sl}</div><div class="sd">{sd}</div></div>')
    return "\n".join(parts)


def build_chips_html(editors_arg):
    """editors_arg: 'a|b|c'。"""
    if not editors_arg:
        editors_arg = "Cloud Code|Cursor|Windsurf|Cline|Aider|等十几种 AI 编程助手"
    items = [e.strip() for e in editors_arg.split("|") if e.strip()]
    parts = []
    for i, e in enumerate(items):
        cls = "chip hot" if i < 2 else ("chip more" if "等" in e or "十几种" in e else "chip")
        parts.append(f'<span class="{cls}">{e}</span>')
    return "\n".join(parts)


def build_tags_html(tags_arg):
    """tags_arg: 'a|b|c' 用于代码窗标签。"""
    if not tags_arg:
        tags_arg = "Agent|Code|Console"
    items = [t.strip() for t in tags_arg.split("|") if t.strip()][:5]
    return "\n".join(f'<span class="tag">{t}</span>' for t in items)


def build_vs_rows(rows_arg, ok=True):
    """rows_arg: 'a|b|c'，返回 .row 列表。"""
    if not rows_arg:
        rows_arg = "自动理解|自动执行|自动汇总" if ok else "手动拆需求|反复看报错"
    items = [r.strip() for r in rows_arg.split("|") if r.strip()][:5]
    mark = "chk" if ok else "x"
    sym = "✓" if ok else "✕"
    return "\n".join(f'<div class="row"><span class="{mark}">{sym}</span> {it}</div>' for it in items)


def fill_lite(segs, aligns, audio_base, dur_total, args):
    groups = []
    for (html, _), a in zip(segs, aligns):
        groups.append({"t": a["start"], "e": a["end"], "html": html})
    scene_start = [0.0]
    for i in range(4, len(groups), 4):
        scene_start.append(round(groups[i]["t"], 2))
    return (TEMPLATE
            .replace("__DURATION__", str(round(dur_total, 2)))
            .replace("__AUDIO__", audio_base)
            .replace("__GROUPS__", json.dumps(groups, ensure_ascii=False))
            .replace("__SCENE_START__", json.dumps(scene_start))
            .replace("__GHOST__", args.ghost)
            .replace("__KICKER__", args.kicker))


def fill_full(segs, aligns, audio_base, dur_total, args):
    groups = []
    for (html, _), a in zip(segs, aligns):
        groups.append({"t": a["start"], "e": a["end"], "html": html})
    title = args.title or "复制一个网站，<br>最快能<span class='hl'>有多快</span>？"
    steps_html = build_steps_html(args.steps)
    chips_html = build_chips_html(args.editors)
    tags_html = build_tags_html(args.code_tags)
    bad_rows = build_vs_rows(args.vs_bad, ok=False)
    good_rows = build_vs_rows(args.vs_good, ok=True)
    return (TEMPLATE_FULL
            .replace("__DURATION__", str(round(dur_total, 2)))
            .replace("__AUDIO__", audio_base)
            .replace("__GROUPS__", json.dumps(groups, ensure_ascii=False))
            .replace("__S1_KICK__", args.s1_kick)
            .replace("__S1_TITLE__", title)
            .replace("__S2_KICK__", args.s2_kick)
            .replace("__PRODUCT__", args.product)
            .replace("__SUBTITLE__", args.subtitle)
            .replace("__S3_KICK__", args.s3_kick)
            .replace("__URL__", args.url)
            .replace("__CODE_BTN__", args.code_btn)
            .replace("__CODE_TAGS__", tags_html)
            .replace("__S4_KICK__", args.s4_kick)
            .replace("__COMMAND__", args.command)
            .replace("__TERM_TITLE__", args.term_title)
            .replace("__TERM_HINT__", args.term_hint)
            .replace("__TERM_STATUS__", args.term_status)
            .replace("__S5_KICK__", args.s5_kick)
            .replace("__VS_BAD_ROWS__", bad_rows)
            .replace("__VS_GOOD_ROWS__", good_rows)
            .replace("__S6_KICK__", args.s6_kick)
            .replace("__STEPS_HTML__", steps_html)
            .replace("__S7_KICK__", args.s7_kick)
            .replace("__CHIPS_HTML__", chips_html)
            .replace("__AUDIENCE__", args.audience)
            .replace("__S8_BEFORE__", args.before)
            .replace("__S8_AFTER__", args.after)
            .replace("__S8_TITLE__", args.outro)
            .replace("__S8_FOOT__", args.foot)
            .replace("__FLOAT_META__", args.float_meta))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", help="直接传文案(支持 **关键词** 高亮)")
    ap.add_argument("--input", help="文案文件(txt, 支持 **关键词** 高亮)")
    ap.add_argument("--audio", help="已有旁白音频, 跳过 TTS")
    ap.add_argument("--voice-config", help="MiniMax 私有配置路径")
    ap.add_argument("--billing", choices=["token", "balance"], default="token",
                    help="MiniMax 计费方式: token=订阅套餐 / balance=按量计费余额(新手推荐)")
    ap.add_argument("--speed", type=float, default=1.0, help="音频加速倍数(如 1.3)")
    ap.add_argument("--template", choices=["full"], default="full",
                    help="lite=纯字幕浮层; full=完整分镜框架(成片同款画面)")
    ap.add_argument("--kicker", default="", help="lite 模板左上角角标")
    ap.add_argument("--ghost", default="AI", help="lite 模板背景水印大字")
    # full 模板内容参数(不传则用成片同款默认)
    ap.add_argument("--title", default="", help="标题卡大字(可含 <br> 与 <span class='hl'>)</span>")
    ap.add_argument("--product", default="OpenHands", help="产品名")
    ap.add_argument("--subtitle", default="自托管的 AI 开发控制台", help="产品副标题")
    ap.add_argument("--url", default="https://github.com/All-Hands-AI/OpenHands", help="展示 URL")
    ap.add_argument("--command", default="修复登录页的报错", help="终端命令")
    ap.add_argument("--steps", default="", help="'标题/描述|标题/描述|...' 最多5步")
    ap.add_argument("--editors", default="", help="'a|b|c' 后端/工具列表")
    ap.add_argument("--audience", default="开发者 / 工程师<br><span class='hl'>提效工具</span>", help="受众文案")
    ap.add_argument("--outro", default="这大概就是 <span class='hl'>AI 时代开发者</span><br>的全新打开方式")
    ap.add_argument("--before", default="你盯着 AI 写代码")
    ap.add_argument("--after", default="派给开发助手")
    ap.add_argument("--foot", default="AI Dev Console")
    ap.add_argument("--s1_kick", default="AI 时代 · 开发者效率")
    ap.add_argument("--s2_kick", default="最近很火的开源项目")
    ap.add_argument("--s3_kick", default="一个需求，自动处理")
    ap.add_argument("--s4_kick", default="用法，一行命令")
    ap.add_argument("--s5_kick", default="它不是……而是……")
    ap.add_argument("--s6_kick", default="整个过程 · 五步")
    ap.add_argument("--s7_kick", default="支持接入 · 多种后端")
    ap.add_argument("--float_meta", default="AI TOOL · DEV CONSOLE")
    ap.add_argument("--code_tags", default="Agent|Code|Console", help="代码窗标签，'a|b|c'")
    ap.add_argument("--code_btn", default="开始 ↧", help="代码窗按钮文字")
    ap.add_argument("--term_title", default="zsh — agent", help="终端标题")
    ap.add_argument("--term_hint", default="任务描述：", help="终端提示文案")
    ap.add_argument("--term_status", default="Agent 开始干活", help="终端状态文案")
    ap.add_argument("--vs_bad", default="手动拆需求|反复看报错", help="对比左侧面板，'a|b|c'")
    ap.add_argument("--vs_good", default="自动理解|自动执行|自动汇总", help="对比右侧面板，'a|b|c'")
    ap.add_argument("--output", default="output.mp4", help="输出 MP4")
    ap.add_argument("--workdir", default=".", help="工作目录(产物落地处)")
    ap.add_argument("--asr", choices=["vosk", "whisper"], default="vosk",
                    help="字幕对齐引擎: vosk(本机稳定, 默认) / whisper(faster-whisper, 本机可能段错误)")
    ap.add_argument("--vosk-model",
                    default=None,
                    help="Vosk 中文模型目录 (--asr vosk 时用, 默认可自动探测)")
    ap.add_argument("--skip-render", action="store_true", help="只生成 index.html")
    ap.add_argument("--skip-snapshot", action="store_true")
    args = ap.parse_args()

    if not args.text and not args.input:
        fatal("必须提供 --text 或 --input")
    text = args.text or open(args.input, encoding="utf-8").read()

    wd = os.path.abspath(args.workdir)
    os.makedirs(wd, exist_ok=True)

    segs = parse_segments(text)
    if not segs:
        fatal("文案拆不出句子")

    # 1) 旁白音频
    if args.audio:
        audio_src = os.path.abspath(args.audio)
        if not os.path.exists(audio_src):
            fatal(f"--audio 不存在: {audio_src}")
        audio_path = os.path.join(wd, os.path.basename(audio_src))
        if os.path.realpath(audio_path) != os.path.realpath(audio_src):
            shutil.copy(audio_src, audio_path)
    else:
        narration_txt = os.path.join(wd, "narration.txt")
        with open(narration_txt, "w", encoding="utf-8") as f:
            f.write(text)
        audio_path = os.path.join(wd, "narration_clone.mp3")
        r = run([sys.executable,
                 os.path.join(SCRIPT_DIR, "generate_clone_voice.py"),
                 "--config", args.voice_config or "",
                 "--billing", args.billing,
                 "--text", narration_txt,
                 "--out", audio_path],
                check=False)
        if r.returncode != 0:
            fatal("MiniMax 克隆声生成失败")

    # 2) 加速
    if args.speed and args.speed != 1.0:
        sped = os.path.join(wd, "narration_sped.mp3")
        r = run(["ffmpeg", "-y", "-i", audio_path,
                 "-filter:a", f"atempo={args.speed}", sped],
                check=False)
        if r.returncode != 0:
            fatal("ffmpeg 加速失败")
        audio_path = sped

    # 3) 时长
    dur = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio_path]
    ).decode().strip()
    TOTAL = float(dur)
    print(f">> 音频时长 {TOTAL:.2f}s")

    # 4) ASR 对齐
    sentences_txt = os.path.join(wd, "sentences.txt")
    with open(sentences_txt, "w", encoding="utf-8") as f:
        for _, plain in segs:
            f.write(plain + "\n")
    asr_json = os.path.join(wd, "asr_segments.json")
    if args.asr == "vosk":
        asr_cmd = [sys.executable,
                   os.path.join(SCRIPT_DIR, "asr_align_vosk.py"),
                   "--audio", audio_path,
                   "--sentences", sentences_txt,
                   "--out", asr_json]
        if args.vosk_model:
            asr_cmd += ["--model", args.vosk_model]
    else:
        asr_cmd = [sys.executable,
                   os.path.join(SCRIPT_DIR, "asr_align.py"),
                   "--audio", audio_path,
                   "--sentences", sentences_txt,
                   "--out", asr_json]
    r = run(asr_cmd, check=False)
    if r.returncode != 0:
        fatal("ASR 对齐失败")

    aligns = json.load(open(asr_json, encoding="utf-8"))
    aligns.sort(key=lambda x: x["i"])

    # 5) 生成 HTML
    dur_total = TOTAL + 1.5
    audio_base = os.path.basename(audio_path)
    html_out = fill_full(segs, aligns, audio_base, dur_total, args)
    index_html = os.path.join(wd, "index.html")
    with open(index_html, "w", encoding="utf-8") as f:
        f.write(html_out)
    print(f">> 生成 {index_html}  ({len(aligns)} 句字幕, 模板={args.template})")

    if args.skip_render:
        print(">> --skip-render, 已完成")
        return

    # 6) 渲染
    out_abs = os.path.abspath(args.output)
    r = run(["npx", "--yes", "hyperframes@latest", "render",
             "-o", out_abs], cwd=wd, check=False)
    if r.returncode != 0:
        fatal("hyperframes 渲染失败")

    if not args.skip_snapshot:
        snap_dir = os.path.join(wd, "snapshots")
        pts = [round(TOTAL * i / 6, 1) for i in range(1, 6)]
        run(["npx", "--yes", "hyperframes@latest", "snapshot",
             "--at", ",".join(str(p) for p in pts),
             "-o", snap_dir], cwd=wd, check=False)

    print(f">> 完成: {out_abs}")


if __name__ == "__main__":
    main()
