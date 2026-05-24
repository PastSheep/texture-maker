# 贴图工坊 (Texture Maker)

Minecraft 模组像素图绘制工具。基于 Python + tkinter + Pillow 构建。

## 功能

- **项目管理**：IDEA 式欢迎页，新建/打开 PNG 项目，最近项目列表
- **画布**：1-128 px，MC 尺寸预设 (16/32/48/64/96/128)，缩放 (1x-64x)，网格叠加，透明背景
- **绘制工具**：画笔、橡皮、油漆桶（泛洪填充）、取色器（屏幕取色），可调大小 1-16 px
- **调色板**：预设色板 (46 色按色相排序)、RGBA 滑块、自定义色板、图片颜色提取、最近使用颜色
- **参考图**：半透明叠加层，可调透明度
- **对称绘制**：水平/垂直镜像
- **撤销/重做**：50 步历史栈
- **画布平移**：空格拖拽 / 中键拖拽
- **1:1 预览窗**：实时像素预览
- **导出**：2x / 4x / 8x PNG（Nearest-Neighbor 放大）
- **快捷键**：B/E/I/G 切换工具，`[`/`]` 调笔刷，Ctrl+Z/Y 撤销重做，Ctrl+滚轮缩放
- **自愈配置**：JSON 配置文件损坏时自动修复，原子写入防损坏

## 截图

> 运行 `python main.py` 启动后可见完整界面。

## 安装与运行

```bash
# 克隆仓库
git clone https://github.com/PastSheep/texture-maker.git
cd texture-maker

# 创建虚拟环境并安装依赖
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS / Linux
pip install Pillow

# 运行
python main.py
```

或使用 `pyproject.toml`：

```bash
pip install -e .
texture-maker
```

## 项目结构

```
texture-making/
├── main.py                         # 入口
├── pyproject.toml                  # 项目元数据 & 依赖
├── tests/                          # 单元测试
├── src/texture_maker/
│   ├── app.py                      # Application 控制器
│   ├── config.py                   # ConfigManager（JSON 持久化）
│   ├── image_model.py              # ImageModel（像素数据 + 撤销/重做）
│   ├── tools.py                    # Tool 枚举 & ToolManager
│   └── ui/
│       ├── canvas_widget.py        # 像素画布组件
│       ├── main_window.py          # 主编辑器窗口
│       ├── new_project_dialog.py   # 新建项目对话框
│       ├── palette.py              # 调色板面板
│       └── welcome_screen.py       # 欢迎页
└── .gitignore
```

## 运行测试

```bash
pip install pytest
pytest tests/ -v
```

## 开发说明

本项目由 **Claude Code**（模型 deepseek-v4-pro）作为 AI 辅助开发工具全程编写，采用 superwork 多 Agent 协作工作流（执行组 + 审查组 + 驳回循环）。

## 许可

MIT License
