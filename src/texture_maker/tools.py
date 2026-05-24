from enum import Enum, auto


class Tool(Enum):
    PEN = auto()       # 画笔
    ERASER = auto()    # 橡皮
    PICKER = auto()    # 取色器（点击画布取色）
    BUCKET = auto()    # 油漆桶（填充连通区域）


class ToolManager:
    """管理当前工具、颜色、大小和参考图状态。"""

    def __init__(self):
        self.current_tool = Tool.PEN
        self.color = (0, 0, 0, 255)   # 当前颜色 RGBA
        self.size = 1                  # 工具大小（1-16）
        self.reference_image = None    # PIL.Image 参考图
        self.reference_opacity = 0.3   # 参考图透明度
        self.symmetry_mode: str = "none"          # 对称模式："none" / "horizontal" / "vertical"
        self.recent_colors: list = []             # 最近使用的 RGBA 颜色列表，上限 16 个

    def add_recent_color(self, color: tuple) -> None:
        """添加 RGBA 颜色到最近使用列表，去重，超过 16 个则移除最旧的一个。"""
        # 如果已存在则先移除（移到最前面）
        if color in self.recent_colors:
            self.recent_colors.remove(color)
        # 插入到最前面
        self.recent_colors.insert(0, color)
        # 截断到上限 16
        if len(self.recent_colors) > 16:
            self.recent_colors = self.recent_colors[:16]

    def get_affected_pixels(self, x: int, y: int):
        """返回画笔/橡皮影响的所有 (px, py) 坐标列表。

        以 (x, y) 为中心，覆盖范围由 self.size 决定。
        奇数尺寸精确居中，偶数尺寸略微偏左上方（通用绘图软件惯例）。
        """
        half = self.size // 2
        x_start = x - half
        x_end = x + (self.size - 1) - half
        y_start = y - half
        y_end = y + (self.size - 1) - half
        pixels = []
        for py in range(y_start, y_end + 1):
            for px in range(x_start, x_end + 1):
                pixels.append((px, py))
        return pixels
