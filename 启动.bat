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

set "PYW=%PY:python.exe=pythonw.exe%"
"%PY%" -c "import tkinter" >nul 2>nul
if %errorlevel%==0 (
  if exist "%PYW%" ( set "RUN=%PYW%" ) else ( set "RUN=%PY%" )
  echo 正在打开图形界面启动器...
  "%RUN%" "%~dp0launcher.py"
) else (
  echo [提示] 未检测到图形界面库(tkinter)，改用命令行模式。
  "%PY%" "%~dp0scripts\run_video.py"
)
pause
endlocal
