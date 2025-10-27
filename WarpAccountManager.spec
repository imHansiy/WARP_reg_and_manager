# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['psutil', 'PyQt5.sip', 'src.core.warp_account_manager', 'src.utils.utils', 'src.config.languages']
hiddenimports += collect_submodules('src')


a = Analysis(
    ['main.py'],
    pathex=['src'],
    binaries=[('D:/pojie/WARP_reg_and_manager/.venv/Lib/site-packages/PyQt5/Qt5/plugins\\platforms\\qwindows.dll', 'qt_plugins/platforms'), ('D:/pojie/WARP_reg_and_manager/.venv/Lib/site-packages/PyQt5/Qt5/plugins\\imageformats\\qico.dll', 'qt_plugins/imageformats'), ('D:/pojie/WARP_reg_and_manager/.venv/Lib/site-packages/PyQt5/Qt5/plugins\\imageformats\\qjpeg.dll', 'qt_plugins/imageformats')],
    datas=[('src/ui/dark_theme.qss', 'src/ui'), ('src/static/img/logo.png', 'src/static/img'), ('src/proxy/warp_proxy_script.py', 'src/proxy')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['playwright', 'playwright_stealth', 'curl_cffi', 'tests', 'PyQt5.QtWebEngineWidgets', 'PyQt5.QtWebEngineCore', 'PyQt5.QtWebEngine', 'PyQt5.Qt3DCore', 'PyQt5.Qt3DRender', 'PyQt5.Qt3DInput', 'PyQt5.Qt3DLogic', 'PyQt5.Qt3DAnimation', 'PyQt5.QtMultimedia', 'PyQt5.QtMultimediaWidgets', 'PyQt5.QtQml', 'PyQt5.QtQuick'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
splash = Splash(
    'src/static/img/logo.png',
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,
    text_size=12,
    minify_script=True,
    always_on_top=True,
)

exe = EXE(
    pyz,
    a.scripts,
    splash,
    [],
    exclude_binaries=True,
    name='WarpAccountManager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['src\\static\\img\\logo.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    splash.binaries,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='WarpAccountManager',
)
