#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频与音轨自动匹配合成工具 - 调试版本
带详细错误输出，用于排查闪退问题
"""

import sys
import traceback

# 重定向错误输出到文件
import logging
logging.basicConfig(
    filename='video_merger_debug.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def log_error(msg):
    """记录错误"""
    print(f"[ERROR] {msg}")
    logging.error(msg)

def log_info(msg):
    """记录信息"""
    print(f"[INFO] {msg}")
    logging.info(msg)

# 捕获所有未处理的异常
def exception_handler(exc_type, exc_value, exc_traceback):
    """全局异常处理"""
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    log_error(f"未捕获的异常:\n{error_msg}")
    print(f"\n发生错误，详情已保存到 video_merger_debug.log")
    input("按回车键退出...")
    sys.exit(1)

sys.excepthook = exception_handler

# 开始加载程序
log_info("程序启动...")
log_info(f"Python版本: {sys.version}")
log_info(f"平台: {sys.platform}")

# 检查必要模块
try:
    log_info("检查tkinter...")
    import tkinter as tk
    log_info(f"tkinter版本: {tk.Tcl().eval('info patchlevel')}")
except Exception as e:
    log_error(f"tkinter加载失败: {e}")
    raise

try:
    log_info("检查其他模块...")
    import os
    import json
    import subprocess
    import threading
    from pathlib import Path
    from difflib import SequenceMatcher
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from datetime import datetime
    log_info("所有模块加载成功")
except Exception as e:
    log_error(f"模块加载失败: {e}")
    raise

# 导入主程序
log_info("加载主程序...")
try:
    # 复制v2的代码到这里
    from tkinter import ttk, filedialog, messagebox, scrolledtext
    log_info("GUI模块加载成功")
except Exception as e:
    log_error(f"GUI模块加载失败: {e}")
    raise


# ========== 高DPI适配 ==========
def setup_high_dpi():
    """设置高DPI适配"""
    log_info("设置高DPI...")
    try:
        if sys.platform == 'win32':
            try:
                from ctypes import windll
                windll.shcore.SetProcessDpiAwareness(1)
                log_info("Windows DPI感知已设置")
            except Exception as e:
                log_info(f"DPI设置警告: {e}")
        
        root = tk.Tk()
        root.withdraw()
        dpi = root.winfo_fpixels('1i')
        scale_factor = dpi / 96.0
        if scale_factor > 1.0:
            root.tk.call('tk', 'scaling', scale_factor)
        root.destroy()
        log_info(f"DPI缩放因子: {scale_factor}")
        return scale_factor
    except Exception as e:
        log_error(f"DPI设置失败: {e}")
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
                if i > 1000:
                    break
                if file_path.is_file():
                    ext = file_path.suffix.lower()
                    if ext in cls.VIDEO_EXTENSIONS:
                        video_count += 1
                    elif ext in cls.AUDIO_EXTENSIONS:
                        audio_count += 1
        except Exception as e:
            log_error(f"扫描文件夹失败: {e}")
            
        return video_count, audio_count
    
    @classmethod
    def find_best_source_folder(cls):
        """找到最适合作为源目录的文件夹"""
        candidates = []
        
        for folder in cls.get_common_folders():
            video_count, audio_count = cls.scan_for_media(folder)
            score = video_count + audio_count
            if video_count > 0 and audio_count > 0:
                score += 100
            candidates.append((folder, video_count, audio_count, score))
        
        candidates.sort(key=lambda x: x[3], reverse=True)
        
        if candidates and candidates[0][3] > 0:
            return candidates[0][0]
        return None


# ========== 主应用 ==========
class VideoAudioMergerGUI:
    """视频音频合成工具的GUI版本"""
    
    VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
    AUDIO_EXTENSIONS = {'.m4a', '.mp3', '.aac', '.wav', '.flac', '.ogg', '.wma', '.mka'}
    
    def __init__(self, root):
        log_info("初始化GUI...")
        self.root = root
        
        self.scale_factor = setup_high_dpi()
        
        self.root.title("视频与音轨自动匹配合成工具 - 调试版")
        
        base_width = 1000
        base_height = 750
        if self.scale_factor > 1.0:
            base_width = int(base_width * self.scale_factor)
            base_height = int(base_height * self.scale_factor)
        
        self.root.geometry(f"{base_width}x{base_height}")
        self.root.minsize(int(base_width * 0.8), int(base_height * 0.8))
        
        self.setup_styles()
        
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
        
        self.config_file = Path.home() / '.video_audio_merger_v2.json'
        
        log_info("加载配置...")
        self.load_config()
        
        if not self.source_dir.get():
            self.auto_detect_folders()
        
        log_info("创建界面...")
        self.create_widgets()
        
        self.root.after(100, self.check_ffmpeg_on_startup)
        log_info("初始化完成")
        
    def setup_styles(self):
        """设置样式"""
        try:
            style = ttk.Style()
            base_font_size = 10
            if self.scale_factor > 1.5:
                base_font_size = 11
            elif self.scale_factor > 2.0:
                base_font_size = 12
            
            default_font = ('Microsoft YaHei', base_font_size)
            style.configure('.', font=default_font)
            style.configure('Treeview', font=default_font, rowheight=int(25 * self.scale_factor))
            log_info("样式设置完成")
        except Exception as e:
            log_error(f"样式设置失败: {e}")
        
    def auto_detect_folders(self):
        """自动检测文件夹"""
        try:
            best_folder = FolderDetector.find_best_source_folder()
            if best_folder:
                self.source_dir.set(str(best_folder))
                log_info(f"自动检测到文件夹: {best_folder}")
        except Exception as e:
            log_error(f"自动检测失败: {e}")
            
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
                    self.similarity_threshold.set(config.get('similarity_threshold', 0.8))
                    self.max_workers.set(config.get('max_workers', 2))
                    self.use_source_as_output.set(config.get('use_source_as_output', True))
                log_info("配置加载成功")
        except Exception as e:
            log_error(f"加载配置失败: {e}")
                
    def save_config(self):
        """保存配置"""
        try:
            config = {
                'ffmpeg_path': self.ffmpeg_path.get(),
                'source_dir': self.source_dir.get(),
                'output_dir': self.output_dir.get(),
                'output_suffix': self.output_suffix.get(),
                'similarity_threshold': self.similarity_threshold.get(),
                'max_workers': self.max_workers.get(),
                'use_source_as_output': self.use_source_as_output.get()
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log_error(f"保存配置失败: {e}")
            
    def check_ffmpeg_on_startup(self):
        """启动时检查FFmpeg"""
        if self.ffmpeg_path.get():
            self.verify_ffmpeg()
            
    def create_widgets(self):
        """创建界面组件"""
        try:
            main_container = ttk.Frame(self.root, padding="10")
            main_container.pack(fill=tk.BOTH, expand=True)
            
            # 标题
            title_frame = ttk.Frame(main_container)
            title_frame.pack(fill=tk.X, pady=(0, 10))
            
            ttk.Label(title_frame, text="视频与音轨自动匹配合成工具", 
                     font=('Microsoft YaHei', 14, 'bold')).pack(side=tk.LEFT)
            ttk.Label(title_frame, text=" - 调试版", foreground="red").pack(side=tk.LEFT)
            
            # FFmpeg设置
            ffmpeg_frame = ttk.LabelFrame(main_container, text=" FFmpeg 设置 ", padding="10")
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
            
            # 目录设置
            dir_frame = ttk.LabelFrame(main_container, text=" 目录设置 ", padding="10")
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
            
            self.source_info = ttk.Label(source_frame, text="", foreground="gray")
            self.source_info.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(2, 0))
            
            # 输出目录
            output_frame = ttk.Frame(dir_frame)
            output_frame.pack(fill=tk.X, pady=(10, 2))
            output_frame.columnconfigure(1, weight=1)
            
            ttk.Label(output_frame, text="输出目录:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
            ttk.Entry(output_frame, textvariable=self.output_dir).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
            ttk.Button(output_frame, text="浏览...", command=self.browse_output_dir, width=8).grid(row=0, column=2, padx=5)
            
            # 输出选项
            options_frame = ttk.Frame(dir_frame)
            options_frame.pack(fill=tk.X, pady=(5, 0))
            
            ttk.Checkbutton(options_frame, text="输出到原目录", variable=self.use_source_as_output).pack(side=tk.LEFT)
            
            # 选项设置
            options_frame = ttk.LabelFrame(main_container, text=" 选项设置 ", padding="10")
            options_frame.pack(fill=tk.X, pady=5)
            
            row1 = ttk.Frame(options_frame)
            row1.pack(fill=tk.X, pady=2)
            
            ttk.Label(row1, text="输出后缀:").pack(side=tk.LEFT)
            ttk.Entry(row1, textvariable=self.output_suffix, width=12).pack(side=tk.LEFT, padx=5)
            
            ttk.Label(row1, text="相似度:").pack(side=tk.LEFT, padx=(20, 0))
            ttk.Spinbox(row1, from_=0.5, to=1.0, increment=0.05, 
                       textvariable=self.similarity_threshold, width=6).pack(side=tk.LEFT, padx=5)
            
            ttk.Label(row1, text="并行:").pack(side=tk.LEFT, padx=(20, 0))
            ttk.Spinbox(row1, from_=1, to=4, increment=1, 
                       textvariable=self.max_workers, width=6).pack(side=tk.LEFT, padx=5)
            
            ttk.Checkbutton(row1, text="覆盖", variable=self.overwrite).pack(side=tk.LEFT, padx=(20, 0))
            
            # 操作按钮
            button_frame = ttk.Frame(main_container)
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
            
            # 统计信息
            self.stats_frame = ttk.LabelFrame(main_container, text=" 扫描统计 ", padding="10")
            self.stats_frame.pack(fill=tk.X, pady=5)
            
            self.stats_label = ttk.Label(self.stats_frame, text="尚未扫描", foreground="gray")
            self.stats_label.pack(anchor=tk.W)
            
            # 日志区域
            log_frame = ttk.LabelFrame(main_container, text=" 日志 ", padding="5")
            log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
            
            self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15, font=('Consolas', 9))
            self.log_text.pack(fill=tk.BOTH, expand=True)
            
            # 进度条
            progress_frame = ttk.Frame(main_container)
            progress_frame.pack(fill=tk.X, pady=5)
            
            self.progress = ttk.Progressbar(progress_frame, mode='determinate')
            self.progress.pack(fill=tk.X)
            
            self.status_label = ttk.Label(progress_frame, text="就绪")
            self.status_label.pack(anchor=tk.W, pady=(5, 0))
            
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            log_info("界面创建完成")
            
        except Exception as e:
            log_error(f"创建界面失败: {e}")
            raise
        
    def auto_find_ffmpeg(self):
        """自动查找FFmpeg"""
        try:
            self.log("正在自动查找FFmpeg...")
            
            if sys.platform == 'win32':
                common_paths = [
                    Path(os.environ.get('ProgramFiles', 'C:\\Program Files')) / 'FFmpeg' / 'bin' / 'ffmpeg.exe',
                    Path('C:/ffmpeg/bin/ffmpeg.exe'),
                    Path('D:/ffmpeg/bin/ffmpeg.exe'),
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
                        
            self.log("✗ 未找到FFmpeg")
            messagebox.showwarning("未找到", "未找到FFmpeg，请手动指定路径")
        except Exception as e:
            log_error(f"自动查找FFmpeg失败: {e}")
            
    def auto_detect_source(self):
        """自动检测源目录"""
        try:
            self.log("正在自动检测源目录...")
            best_folder = FolderDetector.find_best_source_folder()
            
            if best_folder:
                self.source_dir.set(str(best_folder))
                video_count, audio_count = FolderDetector.scan_for_media(best_folder)
                self.source_info.config(text=f"检测到 {video_count} 个视频, {audio_count} 个音频")
                self.log(f"✓ 自动选择: {best_folder}")
            else:
                self.log("✗ 未检测到包含媒体文件的目录")
        except Exception as e:
            log_error(f"自动检测失败: {e}")
            
    def browse_ffmpeg(self):
        """浏览选择FFmpeg"""
        try:
            filetypes = [('可执行文件', '*.exe')] if sys.platform == 'win32' else [('所有文件', '*.*')]
            path = filedialog.askopenfilename(title="选择 FFmpeg", filetypes=filetypes)
            if path:
                self.ffmpeg_path.set(path)
                self.verify_ffmpeg()
        except Exception as e:
            log_error(f"浏览FFmpeg失败: {e}")
            
    def browse_source_dir(self):
        """浏览选择源目录"""
        try:
            path = filedialog.askdirectory(title="选择源目录")
            if path:
                self.source_dir.set(path)
                video_count, audio_count = FolderDetector.scan_for_media(Path(path))
                self.source_info.config(text=f"检测到 {video_count} 个视频, {video_count} 个音频")
        except Exception as e:
            log_error(f"浏览源目录失败: {e}")
            
    def browse_output_dir(self):
        """浏览选择输出目录"""
        try:
            path = filedialog.askdirectory(title="选择输出目录")
            if path:
                self.output_dir.set(path)
        except Exception as e:
            log_error(f"浏览输出目录失败: {e}")
            
    def verify_ffmpeg(self):
        """验证FFmpeg"""
        try:
            path = self.ffmpeg_path.get()
            if not path or not Path(path).exists():
                self.ffmpeg_status.config(text="状态: FFmpeg 路径无效", foreground="red")
                return False
                
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
            log_error(f"验证FFmpeg失败: {e}")
            self.ffmpeg_status.config(text=f"状态: 验证失败", foreground="red")
            return False
            
    def log(self, message):
        """添加日志"""
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
            self.log_text.see(tk.END)
            self.root.update_idletasks()
        except Exception as e:
            log_error(f"添加日志失败: {e}")
        
    def scan_files(self):
        """扫描文件"""
        try:
            directory = self.source_dir.get()
            if not directory:
                messagebox.showwarning("警告", "请先选择源目录")
                return
                
            if not Path(directory).exists():
                messagebox.showerror("错误", "源目录不存在")
                return
                
            self.log(f"正在扫描: {directory}")
            self.status_label.config(text="正在扫描...")
            
            video_files = []
            audio_files = []
            
            for file_path in Path(directory).rglob('*'):
                if file_path.is_file():
                    ext = file_path.suffix.lower()
                    if ext in self.VIDEO_EXTENSIONS:
                        video_files.append(file_path)
                    elif ext in self.AUDIO_EXTENSIONS:
                        audio_files.append(file_path)
                        
            self.log(f"视频: {len(video_files)}, 音频: {len(audio_files)}")
            
            if not video_files or not audio_files:
                messagebox.showinfo("提示", "需要同时存在视频和音频文件")
                return
                
            self.matches = self.match_files(video_files, audio_files)
            
            if not self.matches:
                self.log("未找到匹配的文件对")
                return
                
            exact_count = sum(1 for m in self.matches if m['match_type'] == 'exact')
            self.log(f"完全匹配: {exact_count}, 总计: {len(self.matches)}")
            
            self.stats_label.config(text=f"视频: {len(video_files)} | 音频: {len(audio_files)} | 匹配: {len(self.matches)}")
            self.preview_btn.config(state=tk.NORMAL)
            self.merge_btn.config(state=tk.NORMAL)
            self.status_label.config(text=f"找到 {len(self.matches)} 对匹配")
        except Exception as e:
            log_error(f"扫描文件失败: {e}")
            messagebox.showerror("错误", f"扫描失败: {e}")
            
    def match_files(self, video_files, audio_files):
        """匹配文件"""
        try:
            threshold = self.similarity_threshold.get()
            matches = []
            matched_audio = set()
            
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
                            matches.append({'video': video, 'audio': audio, 'match_type': 'exact', 'similarity': 1.0})
                            matched_audio.add(str(audio))
                            break
                            
            return matches
        except Exception as e:
            log_error(f"匹配文件失败: {e}")
            return []
        
    def preview_matches(self):
        """预览匹配结果"""
        try:
            if not self.matches:
                return
                
            preview_window = tk.Toplevel(self.root)
            preview_window.title("匹配结果预览")
            preview_window.geometry("800x400")
            
            columns = ('#', '类型', '视频文件', '音频文件')
            tree = ttk.Treeview(preview_window, columns=columns, show='headings')
            
            for col in columns:
                tree.heading(col, text=col)
                
            scrollbar = ttk.Scrollbar(preview_window, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            for i, match in enumerate(self.matches, 1):
                match_type = "完全匹配" if match['match_type'] == 'exact' else "相似匹配"
                tree.insert('', tk.END, values=(i, match_type, match['video'].name, match['audio'].name))
        except Exception as e:
            log_error(f"预览匹配失败: {e}")
            
    def start_merge(self):
        """开始合成"""
        try:
            if not self.verify_ffmpeg():
                messagebox.showerror("错误", "FFmpeg 未正确配置")
                return
                
            if not self.matches:
                messagebox.showwarning("警告", "没有可合成的文件")
                return
                
            self.is_running = True
            self.scan_btn.config(state=tk.DISABLED)
            self.preview_btn.config(state=tk.DISABLED)
            self.merge_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            
            thread = threading.Thread(target=self.merge_all)
            thread.daemon = True
            thread.start()
        except Exception as e:
            log_error(f"启动合成失败: {e}")
            
    def stop_merge(self):
        """停止合成"""
        self.is_running = False
        self.log("正在停止...")
        
    def merge_all(self):
        """合成所有文件"""
        try:
            output_dir = self.output_dir.get() or self.source_dir.get()
            suffix = self.output_suffix.get()
            overwrite = self.overwrite.get()
            max_workers = self.max_workers.get()
            
            total = len(self.matches)
            success_count = 0
            
            self.progress['maximum'] = total
            self.progress['value'] = 0
            
            self.log(f"\n开始合成 {total} 个文件...")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_match = {executor.submit(self.merge_single, match, output_dir, suffix, overwrite): match for match in self.matches}
                
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
                    
            self.log(f"完成: {success_count}/{total} 成功")
            
            self.is_running = False
            self.scan_btn.config(state=tk.NORMAL)
            self.preview_btn.config(state=tk.NORMAL)
            self.merge_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.status_label.config(text=f"完成: {success_count}/{total} 成功")
            
            self.save_config()
            
            messagebox.showinfo("完成", f"合成完成!\n成功: {success_count}\n失败: {total - success_count}")
        except Exception as e:
            log_error(f"合成失败: {e}")
            
    def merge_single(self, match, output_dir, suffix, overwrite):
        """合成单个文件"""
        try:
            video = match['video']
            audio = match['audio']
            
            if self.use_source_as_output.get():
                output_path = video.parent / f"{video.stem}{suffix}{video.suffix}"
            else:
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
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', 
                                   errors='ignore', timeout=300)
            
            if result.returncode == 0:
                return True, str(output_path)
            else:
                error = result.stderr[-200:] if result.stderr else "未知错误"
                return False, error
        except Exception as e:
            log_error(f"合成单个文件失败: {e}")
            return False, str(e)
            
    def on_closing(self):
        """窗口关闭"""
        self.save_config()
        self.root.destroy()


def main():
    """主函数"""
    log_info("创建主窗口...")
    try:
        root = tk.Tk()
        log_info("主窗口创建成功")
        app = VideoAudioMergerGUI(root)
        log_info("进入主循环...")
        root.mainloop()
        log_info("程序正常退出")
    except Exception as e:
        log_error(f"程序异常: {e}")
        raise


if __name__ == '__main__':
    main()
