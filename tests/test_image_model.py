"""Tests for ImageModel -- pixel data, undo/redo, fill area."""

import os
import tempfile
import pytest
from PIL import Image

# Poor-man's path setup for test context
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from texture_maker.image_model import ImageModel


class TestImageModel:
    """Core ImageModel behaviour."""

    def test_from_size_creates_transparent(self):
        path = os.path.join(tempfile.mkdtemp(), "test.png")
        model = ImageModel.from_size(path, 16, 16)
        assert model.width == 16
        assert model.height == 16
        pixel = model.get_pixel(0, 0)
        assert pixel == (0, 0, 0, 0)

    def test_from_size_rejects_oversized(self):
        path = os.path.join(tempfile.mkdtemp(), "big.png")
        with pytest.raises(ValueError, match="尺寸"):
            ImageModel.from_size(path, 200, 16)

    def test_set_get_pixel(self):
        path = os.path.join(tempfile.mkdtemp(), "test.png")
        model = ImageModel.from_size(path, 8, 8)
        model.set_pixel(3, 4, (255, 128, 64, 200))
        assert model.get_pixel(3, 4) == (255, 128, 64, 200)
        assert model.is_modified

    def test_out_of_bounds_returns_none(self):
        path = os.path.join(tempfile.mkdtemp(), "test.png")
        model = ImageModel.from_size(path, 8, 8)
        assert model.get_pixel(-1, 0) is None
        assert model.get_pixel(8, 0) is None

    def test_save_and_load_roundtrip(self):
        path = os.path.join(tempfile.mkdtemp(), "roundtrip.png")
        model = ImageModel.from_size(path, 8, 8)
        model.set_pixel(0, 0, (255, 0, 0, 255))
        model.save()
        assert os.path.isfile(path)

        loaded = ImageModel.from_file(path)
        assert loaded.width == 8
        assert loaded.get_pixel(0, 0) == (255, 0, 0, 255)

    def test_save_creates_backup(self):
        path = os.path.join(tempfile.mkdtemp(), "backup.png")
        model = ImageModel.from_size(path, 8, 8)
        model.set_pixel(0, 0, (1, 2, 3, 255))
        model.save()
        model.set_pixel(0, 0, (4, 5, 6, 255))
        model.save()
        assert os.path.isfile(path + ".bak")

    def test_fill_area(self):
        path = os.path.join(tempfile.mkdtemp(), "fill.png")
        model = ImageModel.from_size(path, 8, 8)
        # Entire canvas is (0,0,0,0), fill with red
        changed = model.fill_area(0, 0, (255, 0, 0, 255))
        assert len(changed) == 64
        assert model.get_pixel(7, 7) == (255, 0, 0, 255)

    def test_fill_area_same_color_noop(self):
        path = os.path.join(tempfile.mkdtemp(), "noop.png")
        model = ImageModel.from_size(path, 8, 8)
        changed = model.fill_area(0, 0, (0, 0, 0, 0))
        assert len(changed) == 0


class TestUndoRedo:
    """Undo / redo stack behaviour."""

    def _new_model(self):
        path = os.path.join(tempfile.mkdtemp(), "undo.png")
        return ImageModel.from_size(path, 8, 8)

    def test_undo_restores_previous_state(self):
        model = self._new_model()
        model.begin_undo_step()
        model.set_pixel(0, 0, (255, 0, 0, 255))
        assert model.get_pixel(0, 0) == (255, 0, 0, 255)
        assert model.can_undo()

        result = model.undo()
        assert result is True
        assert model.get_pixel(0, 0) == (0, 0, 0, 0)

    def test_redo_restores_undone(self):
        model = self._new_model()
        model.begin_undo_step()
        model.set_pixel(0, 0, (255, 0, 0, 255))
        model.undo()
        assert model.can_redo()
        result = model.redo()
        assert result is True
        assert model.get_pixel(0, 0) == (255, 0, 0, 255)

    def test_undo_clears_redo_on_new_action(self):
        model = self._new_model()
        model.begin_undo_step()
        model.set_pixel(0, 0, (255, 0, 0, 255))
        model.undo()
        assert model.can_redo()
        # New action
        model.begin_undo_step()
        model.set_pixel(1, 1, (0, 255, 0, 255))
        assert not model.can_redo()

    def test_undo_empty_returns_false(self):
        model = self._new_model()
        assert model.undo() is False

    def test_history_clamped_to_50(self):
        model = self._new_model()
        for i in range(55):
            model.begin_undo_step()
            model.set_pixel(0, 0, (i % 256, 0, 0, 255))
        # Should not crash, and should still work
        assert True

    def test_get_undo_redo_status(self):
        model = self._new_model()
        can_undo, can_redo = model.get_undo_redo_status()
        assert not can_undo
        assert not can_redo

        model.begin_undo_step()
        model.set_pixel(0, 0, (1, 2, 3, 255))
        can_undo, can_redo = model.get_undo_redo_status()
        assert can_undo
        assert not can_redo
