"""NewProjectDialog -- modal dialog for creating a new texture.

Provides MC size presets (16, 32, 48, 64, 96, 128) in a 3x2 grid,
custom width/height spinboxes, save location browser, and file name entry.
"""

import os
import tkinter
from tkinter import filedialog, messagebox

# Minecraft texture size presets
MC_PRESETS = [16, 32, 48, 64, 96, 128]


class NewProjectDialog:
    """Modal "New Project" dialog.  Blocks until the user creates or cancels."""

    def __init__(self, parent, app):
        self.app = app

        self.dialog = tkinter.Toplevel(parent)
        self.dialog.title("新建项目")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)

        # State variables
        self.width_var = tkinter.IntVar(value=16)
        self.height_var = tkinter.IntVar(value=16)
        self.save_dir = tkinter.StringVar(value="")
        self.file_name = tkinter.StringVar(value="贴图")

        self._build_ui()

        # Center over parent
        self.dialog.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        dw = self.dialog.winfo_width()
        dh = self.dialog.winfo_height()
        x = px + (pw - dw) // 2
        y = py + (ph - dh) // 2
        self.dialog.geometry(f"+{max(0, x)}+{max(0, y)}")

        self.dialog.wait_window()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        # -- Canvas Size presets (3 x 2 grid) --
        preset_frame = tkinter.LabelFrame(
            self.dialog,
            text="画布尺寸（MC预设）",
            padx=10,
            pady=10,
        )
        preset_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=8, sticky="ew")

        for i, size in enumerate(MC_PRESETS):
            r = i // 3
            c = i % 3
            btn = tkinter.Button(
                preset_frame,
                text=f"{size}x{size}",
                width=9,
                height=1,
                command=lambda s=size: self._on_preset(s),
            )
            btn.grid(row=r, column=c, padx=4, pady=3)

        # -- Custom size --
        custom_frame = tkinter.LabelFrame(
            self.dialog,
            text="自定义尺寸",
            padx=10,
            pady=8,
        )
        custom_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        tkinter.Label(custom_frame, text="宽：").grid(row=0, column=0, padx=(0, 4))
        self.width_spin = tkinter.Spinbox(
            custom_frame,
            from_=1,
            to=128,
            width=5,
            textvariable=self.width_var,
        )
        self.width_spin.grid(row=0, column=1, padx=(0, 15))

        tkinter.Label(custom_frame, text="高：").grid(row=0, column=2, padx=(0, 4))
        self.height_spin = tkinter.Spinbox(
            custom_frame,
            from_=1,
            to=128,
            width=5,
            textvariable=self.height_var,
        )
        self.height_spin.grid(row=0, column=3)

        # -- Save location --
        loc_frame = tkinter.Frame(self.dialog)
        loc_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        tkinter.Label(loc_frame, text="保存位置：").grid(
            row=0, column=0, sticky="w", pady=(0, 3)
        )

        self.path_label = tkinter.Label(
            loc_frame,
            text="（未选择）",
            fg="gray",
            anchor="w",
            width=45,
        )
        self.path_label.grid(row=1, column=0, padx=(0, 5), sticky="ew")

        browse_btn = tkinter.Button(
            loc_frame, text="浏览...", command=self._on_browse
        )
        browse_btn.grid(row=1, column=1)

        # -- File name --
        name_frame = tkinter.Frame(self.dialog)
        name_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        tkinter.Label(name_frame, text="文件名：").grid(
            row=0, column=0, sticky="w", pady=(0, 3)
        )

        self.name_entry = tkinter.Entry(
            name_frame, textvariable=self.file_name, width=40
        )
        self.name_entry.grid(row=1, column=0, padx=(0, 4), sticky="ew")
        tkinter.Label(name_frame, text=".png").grid(row=1, column=1, sticky="w")

        # -- Action buttons --
        btn_frame = tkinter.Frame(self.dialog)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=12)

        tkinter.Button(
            btn_frame, text="创建", width=12, command=self._on_confirm
        ).pack(side="left", padx=6)
        tkinter.Button(
            btn_frame, text="取消", width=12, command=self._on_cancel
        ).pack(side="left", padx=6)

        # Configure column weights for resizing
        self.dialog.columnconfigure(0, weight=1)
        loc_frame.columnconfigure(0, weight=1)
        name_frame.columnconfigure(0, weight=1)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _on_preset(self, size):
        self.width_var.set(size)
        self.height_var.set(size)

    def _on_browse(self):
        directory = filedialog.askdirectory(title="选择保存位置")
        if directory:
            self.save_dir.set(directory)
            self.path_label.config(text=directory, fg="black")

    def _on_confirm(self):
        # Validate dimensions
        w = self.width_var.get()
        h = self.height_var.get()
        try:
            w = int(w)
            h = int(h)
        except (ValueError, tkinter.TclError):
            messagebox.showwarning("无效的尺寸", "尺寸必须为整数。")
            return

        if w < 1 or w > 128 or h < 1 or h > 128:
            messagebox.showwarning(
                "无效的尺寸", "尺寸必须在1到128之间。"
            )
            return

        # Validate save location
        save_dir = self.save_dir.get().strip()
        if not save_dir:
            messagebox.showwarning("未选择位置", "请选择保存位置。")
            return
        if not os.path.isdir(save_dir):
            messagebox.showwarning(
                "无效的位置", "选择的保存位置不存在。"
            )
            return

        # Validate file name
        file_name = self.file_name.get().strip()
        if not file_name:
            messagebox.showwarning("未输入文件名", "请输入文件名。")
            return

        if not file_name.endswith(".png"):
            file_name += ".png"

        full_path = os.path.join(save_dir, file_name)

        if os.path.exists(full_path):
            if not messagebox.askyesno(
                "文件已存在", f"{file_name} 已存在。\n是否覆盖？"
            ):
                return

        self.dialog.destroy()
        self.app.new_project(full_path, w, h)

    def _on_cancel(self):
        self.dialog.destroy()
