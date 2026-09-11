#! -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""Load ESC/BLE bootloader decision matrix from CSV."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

CHIP_STM32 = "stm32"
CHIP_GD32 = "gd32"
CHIP_AT32 = "at32"
CHIP_STM32F4 = "stm32f4"
CHIPS = (CHIP_STM32, CHIP_GD32, CHIP_AT32, CHIP_STM32F4)

_MATRIX_PATH = Path(__file__).resolve().parent / "data" / "bootloader_matrix.csv"

# stm32f4 reuses the boot_stm32 column (single F4 image per device)
_BOOT_COL = {
    CHIP_STM32: "boot_stm32",
    CHIP_GD32: "boot_gd32",
    CHIP_AT32: "boot_at32",
    CHIP_STM32F4: "boot_stm32",
}


@dataclass(frozen=True)
class DeviceRow:
    device: str
    brand: str
    family: str  # f1 | f4
    chips: tuple[str, ...]
    boot_stm32: str
    boot_gd32: str
    boot_at32: str
    ble: str
    ble_v2: bool

    @property
    def is_f4(self) -> bool:
        return self.family == "f4" or CHIP_STM32F4 in self.chips

    @property
    def supports_ble(self) -> bool:
        return bool(self.ble)


def _parse_chips(raw: str) -> tuple[str, ...]:
    parts = [p.strip().lower() for p in (raw or "").split(";") if p.strip()]
    for p in parts:
        if p not in CHIPS:
            raise ValueError(f"unknown chip {p!r} in bootloader matrix")
    order = {c: i for i, c in enumerate(CHIPS)}
    return tuple(sorted(parts, key=lambda c: order[c]))


def _load_matrix(path: Path | None = None) -> dict[str, DeviceRow]:
    path = path or _MATRIX_PATH
    rows: dict[str, DeviceRow] = {}
    with path.open(newline="", encoding="utf-8") as fh:
        for rec in csv.DictReader(fh):
            device = (rec.get("device") or "").strip()
            if not device or device.startswith("#"):
                continue
            row = DeviceRow(
                device=device,
                brand=(rec.get("brand") or "mi").strip(),
                family=(rec.get("family") or "f1").strip().lower(),
                chips=_parse_chips(rec.get("chips") or ""),
                boot_stm32=(rec.get("boot_stm32") or "").strip(),
                boot_gd32=(rec.get("boot_gd32") or "").strip(),
                boot_at32=(rec.get("boot_at32") or "").strip(),
                ble=(rec.get("ble") or "").strip(),
                ble_v2=(rec.get("ble_v2") or "0").strip() in ("1", "true", "yes"),
            )
            if device in rows:
                raise ValueError(f"duplicate device in bootloader matrix: {device}")
            rows[device] = row
    if not rows:
        raise ValueError(f"empty bootloader matrix: {path}")
    return rows


@lru_cache(maxsize=1)
def matrix() -> dict[str, DeviceRow]:
    return _load_matrix()


def get_row(device: str) -> DeviceRow:
    rows = matrix()
    if device not in rows:
        raise KeyError(f"unknown device {device!r} (not in bootloader matrix)")
    return rows[device]


def allowed_chips(device: str) -> tuple[str, ...]:
    row = get_row(device)
    return row.chips or (CHIP_STM32,)


def supports_chip(device: str, chip: str) -> bool:
    chip = (chip or CHIP_STM32).lower()
    return chip in allowed_chips(device)


def normalize_chip(device: str, chip: str | None = None) -> str:
    """Resolve chip for device; coerce CLI default ``stm32`` → sole ``stm32f4``."""
    chip = (chip or CHIP_STM32).lower()
    allowed = allowed_chips(device)
    if chip in allowed:
        return chip
    if chip == CHIP_STM32 and CHIP_STM32F4 in allowed and len(allowed) == 1:
        return CHIP_STM32F4
    raise ValueError(
        f"chip {chip} not allowed for {device} "
        f"(allowed: {', '.join(allowed) or 'none'})"
    )


def esc_bootloader_name(device: str, chip: str = CHIP_STM32) -> str:
    """Return ESC bootloader filename for device + chip (no path)."""
    row = get_row(device)
    chip = normalize_chip(device, chip)
    col = _BOOT_COL[chip]
    name = getattr(row, col)
    if not name:
        raise ValueError(f"no bootloader for {device} chip={chip} in matrix")
    return name


def ble_bootloader_name(device: str, *, clone_chip: bool) -> str:
    row = get_row(device)
    if not row.supports_ble:
        raise ValueError(f"{device} has no BLE bootloader in matrix")
    if clone_chip or not row.ble_v2:
        return row.ble
    # V2 layout uses *_BLE_V2.bin beside the brand BLE image
    if row.ble.endswith(".bin"):
        return row.ble[:-4] + "_V2.bin"
    return row.ble + "_V2"


def device_brand(device: str) -> str:
    return get_row(device).brand


def f4_devices() -> frozenset[str]:
    return frozenset(d for d, r in matrix().items() if r.is_f4)


def no_ble_devices() -> frozenset[str]:
    return frozenset(d for d, r in matrix().items() if not r.supports_ble)


def v2_ble_devices() -> frozenset[str]:
    return frozenset(d for d, r in matrix().items() if r.ble_v2)


def matrix_devices() -> list[str]:
    """Device ids in CSV order."""
    return list(matrix().keys())
