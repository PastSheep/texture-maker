"""Tests for ToolManager and Tool enum."""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from texture_maker.tools import Tool, ToolManager


class TestToolEnum:
    def test_all_tools_present(self):
        assert Tool.PEN is not None
        assert Tool.ERASER is not None
        assert Tool.PICKER is not None
        assert Tool.BUCKET is not None

    def test_tools_are_unique(self):
        values = {Tool.PEN, Tool.ERASER, Tool.PICKER, Tool.BUCKET}
        assert len(values) == 4


class TestToolManager:
    def test_defaults(self):
        tm = ToolManager()
        assert tm.current_tool == Tool.PEN
        assert tm.color == (0, 0, 0, 255)
        assert tm.size == 1
        assert tm.symmetry_mode == "none"

    def test_get_affected_pixels_size_1(self):
        tm = ToolManager()
        tm.size = 1
        pixels = tm.get_affected_pixels(5, 5)
        assert pixels == [(5, 5)]

    def test_get_affected_pixels_size_3(self):
        tm = ToolManager()
        tm.size = 3
        pixels = tm.get_affected_pixels(5, 5)
        expected = [
            (4, 4), (5, 4), (6, 4),
            (4, 5), (5, 5), (6, 5),
            (4, 6), (5, 6), (6, 6),
        ]
        assert sorted(pixels) == sorted(expected)

    def test_add_recent_color(self):
        tm = ToolManager()
        tm.add_recent_color((255, 0, 0, 255))
        assert len(tm.recent_colors) == 1
        assert (255, 0, 0, 255) in tm.recent_colors

    def test_add_recent_color_dedup(self):
        tm = ToolManager()
        tm.add_recent_color((255, 0, 0, 255))
        tm.add_recent_color((255, 0, 0, 255))
        assert len(tm.recent_colors) == 1

    def test_add_recent_color_order(self):
        tm = ToolManager()
        tm.add_recent_color((255, 0, 0, 255))
        tm.add_recent_color((0, 255, 0, 255))
        assert tm.recent_colors[0] == (0, 255, 0, 255)  # newest first

    def test_recent_colors_max_16(self):
        tm = ToolManager()
        for i in range(20):
            tm.add_recent_color((i, i, i, 255))
        assert len(tm.recent_colors) == 16
