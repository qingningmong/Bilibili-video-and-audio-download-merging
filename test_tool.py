#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本 - 验证视频音频合成工具的安装和配置
"""

import os
import sys
import subprocess
from pathlib import Path


def test_python_version():
    """测试Python版本"""
    print("[1/4] 检查Python版本...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 7:
        print(f"  ✓ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"  ✗ Python版本过低: {version.major}.{version.minor}.{version.micro}")
        print("  需要 Python 3.7 或更高版本")
        return False


def test_ffmpeg():
    """测试FFmpeg"""
    print("\n[2/4] 检查FFmpeg...")
    
    # 尝试从配置读取
    config_file = Path.home() / '.video_audio_merger.json'
    ffmpeg_path = None
    
    if config_file.exists():
        import json
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                ffmpeg_path = config.get('ffmpeg_path')
        except:
            pass
    
    # 尝试从PATH查找
    if not ffmpeg_path:
        for path in os.environ.get('PATH', '').split(os.pathsep):
            exe = 'ffmpeg.exe' if sys.platform == 'win32' else 'ffmpeg'
            full_path = os.path.join(path, exe)
            if Path(full_path).exists():
                ffmpeg_path = full_path
                break
    
    # 尝试常见路径
    if not ffmpeg_path and sys.platform == 'win32':
        common_paths = [
            'C:\\ffmpeg\\bin\\ffmpeg.exe',
            'D:\\ffmpeg\\bin\\ffmpeg.exe',
        ]
        for path in common_paths:
            if Path(path).exists():
                ffmpeg_path = path
                break
    
    if not ffmpeg_path:
        print("  ✗ 未找到FFmpeg")
        print("  请下载并安装FFmpeg: https://ffmpeg.org/download.html")
        print("  或使用 --set-ffmpeg 参数设置路径")
        return False
    
    try:
        result = subprocess.run(
            [ffmpeg_path, '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"  ✓ {version_line}")
            print(f"  路径: {ffmpeg_path}")
            return True
        else:
            print(f"  ✗ FFmpeg无法正常运行")
            return False
    except Exception as e:
        print(f"  ✗ 验证FFmpeg失败: {e}")
        return False


def test_modules():
    """测试必要的模块"""
    print("\n[3/4] 检查Python模块...")
    
    required = [
        'tkinter',
        'json',
        'subprocess',
        'pathlib',
        'difflib',
        'concurrent.futures',
        'argparse',
        'threading'
    ]
    
    all_ok = True
    for module in required:
        try:
            __import__(module)
            print(f"  ✓ {module}")
        except ImportError:
            print(f"  ✗ {module} (缺失)")
            all_ok = False
    
    # 检查PyInstaller（可选）
    try:
        import PyInstaller
        print(f"  ✓ PyInstaller (已安装，可用于打包)")
    except ImportError:
        print(f"  - PyInstaller (未安装，运行 'pip install pyinstaller' 安装)")
    
    return all_ok


def test_files():
    """测试必要的文件"""
    print("\n[4/4] 检查工具文件...")
    
    files = {
        'video_audio_merger.py': '主程序（命令行/交互式）',
        'video_audio_merger_gui.py': 'GUI版本',
        'build_exe.py': '打包脚本',
    }
    
    all_ok = True
    for file, desc in files.items():
        if Path(file).exists():
            print(f"  ✓ {file} ({desc})")
        else:
            print(f"  ✗ {file} 不存在")
            all_ok = False
    
    return all_ok


def main():
    """主函数"""
    print("="*60)
    print("视频与音轨自动匹配合成工具 - 环境测试")
    print("="*60)
    print()
    
    results = []
    results.append(test_python_version())
    results.append(test_ffmpeg())
    results.append(test_modules())
    results.append(test_files())
    
    print("\n" + "="*60)
    if all(results):
        print("✓ 所有检查通过！工具可以正常使用。")
        print()
        print("使用方法:")
        print("  交互模式: python video_audio_merger.py")
        print("  GUI模式:  python video_audio_merger_gui.py")
        print("  打包exe:  python build_exe.py")
    else:
        print("✗ 部分检查未通过，请根据提示修复问题。")
    print("="*60)
    
    input("\n按回车键退出...")


if __name__ == '__main__':
    main()
