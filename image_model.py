"""ImageModel -- pixel-level RGBA image data for Texture Maker."""

import os
import shutil
from pathlib import Path

from PIL import Image

_MAX_SIZE = 128
_MAX_HISTORY = 50  # 撤销历史最大步数


class ImageModel:
    """Represents a single texture image loaded from or destined for a PNG file.

    Responsible for pixel-level read/write, file I/O with automatic backup,
    and basic constraints (max 128 x 128, RGBA-only internally).
    """

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_file(cls, path: str) -> "ImageModel":
        """Load a PNG from *path*.

        Raises ``ValueError`` if dimensions exceed 128 x 128.
        Automatically converts to RGBA if the source lacks an alpha channel.
        """
        path = str(path)
        img = Image.open(path).convert("RGBA")
        if img.width > _MAX_SIZE or img.height > _MAX_SIZE:
            raise ValueError("图片尺寸超过限制")
        model = cls.__new__(cls)
        model.image = img
        model.path = path
        model._is_modified = False
        model._history = []
        model._redo_stack = []
        return model

    @classmethod
    def from_size(cls, path: str, width: int, height: int) -> "ImageModel":
        """Create a new fully-transparent RGBA canvas (width x height).

        *path* is the intended save location; the canvas is **not** written
        to disk until ``save()`` is called.

        Raises ``ValueError`` if dimensions exceed 128 x 128.
        """
        if width > _MAX_SIZE or height > _MAX_SIZE:
            raise ValueError("图片尺寸超过限制")
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        model = cls.__new__(cls)
        model.image = img
        model.path = str(path)
        model._is_modified = False
        model._history = []
        model._redo_stack = []
        return model

    # ------------------------------------------------------------------
    # Pixel API
    # ------------------------------------------------------------------

    def get_pixel(self, x: int, y: int) -> tuple[int, int, int, int] | None:
        """Return the RGBA tuple at (x, y), or ``None`` if out of bounds."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.image.getpixel((x, y))  # type: ignore[return-value]
        return None

    def set_pixel(self, x: int, y: int, color: tuple) -> None:
        """Set the RGBA pixel at (x, y) and mark the model as modified."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.image.putpixel((x, y), color)
            self._is_modified = True

    def fill_area(self, x: int, y: int, color: tuple) -> list[tuple[int, int]]:
        """Flood-fill from (x, y) with *color*.

        Returns the list of ``(x, y)`` pixel coordinates that were changed.
        Uses a stack-based (non-recursive) algorithm.
        """
        if not (0 <= x < self.width and 0 <= y < self.height):
            return []

        target = self.get_pixel(x, y)
        if target == color:
            return []

        changed: list[tuple[int, int]] = []
        stack = [(x, y)]
        visited: set[tuple[int, int]] = set()

        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in visited:
                continue
            if not (0 <= cx < self.width and 0 <= cy < self.height):
                continue
            if self.get_pixel(cx, cy) != target:
                continue

            visited.add((cx, cy))
            changed.append((cx, cy))
            self.image.putpixel((cx, cy), color)

            # Push neighbours.
            stack.append((cx + 1, cy))
            stack.append((cx - 1, cy))
            stack.append((cx, cy + 1))
            stack.append((cx, cy - 1))

        if changed:
            self._is_modified = True
        return changed

    # ------------------------------------------------------------------
    # 撤销 / 重做
    # ------------------------------------------------------------------

    def begin_undo_step(self) -> None:
        """在执行修改操作前快照当前图像，推入撤销栈。

        超过 ``_MAX_HISTORY`` 步时移除最旧的快照，同时清空重做栈。
        """
        snapshot = self.image.copy()
        self._history.append(snapshot)
        self._redo_stack.clear()
        if len(self._history) > _MAX_HISTORY:
            self._history.pop(0)

    def undo(self) -> bool:
        """撤销到上一个历史快照。

        Returns:
            True 如果成功撤销，False 如果没有历史记录。
        """
        if not self._history:
            return False
        snapshot = self._history.pop()
        self._redo_stack.append(self.image)
        self.image = snapshot
        self._is_modified = True
        return True

    def redo(self) -> bool:
        """重做之前撤销的操作。

        Returns:
            True 如果成功重做，False 如果没有重做记录。
        """
        if not self._redo_stack:
            return False
        snapshot = self._redo_stack.pop()
        self._history.append(self.image)
        self.image = snapshot
        self._is_modified = True
        return True

    def can_undo(self) -> bool:
        """返回是否有可撤销的历史记录。"""
        return len(self._history) > 0

    def can_redo(self) -> bool:
        """返回是否有可重做的记录。"""
        return len(self._redo_stack) > 0

    def get_undo_redo_status(self) -> tuple[bool, bool]:
        """返回 (可以撤销, 可以重做) 状态元组。"""
        return (self.can_undo(), self.can_redo())

    # ------------------------------------------------------------------
    # Image access
    # ------------------------------------------------------------------

    def get_image(self) -> Image.Image:
        """Return the underlying Pillow ``Image`` (RGBA)."""
        return self.image

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> None:
        """Save the current image to ``self.path``.

        If a file already exists at that path it is renamed to
        ``<filename>.png.bak`` before overwriting.
        """
        self._backup_existing()
        self.image.save(self.path)
        self._is_modified = False

    def save_as(self, path: str) -> None:
        """Save the current image to a new *path* and update ``self.path``."""
        self.path = str(path)
        self.save()

    # ------------------------------------------------------------------
    # Backup / restore
    # ------------------------------------------------------------------

    def has_backup(self) -> bool:
        """Return ``True`` if a ``.bak`` file exists for the current path."""
        return os.path.isfile(self._backup_path())

    def restore_backup(self) -> None:
        """Restore the image from the ``.bak`` file.

        Raises ``FileNotFoundError`` if no backup exists.
        """
        bak = self._backup_path()
        if not os.path.isfile(bak):
            raise FileNotFoundError(f"备份文件不存在: {bak}")
        img = Image.open(bak).convert("RGBA")
        self.image = img
        self._is_modified = False

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_modified(self) -> bool:
        """``True`` after any ``set_pixel`` / ``fill_area`` call until saved."""
        return self._is_modified

    @property
    def width(self) -> int:
        """Image width in pixels."""
        return self.image.width

    @property
    def height(self) -> int:
        """Image height in pixels."""
        return self.image.height

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _backup_path(self) -> str:
        return self.path + ".bak"

    def _backup_existing(self) -> None:
        if self.path and os.path.isfile(self.path):
            shutil.copy2(self.path, self._backup_path())
