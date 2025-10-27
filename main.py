#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Warp Account Manager - Bootstrap Entry
Shows splash immediately, then lazily imports the heavy UI module.
"""

import sys
import os
import traceback

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

if __name__ == "__main__":
    # Try to update PyInstaller bootloader splash (if enabled)
    try:
        import pyi_splash
        pyi_splash.update_text("正在初始化…")
    except Exception:
        pass

    # Show minimal splash ASAP
    from PyQt5.QtWidgets import QApplication, QSplashScreen
    from PyQt5.QtGui import QPixmap, QColor
    from PyQt5.QtCore import Qt

    app = QApplication(sys.argv)

    splash = None
    try:
        pm = QPixmap(480, 240)
        pm.fill(QColor("#1e1e2e"))
        splash = QSplashScreen(pm)
        splash.setWindowFlag(Qt.WindowStaysOnTopHint)
        splash.showMessage("正在初始化，请稍候…", Qt.AlignHCenter | Qt.AlignVCenter, QColor("#cdd6f4"))
        splash.show()
        app.processEvents()
    except Exception:
        splash = None

    # Lazy import heavy modules after splash is visible
    import importlib
    try:
        wam = importlib.import_module('src.core.warp_account_manager')
        # Set plugin path before any heavy Qt loads
        try:
            if hasattr(wam, '_set_qt_plugin_path'):
                wam._set_qt_plugin_path()
        except Exception:
            pass

        # Apply stylesheet
        try:
            utils = importlib.import_module('src.utils.utils')
            if splash:
                splash.showMessage("正在加载界面主题…", Qt.AlignHCenter | Qt.AlignVCenter, QColor("#cdd6f4"))
                app.processEvents()
            utils.load_stylesheet(app)
        except Exception:
            pass

        # Set icon
        try:
            if hasattr(wam, '_resolve_icon_path'):
                from PyQt5.QtGui import QIcon
                ip = wam._resolve_icon_path()
                if ip:
                    app.setWindowIcon(QIcon(ip))
        except Exception:
            pass

        # Build and show main window
        if splash:
            splash.showMessage("正在加载账户与组件…", Qt.AlignHCenter | Qt.AlignVCenter, QColor("#cdd6f4"))
            app.processEvents()
        window = wam.MainWindow()
        window.show()
        # Close bootloader splash if present
        try:
            if 'pyi_splash' in sys.modules:
                pyi_splash.close()
        except Exception:
            pass
        if splash:
            splash.finish(window)
        sys.exit(app.exec_())
    except Exception as e:
        # Log and rethrow
        _excepthook(type(e), e, e.__traceback__)
        raise
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
