"""Texture Maker -- entry point."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from texture_maker.app import Application

if __name__ == "__main__":
    app = Application()
    app.run()
