# 视频与音轨自动匹配合成工具

一个基于 Python 和 FFmpeg 的工具，能够自动扫描目录中的视频文件和音频文件，根据文件名进行智能匹配，并将匹配的文件合成到一起。

## 功能特点

- **自动匹配**: 根据文件名自动匹配视频和音频文件
- **智能相似度匹配**: 支持模糊匹配，即使文件名略有差异也能正确配对
- **批量处理**: 支持多线程并行处理，提高效率
- **多种运行模式**: 支持命令行、交互式、GUI 三种模式
- **可打包成exe**: 提供打包脚本，可生成独立的Windows可执行文件
- **🆕 高DPI适配**: GUI版本支持高分辨率屏幕，自动缩放
- **🆕 自动检测文件夹**: 智能检测常用下载目录中的媒体文件
- **🆕 记住用户偏好**: 自动保存上次选择的文件夹和设置

## 文件说明

| 文件 | 说明 |
|------|------|
| `video_audio_merger.py` | 主程序（命令行/交互式） |
| `video_audio_merger_gui.py` | GUI版本 v1.0 |
| `video_audio_merger_gui_v2.py` | **GUI版本 v2.0（推荐）** - 支持高DPI、自动检测 |
| `build_exe.py` | 打包脚本 |
| `requirements.txt` | Python依赖 |
| `test_tool.py` | 环境测试脚本 |

## 环境要求

- Python 3.7+
- FFmpeg

### 安装FFmpeg

#### Windows
1. 下载 FFmpeg: https://ffmpeg.org/download.html
2. 解压到任意目录（如 `C:\ffmpeg`）
3. 将 `bin` 目录添加到系统 PATH，或在使用时指定路径

#### Mac
```bash
brew install ffmpeg
```

#### Linux
```bash
sudo apt install ffmpeg  # Ubuntu/Debian
sudo yum install ffmpeg  # CentOS/RHEL
```

## 使用方法

### 1. 交互式模式（推荐新手使用）

```bash
python video_audio_merger.py
```

按提示操作即可：
1. 设置FFmpeg路径（首次使用）
2. 选择要扫描的目录
3. 预览匹配结果
4. 开始合成

### 2. 命令行模式

```bash
# 快速处理当前目录
python video_audio_merger.py

# 指定目录
python video_audio_merger.py -d ./videos

# 指定FFmpeg路径
python video_audio_merger.py -d ./videos --ffmpeg "C:\ffmpeg\bin\ffmpeg.exe"

# 指定输出目录
python video_audio_merger.py -d ./videos -o ./output

# 自定义输出后缀
python video_audio_merger.py -d ./videos -s "_final"

# 设置默认FFmpeg路径
python video_audio_merger.py --set-ffmpeg "C:\ffmpeg\bin\ffmpeg.exe"
```

### 3. GUI模式（图形界面）

#### v2.0 版本（推荐 - 支持高DPI、自动检测）

```bash
python video_audio_merger_gui_v2.py
```

**v2.0 新特性：**
- ✅ **高DPI屏幕适配** - 自动检测屏幕DPI并缩放界面
- ✅ **自动检测文件夹** - 一键检测常用下载目录中的媒体文件
- ✅ **记住用户偏好** - 自动保存上次选择的文件夹和设置
- ✅ **智能输出选项** - 可选择输出到原目录或指定目录
- ✅ **打开输出目录** - 一键打开合成后的文件夹
- ✅ **日志管理** - 支持清空和保存日志

界面操作步骤：
1. 点击"自动查找"设置FFmpeg路径，或手动浏览选择
2. 点击"自动检测"选择源目录，或手动浏览选择
3. 选择输出模式（原目录或指定目录）
4. 点击"扫描文件"查看匹配结果
5. 点击"预览匹配"查看详细列表
6. 点击"开始合成"
7. 点击"打开输出目录"查看结果

#### v1.0 版本（基础GUI）

```bash
python video_audio_merger_gui.py
```

基础图形界面，适合简单使用。

## 匹配规则

工具会按照以下优先级匹配文件：

1. **完全匹配**: 文件名（不含扩展名）完全相同
   - `视频.mp4` ↔ `视频.m4a` ✓

2. **相似匹配**: 文件名相似度达到阈值（默认80%）
   - `视频_1080p.mp4` ↔ `视频_1080p.m4a` ✓
   - `视频.mp4` ↔ `视频_配音版.m4a` ✓（相似度足够高）

## 支持的格式

### 视频格式
- `.mp4`, `.avi`, `.mkv`, `.mov`, `.wmv`, `.flv`, `.webm`, `.m4v`

### 音频格式
- `.m4a`, `.mp3`, `.aac`, `.wav`, `.flac`, `.ogg`, `.wma`, `.mka`

## 打包成exe

### 方法一：使用打包脚本

```bash
# 安装依赖
pip install pyinstaller

# 运行打包脚本
python build_exe.py

# 打包成窗口模式（无控制台）
python build_exe.py --window

# 打包成目录形式（非单文件）
python build_exe.py --dir

# 指定图标
python build_exe.py --icon app.ico
```

### 方法二：手动打包

```bash
# 安装PyInstaller
pip install pyinstaller

# 打包命令行版本
pyinstaller --onefile --console video_audio_merger.py --name VideoAudioMerger

# 打包GUI v1.0版本
pyinstaller --onefile --windowed video_audio_merger_gui.py --name VideoAudioMergerGUI

# 打包GUI v2.0版本（推荐）
pyinstaller --onefile --windowed video_audio_merger_gui_v2.py --name VideoAudioMerger_v2

# 添加图标
pyinstaller --onefile --windowed --icon=app.ico video_audio_merger_gui_v2.py --name VideoAudioMerger
```

打包完成后，可执行文件位于 `dist/` 目录中。

### 打包注意事项

**高DPI屏幕适配：**
- v2.0版本已内置高DPI支持，打包后exe会自动适配
- 如果在高DPI屏幕上显示模糊，可尝试右键exe → 属性 → 兼容性 → 更改高DPI设置 → 替代高DPI缩放行为

**Windows Defender误报：**
- 如果打包后的exe被杀毒软件误报，可尝试：
  1. 使用 `--onedir` 代替 `--onefile`
  2. 添加 `--noupx` 参数禁用UPX压缩
  3. 将exe添加到杀毒软件白名单

## 输出文件命名

默认情况下，输出文件命名为：
```
原视频名_merged.mp4
```

可以通过 `--suffix` 参数自定义后缀：
```bash
python video_audio_merger.py -d ./videos -s "_final"
# 输出: 视频名_final.mp4
```

## 配置说明

工具会自动在用户目录下创建配置文件，保存用户设置，下次启动时自动加载。

### v1.0 配置文件
- 文件名: `.video_audio_merger.json`
- 保存内容: FFmpeg路径

### v2.0 配置文件
- 文件名: `.video_audio_merger_v2.json`
- 保存内容:
  - FFmpeg路径
  - 上次使用的源目录
  - 上次使用的输出目录
  - 输出后缀
  - 相似度阈值
  - 并行任务数
  - 输出模式偏好

配置文件位置：
- Windows: `C:\Users\用户名\.video_audio_merger_v2.json`
- Mac/Linux: `~/.video_audio_merger_v2.json`

**手动编辑配置：**
可以手动编辑JSON文件来修改设置：
```json
{
  "ffmpeg_path": "C:\\ffmpeg\\bin\\ffmpeg.exe",
  "source_dir": "D:\\下载",
  "output_dir": "D:\\输出",
  "output_suffix": "_merged",
  "similarity_threshold": 0.8,
  "max_workers": 2,
  "use_source_as_output": true
}
```

## 常见问题

### Q: 提示"FFmpeg路径未设置"
A: 首次使用需要设置FFmpeg路径，可以通过以下方式：
1. 交互式模式下按提示输入
2. 命令行使用 `--set-ffmpeg` 参数
3. 将FFmpeg添加到系统PATH

### Q: 找不到匹配的文件
A: 请确保：
1. 视频和音频文件在同一目录
2. 文件名足够相似（调整相似度阈值）
3. 文件格式受支持

### Q: 合成失败
A: 可能原因：
1. 视频或音频文件损坏
2. 磁盘空间不足
3. 输出文件已存在（使用 `--overwrite` 覆盖）

### Q: 打包后的exe无法运行
A: 尝试：
1. 使用 `--onedir` 代替 `--onefile`
2. 检查是否包含所有依赖
3. 在相同系统环境下打包

### Q: 高DPI屏幕上界面显示模糊
A: v2.0版本已内置高DPI支持。如果仍有问题：
1. 右键exe → 属性 → 兼容性 → 更改高DPI设置
2. 勾选"替代高DPI缩放行为"
3. 选择"应用程序"或"系统"

### Q: 自动检测找不到文件夹
A: 自动检测会扫描以下位置：
- 下载/Downloads
- 桌面/Desktop
- 视频/Videos
- 文档/Documents
- D:/下载、E:/下载等

确保媒体文件在这些目录中，或手动选择源目录。

### Q: 如何清除保存的设置
A: 删除配置文件即可：
- Windows: 删除 `C:\Users\用户名\.video_audio_merger_v2.json`
- 下次启动时将恢复默认设置

## 示例工作流

假设有以下文件：
```
下载/
├── 一念琉球.mp4      (5.69 GB)
├── 一念琉球.m4a      (212 MB)
├── 不愈之殇.mp4      (1.83 GB)
├── 不愈之殇.m4a      (104 MB)
└── ...
```

运行工具：
```bash
python video_audio_merger.py -d "下载"
```

输出结果：
```
下载/
├── 一念琉球.mp4
├── 一念琉球.m4a
├── 一念琉球_merged.mp4    ← 新生成的合成文件
├── 不愈之殇.mp4
├── 不愈之殇.m4a
├── 不愈之殇_merged.mp4    ← 新生成的合成文件
└── ...
```

## 许可证

MIT License

## 更新日志

### v2.0 (2025-02-23)
- **高DPI屏幕适配** - 自动检测屏幕DPI，界面元素智能缩放
- **自动检测文件夹** - 一键扫描常用下载目录（下载、桌面、视频等）
- **记住用户偏好** - 自动保存上次选择的源目录、输出目录和所有设置
- **智能输出选项** - 可选择输出到原目录或指定目录
- **打开输出目录** - 一键打开合成后的文件夹
- **日志管理** - 支持清空和保存日志到文件
- **FFmpeg自动查找** - 自动在常见路径和PATH中查找FFmpeg
- **界面优化** - 更清晰的统计信息和操作反馈

### v1.0
- 初始版本
- 支持自动匹配和合成
- 支持命令行、交互式、GUI三种模式
- 支持打包成exe
