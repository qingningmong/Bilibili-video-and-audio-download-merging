#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频与音轨自动匹配合成工具 - GUI版本
使用tkinter提供图形界面
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


class VideoAudioMergerGUI:
    """视频音频合成工具的GUI版本"""
    
    VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
    AUDIO_EXTENSIONS = {'.m4a', '.mp3', '.aac', '.wav', '.flac', '.ogg', '.wma', '.mka'}
    
    def __init__(self, root):
        self.root = root
        self.root.title("视频与音轨自动匹配合成工具 v1.0")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # 初始化变量
        self.ffmpeg_path = tk.StringVar()
        self.source_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.output_suffix = tk.StringVar(value='_merged')
        self.similarity_threshold = tk.DoubleVar(value=0.8)
        self.max_workers = tk.IntVar(value=2)
        self.overwrite = tk.BooleanVar(value=False)
        
        self.matches = []
        self.is_running = False
        
        # 加载配置
        self.config_file = Path.home() / '.video_audio_merger.json'
        self.load_config()
        
        # 创建界面
        self.create_widgets()
        
        # 检查FFmpeg
        self.root.after(100, self.check_ffmpeg_on_startup)
        
    def load_config(self):
        """加载配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if config.get('ffmpeg_path'):
                        self.ffmpeg_path.set(config['ffmpeg_path'])
            except:
                pass
                
    def save_config(self):
        """保存配置"""
        config = {'ffmpeg_path': self.ffmpeg_path.get()}
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except:
            pass
            
    def check_ffmpeg_on_startup(self):
        """启动时检查FFmpeg"""
        if self.ffmpeg_path.get():
            self.verify_ffmpeg()
            
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # ===== FFmpeg设置 =====
        ffmpeg_frame = ttk.LabelFrame(main_frame, text="FFmpeg 设置", padding="10")
        ffmpeg_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        ffmpeg_frame.columnconfigure(1, weight=1)
        
        ttk.Label(ffmpeg_frame, text="FFmpeg 路径:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(ffmpeg_frame, textvariable=self.ffmpeg_path).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(ffmpeg_frame, text="浏览...", command=self.browse_ffmpeg).grid(row=0, column=2)
        ttk.Button(ffmpeg_frame, text="验证", command=self.verify_ffmpeg).grid(row=0, column=3, padx=5)
        
        self.ffmpeg_status = ttk.Label(ffmpeg_frame, text="未验证", foreground="red")
        self.ffmpeg_status.grid(row=1, column=0, columnspan=4, sticky=tk.W, pady=(5, 0))
        
        # ===== 目录设置 =====
        dir_frame = ttk.LabelFrame(main_frame, text="目录设置", padding="10")
        dir_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        dir_frame.columnconfigure(1, weight=1)
        
        # 源目录
        ttk.Label(dir_frame, text="源目录:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(dir_frame, textvariable=self.source_dir).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(dir_frame, text="浏览...", command=self.browse_source_dir).grid(row=0, column=2)
        
        # 输出目录
        ttk.Label(dir_frame, text="输出目录:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        ttk.Entry(dir_frame, textvariable=self.output_dir).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=(5, 0))
        ttk.Button(dir_frame, text="浏览...", command=self.browse_output_dir).grid(row=1, column=2, pady=(5, 0))
        
        # 使用原目录选项
        ttk.Checkbutton(dir_frame, text="输出到原目录", 
                       command=self.toggle_output_dir).grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))
        
        # ===== 选项设置 =====
        options_frame = ttk.LabelFrame(main_frame, text="选项设置", padding="10")
        options_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(options_frame, text="输出后缀:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(options_frame, textvariable=self.output_suffix, width=15).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(options_frame, text="相似度阈值:").grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        ttk.Spinbox(options_frame, from_=0.5, to=1.0, increment=0.05, 
                   textvariable=self.similarity_threshold, width=8).grid(row=0, column=3, sticky=tk.W, padx=5)
        
        ttk.Label(options_frame, text="并行任务:").grid(row=0, column=4, sticky=tk.W, padx=(20, 0))
        ttk.Spinbox(options_frame, from_=1, to=4, increment=1, 
                   textvariable=self.max_workers, width=8).grid(row=0, column=5, sticky=tk.W, padx=5)
        
        ttk.Checkbutton(options_frame, text="覆盖已存在文件", 
                       variable=self.overwrite).grid(row=0, column=6, sticky=tk.W, padx=(20, 0))
        
        # ===== 操作按钮 =====
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=10)
        
        self.scan_btn = ttk.Button(button_frame, text="扫描文件", command=self.scan_files, width=15)
        self.scan_btn.pack(side=tk.LEFT, padx=5)
        
        self.preview_btn = ttk.Button(button_frame, text="预览匹配", command=self.preview_matches, 
                                     width=15, state=tk.DISABLED)
        self.preview_btn.pack(side=tk.LEFT, padx=5)
        
        self.merge_btn = ttk.Button(button_frame, text="开始合成", command=self.start_merge, 
                                   width=15, state=tk.DISABLED)
        self.merge_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="停止", command=self.stop_merge, 
                                  width=15, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # ===== 日志区域 =====
        log_frame = ttk.LabelFrame(main_frame, text="日志", padding="5")
        log_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # ===== 进度条 =====
        self.progress = ttk.Progressbar(main_frame, mode='determinate')
        self.progress.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        self.status_label = ttk.Label(main_frame, text="就绪")
        self.status_label.grid(row=6, column=0, columnspan=3, sticky=tk.W)
        
    def toggle_output_dir(self):
        """切换输出目录选项"""
        if self.output_dir.get():
            self.output_dir.set('')
        else:
            self.browse_output_dir()
            
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
            
    def browse_output_dir(self):
        """浏览选择输出目录"""
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            self.output_dir.set(path)
            
    def verify_ffmpeg(self):
        """验证FFmpeg"""
        path = self.ffmpeg_path.get()
        if not path or not Path(path).exists():
            self.ffmpeg_status.config(text="FFmpeg 路径无效", foreground="red")
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
                self.ffmpeg_status.config(text=f"✓ {version[:60]}...", foreground="green")
                self.save_config()
                return True
            else:
                self.ffmpeg_status.config(text="FFmpeg 无法正常运行", foreground="red")
                return False
        except Exception as e:
            self.ffmpeg_status.config(text=f"验证失败: {e}", foreground="red")
            return False
            
    def log(self, message):
        """添加日志"""
        self.log_text.insert(tk.END, message + '\n')
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
            return
            
        # 匹配文件
        self.matches = self.match_files(video_files, audio_files)
        
        if not self.matches:
            self.log("未找到匹配的文件对")
            messagebox.showinfo("提示", "未找到匹配的文件对")
            self.status_label.config(text="扫描完成 - 未找到匹配")
            return
            
        exact_count = sum(1 for m in self.matches if m['match_type'] == 'exact')
        similar_count = len(self.matches) - exact_count
        
        self.log(f"\n匹配结果:")
        self.log(f"  完全匹配: {exact_count}")
        self.log(f"  相似匹配: {similar_count}")
        self.log(f"  总计: {len(self.matches)}")
        
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
            
        preview_window = tk.Toplevel(self.root)
        preview_window.title("匹配结果预览")
        preview_window.geometry("800x500")
        
        # 创建表格
        columns = ('#', '类型', '视频文件', '音频文件', '相似度')
        tree = ttk.Treeview(preview_window, columns=columns, show='headings')
        
        tree.heading('#', text='#')
        tree.heading('类型', text='类型')
        tree.heading('视频文件', text='视频文件')
        tree.heading('音频文件', text='音频文件')
        tree.heading('相似度', text='相似度')
        
        tree.column('#', width=40)
        tree.column('类型', width=80)
        tree.column('视频文件', width=300)
        tree.column('音频文件', width=300)
        tree.column('相似度', width=60)
        
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
        output_dir = self.output_dir.get() or None
        suffix = self.output_suffix.get()
        overwrite = self.overwrite.get()
        max_workers = self.max_workers.get()
        
        total = len(self.matches)
        success_count = 0
        
        self.progress['maximum'] = total
        self.progress['value'] = 0
        
        self.log(f"\n开始合成 {total} 个文件...")
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
        
        messagebox.showinfo("完成", f"合成完成!\n成功: {success_count}\n失败: {total - success_count}")
        
    def merge_single(self, match, output_dir, suffix, overwrite):
        """合成单个文件"""
        video = match['video']
        audio = match['audio']
        
        if output_dir:
            output_path = Path(output_dir) / f"{video.stem}{suffix}{video.suffix}"
        else:
            output_path = video.parent / f"{video.stem}{suffix}{video.suffix}"
            
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
