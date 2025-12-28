#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代書 (Daisho) Log Checker and Diagnostics Tool

A standalone utility to check application logs, view recent errors,
and run system diagnostics without launching the full application.

Usage:
    python check_logs.py              # Show log health summary
    python check_logs.py --errors     # Show recent errors
    python check_logs.py --warnings   # Show recent warnings
    python check_logs.py --tail N     # Show last N log entries
    python check_logs.py --system     # Show system diagnostics
    python check_logs.py --all        # Show everything
"""

import sys
import os
import argparse
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

LOG_DIR = "logs"
LOG_FILE = "daisho.log"


def get_log_path() -> str:
    """Get the full path to the log file."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), LOG_DIR, LOG_FILE)


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print()
    print("=" * 60)
    print(f" {title}")
    print("=" * 60)


def show_log_health() -> None:
    """Display log file health summary."""
    log_path = get_log_path()

    print_header("LOG HEALTH SUMMARY")

    if not os.path.exists(log_path):
        print("Log file does not exist yet.")
        print(f"Expected location: {log_path}")
        return

    # File stats
    size_kb = os.path.getsize(log_path) / 1024
    mtime = datetime.fromtimestamp(os.path.getmtime(log_path))

    print(f"Log file: {log_path}")
    print(f"Size: {size_kb:.1f} KB")
    print(f"Last modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")

    # Count entries by level
    counts = {"ERROR": 0, "WARNING": 0, "INFO": 0, "DEBUG": 0}

    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                for level in counts:
                    if f"| {level}" in line:
                        counts[level] += 1
                        break

        print()
        print("Entry counts:")
        print(f"  Errors:   {counts['ERROR']}")
        print(f"  Warnings: {counts['WARNING']}")
        print(f"  Info:     {counts['INFO']}")
        print(f"  Debug:    {counts['DEBUG']}")

        if counts['ERROR'] > 0:
            print()
            print("⚠️  There are errors in the log. Use --errors to view them.")

    except Exception as e:
        print(f"Error reading log file: {e}")


def show_recent_errors(count: int = 20) -> None:
    """Display recent error entries."""
    log_path = get_log_path()

    print_header(f"RECENT ERRORS (last {count})")

    if not os.path.exists(log_path):
        print("Log file does not exist.")
        return

    errors = []
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                if '| ERROR' in line or '| CRITICAL' in line:
                    errors.append(line.strip())

        if not errors:
            print("No errors found in log file. ✓")
            return

        for err in errors[-count:]:
            print(err)

    except Exception as e:
        print(f"Error reading log file: {e}")


def show_recent_warnings(count: int = 20) -> None:
    """Display recent warning entries."""
    log_path = get_log_path()

    print_header(f"RECENT WARNINGS (last {count})")

    if not os.path.exists(log_path):
        print("Log file does not exist.")
        return

    warnings = []
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                if '| WARNING' in line:
                    warnings.append(line.strip())

        if not warnings:
            print("No warnings found in log file. ✓")
            return

        for warn in warnings[-count:]:
            print(warn)

    except Exception as e:
        print(f"Error reading log file: {e}")


def show_tail(count: int = 50) -> None:
    """Display last N log entries."""
    log_path = get_log_path()

    print_header(f"LAST {count} LOG ENTRIES")

    if not os.path.exists(log_path):
        print("Log file does not exist.")
        return

    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line in lines[-count:]:
            print(line.rstrip())

    except Exception as e:
        print(f"Error reading log file: {e}")


def show_system_diagnostics() -> None:
    """Display system diagnostics."""
    import platform

    print_header("SYSTEM DIAGNOSTICS")

    # Platform info
    print("Platform Information:")
    print(f"  OS: {platform.system()} {platform.release()}")
    print(f"  Version: {platform.version()}")
    print(f"  Machine: {platform.machine()}")
    print(f"  Processor: {platform.processor()}")
    print(f"  Python: {sys.version}")
    print(f"  Executable: {sys.executable}")

    # Memory info
    try:
        import psutil
        mem = psutil.virtual_memory()
        print()
        print("Memory:")
        print(f"  Total: {mem.total / (1024**3):.1f} GB")
        print(f"  Available: {mem.available / (1024**3):.1f} GB")
        print(f"  Used: {mem.percent}%")
    except ImportError:
        print()
        print("Memory: (install psutil for memory info)")

    # GPU info
    print()
    print("GPU Support:")

    # PyTorch
    try:
        import torch
        if torch.cuda.is_available():
            print(f"  PyTorch CUDA: Available")
            print(f"    Device: {torch.cuda.get_device_name(0)}")
            print(f"    CUDA Version: {torch.version.cuda}")
            props = torch.cuda.get_device_properties(0)
            print(f"    GPU Memory: {props.total_memory / (1024**3):.1f} GB")
        else:
            print(f"  PyTorch CUDA: Not available (CPU mode)")
    except ImportError:
        print("  PyTorch: Not installed")
    except Exception as e:
        print(f"  PyTorch: Error - {e}")

    # PaddlePaddle
    try:
        import paddle
        if paddle.device.is_compiled_with_cuda():
            gpu_count = paddle.device.cuda.device_count()
            if gpu_count > 0:
                print(f"  PaddlePaddle CUDA: Available ({gpu_count} GPU(s))")
            else:
                print(f"  PaddlePaddle CUDA: Compiled but no GPU found")
        else:
            print(f"  PaddlePaddle: CPU version")
    except ImportError:
        print("  PaddlePaddle: Not installed")
    except Exception as e:
        print(f"  PaddlePaddle: Error - {e}")

    # Package versions
    print()
    print("Package Versions:")
    packages = [
        ("PyQt6", "PyQt6"),
        ("manga-ocr", "manga_ocr"),
        ("paddleocr", "paddleocr"),
        ("paddlepaddle", "paddle"),
        ("torch", "torch"),
        ("opencv", "cv2"),
        ("Pillow", "PIL"),
        ("numpy", "numpy"),
        ("keyboard", "keyboard"),
        ("mouse", "mouse"),
        ("pyperclip", "pyperclip"),
    ]

    for display_name, import_name in packages:
        try:
            if import_name == "PIL":
                from PIL import __version__ as version
            elif import_name == "cv2":
                import cv2
                version = cv2.__version__
            else:
                mod = __import__(import_name)
                version = getattr(mod, "__version__", "installed")
            print(f"  {display_name}: {version}")
        except ImportError:
            print(f"  {display_name}: Not installed")
        except Exception as e:
            print(f"  {display_name}: Error - {e}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="MangaReader-OCR Log Checker and Diagnostics Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python check_logs.py              Show log health summary
    python check_logs.py --errors     Show recent errors
    python check_logs.py --warnings   Show recent warnings
    python check_logs.py --tail 100   Show last 100 log entries
    python check_logs.py --system     Show system diagnostics
    python check_logs.py --all        Show everything
        """
    )

    parser.add_argument("--errors", "-e", action="store_true",
                       help="Show recent error entries")
    parser.add_argument("--warnings", "-w", action="store_true",
                       help="Show recent warning entries")
    parser.add_argument("--tail", "-t", type=int, metavar="N",
                       help="Show last N log entries")
    parser.add_argument("--system", "-s", action="store_true",
                       help="Show system diagnostics")
    parser.add_argument("--all", "-a", action="store_true",
                       help="Show all diagnostics")
    parser.add_argument("--count", "-c", type=int, default=20,
                       help="Number of entries to show (default: 20)")

    args = parser.parse_args()

    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║            代書 Log Checker & Diagnostics                ║")
    print("╚══════════════════════════════════════════════════════════╝")

    # If no specific option, show health summary
    if not any([args.errors, args.warnings, args.tail, args.system, args.all]):
        show_log_health()
        print()
        print("Use --help for more options")
        return 0

    if args.all or args.system:
        show_system_diagnostics()

    if args.all:
        show_log_health()

    if args.all or args.errors:
        show_recent_errors(args.count)

    if args.all or args.warnings:
        show_recent_warnings(args.count)

    if args.tail:
        show_tail(args.tail)

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
