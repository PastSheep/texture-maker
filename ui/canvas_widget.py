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

    def __init__(self, parent, image_model, tool_manager, config_manager, on_screen_pick=None, **kwargs):
        kwargs.setdefault("highlightthickness", 0)
        kwargs.setdefault("background", "#FFFFFF")
        super().__init__(parent, **kwargs)

        self.image_model = image_model
        self.tool_manager = tool_manager
        self.config_manager = config_manager
        self._on_screen_pick_cb = on_screen_pick

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

        self._setup_canvas()
        self._bind_events()
        self.refresh()

    # ==============================================================
    # 初始化
    # ==============================================================

    def _setup_canvas(self):
        """根据 image_model 和 zoom 设置画布尺寸。"""
        w = self.image_model.width * self.zoom
        h = self.image_model.height * self.zoom
        self.config(width=w, height=h)

    def _bind_events(self):
        """绑定鼠标事件。"""
        self.bind("<Button-1>", self._on_mouse_down)
        self.bind("<B1-Motion>", self._on_mouse_move)
        self.bind("<ButtonRelease-1>", self._on_mouse_up)

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
        # 取色器模式：拾取屏幕上任意位置的像素颜色
        if self.tool_manager.current_tool == Tool.PICKER:
            self._pick_screen_color(event.x_root, event.y_root)
            return
        px, py = self.get_pixel_from_event(event)
        self._drawing = True
        self._last_pixel = None
        self._draw_at(px, py)

    def _on_mouse_move(self, event):
        if not self._drawing:
            return
        px, py = self.get_pixel_from_event(event)
        # 避免同一像素重复绘制
        if (px, py) == self._last_pixel:
            return
        self._draw_at(px, py)

    def _on_mouse_up(self, event):
        self._drawing = False
        self._last_pixel = None

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
        """在 (x, y) 处执行绘制（受当前工具、大小影响）。"""
        affected = self.tool_manager.get_affected_pixels(x, y)
        for px, py in affected:
            if not (0 <= px < self.image_model.width and 0 <= py < self.image_model.height):
                continue
            if self.tool_manager.current_tool == Tool.PEN:
                self.image_model.set_pixel(px, py, self.tool_manager.color)
            elif self.tool_manager.current_tool == Tool.ERASER:
                self.image_model.set_pixel(px, py, (0, 0, 0, 0))
            self.refresh_rect(px, py)
        self._last_pixel = (x, y)

    def update_cursor(self):
        """根据当前工具更新画布鼠标样式。"""
        if self.tool_manager.current_tool == Tool.PICKER:
            self.config(cursor="crosshair")
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
        # 全量刷新（需要重建像素矩形和参考图）
        self.refresh()

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
