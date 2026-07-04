# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Pro Tools Session Builder .app bundle.

Build:  venv/bin/pyinstaller "Pro Tools Session Builder.spec" --noconfirm
Output: dist/Pro Tools Session Builder.app

Notes:
- The two surviving AppleScripts must ship inside the bundle at the same
  relative path the code resolves (Path(__file__).parent / "scripts" in
  src/protools/applescript_runner.py).
- The app talks to Pro Tools over PTSL (gRPC, localhost:31416) and to
  System Events via osascript - the Info.plist usage strings below make
  macOS show proper Automation/Accessibility permission prompts for the
  bundle on first run.
- End-user machine requirements: Pro Tools 2024.3 (PTSL v3), sox
  (brew install sox), and Accessibility permission granted to this app.
"""

# PyInstaller's PySide6 hook bundles the Qt modules the code actually
# imports (Widgets/Gui/Core) - collect_all("PySide6") would drag in all
# of Qt (WebEngine, 3D, ...) and triple the bundle size.
datas = [
    ("src/protools/scripts/*.applescript", "src/protools/scripts"),
]
binaries = []
hiddenimports = []

a = Analysis(
    ["src/main.py"],
    pathex=[SPECPATH],  # project root, so "from src...." imports resolve
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name="Pro Tools Session Builder",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Pro Tools Session Builder",
)
app = BUNDLE(
    coll,
    name="Pro Tools Session Builder.app",
    icon=None,
    bundle_identifier="com.protoolsprepper.sessionbuilder",
    info_plist={
        "CFBundleName": "Pro Tools Session Builder",
        "CFBundleDisplayName": "Pro Tools Session Builder",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1.0.0",
        "NSHighResolutionCapable": True,
        "LSApplicationCategoryType": "public.app-category.music",
        "NSAppleEventsUsageDescription": (
            "Pro Tools Session Builder automates Pro Tools dialogs and MIDI "
            "import via System Events."
        ),
    },
)
