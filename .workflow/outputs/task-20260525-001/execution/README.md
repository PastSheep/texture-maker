# executor-3 产出物说明

## 创建的文件

### `ui/welcome_screen.py` — 欢迎页
- 标题 "Texture Maker"（大号字体）
- 三个按钮：New Project / Open Project / Recent Projects 列表
- RecentItemRow 组件：每个最近项目显示文件名，左侧点击打开，右侧 X 按钮删除
- 从 `Application.config.get_recent()` 读取列表
- Open Project 通过 `filedialog.askopenfilename` 选择 PNG 并验证尺寸 ≤128×128

### `ui/new_project_dialog.py` — 新建项目对话框
- 模态 Toplevel 对话框
- MC 预设按钮 3×2 网格：16, 32, 48, 64, 96, 128
- 自定义尺寸 Spinbox（1-128）
- 保存位置浏览按钮
- 文件名输入（自动补 .png）
- 确认校验后调用 `app.new_project(path, w, h)`

### `ui/palette.py` — 调色板面板
- A: 6 组预设色系（Metal/Ore/Gem/Nature/Basic/Gray），每组 8 色，可折叠
- B: 当前颜色 40×40 预览 + RGB/HEX 显示
- C: RGBA Slider（R/G/B/A Scale 0-255），实时更新
- D: 自定义色板（从 ConfigManager 读写），添加按钮 + 右键删除
- E: 从图片提取颜色（Pillow 取频率最高 16 色，弹出 Toplevel 点选添加）
- F: 取色器工具按钮（同步到工具栏）

### `ui/main_window.py` — 主编辑器窗口
- PanedWindow 横向分割：左侧 PalettePanel（240px）+ 右侧编辑器
- 菜单栏：文件（保存/另存为/关闭）、编辑（撤销/重做占位）、视图（缩放/网格）、帮助（关于）
- 工具栏：Pen/Eraser/Picker 互斥 Radiobutton、大小 Spinbox、缩放显示 Label、参考图加载/清除/透明度 Scale
- PixelCanvas + 滚动条
- 键盘快捷键：Ctrl+S（保存）、Ctrl+Shift+S（另存为）、Ctrl+W（关闭）、Ctrl+=/Ctrl+-/Ctrl+0（缩放）、Ctrl+G（网格切换）
- 标题栏轮询更新：`*文件名.png - Texture Maker`（已修改时）
- 保存流程：Ctrl+S 直接保存 / Ctrl+Shift+S 另存为

## 修改的文件

### `config.py` — 添加了 6 个新方法
- `remove_recent(path)` — 从最近列表中移除
- `get_custom_colors()` / `add_custom_color()` / `remove_custom_color()` — 自定义色板管理
- `set_tool_size()` / `get_tool_size()` — 工具大小持久化

### `app.py` — 完整的 Application 类
- `show_welcome()` — 显示欢迎页（启动时自动显示）
- `show_editor()` — 切换到编辑器
- `open_project(path)` — 加载 PNG → 创建 ToolManager → 显示编辑器
- `new_project(path, w, h)` — 创建空白画布 → 立即保存 → 显示编辑器
- `close_current()` — 检查修改 → 弹窗 [保存] [放弃] [取消] → 返回 bool
- `_clear_ui()` — 销毁当前 UI 并重置菜单栏
- `_on_quit()` — 窗口关闭处理

## 接口兼容性

- 使用 `Tool.PEN`（executor-2 的 enum，非 BRUSH）
- 使用 `tool_manager.color` / `.size` / `.current_tool`（executor-2 的 ToolManager 属性）
- 使用 `ImageModel.from_file()` / `from_size()` 类方法（executor-1 的接口）
- 使用 `canvas.set_zoom()` / `set_show_grid()` / `set_reference_image()`（executor-2 的 PixelCanvas）
- PalettePanel 通过 `on_tool_change` 回调与 MainWindow 工具栏同步
