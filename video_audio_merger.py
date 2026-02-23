#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频与音轨自动匹配合成工具
支持自动匹配同名的视频(.mp4)和音频(.m4a)文件，使用FFmpeg进行合成
"""

import os
import sys
import json
import subprocess
import re
from pathlib import Path
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor, as_completed


class VideoAudioMerger:
    """视频音频自动匹配合成器"""
    
    # 支持的文件格式
    VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
    AUDIO_EXTENSIONS = {'.m4a', '.mp3', '.aac', '.wav', '.flac', '.ogg', '.wma', '.mka'}
    
    def __init__(self, ffmpeg_path=None):
        """
        初始化合成器
        
        Args:
            ffmpeg_path: FFmpeg可执行文件路径，如果为None则尝试从环境变量或配置文件读取
        """
        self.ffmpeg_path = self._get_ffmpeg_path(ffmpeg_path)
        self.config_file = Path.home() / '.video_audio_merger.json'
        self.matches = []  # 存储匹配的文件对
        
    def _get_ffmpeg_path(self, provided_path=None):
        """获取FFmpeg路径"""
        # 1. 优先使用提供的路径
        if provided_path and Path(provided_path).exists():
            return str(Path(provided_path).resolve())
            
        # 2. 尝试从配置文件读取
        if self._load_config().get('ffmpeg_path'):
            saved_path = self._load_config()['ffmpeg_path']
            if Path(saved_path).exists():
                return saved_path
                
        # 3. 尝试从系统PATH查找
        ffmpeg_in_path = self._find_in_path('ffmpeg.exe' if sys.platform == 'win32' else 'ffmpeg')
        if ffmpeg_in_path:
            return ffmpeg_in_path
            
        # 4. 尝试常见安装路径
        common_paths = self._get_common_ffmpeg_paths()
        for path in common_paths:
            if Path(path).exists():
                return path
                
        return None
        
    def _get_common_ffmpeg_paths(self):
        """获取常见的FFmpeg安装路径"""
        paths = []
        if sys.platform == 'win32':
            # Windows常见路径
            program_files = os.environ.get('ProgramFiles', 'C:\\Program Files')
            program_files_x86 = os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')
            paths.extend([
                os.path.join(program_files, 'FFmpeg', 'bin', 'ffmpeg.exe'),
                os.path.join(program_files_x86, 'FFmpeg', 'bin', 'ffmpeg.exe'),
                'C:\\ffmpeg\\bin\\ffmpeg.exe',
                'D:\\ffmpeg\\bin\\ffmpeg.exe',
                os.path.expanduser('~\\ffmpeg\\bin\\ffmpeg.exe'),
            ])
        else:
            # Linux/Mac常见路径
            paths.extend([
                '/usr/bin/ffmpeg',
                '/usr/local/bin/ffmpeg',
                '/opt/homebrew/bin/ffmpeg',
                '/opt/ffmpeg/bin/ffmpeg',
                os.path.expanduser('~/.local/bin/ffmpeg'),
            ])
        return paths
        
    def _find_in_path(self, executable):
        """在系统PATH中查找可执行文件"""
        for path in os.environ.get('PATH', '').split(os.pathsep):
            full_path = os.path.join(path, executable)
            if Path(full_path).exists():
                return full_path
        return None
        
    def _load_config(self):
        """加载配置文件"""
        if Path(self.config_file).exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
        
    def save_config(self):
        """保存配置到文件"""
        config = {'ffmpeg_path': self.ffmpeg_path}
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False
            
    def set_ffmpeg_path(self, path):
        """设置FFmpeg路径"""
        if Path(path).exists():
            self.ffmpeg_path = str(Path(path).resolve())
            self.save_config()
            return True
        return False
        
    def verify_ffmpeg(self):
        """验证FFmpeg是否可用"""
        if not self.ffmpeg_path:
            return False, "FFmpeg路径未设置"
        if not Path(self.ffmpeg_path).exists():
            return False, f"FFmpeg不存在: {self.ffmpeg_path}"
            
        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                return True, version_line
            return False, "FFmpeg无法正常运行"
        except Exception as e:
            return False, f"验证FFmpeg失败: {e}"
            
    def scan_directory(self, directory, recursive=True):
        """
        扫描目录，查找视频和音频文件
        
        Args:
            directory: 要扫描的目录
            recursive: 是否递归扫描子目录
            
        Returns:
            tuple: (视频文件列表, 音频文件列表)
        """
        video_files = []
        audio_files = []
        
        dir_path = Path(directory)
        if not dir_path.exists():
            return [], []
            
        pattern = '**/*' if recursive else '*'
        
        for file_path in dir_path.glob(pattern):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext in self.VIDEO_EXTENSIONS:
                    video_files.append(file_path)
                elif ext in self.AUDIO_EXTENSIONS:
                    audio_files.append(file_path)
                    
        return video_files, audio_files
        
    def similarity(self, a, b):
        """计算两个字符串的相似度"""
        return SequenceMatcher(None, a, b).ratio()
        
    def match_files(self, video_files, audio_files, similarity_threshold=0.8):
        """
        匹配视频和音频文件
        
        匹配规则（按优先级）：
        1. 完全相同的文件名（不含扩展名）
        2. 文件名相似度达到阈值
        
        Args:
            video_files: 视频文件列表
            audio_files: 音频文件列表
            similarity_threshold: 相似度阈值
            
        Returns:
            list: 匹配的文件对列表 [(video_path, audio_path, match_type), ...]
        """
        matches = []
        matched_audio = set()
        
        # 第一步：完全匹配
        audio_dict = {}
        for audio in audio_files:
            stem = audio.stem
            if stem not in audio_dict:
                audio_dict[stem] = []
            audio_dict[stem].append(audio)
            
        for video in video_files:
            video_stem = video.stem
            if video_stem in audio_dict:
                for audio in audio_dict[video_stem]:
                    if str(audio) not in matched_audio:
                        matches.append({
                            'video': video,
                            'audio': audio,
                            'match_type': 'exact',
                            'similarity': 1.0
                        })
                        matched_audio.add(str(audio))
                        break
                        
        # 第二步：相似度匹配（对于未匹配的视频）
        unmatched_videos = [v for v in video_files if not any(m['video'] == v for m in matches)]
        unmatched_audios = [a for a in audio_files if str(a) not in matched_audio]
        
        for video in unmatched_videos:
            video_stem = video.stem
            best_match = None
            best_score = 0
            
            for audio in unmatched_audios:
                audio_stem = audio.stem
                score = self.similarity(video_stem, audio_stem)
                if score > best_score and score >= similarity_threshold:
                    best_score = score
                    best_match = audio
                    
            if best_match:
                matches.append({
                    'video': video,
                    'audio': best_match,
                    'match_type': 'similar',
                    'similarity': best_score
                })
                unmatched_audios.remove(best_match)
                
        self.matches = matches
        return matches
        
    def merge_file(self, match_info, output_dir=None, output_suffix='_merged', 
                   video_codec='copy', audio_codec='aac', overwrite=False):
        """
        合成单个视频和音频文件
        
        Args:
            match_info: 匹配信息字典
            output_dir: 输出目录，默认为视频所在目录
            output_suffix: 输出文件名后缀
            video_codec: 视频编码，'copy'表示直接复制
            audio_codec: 音频编码
            overwrite: 是否覆盖已存在的文件
            
        Returns:
            tuple: (success, message)
        """
        video = match_info['video']
        audio = match_info['audio']
        
        # 确定输出路径
        if output_dir:
            output_path = Path(output_dir) / f"{video.stem}{output_suffix}{video.suffix}"
        else:
            output_path = video.parent / f"{video.stem}{output_suffix}{video.suffix}"
            
        # 检查输出文件
        if output_path.exists() and not overwrite:
            return False, f"输出文件已存在: {output_path}"
            
        # 构建FFmpeg命令
        cmd = [
            self.ffmpeg_path,
            '-i', str(video),
            '-i', str(audio),
            '-c:v', video_codec,
            '-c:a', audio_codec,
            '-map', '0:v:0',  # 使用第一个输入的视频
            '-map', '1:a:0',  # 使用第二个输入的音频
            '-shortest',      # 以较短的为准
            '-y' if overwrite else '-n',
            str(output_path)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            if result.returncode == 0:
                return True, str(output_path)
            else:
                error_msg = result.stderr[-500:] if result.stderr else "未知错误"
                return False, f"FFmpeg错误: {error_msg}"
                
        except Exception as e:
            return False, f"执行失败: {e}"
            
    def merge_all(self, output_dir=None, output_suffix='_merged', 
                  video_codec='copy', audio_codec='aac', 
                  overwrite=False, max_workers=2):
        """
        合成所有匹配的文件对
        
        Args:
            output_dir: 输出目录
            output_suffix: 输出文件名后缀
            video_codec: 视频编码
            audio_codec: 音频编码
            overwrite: 是否覆盖
            max_workers: 最大并行数
            
        Returns:
            list: 结果列表 [(success, message), ...]
        """
        if not self.matches:
            return []
            
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_match = {
                executor.submit(
                    self.merge_file, 
                    match, 
                    output_dir, 
                    output_suffix,
                    video_codec,
                    audio_codec,
                    overwrite
                ): match for match in self.matches
            }
            
            for future in as_completed(future_to_match):
                match = future_to_match[future]
                try:
                    success, message = future.result()
                    results.append({
                        'video': match['video'],
                        'audio': match['audio'],
                        'success': success,
                        'message': message
                    })
                    
                    status = "✓" if success else "✗"
                    print(f"{status} {match['video'].name} + {match['audio'].name}")
                    if not success:
                        print(f"  错误: {message}")
                        
                except Exception as e:
                    results.append({
                        'video': match['video'],
                        'audio': match['audio'],
                        'success': False,
                        'message': str(e)
                    })
                    print(f"✗ {match['video'].name}: {e}")
                    
        return results
        
    def get_statistics(self):
        """获取匹配统计信息"""
        if not self.matches:
            return "未找到匹配的文件"
            
        exact_matches = sum(1 for m in self.matches if m['match_type'] == 'exact')
        similar_matches = sum(1 for m in self.matches if m['match_type'] == 'similar')
        
        stats = f"""
匹配统计:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
总匹配数: {len(self.matches)}
  - 完全匹配: {exact_matches}
  - 相似匹配: {similar_matches}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return stats
        
    def preview_matches(self):
        """预览匹配结果"""
        if not self.matches:
            print("未找到匹配的文件")
            return
            
        print("\n匹配结果预览:")
        print("=" * 80)
        
        for i, match in enumerate(self.matches, 1):
            match_type_str = "[完全匹配]" if match['match_type'] == 'exact' else f"[相似 {match['similarity']:.1%}]"
            print(f"\n{i}. {match_type_str}")
            print(f"   视频: {match['video']}")
            print(f"   音频: {match['audio']}")
            
        print("\n" + "=" * 80)


def interactive_mode():
    """交互式模式"""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║           视频与音轨自动匹配合成工具 v1.0                         ║
╚══════════════════════════════════════════════════════════════════╝
""")
    
    merger = VideoAudioMerger()
    
    # 检查FFmpeg
    while True:
        success, msg = merger.verify_ffmpeg()
        if success:
            print(f"FFmpeg已就绪: {msg}")
            break
        else:
            print(f"\n⚠ {msg}")
            print("请输入FFmpeg可执行文件的路径 (ffmpeg.exe):")
            ffmpeg_path = input("> ").strip().strip('"')
            if ffmpeg_path:
                if merger.set_ffmpeg_path(ffmpeg_path):
                    print("FFmpeg路径已设置")
                else:
                    print("路径无效，请重新输入")
                    
    # 选择工作目录
    print("\n请输入要扫描的目录路径 (直接回车使用当前目录):")
    directory = input("> ").strip().strip('"')
    if not directory:
        directory = os.getcwd()
        
    if not Path(directory).exists():
        print(f"目录不存在: {directory}")
        return
        
    # 扫描文件
    print(f"\n正在扫描目录: {directory}")
    video_files, audio_files = merger.scan_directory(directory)
    
    print(f"找到 {len(video_files)} 个视频文件, {len(audio_files)} 个音频文件")
    
    if not video_files or not audio_files:
        print("需要同时存在视频和音频文件才能进行匹配")
        return
        
    # 匹配文件
    print("\n正在匹配文件...")
    matches = merger.match_files(video_files, audio_files)
    
    if not matches:
        print("未找到匹配的文件对")
        return
        
    print(merger.get_statistics())
    merger.preview_matches()
    
    # 确认合成
    print("\n是否开始合成? (y/n):")
    confirm = input("> ").strip().lower()
    if confirm != 'y':
        print("已取消")
        return
        
    # 输出选项
    print("\n输出选项:")
    print("  1. 输出到原目录")
    print("  2. 指定输出目录")
    output_choice = input("请选择 (1/2): ").strip()
    
    output_dir = None
    if output_choice == '2':
        print("请输入输出目录:")
        output_dir = input("> ").strip().strip('"')
        if not Path(output_dir).exists():
            try:
                Path(output_dir).mkdir(parents=True, exist_ok=True)
            except:
                print("无法创建输出目录，将使用原目录")
                output_dir = None
                
    print("\n请输入输出文件名后缀 (直接回车使用默认 '_merged'):")
    suffix = input("> ").strip()
    output_suffix = suffix if suffix else '_merged'
    
    # 开始合成
    print("\n开始合成...")
    results = merger.merge_all(
        output_dir=output_dir,
        output_suffix=output_suffix,
        overwrite=False,
        max_workers=2
    )
    
    # 统计结果
    success_count = sum(1 for r in results if r['success'])
    print(f"\n合成完成: {success_count}/{len(results)} 成功")
    
    # 保存配置
    merger.save_config()
    print("\n配置已保存，下次启动将自动使用FFmpeg路径")
    
    print("\n按回车键退出...")
    input()


def quick_merge(directory, ffmpeg_path=None, output_dir=None, suffix='_merged'):
    """快速合成模式 - 一键处理"""
    merger = VideoAudioMerger(ffmpeg_path)
    
    success, msg = merger.verify_ffmpeg()
    if not success:
        print(f"FFmpeg错误: {msg}")
        return False
        
    video_files, audio_files = merger.scan_directory(directory)
    matches = merger.match_files(video_files, audio_files)
    
    if not matches:
        print("未找到匹配的文件")
        return False
        
    print(f"找到 {len(matches)} 对匹配文件")
    results = merger.merge_all(
        output_dir=output_dir,
        output_suffix=suffix,
        overwrite=False,
        max_workers=2
    )
    
    success_count = sum(1 for r in results if r['success'])
    print(f"完成: {success_count}/{len(results)} 成功")
    return success_count == len(results)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='视频与音轨自动匹配合成工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 交互式模式
  python video_audio_merger.py
  
  # 快速模式 - 处理当前目录
  python video_audio_merger.py -d ./videos
  
  # 指定FFmpeg路径
  python video_audio_merger.py -d ./videos --ffmpeg "C:\\ffmpeg\\bin\\ffmpeg.exe"
  
  # 指定输出目录
  python video_audio_merger.py -d ./videos -o ./output
        """
    )
    
    parser.add_argument('-d', '--directory', 
                        help='要扫描的目录 (默认: 当前目录)')
    parser.add_argument('--ffmpeg', 
                        help='FFmpeg可执行文件路径')
    parser.add_argument('-o', '--output', 
                        help='输出目录 (默认: 原目录)')
    parser.add_argument('-s', '--suffix', default='_merged',
                        help='输出文件名后缀 (默认: _merged)')
    parser.add_argument('--set-ffmpeg',
                        help='设置默认FFmpeg路径并退出')
    
    args = parser.parse_args()
    
    # 设置默认FFmpeg路径
    if args.set_ffmpeg:
        merger = VideoAudioMerger()
        if merger.set_ffmpeg_path(args.set_ffmpeg):
            print(f"FFmpeg路径已设置为: {args.ffmpeg_path}")
        else:
            print("路径无效")
        sys.exit(0)
        
    # 交互式模式
    if len(sys.argv) == 1:
        interactive_mode()
    else:
        # 命令行模式
        directory = args.directory or os.getcwd()
        quick_merge(
            directory=directory,
            ffmpeg_path=args.ffmpeg,
            output_dir=args.output,
            suffix=args.suffix
        )
