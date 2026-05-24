import tkinter
from PIL import Image, ImageTk, ImageGrab

from ui.tools import Tool


class PixelCanvas(tkinter.Canvas):
    """像素画布组件，继承 tkinter.Canvas。

    功能：
      - 网格显示/隐藏
      - 缩放（zoom 属性）
      - 鼠标绘制（画笔/橡皮/取色器）
      - 参考图半透明叠加
      - 实时局部刷新
    """

    def __init__(self, parent, image_model, tool_manager, config_manager,
                 on_screen_pick=None, on_zoom_changed=None, **kwargs):
        kwargs.setdefault("highlightthickness", 0)
        kwargs.setdefault("background", "#FFFFFF")
        super().__init__(parent, **kwargs)

        self.image_model = image_model
        self.tool_manager = tool_manager
        self.config_manager = config_manager
        self._on_screen_pick_cb = on_screen_pick
        self._on_zoom_changed = on_zoom_changed

        # --- 画布状态 ---
        self.zoom = 16                 # 每像素缩放的屏幕像素数
        self.show_grid = True          # 是否显示网格

        # --- 缓存: canvas item ID 引用 ---
        self._pixel_items = []         # _pixel_items[row][col] -> canvas item ID
        self._grid_items = []          # list of line item IDs
        self._reference_item = None    # 参考图 canvas image item ID

        # --- PhotoImage 引用（tkinter 要求保持引用） ---
        self._reference_photo = None

        # --- 绘制状态 ---
        self._drawing = False
        self._last_pixel = None
        self._pan_mode = False         # 平移模式（空格键切换）

        self._setup_canvas()
        self._bind_events()
        self.refresh()

    # ==============================================================
    # 初始化
    # ==============================================================

    def _setup_canvas(self):
        """根据 image_model 和 zoom 设置画布尺寸和滚动区域。"""
        w = self.image_model.width * self.zoom
        h = self.image_model.height * self.zoom
        self.config(width=w, height=h)
        self.config(scrollregion=(0, 0, w, h))

    def _bind_events(self):
        """绑定鼠标和键盘事件。"""
        self.bind("<Button-1>", self._on_mouse_down)
        self.bind("<B1-Motion>", self._on_mouse_move)
        self.bind("<ButtonRelease-1>", self._on_mouse_up)
        # 右键快速取色/擦除
        self.bind("<Button-3>", self._on_right_click)
        # Ctrl + 滚轮缩放
        self.bind("<Control-MouseWheel>", self._on_wheel_zoom)
        # 中键平移
        self.bind("<Button-2>", self._on_middle_down)
        self.bind("<B2-Motion>", self._on_middle_move)
        self.bind("<ButtonRelease-2>", self._on_middle_up)
        # 空格键切换平移模式
        self.bind_all("<Key-space>", self._on_space_down)
        self.bind_all("<KeyRelease-space>", self._on_space_up)

    # ==============================================================
    # 坐标转换
    # ==============================================================

    def get_pixel_from_event(self, event):
        """从鼠标事件坐标反算像素坐标 (x, y)。"""
        x = event.x // self.zoom
        y = event.y // self.zoom
        return (x, y)

    # ==============================================================
    # 鼠标事件处理
    # ==============================================================

    def _on_mouse_down(self, event):
        # 平移模式：记录扫描锚点
        if self._pan_mode:
            self.scan_mark(event.x, event.y)
            self._drawing = True
            return
        # 取色器模式：拾取屏幕上任意位置的像素颜色
        if self.tool_manager.current_tool == Tool.PICKER:
            self._pick_screen_color(event.x_root, event.y_root)
            return
        px, py = self.get_pixel_from_event(event)
        # 油漆桶：泛洪填充
        if self.tool_manager.current_tool == Tool.BUCKET:
            self.image_model.begin_undo_step()
            changed = self.image_model.fill_area(px, py, self.tool_manager.color)
            for cx, cy in changed:
                self.refresh_rect(cx, cy)
            self.tool_manager.add_recent_color(self.tool_manager.color)
            return
        # 画笔/橡皮：开始新笔画 = 新撤销步骤
        self.image_model.begin_undo_step()
        self._drawing = True
        self._last_pixel = None
        self._draw_at(px, py)

    def _on_mouse_move(self, event):
        if not self._drawing:
            return
        # 平移模式：拖拽移动画布
        if self._pan_mode:
            self.scan_dragto(event.x, event.y, gain=1)
            return
        px, py = self.get_pixel_from_event(event)
        # 避免同一像素重复绘制
        if (px, py) == self._last_pixel:
            return
        self._draw_at(px, py)

    def _on_mouse_up(self, event):
        self._drawing = False
        self._last_pixel = None

    # ==============================================================
    # 右键取色 / 擦除
    # ==============================================================

    def _on_right_click(self, event):
        """右键处理：取色或擦除（取决于配置）。仅在画笔模式下响应。"""
        if self.tool_manager.current_tool != Tool.PEN:
            return
        px, py = self.get_pixel_from_event(event)
        if not (0 <= px < self.image_model.width and 0 <= py < self.image_model.height):
            return
        action = self.config_manager.get("right_click_action", "picker")
        if action == "eraser":
            self.image_model.begin_undo_step()
            affected = self.tool_manager.get_affected_pixels(px, py)
            for ax, ay in affected:
                if 0 <= ax < self.image_model.width and 0 <= ay < self.image_model.height:
                    self.image_model.set_pixel(ax, ay, (0, 0, 0, 0))
                    self.refresh_rect(ax, ay)
        else:  # "picker"
            color = self.image_model.get_pixel(px, py)
            if color:
                self.tool_manager.color = color
                self.tool_manager.add_recent_color(color)

    # ==============================================================
    # Ctrl + 滚轮缩放
    # ==============================================================

    def _on_wheel_zoom(self, event):
        """Ctrl+鼠标滚轮缩放画布。"""
        if event.delta > 0:
            self.set_zoom(self.zoom * 2)
        else:
            self.set_zoom(self.zoom // 2)

    # ==============================================================
    # 画布平移（空格 + 拖拽 / 中键拖拽）
    # ==============================================================

    def _on_middle_down(self, event):
        """中键按下：开始平移。"""
        self.scan_mark(event.x, event.y)
        self._drawing = True

    def _on_middle_move(self, event):
        """中键拖拽：平移画布。"""
        if self._drawing:
            self.scan_dragto(event.x, event.y, gain=1)

    def _on_middle_up(self, event):
        """中键释放：结束平移。"""
        self._drawing = False

    def _on_space_down(self, event):
        """空格键按下：切换到平移模式。"""
        self._pan_mode = True
        self.update_cursor()

    def _on_space_up(self, event):
        """空格键释放：退出平移模式。"""
        self._pan_mode = False
        if self._drawing:
            self._drawing = False
        self.update_cursor()

    # ==============================================================
    # 屏幕取色
    # ==============================================================

    def _pick_screen_color(self, screen_x, screen_y):
        """从屏幕坐标 (screen_x, screen_y) 抓取像素颜色。"""
        try:
            img = ImageGrab.grab(bbox=(screen_x, screen_y, screen_x + 1, screen_y + 1))
            color = img.getpixel((0, 0))
            # ImageGrab 返回 RGB，补齐 alpha 通道
            if len(color) == 3:
                color = (color[0], color[1], color[2], 255)
            self.tool_manager.color = color
            if self._on_screen_pick_cb:
                self._on_screen_pick_cb()
        except Exception:
            pass

    def _draw_at(self, x, y):
        """在 (x, y) 处执行绘制（受当前工具、大小、对称模式影响）。"""
        affected = self.tool_manager.get_affected_pixels(x, y)
        # 对称绘制：收集所有需要绘制的像素（含对称镜像）
        sym_mode = getattr(self.tool_manager, 'symmetry_mode', 'none')
        all_pixels = list(affected)
        if sym_mode in ('horizontal', 'both'):
            h = self.image_model.height
            mirror_y = lambda py: h - 1 - py
            for px, py in affected:
                all_pixels.append((px, mirror_y(py)))
        if sym_mode in ('vertical', 'both'):
            w = self.image_model.width
            for px, py in affected:
                all_pixels.append((w - 1 - px, py))
        if sym_mode == 'both':
            h = self.image_model.height
            w = self.image_model.width
            for px, py in affected:
                all_pixels.append((w - 1 - px, h - 1 - py))

        for px, py in all_pixels:
            if not (0 <= px < self.image_model.width and 0 <= py < self.image_model.height):
                continue
            if self.tool_manager.current_tool == Tool.PEN:
                self.image_model.set_pixel(px, py, self.tool_manager.color)
            elif self.tool_manager.current_tool == Tool.ERASER:
                self.image_model.set_pixel(px, py, (0, 0, 0, 0))
            self.refresh_rect(px, py)
        self._last_pixel = (x, y)

    def update_cursor(self):
        """根据当前工具和状态更新画布鼠标样式。"""
        if self._pan_mode:
            self.config(cursor="fleur")
        elif self.tool_manager.current_tool == Tool.PICKER:
            self.config(cursor="crosshair")
        elif self.tool_manager.current_tool == Tool.BUCKET:
            self.config(cursor="target")
        else:
            self.config(cursor="")

    @staticmethod
    def _rgba_to_hex(r, g, b, a):
        """将 RGBA 颜色转换为 #RRGGBB 格式，透明部分与白色背景混合。"""
        if a == 255:
            return f"#{r:02x}{g:02x}{b:02x}"
        # 与白色背景 (255, 255, 255) 进行 alpha 混合
        ratio = a / 255.0
        nr = int(r * ratio + 255 * (1 - ratio) + 0.5)
        ng = int(g * ratio + 255 * (1 - ratio) + 0.5)
        nb = int(b * ratio + 255 * (1 - ratio) + 0.5)
        nr = min(255, max(0, nr))
        ng = min(255, max(0, ng))
        nb = min(255, max(0, nb))
        return f"#{nr:02x}{ng:02x}{nb:02x}"

    # ==============================================================
    # 全量刷新 / 局部刷新
    # ==============================================================

    def refresh(self):
        """全量重绘：清理并重建所有 canvas items。"""
        self._clear_items()
        self._create_pixel_items()
        self._update_reference()
        self._update_grid()

    def refresh_rect(self, x, y):
        """局部刷新单个像素块 (x, y) 的颜色。"""
        r, g, b, a = self.image_model.get_pixel(x, y)
        fill = self._rgba_to_hex(r, g, b, a) if a > 0 else ""
        self.itemconfig(self._pixel_items[y][x], fill=fill)

    def _clear_items(self):
        """删除所有缓存的 canvas items。"""
        for row in self._pixel_items:
            for item_id in row:
                self.delete(item_id)
        self._pixel_items = []

        for item_id in self._grid_items:
            self.delete(item_id)
        self._grid_items = []

        if self._reference_item is not None:
            self.delete(self._reference_item)
            self._reference_item = None
            self._reference_photo = None

    # ==============================================================
    # 像素矩形管理
    # ==============================================================

    def _create_pixel_items(self):
        """为每个像素创建 canvas 矩形，存入 _pixel_items 二维数组。

        首次创建后，后续只通过 itemconfig 更新颜色，不新建/删除矩形。
        若 zoom 变化则需要重建（由 set_zoom 触发全量刷新）。
        """
        w = self.image_model.width
        h = self.image_model.height
        z = self.zoom
        self._pixel_items = []

        for py in range(h):
            row = []
            for px in range(w):
                r, g, b, a = self.image_model.get_pixel(px, py)
                fill = self._rgba_to_hex(r, g, b, a) if a > 0 else ""
                item = self.create_rectangle(
                    px * z, py * z,
                    px * z + z, py * z + z,
                    fill=fill,
                    outline="",
                    width=0,
                )
                row.append(item)
            self._pixel_items.append(row)

    # ==============================================================
    # 网格
    # ==============================================================

    def set_show_grid(self, show: bool):
        """切换网格显示。"""
        self.show_grid = show
        self._update_grid()

    def _update_grid(self):
        """根据当前 show_grid 状态更新网格线。"""
        # 删除旧网格线
        for item_id in self._grid_items:
            self.delete(item_id)
        self._grid_items = []

        if not self.show_grid:
            return

        w = self.image_model.width
        h = self.image_model.height
        z = self.zoom

        # 竖线
        for x in range(w + 1):
            line = self.create_line(
                x * z, 0, x * z, h * z,
                fill=self.config_manager.get("grid_color", "#AAAAAA"), width=1,
            )
            self._grid_items.append(line)

        # 横线
        for y in range(h + 1):
            line = self.create_line(
                0, y * z, w * z, y * z,
                fill=self.config_manager.get("grid_color", "#AAAAAA"), width=1,
            )
            self._grid_items.append(line)

        # 确保网格在最顶层
        for item_id in self._grid_items:
            self.tag_raise(item_id)

    # ==============================================================
    # 缩放
    # ==============================================================

    def set_zoom(self, z: int):
        """重新计算画布尺寸并刷新。"""
        z = max(1, min(64, z))
        if z == self.zoom:
            return
        self.zoom = z
        w = self.image_model.width * self.zoom
        h = self.image_model.height * self.zoom
        self.config(width=w, height=h)
        self.config(scrollregion=(0, 0, w, h))
        # 全量刷新（需要重建像素矩形和参考图）
        self.refresh()
        # 通知外部缩放变化（如更新缩放百分比显示）
        if self._on_zoom_changed:
            self._on_zoom_changed()

    # ==============================================================
    # 参考图叠加层
    # ==============================================================

    def set_reference_image(self, img: Image.Image | None):
        """设置/清除参考图。

        参考图作为半透明叠加层渲染在像素上方（网格下方）。
        img 为 None 时清除参考图。
        """
        # 清除旧的参考图
        if self._reference_item is not None:
            self.delete(self._reference_item)
            self._reference_item = None
            self._reference_photo = None

        if img is None:
            return

        canvas_w = self.image_model.width * self.zoom
        canvas_h = self.image_model.height * self.zoom

        # 缩放到画布尺寸（使用 NEAREST 保持像素风格）
        resized = img.resize((canvas_w, canvas_h), Image.NEAREST)

        # 确保为 RGBA 模式
        if resized.mode != "RGBA":
            resized = resized.convert("RGBA")

        # 对 alpha 通道应用透明度系数
        opacity = self.tool_manager.reference_opacity
        r_ch, g_ch, b_ch, a_ch = resized.split()
        a_ch = a_ch.point(lambda v: int(v * opacity))
        blended = Image.merge("RGBA", (r_ch, g_ch, b_ch, a_ch))

        self._reference_photo = ImageTk.PhotoImage(blended)
        self._reference_item = self.create_image(
            0, 0,
            anchor="nw",
            image=self._reference_photo,
        )
        # 将参考图置于像素之上、网格之下
        if self._grid_items:
            for item_id in self._grid_items:
                self.tag_raise(item_id)

    def _update_reference(self):
        """重新应用当前参考图（在 zoom 变化后调用）。"""
        ref = self.tool_manager.reference_image
        if ref is not None:
            self.set_reference_image(ref)
