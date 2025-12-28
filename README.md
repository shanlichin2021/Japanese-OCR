# 代書 (Daisho) - Japanese OCR

A high-precision Japanese OCR desktop application for capturing and recognizing Japanese text from screen regions.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![PyQt6](https://img.shields.io/badge/PyQt6-6.5+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Features

- **Multiple OCR Engines**: Choose between manga-ocr (best for manga/games) or PaddleOCR (faster, lightweight)
- **Transparent Overlay**: Resizable capture region that stays on top
- **Global Hotkeys**: Keyboard shortcuts and mouse button support (mouse4, mouse5, middle click)
- **Auto-copy**: Automatically copies recognized text to clipboard
- **Macro Recording**: Record and playback input sequences for workflow automation
- **GPU Acceleration**: Automatic CUDA detection for faster inference
- **Image Preprocessing**: Multiple preprocessing modes for difficult images

## Screenshots

*Coming soon*

## Installation

### Requirements

- Python 3.10 or higher
- Windows 10/11 (primary), Linux, macOS

### Quick Setup (Windows)

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/daisho.git
   cd daisho
   ```

2. Run the setup script:
   ```bash
   setup_new.bat
   ```

3. Start the application:
   ```bash
   start_new.bat
   ```

### Manual Setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/macOS
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements_new.txt
   ```

3. Run the application:
   ```bash
   python main_new.py
   ```

### GPU Support (Optional)

For NVIDIA GPU acceleration with manga-ocr:
```bash
pip uninstall torch
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

## Usage

1. **Start the application** - It will minimize to the system tray
2. **Show the overlay** - Double-click the tray icon or right-click → Show Overlay
3. **Position the overlay** - Drag and resize over the Japanese text you want to capture
4. **Capture** - Press your hotkey (default: Ctrl+Shift) or click the capture button
5. **Get results** - Text is automatically copied to clipboard and shown in the main window

### Hotkey Configuration

- Open Settings to configure your capture hotkey
- Supports keyboard combinations (e.g., `ctrl+shift`, `alt+q`)
- Supports mouse buttons: `mouse4` (back), `mouse5` (forward), `middle`
- Combine modifiers with mouse buttons (e.g., `ctrl+mouse4`)

### OCR Engines

| Engine | Best For | Speed | Model Size |
|--------|----------|-------|------------|
| manga-ocr | Manga, games, stylized text | Slower | ~400MB |
| PaddleOCR | General Japanese text | Faster | ~100MB |

Switch engines via the system tray menu or Settings dialog.

## Project Structure

```
daisho/
├── main_new.py              # Application entry point
├── requirements_new.txt     # Python dependencies
├── setup_new.bat           # Windows setup script
├── start_new.bat           # Windows launch script
├── check_logs.py           # Log diagnostics utility
└── src/
    ├── gui/
    │   ├── main_window.py  # Main application window
    │   ├── overlay.py      # Transparent capture overlay
    │   └── settings.py     # Settings dialog
    ├── core/
    │   ├── ocr_manager.py  # OCR engine manager
    │   ├── ocr_engine.py   # manga-ocr wrapper
    │   ├── paddle_ocr_engine.py  # PaddleOCR wrapper
    │   └── macro_system.py # Input recording/playback
    └── utils/
        ├── logger.py       # Logging utilities
        ├── image_ops.py    # Image preprocessing
        └── clipboard.py    # Clipboard operations
```

## Configuration

Settings are saved to `ocr_settings.json`:

```json
{
  "capture_hotkey": "ctrl+shift",
  "ocr_engine": "manga_ocr",
  "preprocessing_mode": "none",
  "auto_copy": true,
  "show_notification": true,
  "start_minimized": true
}
```

## Troubleshooting

### Check Logs

Run the diagnostics tool:
```bash
python check_logs.py --errors    # Show recent errors
python check_logs.py --system    # Show system info
python check_logs.py --all       # Show everything
```

Logs are stored in `logs/daisho.log`

### Common Issues

- **OCR model loading slow**: First run downloads models (~100-400MB). Be patient.
- **No text detected**: Try a different preprocessing mode in Settings
- **Hotkey not working**: Run as administrator or try a different key combination

## Dependencies

- **PyQt6**: Modern Qt GUI framework
- **manga-ocr**: Vision Encoder-Decoder model for Japanese OCR
- **paddleocr/paddlepaddle**: Alternative OCR engine
- **opencv-python-headless**: Image preprocessing
- **keyboard/mouse**: Global hotkey support
- **Pillow**: Image handling

## Credits

- [manga-ocr](https://github.com/kha-white/manga-ocr) - Specialized Japanese OCR model
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) - Multilingual OCR toolkit

## License

MIT License - See [LICENSE](LICENSE) for details.
