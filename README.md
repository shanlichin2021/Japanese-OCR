# Japanese OCR Clipboard Service

A standalone background service that automatically processes Japanese text from images using manga-ocr. Now includes an enhanced version with an active screen overlay feature.

## Features

### Core Features
- Monitors clipboard for images
- Automatically processes images with manga-ocr
- Replaces clipboard image with extracted Japanese text
- Runs in system tray
- Lightweight and efficient

### NEW: Enhanced Version with Active Overlay
- **Active Screen Overlay**: Draggable and resizable dotted overlay window
- **Region Capture**: Click "Capture" button to capture the overlay area
- **No File Saving**: Captures directly to clipboard for immediate OCR processing
- **Always On Top**: Overlay stays visible above all other windows
- **Easy Positioning**: Drag anywhere on screen, resize from corners/edges

## Setup

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the service:

**Original Version (clipboard monitoring only):**
```bash
python main.py
# Or on Windows:
start_service.bat
```

**Enhanced Version (clipboard + overlay):**
```bash
python main_with_overlay.py
# Or on Windows:
start_enhanced_service.bat
```

## Usage

### Original Clipboard Service
1. Start the service - it will appear in your system tray
2. Copy any image with Japanese text to clipboard (Ctrl+C on screenshot, etc.)
3. The service automatically processes the image and replaces it with extracted text
4. Paste (Ctrl+V) to get the OCR'd text

### Enhanced Service with Overlay
1. Start the enhanced service - it will appear in your system tray
2. **Option A - Clipboard Mode**: Same as original - copy images to clipboard for automatic processing
3. **Option B - Overlay Mode**: 
   - Right-click tray icon → "Toggle Overlay"
   - A dotted overlay window appears on screen
   - Drag the overlay to position it over Japanese text
   - Resize by dragging corners/edges to fit the text area
   - Click "Capture" button in top-right corner
   - Text is automatically extracted and copied to clipboard

## System Tray

### Original Service
- Right-click the tray icon for options
- "Status" shows current service status
- "Quit" stops the service

### Enhanced Service
- Right-click the tray icon for options
- "Status" shows both clipboard and overlay status
- "Toggle Overlay" starts/stops the overlay capture window
- "Quit" stops both services

## Notes

- Requires Windows/Linux/macOS with clipboard access
- First OCR processing may take a few seconds as the model loads
- Subsequent processing is much faster
