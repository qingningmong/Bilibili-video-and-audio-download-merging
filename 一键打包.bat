@echo off
chcp 65001 >nul
title 视频音频合成工具 - 一键打包
echo ========================================
echo   视频与音轨自动匹配合成工具
echo   一键打包脚本
echo ========================================
echo.
echo 请选择打包版本:
echo.
echo  [推荐] 进度版 (v3.0) - 带实时进度显示
echo  [稳定] 稳定版 (v2.1) - 最稳定，兼容性最好
echo  [功能] 完整版 (v2.0) - 功能最全，带高DPI支持
echo  [调试] 调试版 - 带控制台，用于排查问题
echo  [基础] 基础版 (v1.0) - 最简洁
echo.
echo ========================================
echo.

set /p choice=请输入选项 (1/2/3/4/5): 

if "%choice%"=="1" goto progress
if "%choice%"=="2" goto stable
if "%choice%"=="3" goto full
if "%choice%"=="4" goto debug
if "%choice%"=="5" goto basic
goto end

:progress
echo.
echo 正在打包进度版 (v3.0)...
echo 此版本带实时进度显示，推荐日常使用
echo.
pip install pyinstaller
pyinstaller --name "VideoAudioMerger" --onedir --windowed --noupx ^
    --hidden-import tkinter --hidden-import tkinter.filedialog ^
    --hidden-import tkinter.messagebox --hidden-import tkinter.scrolledtext ^
    --hidden-import tkinter.ttk --hidden-import json --hidden-import subprocess ^
    --hidden-import pathlib --hidden-import difflib --hidden-import concurrent.futures ^
    --hidden-import threading --hidden-import datetime --hidden-import time --hidden-import re ^
    video_audio_merger_gui_v3.py
goto finish

:stable
echo.
echo 正在打包稳定版 (v2.1)...
echo 此版本移除了复杂功能，兼容性最好
echo.
pip install pyinstaller
pyinstaller --name "VideoAudioMerger_Stable" --onedir --windowed --noupx ^
    --hidden-import tkinter --hidden-import tkinter.filedialog ^
    --hidden-import tkinter.messagebox --hidden-import tkinter.scrolledtext ^
    --hidden-import tkinter.ttk --hidden-import json --hidden-import subprocess ^
    --hidden-import pathlib --hidden-import difflib --hidden-import concurrent.futures ^
    --hidden-import threading --hidden-import datetime ^
    video_audio_merger_gui_v2_simple.py
goto finish

:full
echo.
echo 正在打包完整版 (v2.0)...
echo 此版本功能最全，带高DPI屏幕适配
echo.
pip install pyinstaller
pyinstaller --name "VideoAudioMerger_Full" --onedir --windowed --noupx ^
    --hidden-import tkinter --hidden-import tkinter.filedialog ^
    --hidden-import tkinter.messagebox --hidden-import tkinter.scrolledtext ^
    --hidden-import tkinter.ttk --hidden-import json --hidden-import subprocess ^
    --hidden-import pathlib --hidden-import difflib --hidden-import concurrent.futures ^
    --hidden-import threading --hidden-import datetime --hidden-import ctypes ^
    video_audio_merger_gui_v2.py
goto finish

:debug
echo.
echo 正在打包调试版...
echo 此版本带控制台窗口，用于排查闪退问题
echo.
pip install pyinstaller
pyinstaller --name "VideoAudioMerger_Debug" --onedir --console --noupx ^
    --hidden-import tkinter --hidden-import tkinter.filedialog ^
    --hidden-import tkinter.messagebox --hidden-import tkinter.scrolledtext ^
    --hidden-import tkinter.ttk --hidden-import json --hidden-import subprocess ^
    --hidden-import pathlib --hidden-import difflib --hidden-import concurrent.futures ^
    --hidden-import threading --hidden-import datetime ^
    video_audio_merger_gui_debug.py
goto finish

:basic
echo.
echo 正在打包基础版 (v1.0)...
echo.
pip install pyinstaller
pyinstaller --name "VideoAudioMerger_Basic" --onedir --windowed --noupx ^
    --hidden-import tkinter --hidden-import tkinter.filedialog ^
    --hidden-import tkinter.messagebox --hidden-import tkinter.scrolledtext ^
    --hidden-import tkinter.ttk ^
    video_audio_merger_gui.py
goto finish

:finish
echo.
echo ========================================
if exist "dist" (
    echo 打包完成！
    echo 输出目录: dist\
    echo.
    echo 使用说明:
    echo  1. 打开 dist\VideoAudioMerger 文件夹
    echo  2. 运行 VideoAudioMerger.exe
    echo  3. 首次使用需要设置FFmpeg路径
    echo.
    echo 如果闪退，请尝试:
    echo  - 关闭杀毒软件后重试
    echo  - 使用调试版查看错误信息
    echo  - 阅读 故障排查指南.md
) else (
    echo 打包失败，请查看错误信息
)
echo ========================================
pause

:end
