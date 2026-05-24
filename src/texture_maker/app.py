"""Application -- root tkinter window and top-level controller."""

import os
import tkinter as tk
from pathlib import Path

from texture_maker.config import ConfigManager
from texture_maker.image_model import ImageModel
from texture_maker.tools import ToolManager


class Application:
    """Top-level application controller.

    Owns the ``tk.Tk`` root window, the ``ConfigManager``, ``ImageModel``,
    ``ToolManager``, and switches between WelcomeScreen and MainWindow.
    """

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("贴图工坊")

        # -- centre a 1200 x 800 window on the primary display ----------
        self.root.geometry("1200x800")
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - 1200) // 2
        y = (sh - 800) // 2
        self.root.geometry(f"1200x800+{x}+{y}")

        self.config = ConfigManager()
        self.current_model: ImageModel | None = None
        self.tool_manager: ToolManager | None = None

        # UI panel references
        self._welcome = None
        self._editor = None

        # -- prevent the window from being destroyed silently -----------
        self.root.protocol("WM_DELETE_WINDOW", self._on_quit)

        # Start on the welcome screen
        self.show_welcome()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Enter the tkinter event loop."""
        self.root.mainloop()

    # ------------------------------------------------------------------
    # Screen switching
    # ------------------------------------------------------------------

    def show_welcome(self) -> None:
        """Display the welcome / landing screen."""
        self._clear_ui()
        from texture_maker.ui.welcome_screen import WelcomeScreen

        self._welcome = WelcomeScreen(self.root, self)
        self.root.title("贴图工坊")

    def show_editor(self) -> None:
        """Display the main editor for the current model."""
        self._clear_ui()
        from texture_maker.ui.main_window import MainWindow

        self._editor = MainWindow(
            self.root, self, self.current_model, self.tool_manager
        )

    # ------------------------------------------------------------------
    # Project management
    # ------------------------------------------------------------------

    def open_project(self, path: str) -> None:
        """Load a texture from *path* and open the editor."""
        if not self.close_current():
            return

        self.current_model = ImageModel.from_file(path)
        self.tool_manager = ToolManager()
        self.config.add_recent(path)
        self.show_editor()

    def new_project(self, path: str, width: int, height: int) -> None:
        """Create a new transparent canvas and open the editor.

        The new file is saved immediately so it exists on disk.
        """
        if not self.close_current():
            return

        self.current_model = ImageModel.from_size(path, width, height)
        self.tool_manager = ToolManager()

        # Ensure directory exists
        parent = os.path.dirname(path)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)

        self.current_model.save()
        self.config.add_recent(path)
        self.show_editor()

    def close_current(self) -> bool:
        """Close the current project, prompting if unsaved changes exist.

        Returns ``True`` if the caller may proceed (closed / saved),
        ``False`` if the user cancelled.
        """
        if self.current_model is None:
            return True

        if self.current_model.is_modified:
            name = Path(self.current_model.path).name
            response = tk.messagebox.askyesnocancel(
                "未保存的更改",
                f"是否保存对 {name} 的更改？",
            )
            if response is None:  # Cancel
                return False
            if response:  # Yes -> Save
                self.current_model.save()

        self.current_model = None
        self.tool_manager = None
        self._clear_ui()
        self.show_welcome()
        return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _clear_ui(self) -> None:
        """Destroy welcome and/or editor frames."""
        if self._welcome is not None:
            self._welcome.destroy()
            self._welcome = None
        if self._editor is not None:
            self._editor.destroy()
            self._editor = None
        # Reset menu bar so the next view starts clean
        self.root.config(menu=tk.Menu(self.root))

    def _on_quit(self) -> None:
        """Handle window close button."""
        if self.close_current():
            self.config.save()
            self.root.destroy()
