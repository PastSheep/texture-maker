"""MainWindow -- primary editor window for Texture Maker.

Layout (PanedWindow horizontal split):
  - Left: PalettePanel (fixed 240 px)
  - Right: Menu bar + Toolbar + PixelCanvas (with scrollbars)

Handles keyboard shortcuts, title bar updates, and save flow.
"""

import os
import tkinter
from tkinter import filedialog, messagebox
from pathlib import Path

from ui.palette import PalettePanel
from ui.canvas_widget import PixelCanvas
from ui.tools import Tool


class MainWindow(tkinter.Frame):
    """Main editor frame that replaces the welcome screen."""

    def __init__(self, parent, app, image_model, tool_manager, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.image_model = image_model
        self.tool_manager = tool_manager

        self.pack(expand=True, fill="both")

        self._build_ui()
        self._setup_bindings()
        self._update_title()
        self._start_title_watcher()

    # ==================================================================
    # Layout
    # ==================================================================

    def _build_ui(self):
        # PanedWindow: left=palette, right=editor
        self.pane = tkinter.PanedWindow(
            self,
            orient="horizontal",
            sashrelief="raised",
            sashwidth=3,
        )
        self.pane.pack(expand=True, fill="both")

        # -- Left: PalettePanel --
        self.palette = PalettePanel(
            self.pane,
            self.tool_manager,
            self.app.config,
            width=240,
        )
        self.pane.add(self.palette, width=240)

        # -- Right: editor area --
        editor_frame = tkinter.Frame(self.pane)
        self.pane.add(editor_frame, stretch="always")

        self._build_menu()
        self._build_canvas_area(editor_frame)
        self._build_toolbar(editor_frame)

    # ----------------------------------------------------------------
    # Menu bar
    # ----------------------------------------------------------------

    def _build_menu(self):
        root = self.winfo_toplevel()
        menu_bar = tkinter.Menu(root)
        root.config(menu=menu_bar)

        # File
        file_menu = tkinter.Menu(menu_bar, tearoff=0)
        file_menu.add_command(
            label="保存",
            command=self._on_save,
            accelerator="Ctrl+S",
        )
        file_menu.add_command(
            label="另存为...",
            command=self._on_save_as,
            accelerator="Ctrl+Shift+S",
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="关闭",
            command=self._on_close,
            accelerator="Ctrl+W",
        )
        menu_bar.add_cascade(label="文件", menu=file_menu)

        # Edit
        edit_menu = tkinter.Menu(menu_bar, tearoff=0)
        edit_menu.add_command(label="撤销", state="disabled")
        edit_menu.add_command(label="重做", state="disabled")
        menu_bar.add_cascade(label="编辑", menu=edit_menu)

        # View
        view_menu = tkinter.Menu(menu_bar, tearoff=0)
        view_menu.add_command(
            label="放大",
            command=self._on_zoom_in,
            accelerator="Ctrl+=",
        )
        view_menu.add_command(
            label="缩小",
            command=self._on_zoom_out,
            accelerator="Ctrl+-",
        )
        view_menu.add_command(
            label="重置缩放",
            command=self._on_zoom_reset,
            accelerator="Ctrl+0",
        )
        view_menu.add_separator()
        self._grid_var = tkinter.BooleanVar(value=True)
        view_menu.add_checkbutton(
            label="显示网格",
            variable=self._grid_var,
            command=self._on_toggle_grid,
            accelerator="Ctrl+G",
        )
        menu_bar.add_cascade(label="视图", menu=view_menu)

        # Help
        help_menu = tkinter.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="关于", command=self._on_about)
        menu_bar.add_cascade(label="帮助", menu=help_menu)

    # ----------------------------------------------------------------
    # Toolbar
    # ----------------------------------------------------------------

    def _build_toolbar(self, parent):
        toolbar = tkinter.Frame(parent, relief="raised", bd=1)
        toolbar.pack(fill="x", padx=2, pady=2)

        # Tool radio buttons
        self._tool_var = tkinter.StringVar(value=Tool.PEN.name.lower())
        for tool_type, label in [
            (Tool.PEN, "画笔"),
            (Tool.ERASER, "橡皮"),
            (Tool.PICKER, "取色器"),
        ]:
            btn = tkinter.Radiobutton(
                toolbar,
                text=label,
                variable=self._tool_var,
                value=tool_type.name.lower(),
                indicatoron=False,
                width=7,
                command=lambda t=tool_type: self._on_tool_change(t),
            )
            btn.pack(side="left", padx=2)

        # Separator
        tkinter.Frame(toolbar, width=2, bd=1, relief="sunken").pack(
            side="left", padx=6, fill="y"
        )

        # Tool size
        tkinter.Label(toolbar, text="大小：").pack(side="left", padx=(0, 2))
        self._size_var = tkinter.IntVar(value=self.tool_manager.size)
        self.size_spin = tkinter.Spinbox(
            toolbar,
            from_=1,
            to=16,
            width=3,
            textvariable=self._size_var,
            command=self._on_size_change,
        )
        self.size_spin.pack(side="left", padx=2)

        # Separator
        tkinter.Frame(toolbar, width=2, bd=1, relief="sunken").pack(
            side="left", padx=6, fill="y"
        )

        # Zoom label
        tkinter.Label(toolbar, text="缩放：").pack(side="left", padx=(0, 2))
        self._zoom_label = tkinter.Label(
            toolbar, text="", font=("Courier", 9)
        )
        self._zoom_label.pack(side="left", padx=2)
        self._update_zoom_display()

        # Separator
        tkinter.Frame(toolbar, width=2, bd=1, relief="sunken").pack(
            side="left", padx=6, fill="y"
        )

        # Reference image controls
        tkinter.Label(toolbar, text="参考：").pack(side="left", padx=(0, 2))

        self._ref_load_btn = tkinter.Button(
            toolbar, text="加载", command=self._on_ref_load
        )
        self._ref_load_btn.pack(side="left", padx=1)

        self._ref_clear_btn = tkinter.Button(
            toolbar, text="清除", command=self._on_ref_clear
        )
        self._ref_clear_btn.pack(side="left", padx=1)

        self._ref_alpha_var = tkinter.DoubleVar(value=0.3)
        self._ref_alpha_scale = tkinter.Scale(
            toolbar,
            from_=0.0,
            to=1.0,
            resolution=0.05,
            orient="horizontal",
            variable=self._ref_alpha_var,
            command=self._on_ref_alpha,
            showvalue=False,
            length=60,
        )
        self._ref_alpha_scale.pack(side="left", padx=2)

    # ----------------------------------------------------------------
    # Canvas area with scrollbars
    # ----------------------------------------------------------------

    def _build_canvas_area(self, parent):
        container = tkinter.Frame(parent)
        container.pack(expand=True, fill="both", padx=2, pady=2)

        h_scroll = tkinter.Scrollbar(container, orient="horizontal")
        v_scroll = tkinter.Scrollbar(container, orient="vertical")

        self.canvas = PixelCanvas(
            container,
            self.image_model,
            self.tool_manager,
            self.app.config,
            on_screen_pick=self._on_screen_pick,
            xscrollcommand=h_scroll.set,
            yscrollcommand=v_scroll.set,
            bg="#e0e0e0",
        )

        h_scroll.config(command=self.canvas.xview)
        v_scroll.config(command=self.canvas.yview)

        h_scroll.pack(side="bottom", fill="x")
        v_scroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", expand=True, fill="both")

    # ==================================================================
    # Keyboard shortcuts
    # ==================================================================

    def _setup_bindings(self):
        root = self.winfo_toplevel()
        root.bind("<Control-s>", lambda _e: self._on_save())
        root.bind("<Control-S>", lambda _e: self._on_save_as())
        root.bind("<Control-w>", lambda _e: self._on_close())
        root.bind("<Control-W>", lambda _e: self._on_close())
        root.bind("<Control-equal>", lambda _e: self._on_zoom_in())
        root.bind("<Control-minus>", lambda _e: self._on_zoom_out())
        root.bind("<Control-0>", lambda _e: self._on_zoom_reset())
        root.bind("<Control-g>", lambda _e: self._on_toggle_grid())
        root.bind("<Control-G>", lambda _e: self._on_toggle_grid())

    # ==================================================================
    # Title bar update
    # ==================================================================

    def _update_title(self):
        path = self.image_model.path
        if path:
            name = Path(path).name
        else:
            name = "未命名.png"

        if self.image_model.is_modified:
            title = f"*{name} - 贴图工坊"
        else:
            title = f"{name} - 贴图工坊"

        self.winfo_toplevel().title(title)

    def _start_title_watcher(self):
        """Poll is_modified every 500 ms for title bar updates."""
        self._last_modified = self.image_model.is_modified
        self._tick_title()

    def _tick_title(self):
        if self.image_model.is_modified != self._last_modified:
            self._last_modified = self.image_model.is_modified
            self._update_title()
        self.after(500, self._tick_title)

    # ==================================================================
    # Toolbar handlers
    # ==================================================================

    def _on_tool_change(self, tool):
        self.tool_manager.current_tool = tool
        self.canvas.update_cursor()

    def _on_screen_pick(self):
        """Called after screen colour picker grabs a colour."""
        self.palette.sync_from_tool()
        # 取色后自动切回画笔
        self.tool_manager.current_tool = Tool.PEN
        self._tool_var.set(Tool.PEN.name.lower())
        self.canvas.update_cursor()

    def _on_size_change(self):
        try:
            size = int(self._size_var.get())
            self.tool_manager.size = max(1, min(16, size))
            self.app.config.set_tool_size(self.tool_manager.size)
        except (ValueError, tkinter.TclError):
            pass

    def _update_zoom_display(self):
        pct = self.canvas.zoom * 100 // 16  # scale relative to 1x = 100%
        # or simpler: zoom * 100 / 16, but let's just show zoom*100/16
        # Actually zoom=16 means 16 screen px per pixel, so 16/16*100 = 100%
        display = int(self.canvas.zoom * 100 / 16)
        self._zoom_label.config(text=f"{display}%")

    def _on_zoom_in(self):
        z = min(64, self.canvas.zoom * 2)
        self.canvas.set_zoom(z)
        self._update_zoom_display()

    def _on_zoom_out(self):
        z = max(1, self.canvas.zoom // 2)
        self.canvas.set_zoom(z)
        self._update_zoom_display()

    def _on_zoom_reset(self):
        self.canvas.set_zoom(16)
        self._update_zoom_display()

    def _on_toggle_grid(self):
        self.canvas.set_show_grid(self._grid_var.get())

    def _on_ref_load(self):
        path = filedialog.askopenfilename(
            title="加载参考图",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        try:
            from PIL import Image
            img = Image.open(path)
            self.canvas.set_reference_image(img)
            self.tool_manager.reference_image = img
        except Exception as exc:
            messagebox.showerror("错误", f"无法加载参考图：\n{exc}")

    def _on_ref_clear(self):
        self.canvas.set_reference_image(None)

    def _on_ref_alpha(self, _=None):
        self.tool_manager.reference_opacity = self._ref_alpha_var.get()
        # Re-apply reference image with new opacity
        ref = self.tool_manager.reference_image
        if ref is not None:
            self.canvas.set_reference_image(ref)

    # ==================================================================
    # Save flow
    # ==================================================================

    def _on_save(self):
        """Save to the current path, or prompt for a path if none set."""
        path = self.image_model.path
        if path and os.path.exists(path):
            self.image_model.save()
            self._update_title()
        else:
            self._on_save_as()

    def _on_save_as(self):
        path = filedialog.asksaveasfilename(
            title="另存为",
            defaultextension=".png",
            filetypes=[("PNG files", "*.png")],
        )
        if not path:
            return
        self.image_model.save_as(path)
        self._update_title()
        self.app.config.add_recent(path)

    def _on_close(self):
        self.app.close_current()

    # ==================================================================
    # Menu helpers
    # ==================================================================

    def _on_about(self):
        messagebox.showinfo(
            "关于贴图工坊",
            "贴图工坊 v1.0\n\n"
            "Minecraft 模组像素图绘制工具。\n"
            "基于 Python、tkinter 和 Pillow 构建。",
        )
