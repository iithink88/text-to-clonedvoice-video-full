@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

REM ==== text-to-clonedvoice-video-full 启动器 (可移植版) ====
REM 优先用 WorkBuddy 自带的托管 Python, 找不到再退回系统 PATH 里的 python
set "MGR_PY=%USERPROFILE%\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
if exist "%MGR_PY%" (
  set "PY=%MGR_PY%"
) else (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo [ERROR] 没找到 Python。请先安装 WorkBuddy(自带 Python), 或在系统里安装 Python 3.11+ 并加入 PATH。
  pause
  exit /b 1
)

"%PY%" "%~dp0scripts\run_video.py"
echo.
pause
endlocal
