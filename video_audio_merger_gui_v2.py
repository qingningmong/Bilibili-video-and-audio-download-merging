#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频与音轨自动匹配合成工具 - GUI版本 v2.0
支持高DPI屏幕、自动选择文件夹、记住用户偏好
"""

import os
import sys
import json
import subprocess
import threading
from pathlib import Path
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, scrolledtext
except ImportError:
    print("错误: 无法导入tkinter模块")
    print("请确保Python安装了tkinter支持")
    sys.exit(1)


# ========== 高DPI适配 ==========
def setup_high_dpi():
    """设置高DPI适配"""
    if sys.platform == 'win32':
        try:
            # Windows高DPI支持
            from ctypes import windll
            # 设置进程DPI感知
            windll.shcore.SetProcessDpiAwareness(1)
            # 或者使用更兼容的方式
            # windll.user32.SetProcessDPIAware()
        except:
            pass
    
    # 尝试检测屏幕DPI并设置缩放
    try:
        root = tk.Tk()
        root.withdraw()
        
        # 获取屏幕DPI
        dpi = root.winfo_fpixels('1i')
        scale_factor = dpi / 96.0  # 96是标准DPI
        
        # 设置缩放
        if scale_factor > 1.0:
            root.tk.call('tk', 'scaling', scale_factor)
            
        root.destroy()
        return scale_factor
    except:
        return 1.0


# ========== 自动文件夹检测 ==========
class FolderDetector:
    """自动检测可能包含媒体文件的文件夹"""
    
    VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
    AUDIO_EXTENSIONS = {'.m4a', '.mp3', '.aac', '.wav', '.flac', '.ogg', '.wma', '.mka'}
    
    @classmethod
    def get_common_folders(cls):
        """获取常用文件夹列表"""
        folders = []
        home = Path.home()
        
        # Windows常用下载目录
        if sys.platform == 'win32':
            common_paths = [
                home / 'Downloads',
                home / '下载',
                home / 'Desktop',
                home / '桌面',
                home / 'Videos',
                home / '视频',
                home / 'Documents',
                home / '文档',
                Path('D:/下载'),
                Path('D:/Downloads'),
                Path('E:/下载'),
                Path('E:/Downloads'),
            ]
        else:
            # Mac/Linux
            common_paths = [
                home / 'Downloads',
                home / 'Desktop',
                home / 'Videos',
                home / 'Movies',
                home / 'Documents',
            ]
        
        for path in common_paths:
            if path.exists() and path.is_dir():
                folders.append(path)
                
        return folders
    
    @classmethod
    def scan_for_media(cls, folder, max_depth=2):
        """扫描文件夹中的媒体文件数量"""
        video_count = 0
        audio_count = 0
        
        try:
            for i, file_path in enumerate(Path(folder).rglob('*')):
                if i > 1000:  # 限制扫描数量
                    break
                if file_path.is_file():
                    ext = file_path.suffix.lower()
                    if ext in cls.VIDEO_EXTENSIONS:
                        video_count += 1
                    elif ext in cls.AUDIO_EXTENSIONS:
                        audio_count += 1
        except:
            pass
            
        return video_count, audio_count
    
    @classmethod
    def find_best_source_folder(cls):
        """找到最适合作为源目录的文件夹"""
        candidates = []
        
        for folder in cls.get_common_folders():
            video_count, audio_count = cls.scan_for_media(folder)
            # 评分：同时有视频和音频的文件夹得分更高
            score = video_count + audio_count
            if video_count > 0 and audio_count > 0:
                score += 100  # 优先推荐同时有视频和音频的文件夹
            candidates.append((folder, video_count, audio_count, score))
        
        # 按分数排序
        candidates.sort(key=lambda x: x[3], reverse=True)
        
        # 返回分数最高的文件夹
        if candidates and candidates[0][3] > 0:
            return candidates[0][0]
        return None
    
    @classmethod
    def suggest_output_folder(cls, source_folder=None):
        """建议输出文件夹"""
        if source_folder:
            source = Path(source_folder)
            # 建议在同目录下创建output子目录
            output = source / 'output'
            return output
        return None


# ========== 主应用 ==========
class VideoAudioMergerGUI:
    """视频音频合成工具的GUI版本"""
    
    VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
    AUDIO_EXTENSIONS = {'.m4a', '.mp3', '.aac', '.wav', '.flac', '.ogg', '.wma', '.mka'}
    
    def __init__(self, root):
        self.root = root
        
        # 设置高DPI
        self.scale_factor = setup_high_dpi()
        
        # 设置窗口标题和大小
        self.root.title("视频与音轨自动匹配合成工具 v2.0")
        
        # 根据DPI调整窗口大小
        base_width = 1000
        base_height = 750
        if self.scale_factor > 1.0:
            base_width = int(base_width * self.scale_factor)
            base_height = int(base_height * self.scale_factor)
        
        self.root.geometry(f"{base_width}x{base_height}")
        self.root.minsize(int(base_width * 0.8), int(base_height * 0.8))
        
        # 设置主题样式（适配高DPI）
        self.setup_styles()
        
        # 初始化变量
        self.ffmpeg_path = tk.StringVar()
        self.source_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.output_suffix = tk.StringVar(value='_merged')
        self.similarity_threshold = tk.DoubleVar(value=0.8)
        self.max_workers = tk.IntVar(value=2)
        self.overwrite = tk.BooleanVar(value=False)
        self.use_source_as_output = tk.BooleanVar(value=True)
        
        self.matches = []
        self.is_running = False
        
        # 配置文件路径
        self.config_file = Path.home() / '.video_audio_merger_v2.json'
        
        # 加载配置
        self.load_config()
        
        # 如果没有设置源目录，自动检测
        if not self.source_dir.get():
            self.auto_detect_folders()
        
        # 创建界面
        self.create_widgets()
        
        # 检查FFmpeg
        self.root.after(100, self.check_ffmpeg_on_startup)
        
    def setup_styles(self):
        """设置样式（适配高DPI）"""
        style = ttk.Style()
        
        # 根据DPI调整字体大小
        base_font_size = 10
        if self.scale_factor > 1.5:
            base_font_size = 11
        elif self.scale_factor > 2.0:
            base_font_size = 12
        
        # 配置字体
        default_font = ('Microsoft YaHei', base_font_size)
        title_font = ('Microsoft YaHei', base_font_size + 2, 'bold')
        small_font = ('Microsoft YaHei', base_font_size - 1)
        
        style.configure('.', font=default_font)
        style.configure('Title.TLabel', font=title_font)
        style.configure('Small.TLabel', font=small_font)
        style.configure('TLabelframe.Label', font=default_font)
        style.configure('TButton', font=default_font)
        
        # 配置Treeview字体
        style.configure('Treeview', font=default_font, rowheight=int(25 * self.scale_factor))
        style.configure('Treeview.Heading', font=default_font)
        
    def auto_detect_folders(self):
        """自动检测文件夹"""
        # 自动查找最佳源目录
        best_folder = FolderDetector.find_best_source_folder()
        if best_folder:
            self.source_dir.set(str(best_folder))
            
            # 自动设置输出目录
            output = FolderDetector.suggest_output_folder(best_folder)
            if output:
                self.output_dir.set(str(output))
                
    def load_config(self):
        """加载配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.ffmpeg_path.set(config.get('ffmpeg_path', ''))
                    self.source_dir.set(config.get('source_dir', ''))
                    self.output_dir.set(config.get('output_dir', ''))
                    self.output_suffix.set(config.get('output_suffix', '_merged'))
                    self.similarity_threshold.set(config.get('similarity_threshold', 0.8))
                    self.max_workers.set(config.get('max_workers', 2))
                    self.use_source_as_output.set(config.get('use_source_as_output', True))
            except Exception as e:
                print(f"加载配置失败: {e}")
                
    def save_config(self):
        """保存配置"""
        config = {
            'ffmpeg_path': self.ffmpeg_path.get(),
            'source_dir': self.source_dir.get(),
            'output_dir': self.output_dir.get(),
            'output_suffix': self.output_suffix.get(),
            'similarity_threshold': self.similarity_threshold.get(),
            'max_workers': self.max_workers.get(),
            'use_source_as_output': self.use_source_as_output.get()
        }
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")
            
    def check_ffmpeg_on_startup(self):
        """启动时检查FFmpeg"""
        if self.ffmpeg_path.get():
            self.verify_ffmpeg()
            
    def create_widgets(self):
        """创建界面组件"""
        # 主框架 - 使用Canvas支持滚动
        main_container = ttk.Frame(self.root, padding="10")
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # 创建Canvas和滚动条
        canvas = tk.Canvas(main_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, padding="5")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 鼠标滚轮支持
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # ===== 标题区域 =====
        title_frame = ttk.Frame(scrollable_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = ttk.Label(
            title_frame, 
            text="视频与音轨自动匹配合成工具", 
            style='Title.TLabel'
        )
        title_label.pack(side=tk.LEFT)
        
        version_label = ttk.Label(
            title_frame, 
            text="v2.0", 
            foreground="gray",
            style='Small.TLabel'
        )
        version_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # ===== FFmpeg设置 =====
        ffmpeg_frame = ttk.LabelFrame(scrollable_frame, text=" FFmpeg 设置 ", padding="10")
        ffmpeg_frame.pack(fill=tk.X, pady=5)
        
        ffmpeg_inner = ttk.Frame(ffmpeg_frame)
        ffmpeg_inner.pack(fill=tk.X)
        ffmpeg_inner.columnconfigure(1, weight=1)
        
        ttk.Label(ffmpeg_inner, text="FFmpeg 路径:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        ffmpeg_entry = ttk.Entry(ffmpeg_inner, textvariable=self.ffmpeg_path)
        ffmpeg_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        
        btn_frame = ttk.Frame(ffmpeg_inner)
        btn_frame.grid(row=0, column=2, padx=5)
        ttk.Button(btn_frame, text="浏览...", command=self.browse_ffmpeg, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="自动查找", command=self.auto_find_ffmpeg, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="验证", command=self.verify_ffmpeg, width=8).pack(side=tk.LEFT, padx=2)
        
        self.ffmpeg_status = ttk.Label(ffmpeg_inner, text="状态: 未验证", foreground="red")
        self.ffmpeg_status.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))
        
        # ===== 目录设置 =====
        dir_frame = ttk.LabelFrame(scrollable_frame, text=" 目录设置 ", padding="10")
        dir_frame.pack(fill=tk.X, pady=5)
        
        # 源目录
        source_frame = ttk.Frame(dir_frame)
        source_frame.pack(fill=tk.X, pady=2)
        source_frame.columnconfigure(1, weight=1)
        
        ttk.Label(source_frame, text="源目录:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        source_entry = ttk.Entry(source_frame, textvariable=self.source_dir)
        source_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        
        source_btn_frame = ttk.Frame(source_frame)
        source_btn_frame.grid(row=0, column=2, padx=5)
        ttk.Button(source_btn_frame, text="浏览...", command=self.browse_source_dir, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(source_btn_frame, text="自动检测", command=self.auto_detect_source, width=8).pack(side=tk.LEFT, padx=2)
        
        # 源目录信息
        self.source_info = ttk.Label(source_frame, text="", foreground="gray", style='Small.TLabel')
        self.source_info.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(2, 0))
        
        # 输出目录
        output_frame = ttk.Frame(dir_frame)
        output_frame.pack(fill=tk.X, pady=(10, 2))
        output_frame.columnconfigure(1, weight=1)
        
        ttk.Label(output_frame, text="输出目录:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        output_entry = ttk.Entry(output_frame, textvariable=self.output_dir, 
                                 state='disabled' if self.use_source_as_output.get() else 'normal')
        output_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        
        ttk.Button(output_frame, text="浏览...", command=self.browse_output_dir, width=8).grid(row=0, column=2, padx=5)
        
        # 输出选项
        options_frame = ttk.Frame(dir_frame)
        options_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Checkbutton(
            options_frame, 
            text="输出到原目录（与视频文件同目录）",
            variable=self.use_source_as_output,
            command=self.toggle_output_mode
        ).pack(side=tk.LEFT)
        
        # ===== 选项设置 =====
        options_frame = ttk.LabelFrame(scrollable_frame, text=" 选项设置 ", padding="10")
        options_frame.pack(fill=tk.X, pady=5)
        
        # 第一行选项
        row1 = ttk.Frame(options_frame)
        row1.pack(fill=tk.X, pady=2)
        
        ttk.Label(row1, text="输出后缀:").pack(side=tk.LEFT)
        ttk.Entry(row1, textvariable=self.output_suffix, width=12).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(row1, text="相似度阈值:").pack(side=tk.LEFT, padx=(20, 0))
        threshold_spin = ttk.Spinbox(row1, from_=0.5, to=1.0, increment=0.05, 
                                     textvariable=self.similarity_threshold, width=6)
        threshold_spin.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(row1, text="并行任务:").pack(side=tk.LEFT, padx=(20, 0))
        workers_spin = ttk.Spinbox(row1, from_=1, to=4, increment=1, 
                                   textvariable=self.max_workers, width=6)
        workers_spin.pack(side=tk.LEFT, padx=5)
        
        ttk.Checkbutton(row1, text="覆盖已存在文件", variable=self.overwrite).pack(side=tk.LEFT, padx=(20, 0))
        
        # ===== 操作按钮 =====
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        btn_width = 12
        self.scan_btn = ttk.Button(button_frame, text="扫描文件", command=self.scan_files, width=btn_width)
        self.scan_btn.pack(side=tk.LEFT, padx=5)
        
        self.preview_btn = ttk.Button(button_frame, text="预览匹配", command=self.preview_matches, 
                                     width=btn_width, state=tk.DISABLED)
        self.preview_btn.pack(side=tk.LEFT, padx=5)
        
        self.merge_btn = ttk.Button(button_frame, text="开始合成", command=self.start_merge, 
                                   width=btn_width, state=tk.DISABLED)
        self.merge_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="停止", command=self.stop_merge, 
                                  width=btn_width, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="打开输出目录", command=self.open_output_dir, 
                  width=btn_width).pack(side=tk.LEFT, padx=5)
        
        # ===== 统计信息 =====
        self.stats_frame = ttk.LabelFrame(scrollable_frame, text=" 扫描统计 ", padding="10")
        self.stats_frame.pack(fill=tk.X, pady=5)
        
        self.stats_label = ttk.Label(self.stats_frame, text="尚未扫描", foreground="gray")
        self.stats_label.pack(anchor=tk.W)
        
        # ===== 日志区域 =====
        log_frame = ttk.LabelFrame(scrollable_frame, text=" 日志 ", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # 日志文本框
        self.log_text = scrolledtext.ScrolledText(
            log_frame, 
            wrap=tk.WORD, 
            height=15,
            font=('Consolas', 10)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 日志操作按钮
        log_btn_frame = ttk.Frame(log_frame)
        log_btn_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(log_btn_frame, text="清空日志", command=self.clear_log, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(log_btn_frame, text="保存日志", command=self.save_log, width=10).pack(side=tk.LEFT, padx=2)
        
        # ===== 进度条 =====
        progress_frame = ttk.Frame(scrollable_frame)
        progress_frame.pack(fill=tk.X, pady=5)
        
        self.progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress.pack(fill=tk.X)
        
        self.status_label = ttk.Label(progress_frame, text="就绪")
        self.status_label.pack(anchor=tk.W, pady=(5, 0))
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def toggle_output_mode(self):
        """切换输出模式"""
        # 这里不需要实际禁用输入框，因为我们会在合成时判断
        pass
        
    def auto_find_ffmpeg(self):
        """自动查找FFmpeg"""
        self.log("正在自动查找FFmpeg...")
        
        # 常见路径
        if sys.platform == 'win32':
            common_paths = [
                Path(os.environ.get('ProgramFiles', 'C:\\Program Files')) / 'FFmpeg' / 'bin' / 'ffmpeg.exe',
                Path(os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')) / 'FFmpeg' / 'bin' / 'ffmpeg.exe',
                Path('C:/ffmpeg/bin/ffmpeg.exe'),
                Path('D:/ffmpeg/bin/ffmpeg.exe'),
                Path.home() / 'ffmpeg' / 'bin' / 'ffmpeg.exe',
            ]
        else:
            common_paths = [
                Path('/usr/bin/ffmpeg'),
                Path('/usr/local/bin/ffmpeg'),
                Path('/opt/homebrew/bin/ffmpeg'),
                Path('/opt/ffmpeg/bin/ffmpeg'),
            ]
        
        # 从PATH查找
        for path in os.environ.get('PATH', '').split(os.pathsep):
            exe = 'ffmpeg.exe' if sys.platform == 'win32' else 'ffmpeg'
            full_path = Path(path) / exe
            common_paths.append(full_path)
        
        # 测试每个路径
        for path in common_paths:
            if path.exists():
                self.ffmpeg_path.set(str(path))
                if self.verify_ffmpeg():
                    self.log(f"✓ 找到FFmpeg: {path}")
                    return
                    
        self.log("✗ 未找到FFmpeg，请手动指定路径")
        messagebox.showwarning("未找到", "未找到FFmpeg，请手动指定路径或下载安装。\n\n下载地址: https://ffmpeg.org/download.html")
        
    def auto_detect_source(self):
        """自动检测源目录"""
        self.log("正在自动检测源目录...")
        best_folder = FolderDetector.find_best_source_folder()
        
        if best_folder:
            self.source_dir.set(str(best_folder))
            video_count, audio_count = FolderDetector.scan_for_media(best_folder)
            self.source_info.config(text=f"检测到 {video_count} 个视频, {audio_count} 个音频")
            self.log(f"✓ 自动选择: {best_folder}")
            self.log(f"  视频: {video_count}, 音频: {audio_count}")
            
            # 自动设置输出目录
            if self.use_source_as_output.get():
                output = FolderDetector.suggest_output_folder(best_folder)
                if output:
                    self.output_dir.set(str(output))
        else:
            self.log("✗ 未检测到包含媒体文件的目录")
            messagebox.showinfo("提示", "未自动检测到包含视频/音频的文件夹，请手动选择。")
            
    def open_output_dir(self):
        """打开输出目录"""
        output_dir = self.get_output_dir()
        if output_dir and Path(output_dir).exists():
            if sys.platform == 'win32':
                os.startfile(output_dir)
            elif sys.platform == 'darwin':
                subprocess.run(['open', output_dir])
            else:
                subprocess.run(['xdg-open', output_dir])
        else:
            messagebox.showwarning("警告", "输出目录不存在")
            
    def get_output_dir(self):
        """获取实际输出目录"""
        if self.use_source_as_output.get():
            return self.source_dir.get()
        else:
            return self.output_dir.get()
            
    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
        
    def save_log(self):
        """保存日志"""
        log_content = self.log_text.get(1.0, tk.END)
        if not log_content.strip():
            messagebox.showinfo("提示", "日志为空")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                messagebox.showinfo("成功", "日志已保存")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {e}")
                
    def on_closing(self):
        """窗口关闭时保存配置"""
        self.save_config()
        self.root.destroy()
        
    def browse_ffmpeg(self):
        """浏览选择FFmpeg"""
        filetypes = [('可执行文件', '*.exe')] if sys.platform == 'win32' else [('所有文件', '*.*')]
        path = filedialog.askopenfilename(
            title="选择 FFmpeg 可执行文件",
            filetypes=filetypes
        )
        if path:
            self.ffmpeg_path.set(path)
            self.verify_ffmpeg()
            
    def browse_source_dir(self):
        """浏览选择源目录"""
        path = filedialog.askdirectory(title="选择源目录")
        if path:
            self.source_dir.set(path)
            # 更新源目录信息
            video_count, audio_count = FolderDetector.scan_for_media(Path(path))
            self.source_info.config(text=f"检测到 {video_count} 个视频, {audio_count} 个音频")
            
    def browse_output_dir(self):
        """浏览选择输出目录"""
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            self.output_dir.set(path)
            self.use_source_as_output.set(False)
            
    def verify_ffmpeg(self):
        """验证FFmpeg"""
        path = self.ffmpeg_path.get()
        if not path or not Path(path).exists():
            self.ffmpeg_status.config(text="状态: FFmpeg 路径无效", foreground="red")
            return False
            
        try:
            result = subprocess.run(
                [path, '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.split('\n')[0]
                self.ffmpeg_status.config(text=f"✓ {version[:50]}...", foreground="green")
                self.save_config()
                return True
            else:
                self.ffmpeg_status.config(text="状态: FFmpeg 无法正常运行", foreground="red")
                return False
        except Exception as e:
            self.ffmpeg_status.config(text=f"状态: 验证失败 - {e}", foreground="red")
            return False
            
    def log(self, message):
        """添加日志"""
        from datetime import datetime
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
            
        self.log(f"正在扫描目录: {directory}")
        self.status_label.config(text="正在扫描...")
        self.root.update()
        
        # 扫描文件
        video_files = []
        audio_files = []
        
        for file_path in Path(directory).rglob('*'):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext in self.VIDEO_EXTENSIONS:
                    video_files.append(file_path)
                elif ext in self.AUDIO_EXTENSIONS:
                    audio_files.append(file_path)
                    
        self.log(f"找到 {len(video_files)} 个视频文件, {len(audio_files)} 个音频文件")
        
        if not video_files or not audio_files:
            messagebox.showinfo("提示", "需要同时存在视频和音频文件才能进行匹配")
            self.status_label.config(text="扫描完成 - 未找到足够的文件")
            self.stats_label.config(text=f"视频: {len(video_files)}, 音频: {len(audio_files)}, 匹配: 0")
            return
            
        # 匹配文件
        self.matches = self.match_files(video_files, audio_files)
        
        if not self.matches:
            self.log("未找到匹配的文件对")
            messagebox.showinfo("提示", "未找到匹配的文件对")
            self.status_label.config(text="扫描完成 - 未找到匹配")
            self.stats_label.config(text=f"视频: {len(video_files)}, 音频: {len(audio_files)}, 匹配: 0")
            return
            
        exact_count = sum(1 for m in self.matches if m['match_type'] == 'exact')
        similar_count = len(self.matches) - exact_count
        
        self.log(f"\n匹配结果:")
        self.log(f"  完全匹配: {exact_count}")
        self.log(f"  相似匹配: {similar_count}")
        self.log(f"  总计: {len(self.matches)}")
        
        # 更新统计
        self.stats_label.config(
            text=f"视频: {len(video_files)} | 音频: {len(audio_files)} | 完全匹配: {exact_count} | 相似匹配: {similar_count} | 总计: {len(self.matches)}",
            foreground="green"
        )
        
        self.preview_btn.config(state=tk.NORMAL)
        self.merge_btn.config(state=tk.NORMAL)
        self.status_label.config(text=f"找到 {len(self.matches)} 对匹配文件")
        
    def match_files(self, video_files, audio_files):
        """匹配文件"""
        threshold = self.similarity_threshold.get()
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
                        matches.append({
                            'video': video,
                            'audio': audio,
                            'match_type': 'exact',
                            'similarity': 1.0
                        })
                        matched_audio.add(str(audio))
                        break
                        
        # 相似匹配
        unmatched_videos = [v for v in video_files if not any(m['video'] == v for m in matches)]
        unmatched_audios = [a for a in audio_files if str(a) not in matched_audio]
        
        for video in unmatched_videos:
            video_stem = video.stem
            best_match = None
            best_score = 0
            
            for audio in unmatched_audios:
                score = SequenceMatcher(None, video_stem, audio.stem).ratio()
                if score > best_score and score >= threshold:
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
                
        return matches
        
    def preview_matches(self):
        """预览匹配结果"""
        if not self.matches:
            return
            
        # 创建新窗口
        preview_window = tk.Toplevel(self.root)
        preview_window.title("匹配结果预览")
        
        # 根据DPI调整大小
        width = int(900 * self.scale_factor)
        height = int(500 * self.scale_factor)
        preview_window.geometry(f"{width}x{height}")
        
        # 创建表格
        columns = ('#', '类型', '视频文件', '音频文件', '相似度')
        tree = ttk.Treeview(preview_window, columns=columns, show='headings')
        
        tree.heading('#', text='#')
        tree.heading('类型', text='类型')
        tree.heading('视频文件', text='视频文件')
        tree.heading('音频文件', text='音频文件')
        tree.heading('相似度', text='相似度')
        
        tree.column('#', width=int(40 * self.scale_factor))
        tree.column('类型', width=int(80 * self.scale_factor))
        tree.column('视频文件', width=int(350 * self.scale_factor))
        tree.column('音频文件', width=int(350 * self.scale_factor))
        tree.column('相似度', width=int(60 * self.scale_factor))
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(preview_window, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 填充数据
        for i, match in enumerate(self.matches, 1):
            match_type = "完全匹配" if match['match_type'] == 'exact' else "相似匹配"
            similarity = f"{match['similarity']:.0%}" if match['match_type'] == 'similar' else "100%"
            tree.insert('', tk.END, values=(
                i,
                match_type,
                match['video'].name,
                match['audio'].name,
                similarity
            ))
            
    def start_merge(self):
        """开始合成"""
        if not self.verify_ffmpeg():
            messagebox.showerror("错误", "FFmpeg 未正确配置")
            return
            
        if not self.matches:
            messagebox.showwarning("警告", "没有可合成的文件")
            return
            
        # 确认输出目录
        output_dir = self.get_output_dir()
        if not output_dir:
            messagebox.showwarning("警告", "请设置输出目录")
            return
            
        # 如果输出目录不存在，询问是否创建
        output_path = Path(output_dir)
        if not output_path.exists():
            if messagebox.askyesno("确认", f"输出目录不存在，是否创建?\n{output_dir}"):
                try:
                    output_path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    messagebox.showerror("错误", f"创建目录失败: {e}")
                    return
            else:
                return
                
        self.is_running = True
        self.scan_btn.config(state=tk.DISABLED)
        self.preview_btn.config(state=tk.DISABLED)
        self.merge_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        # 在新线程中运行合成
        thread = threading.Thread(target=self.merge_all)
        thread.daemon = True
        thread.start()
        
    def stop_merge(self):
        """停止合成"""
        self.is_running = False
        self.log("正在停止...")
        
    def merge_all(self):
        """合成所有文件"""
        output_dir = self.get_output_dir()
        suffix = self.output_suffix.get()
        overwrite = self.overwrite.get()
        max_workers = self.max_workers.get()
        
        total = len(self.matches)
        success_count = 0
        
        self.progress['maximum'] = total
        self.progress['value'] = 0
        
        self.log(f"\n开始合成 {total} 个文件...")
        self.log(f"输出目录: {output_dir}")
        self.log("="*60)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_match = {}
            
            for match in self.matches:
                if not self.is_running:
                    break
                    
                future = executor.submit(
                    self.merge_single,
                    match,
                    output_dir,
                    suffix,
                    overwrite
                )
                future_to_match[future] = match
                
            for future in as_completed(future_to_match):
                if not self.is_running:
                    executor.shutdown(wait=False)
                    break
                    
                match = future_to_match[future]
                try:
                    success, message = future.result()
                    if success:
                        success_count += 1
                        self.log(f"✓ {match['video'].name}")
                    else:
                        self.log(f"✗ {match['video'].name}: {message}")
                except Exception as e:
                    self.log(f"✗ {match['video'].name}: {e}")
                    
                self.progress['value'] += 1
                self.status_label.config(text=f"进度: {self.progress['value']}/{total}")
                self.root.update_idletasks()
                
        self.log("="*60)
        self.log(f"合成完成: {success_count}/{total} 成功")
        
        self.is_running = False
        self.scan_btn.config(state=tk.NORMAL)
        self.preview_btn.config(state=tk.NORMAL)
        self.merge_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_label.config(text=f"完成: {success_count}/{total} 成功")
        
        # 保存配置
        self.save_config()
        
        messagebox.showinfo("完成", f"合成完成!\n成功: {success_count}\n失败: {total - success_count}")
        
    def merge_single(self, match, output_dir, suffix, overwrite):
        """合成单个文件"""
        video = match['video']
        audio = match['audio']
        
        if self.use_source_as_output.get():
            # 输出到原目录
            output_path = video.parent / f"{video.stem}{suffix}{video.suffix}"
        else:
            # 输出到指定目录
            output_path = Path(output_dir) / f"{video.stem}{suffix}{video.suffix}"
            
        if output_path.exists() and not overwrite:
            return False, "文件已存在"
            
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
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=300
            )
            
            if result.returncode == 0:
                return True, str(output_path)
            else:
                error = result.stderr[-200:] if result.stderr else "未知错误"
                return False, error
        except Exception as e:
            return False, str(e)


def main():
    """主函数"""
    root = tk.Tk()
    app = VideoAudioMergerGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
