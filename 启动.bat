@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"
set "LOG=%~dp0启动日志.txt"
echo [%date% %time%] 启动 >> "%LOG%"

set "MGR_PY=%USERPROFILE%\.workbuddyinaries\python\envs\default\Scripts\python.exe"
set "PY="
if exist "%MGR_PY%" (set "PY=%MGR_PY%") else (where python >nul 2>nul && set "PY=python")
if not defined PY (
  echo [错误] 找不到 Python。请安装 Python 3.11+ 并加入 PATH，或安装 WorkBuddy(自带 Python)。
  echo 详见同目录「新手安装指导.md」
  pause
  exit /b 1
)

"%PY%" -c "import tkinter" >> "%LOG%" 2>&1
if errorlevel 1 (
  echo [提示] 未检测到 tkinter 图形库，改用命令行模式。
  "%PY%" "%~dp0scriptsun_video.py"
  pause
  exit /b
)

echo 正在打开图形界面启动器...
echo 若未弹出窗口，请查看同目录「启动日志.txt」了解原因。
echo 使用 Python: %PY% >> "%LOG%"
echo 启动命令: "%PY%" "%~dp0launcher.py" >> "%LOG%"
echo 开始调用 launcher.py ... >> "%LOG%"
"%PY%" "%~dp0launcher.py"
set RC=%errorlevel%
echo [图形界面已关闭，退出码=%RC%] >> "%LOG%"
if not %RC%==0 (
  echo [错误] 图形界面异常退出(退出码 %RC%)，请查看「启动日志.txt」。
  pause
) else (
  echo 完成。窗口将关闭。
)
pause
endlocal
