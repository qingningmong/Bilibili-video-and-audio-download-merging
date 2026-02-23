#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包脚本 v2.0 - 解决闪退问题
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path


def install_dependencies():
    """安装必要的依赖"""
    print("正在检查依赖...")
    
    deps = ['pyinstaller', 'pywin32;platform_system=="Windows"']
    for dep in deps:
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', dep], 
                          check=True, capture_output=True)
            print(f"  ✓ {dep}")
        except:
            print(f"  ✗ {dep} 安装失败")


def clean_build():
    """清理之前的构建文件"""
    print("\n清理之前的构建...")
    dirs_to_remove = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_remove:
        if Path(dir_name).exists():
            try:
                shutil.rmtree(dir_name)
                print(f"  已删除 {dir_name}/")
            except:
                pass
    
    # 删除spec文件
    for spec in Path('.').glob('*.spec'):
        try:
            spec.unlink()
            print(f"  已删除 {spec.name}")
        except:
            pass


def create_hook_file():
    """创建PyInstaller钩子文件，确保所有依赖被正确打包"""
    hook_content = '''
# PyInstaller钩子 - 确保tkinter正确打包
import os
import sys

# 确保tkinter被包含
hiddenimports = [
    'tkinter',
    'tkinter.filedialog',
    'tkinter.messagebox',
    'tkinter.scrolledtext',
    'tkinter.ttk',
]

# Windows特定
if sys.platform == 'win32':
    hiddenimports.extend([
        'ctypes',
        'ctypes.wintypes',
    ])
'''
    hook_dir = Path('hooks')
    hook_dir.mkdir(exist_ok=True)
    
    hook_file = hook_dir / 'hook-tkinter.py'
    with open(hook_file, 'w', encoding='utf-8') as f:
        f.write(hook_content)
    
    return str(hook_dir)


def build_exe(version='v2', console=False, onedir=False, debug=False):
    """
    打包exe
    
    Args:
        version: 版本 'v1' 或 'v2'
        console: 是否显示控制台
        onedir: 是否打包成目录（更稳定）
        debug: 是否启用调试模式
    """
    script_name = f'video_audio_merger_gui_{version}.py' if version == 'v2' else 'video_audio_merger_gui.py'
    
    if not Path(script_name).exists():
        print(f"错误: 找不到 {script_name}")
        return False
    
    exe_name = f'VideoAudioMerger_{version}'
    
    # 基础命令
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        script_name,
        '--name', exe_name,
        '--clean',
        '--noconfirm',
    ]
    
    # 打包模式
    if onedir:
        cmd.append('--onedir')
    else:
        cmd.append('--onefile')
    
    # 控制台模式
    if console:
        cmd.append('--console')
    else:
        cmd.append('--windowed')
    
    # 调试模式
    if debug:
        cmd.append('--debug=all')
    
    # 隐藏导入
    hidden_imports = [
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
        'tkinter.ttk',
        'json',
        'subprocess',
        'pathlib',
        'difflib',
        'concurrent.futures',
        'argparse',
        'threading',
        'datetime',
    ]
    
    for imp in hidden_imports:
        cmd.extend(['--hidden-import', imp])
    
    # Windows特定
    if sys.platform == 'win32':
        cmd.extend(['--hidden-import', 'ctypes'])
        # 禁用UPX（有时会导致问题）
        cmd.append('--noupx')
    
    # 添加钩子路径
    hook_dir = create_hook_file()
    cmd.extend(['--additional-hooks-dir', hook_dir])
    
    # 收集所有数据文件
    cmd.extend(['--collect-all', 'tkinter'])
    
    print(f"\n打包命令:")
    print(' '.join(cmd))
    print("\n开始打包，请稍候...")
    print("="*60)
    
    try:
        result = subprocess.run(cmd, check=True)
        print("="*60)
        print("✓ 打包成功!")
        
        # 显示输出路径
        if onedir:
            dist_path = Path('dist') / exe_name
        else:
            dist_path = Path('dist') / f'{exe_name}.exe'
        
        if dist_path.exists():
            print(f"\n输出路径: {dist_path.absolute()}")
            if not onedir:
                size = dist_path.stat().st_size / 1024 / 1024
                print(f"文件大小: {size:.2f} MB")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n✗ 打包失败: {e}")
        return False


def create_debug_version():
    """创建调试版本（带控制台窗口，方便查看错误）"""
    print("\n" + "="*60)
    print("创建调试版本（带控制台，用于排查问题）")
    print("="*60)
    return build_exe(version='v2', console=True, onedir=True, debug=True)


def create_release_version():
    """创建发布版本"""
    print("\n" + "="*60)
    print("创建发布版本")
    print("="*60)
    
    # 推荐使用onedir模式，更稳定
    print("\n推荐选择:")
    print("1. 目录模式（推荐，更稳定，启动更快）")
    print("2. 单文件模式（便携，但启动较慢）")
    
    choice = input("\n请选择 (1/2): ").strip()
    
    onedir = (choice == '1')
    
    return build_exe(version='v2', console=False, onedir=onedir, debug=False)


def test_exe():
    """测试生成的exe"""
    exe_path = Path('dist') / 'VideoAudioMerger_v2.exe'
    if not exe_path.exists():
        exe_path = Path('dist') / 'VideoAudioMerger_v2' / 'VideoAudioMerger_v2.exe'
    
    if exe_path.exists():
        print(f"\n找到exe: {exe_path}")
        print("是否立即测试运行? (y/n): ")
        if input().strip().lower() == 'y':
            print("\n启动exe...")
            try:
                subprocess.Popen([str(exe_path)], cwd=str(exe_path.parent))
                print("exe已启动，请查看是否有窗口弹出")
            except Exception as e:
                print(f"启动失败: {e}")
    else:
        print("未找到exe文件")


def main():
    """主函数"""
    print("="*60)
    print("视频音频合成工具 - 打包脚本 v2.0")
    print("="*60)
    
    print("\n请选择操作:")
    print("1. 创建发布版本（正常使用）")
    print("2. 创建调试版本（带控制台，排查闪退问题）")
    print("3. 清理构建文件")
    print("4. 安装依赖")
    print("5. 全部执行（安装依赖+清理+创建发布版本）")
    print("6. 退出")
    
    choice = input("\n请选择 (1-6): ").strip()
    
    if choice == '1':
        create_release_version()
    elif choice == '2':
        create_debug_version()
    elif choice == '3':
        clean_build()
    elif choice == '4':
        install_dependencies()
    elif choice == '5':
        install_dependencies()
        clean_build()
        create_release_version()
        test_exe()
    elif choice == '6':
        return
    else:
        print("无效选择")
    
    print("\n按回车键退出...")
    input()


if __name__ == '__main__':
    main()
