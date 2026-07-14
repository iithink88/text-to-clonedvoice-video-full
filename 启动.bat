@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"

set "LOG=%~dp0启动日志.txt"
echo [%date% %time%] 启动 >> "%LOG%"

REM 依次探测 Python：本地 venv 优先，其次 WorkBuddy 托管 Python，最后系统 PATH
set "PY="
if exist "%~dp0venv\Scripts\python.exe" set "PY=%~dp0venv\Scripts\python.exe"
if not defined PY if exist "%USERPROFILE%\.workbuddy\binaries\python\envs\default\Scripts\python.exe" set "PY=%USERPROFILE%\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
if not defined PY where python >nul 2>nul && set "PY=python"

if not defined PY goto NOPY

echo 使用 Python: %PY% >> "%LOG%"

"%PY%" -c "import tkinter" >> "%LOG%" 2>&1
if errorlevel 1 goto CLI

echo 正在打开图形界面启动器...
echo 若未弹出窗口，请查看同目录「启动日志.txt」。
echo 启动命令: "%PY%" "%~dp0launcher.py" >> "%LOG%"
echo 开始调用 launcher.py ... >> "%LOG%"
"%PY%" "%~dp0launcher.py"
set RC=%errorlevel%
echo [图形界面已关闭，退出码=%RC%] >> "%LOG%"
if not "%RC%"=="0" goto GUIERR
echo 完成。窗口将稍后关闭。
pause
goto END

:GUIERR
echo [错误] 图形界面异常退出，退出码 %RC%，请查看「启动日志.txt」。
pause
goto END

:CLI
echo [提示] 未检测到 tkinter 图形库，改用命令行模式。
"%PY%" "%~dp0scripts\run_video.py"
pause
goto END

:NOPY
echo [错误] 找不到 Python。请先安装 Python 3.11 或更高版本并加入 PATH。
echo 详见同目录「新手安装指导.md」
pause
goto END

:END
endlocal