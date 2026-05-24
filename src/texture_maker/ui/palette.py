"""PalettePanel -- vertical colour palette panel for Texture Maker.

Contains:
  A. Preset colour swatches (flat grid)
  B. Current colour preview with RGB/HEX readout
  C. RGB + Alpha sliders
  D. Custom palette (from config, with add/remove)
  E. Extract-from-image button
  F. Colour picker tool button
"""

import tkinter
from tkinter import filedialog, messagebox
from collections import Counter
import colorsys

from PIL import Image

from texture_maker.tools import Tool

# ---------------------------------------------------------------------------
# Built-in colour presets (Minecraft-themed)
# ---------------------------------------------------------------------------

PRESET_COLORS = [
    "#C0C0C0", "#808080", "#FFD700", "#CD7F32",
    "#A0A0A0", "#E8E8E8", "#B87333", "#D4AF37",
    "#6B8E23", "#8B4513", "#A0522D", "#CD853F",
    "#D2691E", "#B8860B", "#556B2F", "#8B0000",
    "#FF0000", "#00FF00", "#0000FF", "#00FFFF",
    "#FF00FF", "#7FFFD4", "#4B0082", "#FF1493",
    "#228B22", "#8B4513", "#F5F5DC", "#87CEEB",
    "#808080", "#2F4F4F", "#D2B48C", "#778899",
    "#000000", "#FFFFFF", "#FF0000", "#00FF00",
    "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF",
    "#333333", "#666666", "#999999",
    "#CCCCCC", "#1A1A1A", "#4D4D4D",
]


class PalettePanel(tkinter.Frame):
    """Vertical colour palette docked to the left of the editor."""

    def __init__(self, parent, tool_manager, config_manager, on_tool_change=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.tool_manager = tool_manager
        self.config_manager = config_manager
        self._on_tool_change_cb = on_tool_change
        self._custom_refresh_job = None
        self._recent_colors = []  # internal list of RGBA tuples, newest first
        self._has_recent_colors_api = hasattr(tool_manager, 'add_recent_color')

        self.configure(width=240)
        self.pack_propagate(False)

        self._build_ui()
        self._sync_from_tool_manager()

    # ==================================================================
    # UI construction
    # ==================================================================

    def _build_ui(self):
        self._build_current_color()
        self._build_rgb_sliders()
        self._build_preset_categories()
        self._build_recent_colors()
        self._build_custom_palette()
        self._build_action_buttons()

    # ----------------------------------------------------------------
    # A. Current colour preview
    # ----------------------------------------------------------------

    def _build_current_color(self):
        frame = tkinter.LabelFrame(self, text="当前颜色", padx=6, pady=5)
        frame.pack(fill="x", padx=5, pady=(5, 2))

        row = tkinter.Frame(frame)
        row.pack(fill="x")

        self._color_preview = tkinter.Canvas(
            row, width=40, height=40,
            highlightthickness=1, highlightbackground="#aaa",
        )
        self._color_preview.pack(side="left", padx=(0, 8))

        self._color_info = tkinter.Label(
            row,
            text="#000000\nR:0  G:0  B:0  A:255",
            justify="left",
            font=("Courier", 9),
        )
        self._color_info.pack(side="left")

    # ----------------------------------------------------------------
    # C. RGB + Alpha sliders
    # ----------------------------------------------------------------

    def _build_rgb_sliders(self):
        frame = tkinter.LabelFrame(self, text="RGBA 颜色生成器", padx=6, pady=5)
        frame.pack(fill="x", padx=5, pady=2)

        self._slider_vars = {}
        for label, default in [("R", 0), ("G", 0), ("B", 0), ("A", 255)]:
            sub = tkinter.Frame(frame)
            sub.pack(fill="x", pady=1)

            tkinter.Label(sub, text=label, width=2, anchor="e").pack(side="left")

            var = tkinter.IntVar(value=default)
            self._slider_vars[label.lower()] = var

            scale = tkinter.Scale(
                sub,
                from_=0,
                to=255,
                orient="horizontal",
                variable=var,
                command=self._on_slider_change,
                showvalue=False,
                length=130,
            )
            scale.pack(side="left", padx=3)

            val_label = tkinter.Label(
                sub, textvariable=var, width=3, font=("Courier", 9)
            )
            val_label.pack(side="left")

    # ----------------------------------------------------------------
    # B. Preset swatches (flat grid)
    # ----------------------------------------------------------------

    def _build_preset_categories(self):
        frame = tkinter.LabelFrame(self, text="预设色板", padx=4, pady=3)
        frame.pack(fill="x", padx=5, pady=2)

        # 按色相→饱和度→明度排序
        def _hsv_key(hex_color):
            h = hex_color.lstrip("#")
            r, g, b = int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0
            h_val, s_val, v_val = colorsys.rgb_to_hsv(r, g, b)
            return (h_val, s_val, v_val)

        sorted_colors = sorted(PRESET_COLORS, key=_hsv_key)

        cols = 8
        for i, hex_color in enumerate(sorted_colors):
            r = i // cols
            c = i % cols
            swatch = tkinter.Canvas(
                frame,
                width=22,
                height=22,
                highlightthickness=1,
                highlightbackground="#ccc",
                cursor="hand2",
            )
            swatch.grid(row=r, column=c, padx=1, pady=1)
            swatch.create_rectangle(0, 0, 22, 22, fill=hex_color, outline="")
            swatch.bind(
                "<Button-1>",
                lambda _e, h=hex_color: self._on_color_click(h),
            )

    # ----------------------------------------------------------------
    # D. Custom palette
    # ----------------------------------------------------------------

    def _build_custom_palette(self):
        frame = tkinter.LabelFrame(self, text="自定义色板", padx=4, pady=3)
        frame.pack(fill="x", padx=5, pady=2)

        self._custom_container = tkinter.Frame(frame)
        self._custom_container.pack()

        add_btn = tkinter.Button(
            frame,
            text="添加当前颜色",
            command=self._on_add_custom,
        )
        add_btn.pack(pady=3, fill="x")

        hint = tkinter.Label(
            frame,
            text="右键点击色块删除",
            fg="#999",
            font=("TkDefaultFont", 8),
        )
        hint.pack()

        self._refresh_custom()

    def _refresh_custom(self):
        for w in self._custom_container.winfo_children():
            w.destroy()

        colors = self.config_manager.get_custom_colors()
        if not colors:
            empty = tkinter.Label(
                self._custom_container,
                text="（空）",
                fg="#999",
                font=("TkDefaultFont", 9),
            )
            empty.pack()
            return

        cols = 8
        for i, hex_color in enumerate(colors):
            r = i // cols
            c = i % cols
            swatch = tkinter.Canvas(
                self._custom_container,
                width=24,
                height=24,
                highlightthickness=1,
                highlightbackground="#ccc",
                cursor="hand2",
            )
            swatch.grid(row=r, column=c, padx=2, pady=2)
            swatch.create_rectangle(0, 0, 24, 24, fill=hex_color, outline="")
            swatch.bind(
                "<Button-1>",
                lambda _e, h=hex_color: self._on_color_click(h),
            )
            swatch.bind(
                "<Button-3>",
                lambda _e, h=hex_color: self._on_remove_custom(h),
            )

    # ----------------------------------------------------------------
    # E. Extract from image
    # ----------------------------------------------------------------

    def _on_extract(self):
        path = filedialog.askopenfilename(
            title="从图片提取颜色",
            filetypes=[("PNG files", "*.png")],
        )
        if not path:
            return

        try:
            img = Image.open(path).convert("RGBA")
        except Exception as exc:
            messagebox.showerror("错误", f"无法打开图片：\n{exc}")
            return

        pixels = img.load()
        counter = Counter()

        for y in range(img.height):
            for x in range(img.width):
                r, g, b, a = pixels[x, y]
                if a < 128:  # skip mostly transparent pixels
                    continue
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
                counter[hex_color] += 1

        if not counter:
            messagebox.showinfo(
                "未提取到颜色",
                "图片中未提取到足够不透明的像素颜色。",
            )
            return

        # Top 16 most frequent colours
        top_colors = [c for c, _ in counter.most_common(16)]

        # Show in popup
        self._show_extracted_colors(top_colors)

    def _show_extracted_colors(self, colors):
        top = tkinter.Toplevel(self)
        top.title("提取的颜色")
        top.transient(self.winfo_toplevel())
        top.grab_set()

        tkinter.Label(
            top,
            text="点击颜色将其添加到自定义色板：",
            font=("TkDefaultFont", 10),
        ).pack(pady=(8, 4))

        cf = tkinter.Frame(top)
        cf.pack(padx=12, pady=6)

        cols = 8
        for i, hex_color in enumerate(colors):
            r = i // cols
            c = i % cols
            swatch = tkinter.Canvas(
                cf,
                width=24,
                height=24,
                highlightthickness=1,
                highlightbackground="#ccc",
                cursor="hand2",
            )
            swatch.grid(row=r, column=c, padx=2, pady=2)
            swatch.create_rectangle(0, 0, 28, 28, fill=hex_color, outline="")
            swatch.bind(
                "<Button-1>",
                lambda _e, h=hex_color, t=top: self._on_extracted_click(h, t),
            )

        tkinter.Button(top, text="关闭", command=top.destroy).pack(pady=(4, 8))

        top.update_idletasks()
        top.minsize(top.winfo_width(), top.winfo_height())

    def _on_extracted_click(self, hex_color, popup):
        self._on_color_click(hex_color)
        self.config_manager.add_custom_color(hex_color)
        self._refresh_custom()
        popup.destroy()

    # ----------------------------------------------------------------
    # F. Action buttons
    # ----------------------------------------------------------------

    def _build_action_buttons(self):
        extract_btn = tkinter.Button(
            self,
            text="从图片提取",
            command=self._on_extract,
        )
        extract_btn.pack(fill="x", padx=5, pady=2)

    # ==================================================================
    # Colour selection
    # ==================================================================

    def _on_color_click(self, hex_color):
        """Set tool_manager colour from a hex string like '#FF8800'."""
        h = hex_color.lstrip("#")
        r = int(h[0:2], 16)
        g = int(h[2:4], 16)
        b = int(h[4:6], 16)
        a = self._slider_vars["a"].get()

        self.tool_manager.color = (r, g, b, a)
        self._slider_vars["r"].set(r)
        self._slider_vars["g"].set(g)
        self._slider_vars["b"].set(b)
        self._update_preview()
        self._record_recent_color()

    def _on_slider_change(self, _=None):
        r = self._slider_vars["r"].get()
        g = self._slider_vars["g"].get()
        b = self._slider_vars["b"].get()
        a = self._slider_vars["a"].get()
        self.tool_manager.color = (r, g, b, a)
        self._update_preview()

    def sync_from_tool(self):
        """外部颜色变更后同步 RGB 滑块和预览（如屏幕取色器）。"""
        r, g, b, a = self.tool_manager.color
        self._slider_vars["r"].set(r)
        self._slider_vars["g"].set(g)
        self._slider_vars["b"].set(b)
        self._slider_vars["a"].set(a)
        self._update_preview()
        self._record_recent_color()

    def _on_add_custom(self):
        r, g, b, a = self.tool_manager.color
        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        self.config_manager.add_custom_color(hex_color)
        self._refresh_custom()

    def _on_remove_custom(self, hex_color):
        self.config_manager.remove_custom_color(hex_color)
        self._refresh_custom()

    # ----------------------------------------------------------------
    # G. Recent colors
    # ----------------------------------------------------------------

    def _build_recent_colors(self):
        frame = tkinter.LabelFrame(self, text="最近使用", padx=4, pady=3)
        frame.pack(fill="x", padx=5, pady=2)

        self._recent_container = tkinter.Frame(frame)
        self._recent_container.pack()

        self._refresh_recent()

    def _refresh_recent(self):
        for w in self._recent_container.winfo_children():
            w.destroy()

        # Get recent colors from tool_manager or internal list
        if self._has_recent_colors_api:
            colors = self.tool_manager.recent_colors
        else:
            colors = self._recent_colors

        if not colors:
            empty = tkinter.Label(
                self._recent_container,
                text="（空）",
                fg="#999",
                font=("TkDefaultFont", 9),
            )
            empty.pack()
            return

        # Show up to 16 colors in 4-column grid
        display_colors = colors[:16]
        cols = 4
        for i, rgba in enumerate(display_colors):
            r = i // cols
            c = i % cols
            hex_color = f"#{rgba[0]:02x}{rgba[1]:02x}{rgba[2]:02x}"
            swatch = tkinter.Canvas(
                self._recent_container,
                width=24,
                height=24,
                highlightthickness=1,
                highlightbackground="#ccc",
                cursor="hand2",
            )
            swatch.grid(row=r, column=c, padx=2, pady=2)
            swatch.create_rectangle(0, 0, 24, 24, fill=hex_color, outline="")
            swatch.bind(
                "<Button-1>",
                lambda _e, h=hex_color: self._on_color_click(h),
            )

    def _record_recent_color(self):
        """Record current tool_manager color to recent list."""
        rgba = self.tool_manager.color
        if self._has_recent_colors_api:
            self.tool_manager.add_recent_color(rgba)
        else:
            # Deduplicate: remove existing occurrence
            if rgba in self._recent_colors:
                self._recent_colors.remove(rgba)
            # Insert at front (newest first)
            self._recent_colors.insert(0, rgba)
            # Keep max 16
            self._recent_colors[:] = self._recent_colors[:16]
        self._refresh_recent()

    # ==================================================================
    # Preview update
    # ==================================================================

    def _update_preview(self):
        r, g, b, a = self.tool_manager.color
        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        self._color_preview.delete("all")
        self._color_preview.create_rectangle(
            0, 0, 40, 40, fill=hex_color, outline=""
        )
        self._color_info.config(
            text=f"{hex_color}\nR:{r}  G:{g}  B:{b}  A:{a}"
        )

    def _sync_from_tool_manager(self):
        """Sync UI state from the tool_manager (called once at init)."""
        r, g, b, a = self.tool_manager.color
        self._slider_vars["r"].set(r)
        self._slider_vars["g"].set(g)
        self._slider_vars["b"].set(b)
        self._slider_vars["a"].set(a)
        self._update_preview()
