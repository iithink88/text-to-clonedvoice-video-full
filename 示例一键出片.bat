@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "MGR_PY=%USERPROFILE%\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
if exist "%MGR_PY%" ( set "PY=%MGR_PY%" ) else ( where python >nul 2>nul && set "PY=python" )
if not defined PY (
  echo [ERROR] 没找到 Python。请先安装 WorkBuddy(自带 Python)，或在系统安装 Python 3.11+ 并加入 PATH。
  pause
  exit /b 1
)

echo 用 input/文案.txt + 免费声(B) + 加速1.3 直接出片(无需输入)...
echo 渲染需要一点时间，请勿关闭窗口。
"%PY%" "%~dp0scripts\run_video.py" --auto
echo.
echo 完成! 成片已放到桌面: 克隆声视频_*.mp4
echo 按任意键关闭本窗口。
pause
endlocal
