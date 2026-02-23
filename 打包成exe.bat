@echo off
chcp 65001 >nul
title 打包成exe
echo ========================================
echo   打包视频音频合成工具
echo ========================================
echo.
echo 请选择打包模式:
echo 1. 控制台模式 (显示命令行窗口)
echo 2. 窗口模式 (GUI，无控制台窗口)
echo 3. 退出
echo.
set /p choice=请选择 (1/2/3): 

if "%choice%"=="1" goto console
if "%choice%"=="2" goto window
if "%choice%"=="3" exit
goto end

:console
echo.
echo 正在安装依赖...
pip install pyinstaller
echo.
echo 开始打包...
python build_exe.py
goto end

:window
echo.
echo 正在安装依赖...
pip install pyinstaller
echo.
echo 开始打包 (窗口模式)...
python build_exe.py --window
goto end

:end
pause
