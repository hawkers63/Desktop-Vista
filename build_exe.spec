# PyInstaller spec for Desktop Vista.
#
# Build with:
#     pyinstaller build_exe.spec
#
# Output: dist\DesktopVista.exe (single-file, windowed — no console).
# customtkinter ships its theme JSON and font assets as package data, which
# PyInstaller's default module analysis does not pick up on its own, so they
# are collected explicitly below; without them the frozen app raises a
# FileNotFoundError for the default theme on first launch.

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

datas = collect_data_files("customtkinter")
datas += [("icon", "icon")]

# numpy (and its bundled OpenBLAS DLL, tens of MB on its own) is pulled in
# transitively by Pillow's PyInstaller hook purely because it happens to be
# installed in this environment — desktop_vista.py never uses NumPy-backed
# Pillow features (no Image.fromarray/np.array), so it's safe to exclude
# and keeps the single-file build well under typical distribution limits.
a = Analysis(
    ["desktop_vista.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["numpy"],
    noarchive=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="DesktopVista",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="icon/desktop_vista.ico",
)
