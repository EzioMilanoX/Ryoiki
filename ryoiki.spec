# -*- mode: python ; coding: utf-8 -*-
"""
Receita do executavel:  python -m PyInstaller ryoiki.spec

Sai em dist/Ryoiki/ (Ryoiki.exe e a pasta _internal ao lado). Leva `ryoiki/data/`
no mesmo caminho, porque `DADOS` e relativo ao proprio modulo. A OuroborosEngine
esta instalada em modo editavel (repo irmao): o PyInstaller nao segue esse
ponteiro sozinho, entao a raiz dela entra no pathex. `onedir`, nao `onefile`:
o Controle Inteligente de Aplicativos do Windows 11 barra o onefile.
"""
from pathlib import Path

import ouroboros
from PyInstaller.utils.hooks import collect_submodules

RAIZ = Path(SPECPATH).resolve()
ENGINE = Path(ouroboros.__file__).resolve().parent.parent
icone = RAIZ / "ryoiki" / "data" / "icone.ico"

analysis = Analysis(
    [str(RAIZ / "ryoiki" / "__main__.py")],
    pathex=[str(RAIZ), str(ENGINE)],
    binaries=[],
    datas=[(str(RAIZ / "ryoiki" / "data"), "ryoiki/data")],
    hiddenimports=[n for n in collect_submodules("ouroboros") if not n.startswith("ouroboros.rhythm.offline")]
    + collect_submodules("ryoiki"),
    excludes=["tkinter", "unittest", "pytest", "numpy.testing", "pygame.tests",
              "scipy", "matplotlib", "PIL", "ouroboros.rhythm.offline"],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(pyz, analysis.scripts, [], exclude_binaries=True, name="Ryoiki", debug=False,
          strip=False, upx=False, console=False, icon=str(icone) if icone.is_file() else None)
collected = COLLECT(exe, analysis.binaries, analysis.datas, strip=False, upx=False, name="Ryoiki")
