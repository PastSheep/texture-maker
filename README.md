# Texture Maker / 贴图工坊

> [中文版](README_zh.md)

A Minecraft mod pixel art drawing tool built with Python + tkinter + Pillow.

## Features

- **Project Management** — IDEA-style welcome screen, new/open PNG projects, recent files list
- **Canvas** — 1-128 px, MC size presets (16/32/48/64/96/128), zoom (1x-64x), grid overlay, transparent background
- **Drawing Tools** — pen, eraser, bucket (flood fill), eyedropper (screen picker), adjustable size 1-16 px
- **Palette** — 46 preset colors sorted by hue, RGBA sliders, custom palette, extract from image, recent colors
- **Reference Image** — semi-transparent overlay with adjustable opacity
- **Symmetry Drawing** — horizontal / vertical mirror
- **Undo/Redo** — 50-step history stack
- **Canvas Panning** — Space+drag / middle-button drag
- **1:1 Preview** — real-time pixel preview window
- **Export** — 2x / 4x / 8x PNG with Nearest-Neighbor scaling
- **Keyboard Shortcuts** — B/E/I/G for tools, `[`/`]` for brush size, Ctrl+Z/Y undo/redo, Ctrl+scroll zoom
- **Self-healing Config** — corrupted JSON config auto-repaired, atomic writes

## Screenshots

> Run `python main.py` to see the full interface.

## Install & Run

```bash
# Clone
git clone https://github.com/PastSheep/texture-maker.git
cd texture-maker

# Create venv & install
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS / Linux
pip install Pillow

# Run
python main.py
```

Or via `pyproject.toml`:

```bash
pip install -e .
texture-maker
```

## Project Structure

```
texture-making/
├── main.py                         # entry point
├── pyproject.toml                  # metadata & dependencies
├── tests/                          # unit tests
├── src/texture_maker/
│   ├── app.py                      # application controller
│   ├── config.py                   # JSON config persistence
│   ├── image_model.py              # pixel data + undo/redo
│   ├── tools.py                    # tool enum & manager
│   └── ui/
│       ├── canvas_widget.py        # pixel canvas widget
│       ├── main_window.py          # main editor window
│       ├── new_project_dialog.py   # new project dialog
│       ├── palette.py              # palette panel
│       └── welcome_screen.py       # welcome screen
└── .gitignore
```

## Tests

```bash
pip install pytest
pytest tests/ -v
```

## Credits

This project was developed entirely by **Claude Code** (model deepseek-v4-pro) as an AI-assisted development tool, using the superwork multi-agent collaborative workflow (execution group + review group + reject loop).

## License

CC BY-NC 4.0
