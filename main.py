#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Warp Account Manager - Main Entry Point
This is the entry point for the application after restructuring into packages.
"""

import sys
import os
import traceback
from PyQt5.QtGui import QIcon

# Force UTF-8 stdout/stderr to avoid Windows GBK encode errors with emojis
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Basic app root resolver (works for PyInstaller and source)
def _app_root():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

LOG_PATH = os.path.join(_app_root(), 'app_error.log')

# Global exception hook to log crashes even when --noconsole is used
def _excepthook(exc_type, exc_value, exc_tb):
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write("\n=== Unhandled exception ===\n")
            traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
            f.write("\n")
    except Exception:
        pass
    # Best-effort native dialog on Windows to inform user
    try:
        import ctypes
        msg = f"应用启动失败，详情见: {LOG_PATH}"
        ctypes.windll.user32.MessageBoxW(0, msg, "WarpAccountManager 错误", 0x10)
    except Exception:
        pass

sys.excepthook = _excepthook

# Optional: enable faulthandler to log hard crashes
try:
    import faulthandler
    fh = open(LOG_PATH, 'a', encoding='utf-8')
    faulthandler.enable(fh)
except Exception:
    pass

# Add src directory to Python path
sys.path.insert(0, os.path.join(_app_root(), 'src'))

# Import and run the main application
from src.core.warp_account_manager import main

# Try set application icon
def _set_app_icon():
    try:
        # Candidates in packaged and source layouts
        bases = []
        if getattr(sys, 'frozen', False):
            bases.append(getattr(sys, '_MEIPASS', os.path.dirname(sys.executable)))
            bases.append(os.path.dirname(sys.executable))
        else:
            bases.append(os.path.dirname(os.path.abspath(__file__)))
        candidates = []
        for b in bases:
            candidates.append(os.path.join(b, 'src', 'static', 'img', 'logo.jpg'))
            candidates.append(os.path.join(b, 'static', 'img', 'logo.jpg'))
        for p in candidates:
            if os.path.exists(p):
                from PyQt5.QtWidgets import QApplication
                app = QApplication.instance()
                if app is None:
                    app = QApplication(sys.argv)
                app.setWindowIcon(QIcon(p))
                return app
    except Exception:
        return None
    return None

if __name__ == "__main__":
    main()
