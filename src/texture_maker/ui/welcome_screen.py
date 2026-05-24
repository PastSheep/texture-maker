"""WelcomeScreen -- landing page for Texture Maker.

Displays the application title, three action buttons (New, Open, Recent),
and a per-item recent-projects list with delete buttons.
"""

import os
import tkinter
from tkinter import filedialog, messagebox


class RecentItemRow(tkinter.Frame):
    """A single row in the recent-projects list with a clickable label
    and a delete button on the right."""

    def __init__(self, parent, path, on_open, on_delete, **kwargs):
        super().__init__(parent, **kwargs)
        self.path = path
        self.configure(bd=1, relief="flat")

        name = os.path.basename(path) if path else path

        # Clickable label (fills remaining space)
        label = tkinter.Label(
            self,
            text=name,
            anchor="w",
            cursor="hand2",
            font=("TkDefaultFont", 10),
            padx=8,
            pady=4,
        )
        label.pack(side="left", fill="x", expand=True)
        label.bind("<Button-1>", lambda e: on_open(path))

        # Also make the frame background clickable
        self.bind("<Button-1>", lambda e: on_open(path))

        # Alternate background colour on hover
        label.bind("<Enter>", lambda e: label.configure(bg="#e8e8e8"))
        label.bind("<Leave>", lambda e: label.configure(bg=parent.cget("bg")))

        # Delete button
        del_btn = tkinter.Button(
            self,
            text="×",
            width=2,
            bd=0,
            fg="#999",
            activeforeground="red",
            cursor="hand2",
            command=lambda: on_delete(path),
        )
        del_btn.pack(side="right", padx=(0, 4))

        self.pack(fill="x", padx=2, pady=1)


class WelcomeScreen(tkinter.Frame):
    """Full-window welcome page shown when no project is open."""

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self._rows = []

        self.pack(expand=True, fill="both")

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        # Centering spacer at top
        self.pack_propagate(False)

        # Container that centres everything vertically
        outer = tkinter.Frame(self)
        outer.place(relx=0.5, rely=0.45, anchor="center")

        # -- Title --
        title = tkinter.Label(
            outer,
            text="贴图工坊",
            font=("TkDefaultFont", 36, "bold"),
        )
        title.pack(pady=(0, 30))

        # -- Buttons --
        btn_frame = tkinter.Frame(outer)
        btn_frame.pack(pady=(0, 30))

        self._new_btn = tkinter.Button(
            btn_frame,
            text="新建项目",
            width=22,
            height=2,
            font=("TkDefaultFont", 11),
            command=self._on_new_project,
        )
        self._new_btn.pack(pady=4)

        self._open_btn = tkinter.Button(
            btn_frame,
            text="打开项目",
            width=22,
            height=2,
            font=("TkDefaultFont", 11),
            command=self._on_open_project,
        )
        self._open_btn.pack(pady=4)

        # -- Recent projects --
        recent_container = tkinter.Frame(outer)
        recent_container.pack(fill="x")

        recent_header = tkinter.Label(
            recent_container,
            text="最近项目",
            font=("TkDefaultFont", 12, "bold"),
            anchor="w",
        )
        recent_header.pack(fill="x", pady=(0, 4))

        # Scrollable area for recent items
        self._recent_canvas = tkinter.Canvas(
            recent_container,
            height=180,
            highlightthickness=0,
        )
        scrollbar = tkinter.Scrollbar(
            recent_container,
            orient="vertical",
            command=self._recent_canvas.yview,
        )
        self._recent_list = tkinter.Frame(self._recent_canvas)

        self._recent_list.bind(
            "<Configure>",
            lambda e: self._recent_canvas.configure(
                scrollregion=self._recent_canvas.bbox("all")
            ),
        )
        self._recent_canvas.create_window(
            (0, 0), window=self._recent_list, anchor="nw"
        )
        self._recent_canvas.configure(yscrollcommand=scrollbar.set)

        self._recent_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._refresh_recent()

    # ------------------------------------------------------------------
    # Refresh recent list
    # ------------------------------------------------------------------

    def _refresh_recent(self):
        """Clear and rebuild the recent-projects list from config."""
        for row in self._rows:
            row.destroy()
        self._rows.clear()

        recent = self.app.config.get_recent()
        if not recent:
            empty = tkinter.Label(
                self._recent_list,
                text="（暂无最近项目）",
                fg="#999",
                font=("TkDefaultFont", 9),
            )
            empty.pack(pady=10)
            self._rows.append(empty)
            return

        for path in recent:
            row = RecentItemRow(
                self._recent_list,
                path,
                on_open=self.app.open_project,
                on_delete=self._on_delete_recent,
            )
            self._rows.append(row)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_new_project(self):
        from ui.new_project_dialog import NewProjectDialog

        NewProjectDialog(self, self.app)

    def _on_open_project(self):
        path = filedialog.askopenfilename(
            title="打开PNG贴图",
            filetypes=[("PNG files", "*.png")],
        )
        if not path:
            return

        # Validate size (max 128 x 128)
        try:
            from PIL import Image

            img = Image.open(path)
            if img.width > 128 or img.height > 128:
                messagebox.showwarning(
                    "尺寸超限",
                    f"图片尺寸（{img.width}×{img.height}）超过了128×128的上限。",
                )
                return
        except Exception as exc:
            messagebox.showerror("错误", f"无法打开图片：\n{exc}")
            return

        self.app.open_project(path)

    def _on_delete_recent(self, path):
        self.app.config.remove_recent(path)
        self._refresh_recent()
