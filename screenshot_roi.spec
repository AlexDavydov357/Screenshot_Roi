# -*- mode: python ; coding: utf-8 -*-
# Сборка exe (onefile, без консоли): pyinstaller --noconfirm screenshot_roi.spec
# Запускать из окружения conda «excel» (проще всего через build_exe.bat).
import os
import sys

# Модули conda (_ctypes, pyexpat, ...) зависят от DLL в <окружение>\Library\bin (ffi.dll, libexpat.dll, ...).
# Без этой папки в PATH PyInstaller их не находит и не кладёт в exe, а exe падает:
# «DLL load failed while importing _ctypes». PATH меняется только для процесса сборки.
CONDA_BIN = os.path.join(sys.prefix, 'Library', 'bin')
if os.path.isdir(CONDA_BIN):
    os.environ['PATH'] = CONDA_BIN + os.pathsep + os.environ.get('PATH', '')

a = Analysis(
    ['screenshot_roi.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
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
    a.binaries,
    a.datas,
    [],
    name='screenshot_roi',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['images/screen_shot_icon_32.ico'],
)
