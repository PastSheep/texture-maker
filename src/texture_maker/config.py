"""ConfigManager -- persistent JSON config for Texture Maker."""

import json
import os

_DEFAULT_CONFIG = {
    "recent_projects": [],
    "last_save_dir": "",
    "max_recent": 10,
    "default_canvas_size": 16,
    "palette": {"custom_colors": []},
    "tool_size": 1,
    "zoom_level": 16,
    "reference_opacity": 0.3,
    "show_grid": True,
    "grid_color": "#808080",
    "right_click_action": "picker",
    "symmetry_mode": "none",
}


def _get_config_path() -> str:
    """Return the path to the JSON config file under the user home directory."""
    config_dir = os.path.join(os.path.expanduser("~"), ".texture-maker")
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "config.json")


class ConfigManager:
    """Load, access, persist application configuration.

    Usage:
        cfg = ConfigManager()          # auto-loads from ~/.texture-maker/config.json
        val = cfg.get("zoom_level", 1)
        cfg.set("show_grid", False)    # also calls save()
    """

    def __init__(self) -> None:
        self._path = _get_config_path()
        self._data: dict = _DEFAULT_CONFIG.copy()
        self._load()

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def get(self, key: str, default=None):
        """Retrieve a configuration value by key."""
        return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        """Set a configuration value and immediately persist to disk."""
        self._data[key] = value
        self.save()

    def save(self) -> None:
        """Write the current configuration to the JSON file.

        使用原子写入：先写临时文件，再替换目标文件，
        避免写入过程中程序崩溃导致配置文件损坏。
        """
        tmp_path = self._path + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self._path)
        except OSError:
            pass

    def add_recent(self, path: str) -> None:
        """Insert *path* at the front of the recent-projects list.

        Duplicates are removed and the list is truncated to *max_recent* entries.
        """
        recent: list = self._data.setdefault("recent_projects", [])
        # Remove any existing occurrence of the same path.
        if path in recent:
            recent.remove(path)
        # Insert at the front.
        recent.insert(0, path)
        # Truncate.
        max_recent = self._data.get("max_recent", 10)
        self._data["recent_projects"] = recent[:max_recent]
        self.save()

    def get_recent(self) -> list[str]:
        """Return the list of recent project file paths."""
        return list(self._data.get("recent_projects", []))

    # ------------------------------------------------------------------
    # Custom palette colors
    # ------------------------------------------------------------------

    def get_custom_colors(self) -> list[str]:
        """Return the list of custom palette hex colours."""
        palette = self._data.setdefault("palette", {})
        return list(palette.get("custom_colors", []))

    def add_custom_color(self, hex_color: str) -> None:
        """Add a hex colour to the custom palette if not already present."""
        palette = self._data.setdefault("palette", {})
        colors: list = palette.setdefault("custom_colors", [])
        if hex_color not in colors:
            colors.append(hex_color)
            self.save()

    def remove_custom_color(self, hex_color: str) -> None:
        """Remove a hex colour from the custom palette."""
        palette = self._data.setdefault("palette", {})
        colors: list = palette.setdefault("custom_colors", [])
        if hex_color in colors:
            colors.remove(hex_color)
            self.save()

    def remove_recent(self, path: str) -> None:
        """Remove *path* from the recent-projects list."""
        recent: list = self._data.get("recent_projects", [])
        if path in recent:
            recent.remove(path)
            self.save()

    def set_tool_size(self, size: int) -> None:
        """Persist the last-used tool size."""
        self.set("tool_size", size)

    def get_tool_size(self, default: int = 1) -> int:
        """Return the persisted tool size."""
        return self.get("tool_size", default)

    # ------------------------------------------------------------------
    # 右键行为配置
    # ------------------------------------------------------------------

    def get_right_click_action(self) -> str:
        """返回右键点击行为，可选值 "picker" 或 "eraser"。"""
        return self.get("right_click_action", "picker")

    def set_right_click_action(self, action: str) -> None:
        """设置右键点击行为并保存，action 应为 "picker" 或 "eraser"。"""
        self.set("right_click_action", action)

    # ------------------------------------------------------------------
    # 对称模式配置
    # ------------------------------------------------------------------

    def get_symmetry_mode(self) -> str:
        """返回对称模式，可选值 "none" / "horizontal" / "vertical"。"""
        return self.get("symmetry_mode", "none")

    def set_symmetry_mode(self, mode: str) -> None:
        """设置对称模式并保存，mode 应为 "none" / "horizontal" / "vertical"。"""
        self.set("symmetry_mode", mode)

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """从磁盘加载配置，异常时回退默认值并修复损坏文件。"""
        if not os.path.isfile(self._path):
            self.save()
            return

        corrupted = False
        try:
            with open(self._path, "r", encoding="utf-8") as fh:
                stored = json.load(fh)
        except (json.JSONDecodeError, OSError):
            stored = {}
            corrupted = True

        merged = _DEFAULT_CONFIG.copy()
        merged.update(stored)
        self._data = merged

        if corrupted:
            self.save()
