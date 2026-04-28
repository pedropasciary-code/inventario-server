# -*- mode: python ; coding: utf-8 -*-

# Configuração gerada/ajustada para o PyInstaller empacotar o agent em um exe.
a = Analysis(
    # Arquivo de entrada que inicia a coleta e o envio do inventário.
    ['agent\\agent.py'],
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

# Agrupa os módulos Python puros encontrados na análise.
pyz = PYZ(a.pure)

# Monta o executável final chamado rdp-agent.exe.
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='rdp-agent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
