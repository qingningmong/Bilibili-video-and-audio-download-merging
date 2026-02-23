@echo off
chcp 65001 >nul
title 视频与音轨自动匹配合成工具 - GUI调试版
echo ========================================
echo   视频与音轨自动匹配合成工具
echo   调试版本 - 用于排查问题
echo ========================================
echo.
echo 此版本会显示详细的错误信息
echo 如果程序崩溃，请查看以下信息：
echo  1. 本窗口中的错误输出
echo  2. video_merger_debug.log 日志文件
echo.
echo 按任意键开始运行...
pause >nul
cls
python video_audio_merger_gui_debug.py
echo.
echo ========================================
echo 程序已退出
echo ========================================
pause
