# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:/Users/Admin/AndroidStudioProjects/MacroEngine/server/server.py'],
    pathex=[],
    binaries=[],
    datas=[('C:/Users/Admin/AndroidStudioProjects/MacroEngine/server/assets', 'assets')],
    hiddenimports=['winsdk', 'winsdk.windows.media.control', 'winsdk.windows.storage.streams', 'obswebsocket', 'pystray', 'PIL', 'PIL.Image', 'PIL.ImageDraw', 'psutil', 'win32gui', 'win32process', 'win32con', 'win32api', 'requests', 'urllib3'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MacroEngineServer',
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
    icon=['C:/Users/Admin/AndroidStudioProjects/MacroEngine/server/assets/app_icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MacroEngineServer',
)
