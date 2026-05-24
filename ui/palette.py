"""PalettePanel -- vertical colour palette panel for Texture Maker.

Contains:
  A. Preset colour swatches by category (collapsible)
  B. Current colour preview with RGB/HEX readout
  C. RGB + Alpha sliders
  D. Custom palette (from config, with add/remove)
  E. Extract-from-image button
  F. Colour picker tool button
"""

import tkinter
from tkinter import filedialog, messagebox
from collections import Counter

from PIL import Image

from ui.tools import Tool

# ---------------------------------------------------------------------------
# Built-in colour presets (Minecraft-themed)
# ---------------------------------------------------------------------------

PRESET_COLORS = {
    "Metal": [
        "#C0C0C0", "#808080", "#FFD700", "#CD7F32",
        "#A0A0A0", "#E8E8E8", "#B87333", "#D4AF37",
    ],
    "Ore": [
        "#6B8E23", "#8B4513", "#A0522D", "#CD853F",
        "#D2691E", "#B8860B", "#556B2F", "#8B0000",
    ],
    "Gem": [
        "#FF0000", "#00FF00", "#0000FF", "#00FFFF",
        "#FF00FF", "#7FFFD4", "#4B0082", "#FF1493",
    ],
    "Nature": [
        "#228B22", "#8B4513", "#F5F5DC", "#87CEEB",
        "#808080", "#2F4F4F", "#D2B48C", "#778899",
    ],
    "Basic": [
        "#000000", "#FFFFFF", "#FF0000", "#00FF00",
        "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF",
    ],
    "Gray": [
        "#000000", "#333333", "#666666", "#999999",
        "#CCCCCC", "#FFFFFF", "#1A1A1A", "#4D4D4D",
    ],
}


class PalettePanel(tkinter.Frame):
    """Vertical colour palette docked to the left of the editor."""

    def __init__(self, parent, tool_manager, config_manager, on_tool_change=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.tool_manager = tool_manager
        self.config_manager = config_manager
        self._on_tool_change_cb = on_tool_change
        self._custom_refresh_job = None

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
        self._build_custom_palette()
        self._build_action_buttons()

    # ----------------------------------------------------------------
    # A. Current colour preview
    # ----------------------------------------------------------------

    def _build_current_color(self):
        frame = tkinter.LabelFrame(self, text="Current Color", padx=6, pady=5)
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
        frame = tkinter.LabelFrame(self, text="RGBA Generator", padx=6, pady=5)
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
    # B. Preset categories (collapsible)
    # ----------------------------------------------------------------

    def _build_preset_categories(self):
        self._preset_frames = []
        for category, colors in PRESET_COLORS.items():
            self._add_preset_category(category, colors)

    def _add_preset_category(self, name, colors):
        outer = tkinter.LabelFrame(self, text=name, padx=4, pady=3)
        outer.pack(fill="x", padx=5, pady=2)

        # Collapse toggle button
        hdr = tkinter.Frame(outer)
        hdr.pack(fill="x")
        toggle_btn = tkinter.Button(
            hdr,
            text="[-]",
            width=3,
            bd=0,
            font=("Courier", 9),
            command=lambda: self._toggle_category(outer),
        )
        toggle_btn.pack(side="right")

        # Swatch grid container
        container = tkinter.Frame(outer)
        container.pack()
        outer._expanded = True
        outer._container = container

        cols = 4
        for i, hex_color in enumerate(colors):
            r = i // cols
            c = i % cols
            swatch = tkinter.Canvas(
                container,
                width=20,
                height=20,
                highlightthickness=1,
                highlightbackground="#ccc",
                cursor="hand2",
            )
            swatch.grid(row=r, column=c, padx=1, pady=1)
            swatch.create_rectangle(0, 0, 20, 20, fill=hex_color, outline="")
            swatch.bind(
                "<Button-1>",
                lambda _e, h=hex_color: self._on_color_click(h),
            )

        self._preset_frames.append(outer)

    @staticmethod
    def _toggle_category(outer):
        outer._expanded = not outer._expanded
        if outer._expanded:
            outer._container.pack()
        else:
            outer._container.pack_forget()

    # ----------------------------------------------------------------
    # D. Custom palette
    # ----------------------------------------------------------------

    def _build_custom_palette(self):
        frame = tkinter.LabelFrame(self, text="Custom Palette", padx=4, pady=3)
        frame.pack(fill="x", padx=5, pady=2)

        self._custom_container = tkinter.Frame(frame)
        self._custom_container.pack()

        add_btn = tkinter.Button(
            frame,
            text="Add to Custom Palette",
            command=self._on_add_custom,
        )
        add_btn.pack(pady=3, fill="x")

        self._refresh_custom()

    def _refresh_custom(self):
        for w in self._custom_container.winfo_children():
            w.destroy()

        colors = self.config_manager.get_custom_colors()
        if not colors:
            empty = tkinter.Label(
                self._custom_container,
                text="(empty)",
                fg="#999",
                font=("TkDefaultFont", 9),
            )
            empty.pack()
            return

        cols = 4
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
            title="Extract Colors from Image",
            filetypes=[("PNG files", "*.png")],
        )
        if not path:
            return

        try:
            img = Image.open(path).convert("RGBA")
        except Exception as exc:
            messagebox.showerror("Error", f"Could not open image:\n{exc}")
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
                "No Colors",
                "No sufficiently opaque pixels found in the image.",
            )
            return

        # Top 16 most frequent colours
        top_colors = [c for c, _ in counter.most_common(16)]

        # Show in popup
        self._show_extracted_colors(top_colors)

    def _show_extracted_colors(self, colors):
        top = tkinter.Toplevel(self)
        top.title("Extracted Colors")
        top.transient(self.winfo_toplevel())
        top.grab_set()

        tkinter.Label(
            top,
            text="Click a colour to add it to your custom palette:",
            font=("TkDefaultFont", 10),
        ).pack(pady=(8, 4))

        cf = tkinter.Frame(top)
        cf.pack(padx=12, pady=6)

        cols = 4
        for i, hex_color in enumerate(colors):
            r = i // cols
            c = i % cols
            swatch = tkinter.Canvas(
                cf,
                width=28,
                height=28,
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

        tkinter.Button(top, text="Close", command=top.destroy).pack(pady=(4, 8))

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
        # Extract from image
        extract_btn = tkinter.Button(
            self,
            text="Extract from Image",
            command=self._on_extract,
        )
        extract_btn.pack(fill="x", padx=5, pady=2)

        # Color picker tool
        picker_btn = tkinter.Button(
            self,
            text="Color Picker Tool",
            command=self._on_picker_tool,
        )
        picker_btn.pack(fill="x", padx=5, pady=(2, 5))

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

    def _on_slider_change(self, _=None):
        r = self._slider_vars["r"].get()
        g = self._slider_vars["g"].get()
        b = self._slider_vars["b"].get()
        a = self._slider_vars["a"].get()
        self.tool_manager.color = (r, g, b, a)
        self._update_preview()

    def _on_picker_tool(self):
        self.tool_manager.current_tool = Tool.PICKER
        if self._on_tool_change_cb:
            self._on_tool_change_cb(Tool.PICKER)

    def _on_add_custom(self):
        r, g, b, a = self.tool_manager.color
        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        self.config_manager.add_custom_color(hex_color)
        self._refresh_custom()

    def _on_remove_custom(self, hex_color):
        self.config_manager.remove_custom_color(hex_color)
        self._refresh_custom()

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
