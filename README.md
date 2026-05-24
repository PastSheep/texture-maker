# Texture Maker / 贴图工坊

A Minecraft mod pixel art drawing tool built with Python + tkinter + Pillow.

Minecraft 模组像素图绘制工具，基于 Python + tkinter + Pillow 构建。

## Features / 功能

- **Project Management** — IDEA-style welcome screen, new/open PNG projects, recent files list
  **项目管理** — IDEA 式欢迎页，新建/打开 PNG 项目，最近项目列表
- **Canvas** — 1-128 px, MC size presets (16/32/48/64/96/128), zoom (1x-64x), grid overlay, transparent background
  **画布** — MC 尺寸预设，缩放，网格叠加，透明背景
- **Drawing Tools** — pen, eraser, bucket (flood fill), eyedropper (screen picker), adjustable size 1-16 px
  **绘制工具** — 画笔、橡皮、油漆桶（泛洪填充）、取色器（屏幕取色），可调大小
- **Palette** — 46 preset colors sorted by hue, RGBA sliders, custom palette, extract from image, recent colors
  **调色板** — 预设色板按色相排序、RGBA 滑块、自定义色板、图片颜色提取、最近使用颜色
- **Reference Image** — semi-transparent overlay with adjustable opacity
  **参考图** — 半透明叠加层，可调透明度
- **Symmetry Drawing** — horizontal / vertical mirror
  **对称绘制** — 水平/垂直镜像
- **Undo/Redo** — 50-step history stack
  **撤销/重做** — 50 步历史栈
- **Canvas Panning** — Space+drag / middle-button drag
  **画布平移** — 空格拖拽 / 中键拖拽
- **1:1 Preview** — real-time pixel preview window
  **1:1 预览窗** — 实时像素预览
- **Export** — 2x / 4x / 8x PNG with Nearest-Neighbor scaling
  **导出** — Nearest-Neighbor 放大导出
- **Keyboard Shortcuts** — B/E/I/G for tools, `[`/`]` for brush size, Ctrl+Z/Y undo/redo, Ctrl+scroll zoom
  **快捷键** — B/E/I/G 切换工具，`[`/`]` 调笔刷，Ctrl+Z/Y 撤销重做，Ctrl+滚轮缩放
- **Self-healing Config** — corrupted JSON config auto-repaired, atomic writes
  **自愈配置** — JSON 配置损坏自动修复，原子写入

## Screenshots / 截图

> Run `python main.py` to see the full interface.
> 运行 `python main.py` 启动查看完整界面。

## Install & Run / 安装与运行

```bash
# Clone / 克隆
git clone https://github.com/PastSheep/texture-maker.git
cd texture-maker

# Create venv & install / 创建虚拟环境并安装
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS / Linux
pip install Pillow

# Run / 运行
python main.py
```

Or via `pyproject.toml` / 或通过 `pyproject.toml`：

```bash
pip install -e .
texture-maker
```

## Project Structure / 项目结构

```
texture-making/
├── main.py                         # entry / 入口
├── pyproject.toml                  # metadata & deps / 元数据与依赖
├── tests/                          # unit tests / 单元测试
├── src/texture_maker/
│   ├── app.py                      # Application controller / 应用控制器
│   ├── config.py                   # ConfigManager (JSON persistence) / JSON 持久化
│   ├── image_model.py              # ImageModel (pixel data + undo/redo) / 像素数据+撤销重做
│   ├── tools.py                    # Tool enum & ToolManager / 工具枚举与管理
│   └── ui/
│       ├── canvas_widget.py        # pixel canvas widget / 像素画布组件
│       ├── main_window.py          # main editor window / 主编辑器窗口
│       ├── new_project_dialog.py   # new project dialog / 新建项目对话框
│       ├── palette.py              # palette panel / 调色板面板
│       └── welcome_screen.py       # welcome screen / 欢迎页
└── .gitignore
```

## Tests / 测试

```bash
pip install pytest
pytest tests/ -v
```

## Credits / 开发说明

This project was developed entirely by **Claude Code** (model deepseek-v4-pro) as an AI-assisted development tool, using the superwork multi-agent collaborative workflow (execution group + review group + reject loop).

本项目由 **Claude Code**（模型 deepseek-v4-pro）作为 AI 辅助开发工具全程编写，采用 superwork 多 Agent 协作工作流（执行组 + 审查组 + 驳回循环）。

## License / 许可

MIT
