#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频与音轨自动匹配合成工具 - GUI版本 v2.1 (简化稳定版)
移除了可能导致问题的复杂功能，提高兼容性
"""

import os
import sys
import json
import subprocess
import threading
from pathlib import Path
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor, as_completed

# 导入tkinter
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, scrolledtext
except ImportError as e:
    print(f"错误: 无法导入tkinter - {e}")
    input("按回车键退出...")
    sys.exit(1)


class VideoAudioMergerGUI:
    """视频音频合成工具 - 简化稳定版"""
    
    VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
    AUDIO_EXTENSIONS = {'.m4a', '.mp3', '.aac', '.wav', '.flac', '.ogg', '.wma', '.mka'}
    
    def __init__(self, root):
        self.root = root
        self.root.title("视频与音轨自动匹配合成工具 v2.1")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # 初始化变量
        self.ffmpeg_path = tk.StringVar()
        self.source_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.output_suffix = tk.StringVar(value='_merged')
        self.use_source_as_output = tk.BooleanVar(value=True)
        
        self.matches = []
        self.is_running = False
        
        # 配置文件
        self.config_file = Path.home() / '.video_audio_merger.json'
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
        title_label = ttk.Label(main_frame, text="视频与音轨自动匹配合成工具", 
                               font=('Microsoft YaHei', 14, 'bold'))
        title_label.pack(pady=(0, 10))
        
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
        ttk.Button(source_frame, text="浏览...", command=self.browse_source_dir, width=8).grid(row=0, column=2, padx=5)
        
        # 输出目录
        output_frame = ttk.Frame(dir_frame)
        output_frame.pack(fill=tk.X, pady=(10, 2))
        output_frame.columnconfigure(1, weight=1)
        
        ttk.Label(output_frame, text="输出目录:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.output_entry = ttk.Entry(output_frame, textvariable=self.output_dir)
        self.output_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(output_frame, text="浏览...", command=self.browse_output_dir, width=8).grid(row=0, column=2, padx=5)
        
        # 输出选项
        ttk.Checkbutton(dir_frame, text="输出到原目录（与视频同目录）", 
                       variable=self.use_source_as_output,
                       command=self.toggle_output).pack(anchor=tk.W, pady=(5, 0))
        
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
        
        # ===== 统计信息 =====
        self.stats_label = ttk.Label(main_frame, text="尚未扫描", foreground="gray")
        self.stats_label.pack(anchor=tk.W, pady=5)
        
        # ===== 日志区域 =====
        log_frame = ttk.LabelFrame(main_frame, text=" 日志 ", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=12, font=('Consolas', 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 进度条
        self.progress = ttk.Progressbar(main_frame, mode='determinate')
        self.progress.pack(fill=tk.X, pady=5)
        
        self.status_label = ttk.Label(main_frame, text="就绪")
        self.status_label.pack(anchor=tk.W)
        
        # 初始状态
        self.toggle_output()
        
        # 关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
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
        
        # 常见路径
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
        
        # 从PATH查找
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
            
        self.log(f"正在扫描: {directory}")
        self.status_label.config(text="正在扫描...")
        
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
        self.stats_label.config(text=f"视频: {len(video_files)} | 音频: {len(audio_files)} | 匹配: {len(self.matches)}")
        
        self.preview_btn.config(state=tk.NORMAL)
        self.merge_btn.config(state=tk.NORMAL)
        self.status_label.config(text=f"找到 {len(self.matches)} 对匹配文件")
        
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
        self.scan_btn.config(state=tk.DISABLED)
        self.preview_btn.config(state=tk.DISABLED)
        self.merge_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
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
        success_count = 0
        
        self.progress['maximum'] = total
        self.progress['value'] = 0
        
        self.log(f"\n开始合成 {total} 个文件...")
        
        for match in self.matches:
            if not self.is_running:
                break
                
            try:
                success, message = self.merge_single(match, suffix, overwrite)
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
                    
        self.log(f"\n完成: {success_count}/{total} 成功")
        
        self.is_running = False
        self.scan_btn.config(state=tk.NORMAL)
        self.preview_btn.config(state=tk.NORMAL)
        self.merge_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_label.config(text=f"完成: {success_count}/{total} 成功")
        
        self.save_config()
        
        messagebox.showinfo("完成", f"合成完成!\n成功: {success_count}\n失败: {total - success_count}")
        
    def merge_single(self, match, suffix, overwrite):
        """合成单个文件"""
        video = match['video']
        audio = match['audio']
        
        if self.use_source_as_output.get():
            output_path = video.parent / f"{video.stem}{suffix}{video.suffix}"
        else:
            output_dir = self.output_dir.get()
            if not output_dir:
                return False, "未设置输出目录"
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
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', 
                                   errors='ignore', timeout=300)
            
            if result.returncode == 0:
                return True, str(output_path)
            else:
                error = result.stderr[-200:] if result.stderr else "未知错误"
                return False, error
        except Exception as e:
            return False, str(e)
            
    def on_closing(self):
        """窗口关闭"""
        self.save_config()
        self.root.destroy()


def main():
    """主函数"""
    root = tk.Tk()
    app = VideoAudioMergerGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
