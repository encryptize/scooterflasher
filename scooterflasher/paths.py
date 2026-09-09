#! -*- coding: utf-8 -*-
#!/usr/bin/env python3

import os
import sys
from pathlib import Path


def _tool_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


TOOL_ROOT = _tool_root()
OOCD_SCRIPTS = TOOL_ROOT / "oocd" / "scripts"
BINARIES = TOOL_ROOT / "binaries"
BOOTLOADER_DIR = BINARIES / "bootloader"
FIRMWARE_DIR = BINARIES / "firmware"


def posix(path: str | os.PathLike) -> str:
    return Path(path).resolve().as_posix()
