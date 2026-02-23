#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包脚本 - 将video_audio_merger.py打包成Windows可执行文件
"""

import subprocess
import sys
import os
from pathlib import Path


def check_pyinstaller():
    """检查是否安装了PyInstaller"""
    try:
        import PyInstaller
        return True
    except ImportError:
        return False


def install_pyinstaller():
    """安装PyInstaller"""
    print("正在安装 PyInstaller...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], 
                      check=True)
        print("PyInstaller 安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"安装失败: {e}")
        return False


def build_exe(console=True, onefile=True, icon=None):
    """
    打包成exe文件
    
    Args:
        console: 是否显示控制台窗口
        onefile: 是否打包成单个文件
        icon: 图标文件路径
    """
    if not check_pyinstaller():
        if not install_pyinstaller():
            print("无法安装 PyInstaller，请手动安装: pip install pyinstaller")
            return False
    
    script_path = Path(__file__).parent / 'video_audio_merger.py'
    
    if not script_path.exists():
        print(f"找不到主脚本: {script_path}")
        return False
    
    # 构建命令
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        str(script_path),
        '--name', 'VideoAudioMerger',
        '--clean'
    ]
    
    if onefile:
        cmd.append('--onefile')
    else:
        cmd.append('--onedir')
        
    if console:
        cmd.append('--console')
    else:
        cmd.append('--windowed')
        
    if icon and Path(icon).exists():
        cmd.extend(['--icon', icon])
    
    # 添加隐藏导入
    cmd.extend([
        '--hidden-import', 'json',
        '--hidden-import', 'subprocess',
        '--hidden-import', 'pathlib',
        '--hidden-import', 'difflib',
        '--hidden-import', 'concurrent.futures',
        '--hidden-import', 'argparse'
    ])
    
    print("开始打包...")
    print(f"命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True)
        print("\n" + "="*60)
        print("打包成功!")
        print("="*60)
        
        # 显示输出路径
        dist_path = Path(__file__).parent / 'dist' / 'VideoAudioMerger.exe'
        if dist_path.exists():
            print(f"可执行文件: {dist_path}")
            print(f"文件大小: {dist_path.stat().st_size / 1024 / 1024:.2f} MB")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"打包失败: {e}")
        return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='打包视频音频合成工具')
    parser.add_argument('--window', action='store_true',
                       help='使用窗口模式（不显示控制台）')
    parser.add_argument('--dir', action='store_true',
                       help='打包成目录（非单文件）')
    parser.add_argument('--icon', help='指定图标文件(.ico)')
    
    args = parser.parse_args()
    
    print("="*60)
    print("视频音频合成工具 - 打包脚本")
    print("="*60)
    
    success = build_exe(
        console=not args.window,
        onefile=not args.dir,
        icon=args.icon
    )
    
    if success:
        print("\n提示:")
        print("  - 生成的exe文件在 dist/ 目录中")
        print("  - 可以将exe文件复制到任意位置使用")
        print("  - 首次运行时会提示设置FFmpeg路径")
    else:
        print("\n打包失败，请检查错误信息")
        
    input("\n按回车键退出...")


if __name__ == '__main__':
    main()
