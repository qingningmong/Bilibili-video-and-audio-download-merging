#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频与音轨自动匹配合成工具 - GUI版本 v3.0
支持实时进度显示、每个视频的合成百分比
"""

import os
import sys
import json
import subprocess
import threading
import re
import time
from pathlib import Path
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, scrolledtext
except ImportError:
    print("错误: 无法导入tkinter模块")
    sys.exit(1)


class FFmpegProgress:
    """FFmpeg进度解析器"""
    
    def __init__(self):
        self.duration = 0  # 视频总时长（秒）
        self.current_time = 0  # 当前处理时间（秒）
        self.frame = 0
        self.fps = 0
        self.bitrate = 0
        self.speed = 0
        self.percentage = 0
        
    def parse_duration(self, line):
        """从FFmpeg输出解析视频时长"""
        # Duration: 00:05:30.50
        match = re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)', line)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = float(match.group(3))
            self.duration = hours * 3600 + minutes * 60 + seconds
            return True
        return False
        
    def parse_progress(self, line):
        """解析进度信息"""
        # frame=  500 fps=120 q=-1.0 size=    5000kB time=00:00:20.50 bitrate=...
        updated = False
        
        # 解析时间
        time_match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
        if time_match:
            hours = int(time_match.group(1))
            minutes = int(time_match.group(2))
            seconds = float(time_match.group(3))
            self.current_time = hours * 3600 + minutes * 60 + seconds
            updated = True
            
        # 解析帧数
        frame_match = re.search(r'frame=\s*(\d+)', line)
        if frame_match:
            self.frame = int(frame_match.group(1))
            
        # 解析fps
        fps_match = re.search(r'fps=\s*(\d+)', line)
        if fps_match:
            self.fps = int(fps_match.group(1))
            
        # 解析速度
        speed_match = re.search(r'speed=\s*([\d.]+)x', line)
        if speed_match:
            self.speed = float(speed_match.group(1))
            
        # 计算百分比
        if self.duration > 0 and self.current_time > 0:
            self.percentage = min(100, (self.current_time / self.duration) * 100)
            
        return updated
        
    def get_progress_text(self):
        """获取进度文本"""
        if self.duration > 0:
            current_str = str(timedelta(seconds=int(self.current_time)))
            duration_str = str(timedelta(seconds=int(self.duration)))
            return f"{self.percentage:.1f}% ({current_str}/{duration_str})"
        elif self.frame > 0:
            return f"已处理 {self.frame} 帧"
        else:
            return "处理中..."


class VideoAudioMergerGUI:
    """视频音频合成工具 - 带进度显示"""
    
    VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
    AUDIO_EXTENSIONS = {'.m4a', '.mp3', '.aac', '.wav', '.flac', '.ogg', '.wma', '.mka'}
    
    def __init__(self, root):
        self.root = root
        self.root.title("视频与音轨自动匹配合成工具 v3.0")
        self.root.geometry("1000x800")
        self.root.minsize(900, 700)
        
        # 初始化变量
        self.ffmpeg_path = tk.StringVar()
        self.source_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.output_suffix = tk.StringVar(value='_merged')
        self.use_source_as_output = tk.BooleanVar(value=True)
        self.show_detailed_progress = tk.BooleanVar(value=True)
        
        self.matches = []
        self.is_running = False
        self.current_progress = {}  # 存储每个文件的进度
        self.progress_lock = threading.Lock()
        
        # 配置文件
        self.config_file = Path.home() / '.video_audio_merger_v3.json'
        self.load_config()
        
        # 创建界面
        self.create_widgets()
        
    def load_config(self):
        """加载配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.ffmpeg_path.set(config.get('ffmpeg_path', ''))
                    self.source_dir.set(config.get('source_dir', ''))
                    self.output_dir.set(config.get('output_dir', ''))
                    self.output_suffix.set(config.get('output_suffix', '_merged'))
                    self.show_detailed_progress.set(config.get('show_detailed_progress', True))
        except:
            pass
                
    def save_config(self):
        """保存配置"""
        try:
            config = {
                'ffmpeg_path': self.ffmpeg_path.get(),
                'source_dir': self.source_dir.get(),
                'output_dir': self.output_dir.get(),
                'output_suffix': self.output_suffix.get(),
                'show_detailed_progress': self.show_detailed_progress.get(),
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except:
            pass
            
    def create_widgets(self):
        """创建界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="视频与音轨自动匹配合成工具 v3.0", 
                               font=('Microsoft YaHei', 14, 'bold'))
        title_label.pack(pady=(0, 5))
        
        subtitle = ttk.Label(main_frame, text="支持实时进度显示", foreground="gray")
        subtitle.pack(pady=(0, 10))
        
        # ===== FFmpeg设置 =====
        ffmpeg_frame = ttk.LabelFrame(main_frame, text=" FFmpeg 设置 ", padding="10")
        ffmpeg_frame.pack(fill=tk.X, pady=5)
        
        ffmpeg_inner = ttk.Frame(ffmpeg_frame)
        ffmpeg_inner.pack(fill=tk.X)
        ffmpeg_inner.columnconfigure(1, weight=1)
        
        ttk.Label(ffmpeg_inner, text="FFmpeg 路径:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        ttk.Entry(ffmpeg_inner, textvariable=self.ffmpeg_path).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        
        btn_frame = ttk.Frame(ffmpeg_inner)
        btn_frame.grid(row=0, column=2, padx=5)
        ttk.Button(btn_frame, text="浏览...", command=self.browse_ffmpeg, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="自动查找", command=self.auto_find_ffmpeg, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="验证", command=self.verify_ffmpeg, width=8).pack(side=tk.LEFT, padx=2)
        
        self.ffmpeg_status = ttk.Label(ffmpeg_inner, text="状态: 未验证", foreground="red")
        self.ffmpeg_status.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))
        
        # ===== 目录设置 =====
        dir_frame = ttk.LabelFrame(main_frame, text=" 目录设置 ", padding="10")
        dir_frame.pack(fill=tk.X, pady=5)
        
        # 源目录
        source_frame = ttk.Frame(dir_frame)
        source_frame.pack(fill=tk.X, pady=2)
        source_frame.columnconfigure(1, weight=1)
        
        ttk.Label(source_frame, text="源目录:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        ttk.Entry(source_frame, textvariable=self.source_dir).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        
        source_btn_frame = ttk.Frame(source_frame)
        source_btn_frame.grid(row=0, column=2, padx=5)
        ttk.Button(source_btn_frame, text="浏览...", command=self.browse_source_dir, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(source_btn_frame, text="自动检测", command=self.auto_detect_source, width=8).pack(side=tk.LEFT, padx=2)
        
        # 输出目录
        output_frame = ttk.Frame(dir_frame)
        output_frame.pack(fill=tk.X, pady=(10, 2))
        output_frame.columnconfigure(1, weight=1)
        
        ttk.Label(output_frame, text="输出目录:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.output_entry = ttk.Entry(output_frame, textvariable=self.output_dir)
        self.output_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(output_frame, text="浏览...", command=self.browse_output_dir, width=8).grid(row=0, column=2, padx=5)
        
        # 输出选项
        options_frame = ttk.Frame(dir_frame)
        options_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Checkbutton(options_frame, text="输出到原目录", 
                       variable=self.use_source_as_output,
                       command=self.toggle_output).pack(side=tk.LEFT)
        
        ttk.Checkbutton(options_frame, text="显示详细进度", 
                       variable=self.show_detailed_progress).pack(side=tk.LEFT, padx=(20, 0))
        
        # ===== 选项设置 =====
        options_frame = ttk.LabelFrame(main_frame, text=" 选项设置 ", padding="10")
        options_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(options_frame, text="输出后缀:").pack(side=tk.LEFT)
        ttk.Entry(options_frame, textvariable=self.output_suffix, width=15).pack(side=tk.LEFT, padx=5)
        
        # ===== 操作按钮 =====
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.scan_btn = ttk.Button(button_frame, text="扫描文件", command=self.scan_files, width=12)
        self.scan_btn.pack(side=tk.LEFT, padx=5)
        
        self.preview_btn = ttk.Button(button_frame, text="预览匹配", command=self.preview_matches, 
                                     width=12, state=tk.DISABLED)
        self.preview_btn.pack(side=tk.LEFT, padx=5)
        
        self.merge_btn = ttk.Button(button_frame, text="开始合成", command=self.start_merge, 
                                   width=12, state=tk.DISABLED)
        self.merge_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="停止", command=self.stop_merge, 
                                  width=12, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # ===== 进度显示区域 =====
        progress_frame = ttk.LabelFrame(main_frame, text=" 合成进度 ", padding="5")
        progress_frame.pack(fill=tk.X, pady=5)
        
        # 总进度
        self.total_progress_label = ttk.Label(progress_frame, text="总进度: 0/0")
        self.total_progress_label.pack(anchor=tk.W)
        
        self.total_progress_bar = ttk.Progressbar(progress_frame, mode='determinate', length=400)
        self.total_progress_bar.pack(fill=tk.X, pady=5)
        
        # 当前文件进度
        self.current_file_label = ttk.Label(progress_frame, text="当前: 等待开始...")
        self.current_file_label.pack(anchor=tk.W)
        
        self.current_progress_bar = ttk.Progressbar(progress_frame, mode='determinate', length=400)
        self.current_progress_bar.pack(fill=tk.X, pady=5)
        
        # 详细进度列表
        self.detail_frame = ttk.Frame(progress_frame)
        self.detail_frame.pack(fill=tk.X, pady=5)
        
        # 创建进度标签字典
        self.progress_labels = {}
        
        # ===== 日志区域 =====
        log_frame = ttk.LabelFrame(main_frame, text=" 日志 ", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=10, font=('Consolas', 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 状态栏
        self.status_label = ttk.Label(main_frame, text="就绪")
        self.status_label.pack(anchor=tk.W, pady=(5, 0))
        
        # 初始状态
        self.toggle_output()
        
        # 关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 启动进度更新定时器
        self.update_progress_ui()
        
    def update_progress_ui(self):
        """定时更新进度UI"""
        if self.is_running and self.show_detailed_progress.get():
            self.refresh_progress_display()
        self.root.after(500, self.update_progress_ui)  # 每500ms更新一次
        
    def refresh_progress_display(self):
        """刷新进度显示"""
        with self.progress_lock:
            for filename, info in self.current_progress.items():
                if filename in self.progress_labels:
                    label, progress_var = self.progress_labels[filename]
                    progress_text = info.get('text', '处理中...')
                    percentage = info.get('percentage', 0)
                    label.config(text=f"{filename}: {progress_text}")
                    progress_var.set(percentage)
                    
    def toggle_output(self):
        """切换输出模式"""
        if self.use_source_as_output.get():
            self.output_entry.config(state='disabled')
        else:
            self.output_entry.config(state='normal')
        
    def browse_ffmpeg(self):
        """浏览选择FFmpeg"""
        filetypes = [('可执行文件', '*.exe')] if sys.platform == 'win32' else [('所有文件', '*.*')]
        path = filedialog.askopenfilename(title="选择 FFmpeg", filetypes=filetypes)
        if path:
            self.ffmpeg_path.set(path)
            self.verify_ffmpeg()
            
    def auto_find_ffmpeg(self):
        """自动查找FFmpeg"""
        self.log("正在自动查找FFmpeg...")
        
        common_paths = []
        if sys.platform == 'win32':
            common_paths = [
                Path('C:/ffmpeg/bin/ffmpeg.exe'),
                Path('D:/ffmpeg/bin/ffmpeg.exe'),
                Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'FFmpeg' / 'bin' / 'ffmpeg.exe',
            ]
        else:
            common_paths = [
                Path('/usr/bin/ffmpeg'),
                Path('/usr/local/bin/ffmpeg'),
            ]
        
        for path in os.environ.get('PATH', '').split(os.pathsep):
            exe = 'ffmpeg.exe' if sys.platform == 'win32' else 'ffmpeg'
            common_paths.append(Path(path) / exe)
        
        for path in common_paths:
            if path.exists():
                self.ffmpeg_path.set(str(path))
                if self.verify_ffmpeg():
                    self.log(f"✓ 找到FFmpeg: {path}")
                    return
                    
        self.log("✗ 未找到FFmpeg，请手动指定")
        messagebox.showwarning("未找到", "未找到FFmpeg，请手动指定路径")
            
    def browse_source_dir(self):
        """浏览选择源目录"""
        path = filedialog.askdirectory(title="选择源目录")
        if path:
            self.source_dir.set(path)
            
    def auto_detect_source(self):
        """自动检测源目录"""
        self.log("正在自动检测源目录...")
        
        # 常用目录
        home = Path.home()
        candidates = []
        
        if sys.platform == 'win32':
            common_paths = [
                home / 'Downloads',
                home / '下载',
                home / 'Desktop',
                home / '桌面',
                home / 'Videos',
                home / '视频',
                Path('D:/下载'),
                Path('D:/Downloads'),
                Path('E:/下载'),
                Path('E:/Downloads'),
            ]
        else:
            common_paths = [
                home / 'Downloads',
                home / 'Desktop',
                home / 'Videos',
            ]
        
        # 扫描每个目录
        for folder in common_paths:
            if folder.exists():
                video_count = 0
                audio_count = 0
                try:
                    for file_path in folder.rglob('*'):
                        if file_path.is_file():
                            ext = file_path.suffix.lower()
                            if ext in self.VIDEO_EXTENSIONS:
                                video_count += 1
                            elif ext in self.AUDIO_EXTENSIONS:
                                audio_count += 1
                        if video_count + audio_count > 1000:  # 限制扫描数量
                            break
                except:
                    pass
                
                score = video_count + audio_count
                if video_count > 0 and audio_count > 0:
                    score += 100  # 优先推荐同时有视频和音频的目录
                candidates.append((folder, video_count, audio_count, score))
        
        # 按分数排序
        candidates.sort(key=lambda x: x[3], reverse=True)
        
        if candidates and candidates[0][3] > 0:
            best_folder = candidates[0][0]
            video_count, audio_count = candidates[0][1], candidates[0][2]
            self.source_dir.set(str(best_folder))
            self.log(f"✓ 自动选择: {best_folder}")
            self.log(f"  视频: {video_count}, 音频: {audio_count}")
        else:
            self.log("✗ 未检测到包含媒体文件的目录")
            messagebox.showinfo("提示", "未自动检测到包含视频/音频的文件夹，请手动选择。")
            
    def browse_output_dir(self):
        """浏览选择输出目录"""
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            self.output_dir.set(path)
            
    def verify_ffmpeg(self):
        """验证FFmpeg"""
        path = self.ffmpeg_path.get()
        if not path or not Path(path).exists():
            self.ffmpeg_status.config(text="状态: FFmpeg 路径无效", foreground="red")
            return False
            
        try:
            result = subprocess.run([path, '-version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version = result.stdout.split('\n')[0]
                self.ffmpeg_status.config(text=f"✓ {version[:50]}...", foreground="green")
                self.save_config()
                return True
            else:
                self.ffmpeg_status.config(text="状态: FFmpeg 无法运行", foreground="red")
                return False
        except Exception as e:
            self.ffmpeg_status.config(text=f"状态: 验证失败", foreground="red")
            return False
            
    def log(self, message):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def scan_files(self):
        """扫描文件"""
        directory = self.source_dir.get()
        if not directory:
            messagebox.showwarning("警告", "请先选择源目录")
            return
            
        if not Path(directory).exists():
            messagebox.showerror("错误", "源目录不存在")
            return
            
        self.log(f"正在扫描: {directory}")
        self.status_label.config(text="正在扫描...")
        
        # 清空之前的进度显示
        for widget in self.detail_frame.winfo_children():
            widget.destroy()
        self.progress_labels.clear()
        
        # 扫描文件
        video_files = []
        audio_files = []
        
        try:
            for file_path in Path(directory).rglob('*'):
                if file_path.is_file():
                    ext = file_path.suffix.lower()
                    if ext in self.VIDEO_EXTENSIONS:
                        video_files.append(file_path)
                    elif ext in self.AUDIO_EXTENSIONS:
                        audio_files.append(file_path)
        except Exception as e:
            messagebox.showerror("错误", f"扫描失败: {e}")
            return
                        
        self.log(f"视频: {len(video_files)}, 音频: {len(audio_files)}")
        
        if not video_files or not audio_files:
            messagebox.showinfo("提示", "需要同时存在视频和音频文件")
            return
            
        # 匹配文件
        self.matches = self.match_files(video_files, audio_files)
        
        if not self.matches:
            self.log("未找到匹配的文件对")
            messagebox.showinfo("提示", "未找到匹配的文件对")
            return
            
        self.log(f"找到 {len(self.matches)} 对匹配文件")
        
        # 创建进度显示
        self.create_progress_widgets()
        
        self.preview_btn.config(state=tk.NORMAL)
        self.merge_btn.config(state=tk.NORMAL)
        self.status_label.config(text=f"找到 {len(self.matches)} 对匹配文件")
        
    def create_progress_widgets(self):
        """为每个匹配文件创建进度显示"""
        # 清空旧的小部件
        for widget in self.detail_frame.winfo_children():
            widget.destroy()
        self.progress_labels.clear()
        
        if not self.show_detailed_progress.get():
            return
            
        # 创建滚动区域
        canvas = tk.Canvas(self.detail_frame, height=150)
        scrollbar = ttk.Scrollbar(self.detail_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 为每个文件创建进度条
        for match in self.matches:
            filename = match['video'].name
            
            frame = ttk.Frame(scrollable_frame)
            frame.pack(fill=tk.X, pady=2)
            
            label = ttk.Label(frame, text=f"{filename}: 等待中...", width=60)
            label.pack(side=tk.LEFT)
            
            progress_var = tk.DoubleVar(value=0)
            progress_bar = ttk.Progressbar(frame, variable=progress_var, mode='determinate', length=150)
            progress_bar.pack(side=tk.LEFT, padx=5)
            
            self.progress_labels[filename] = (label, progress_var)
            
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def match_files(self, video_files, audio_files):
        """匹配文件"""
        matches = []
        matched_audio = set()
        
        # 完全匹配
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
                        matches.append({'video': video, 'audio': audio})
                        matched_audio.add(str(audio))
                        break
                        
        return matches
        
    def preview_matches(self):
        """预览匹配结果"""
        if not self.matches:
            return
            
        preview_window = tk.Toplevel(self.root)
        preview_window.title("匹配结果预览")
        preview_window.geometry("700x400")
        
        columns = ('#', '视频文件', '音频文件')
        tree = ttk.Treeview(preview_window, columns=columns, show='headings')
        
        for col in columns:
            tree.heading(col, text=col)
            
        tree.column('#', width=40)
        tree.column('视频文件', width=300)
        tree.column('音频文件', width=300)
            
        scrollbar = ttk.Scrollbar(preview_window, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        for i, match in enumerate(self.matches, 1):
            tree.insert('', tk.END, values=(i, match['video'].name, match['audio'].name))
            
    def start_merge(self):
        """开始合成"""
        if not self.verify_ffmpeg():
            messagebox.showerror("错误", "FFmpeg 未正确配置")
            return
            
        if not self.matches:
            messagebox.showwarning("警告", "没有可合成的文件")
            return
            
        self.is_running = True
        self.current_progress.clear()
        self.scan_btn.config(state=tk.DISABLED)
        self.preview_btn.config(state=tk.DISABLED)
        self.merge_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        # 重置进度
        self.total_progress_bar['maximum'] = len(self.matches)
        self.total_progress_bar['value'] = 0
        self.total_progress_label.config(text=f"总进度: 0/{len(self.matches)}")
        
        thread = threading.Thread(target=self.merge_all)
        thread.daemon = True
        thread.start()
        
    def stop_merge(self):
        """停止合成"""
        self.is_running = False
        self.log("正在停止...")
        
    def merge_all(self):
        """合成所有文件"""
        suffix = self.output_suffix.get()
        overwrite = False
        
        total = len(self.matches)
        completed = 0
        
        self.log(f"\n开始合成 {total} 个文件...")
        
        for i, match in enumerate(self.matches):
            if not self.is_running:
                break
                
            filename = match['video'].name
            self.current_file_label.config(text=f"当前: {filename}")
            self.current_progress_bar['value'] = 0
            
            # 更新进度状态
            with self.progress_lock:
                self.current_progress[filename] = {'text': '开始处理...', 'percentage': 0}
            
            try:
                success = self.merge_single_with_progress(match, suffix, overwrite, i)
                if success:
                    completed += 1
                    self.log(f"✓ {filename}")
                    with self.progress_lock:
                        self.current_progress[filename] = {'text': '完成', 'percentage': 100}
                else:
                    self.log(f"✗ {filename}")
                    with self.progress_lock:
                        self.current_progress[filename] = {'text': '失败', 'percentage': 0}
            except Exception as e:
                self.log(f"✗ {filename}: {e}")
                with self.progress_lock:
                    self.current_progress[filename] = {'text': f'错误: {e}', 'percentage': 0}
                
            completed_count = i + 1
            self.total_progress_bar['value'] = completed_count
            self.total_progress_label.config(text=f"总进度: {completed_count}/{total}")
            self.status_label.config(text=f"进度: {completed_count}/{total}")
            self.root.update_idletasks()
                    
        self.log(f"\n完成: {completed}/{total} 成功")
        
        self.is_running = False
        self.scan_btn.config(state=tk.NORMAL)
        self.preview_btn.config(state=tk.NORMAL)
        self.merge_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.current_file_label.config(text="当前: 完成")
        self.status_label.config(text=f"完成: {completed}/{total} 成功")
        
        self.save_config()
        
        messagebox.showinfo("完成", f"合成完成!\n成功: {completed}\n失败: {total - completed}")
        
    def merge_single_with_progress(self, match, suffix, overwrite, index):
        """合成单个文件并显示进度"""
        video = match['video']
        audio = match['audio']
        filename = video.name
        
        if self.use_source_as_output.get():
            output_path = video.parent / f"{video.stem}{suffix}{video.suffix}"
        else:
            output_dir = self.output_dir.get()
            if not output_dir:
                return False
            output_path = Path(output_dir) / f"{video.stem}{suffix}{video.suffix}"
            
        if output_path.exists() and not overwrite:
            return False
            
        cmd = [
            self.ffmpeg_path.get(),
            '-i', str(video),
            '-i', str(audio),
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-map', '0:v:0',
            '-map', '1:a:0',
            '-shortest',
            '-y' if overwrite else '-n',
            str(output_path)
        ]
        
        # 如果不显示详细进度，使用简单模式
        if not self.show_detailed_progress.get():
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', 
                                       errors='ignore', timeout=300)
                return result.returncode == 0
            except:
                return False
        
        # 显示详细进度模式
        progress = FFmpegProgress()
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding='utf-8',
                errors='ignore',
                bufsize=1
            )
            
            last_update = time.time()
            
            for line in process.stdout:
                # 解析时长（只在开始时）
                if progress.duration == 0:
                    progress.parse_duration(line)
                
                # 解析进度
                if progress.parse_progress(line):
                    # 更新进度（限制更新频率）
                    current_time = time.time()
                    if current_time - last_update > 0.5:  # 每0.5秒更新一次UI
                        progress_text = progress.get_progress_text()
                        with self.progress_lock:
                            self.current_progress[filename] = {
                                'text': progress_text,
                                'percentage': progress.percentage
                            }
                        
                        # 更新当前进度条
                        self.current_progress_bar['value'] = progress.percentage
                        self.current_file_label.config(text=f"当前: {filename} - {progress_text}")
                        self.root.update_idletasks()
                        last_update = current_time
            
            process.wait(timeout=300)
            return process.returncode == 0
            
        except Exception as e:
            self.log(f"合成出错: {e}")
            return False
            
    def on_closing(self):
        """窗口关闭"""
        self.is_running = False
        self.save_config()
        self.root.destroy()


def main():
    """主函数"""
    root = tk.Tk()
    app = VideoAudioMergerGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
