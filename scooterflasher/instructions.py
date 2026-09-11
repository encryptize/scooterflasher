#! -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""Contextual flashing instructions for the GUI / CLI help."""

from scooterflasher.matrix import esc_bootloader_name
from scooterflasher.utils import (
    CHIP_AT32,
    CHIP_GD32,
    CHIP_STM32,
    F4_DEV,
)

GENERAL = """\
ScooterFlasher - ST-Link SWD flasher (OpenOCD Tcl RPC on port 6666).

1. Wire SWDIO / SWCLK / GND / 3V3 (and NRST if available).
2. Power the board (or power from ST-Link 3V3 if the design allows).
3. Pick device + target + chip (stm32/gd32/at32), then Flash (or Unlock first).

OpenOCD is started automatically, or use Attach if you already started it.
Dry run logs Tcl commands without starting OpenOCD or writing flash.

Bootloader assignment is defined in scooterflasher/data/bootloader_matrix.csv.
"""

F4_ITA = """\
4proita = Xiaomi 4 Pro F4 ESC (STM32F400CBT6 ≈ F410) - STM32F4 only.

• Target: ESC only (no BLE in this tool).
• Firmware is required. Boot @ 0x08000000 (mi_DRV_F4.bin jump stub), app @ 0x08004000.
• SN/UUID live in I2C EEPROM - not written over SWD.
• Unlock flow: Unlock F4 → true power-cycle (POR) → restart OpenOCD → Flash.
  NRST alone is not enough after RDP clear (RM0401 §3.6.3).
• Chip: stm32f4 only (not stm32/gd32/at32).
"""

GD32 = """\
GD32 ESC (--chip gd32):
• Uses stm32f1x-nocpuid + register unlock poke.
• Halt timeout messages during unlock are often expected.
"""

AT32 = """\
AT32 ESC (--chip at32):
• Needs OpenOCD with AT32 support (bundled Windows build, or openocd-at32).
• Uses nb_DRV_AT32.bin bootloader. No separate Unlock step - Flash mass-erases.
"""

BLE = """\
BLE (nRF51):
• Firmware is required. Mass-erase + SoftDevice/boot layout + UICR.
• Fast mode needs C16 removed on many dashboards.
• --chip gd32 or at32 selects 16k RAM layout / UICR.bin (same as former --fake-chip).
"""

ESC_STD = """\
ESC (STM32 F1-class, --chip stm32):
• Firmware is required. Writes bootloader @ 0x08000000, app @ +0x1000,
  userdata @ 0xF800 (Mi) or 0x1C000 (NB/V2).
• Optional: extract UID, activate ECU, set SN/km, or restore from RAM dump.
"""


def instructions_for(device: str, target: str = "ESC", chip: str = CHIP_STM32) -> str:
    chip = (chip or CHIP_STM32).lower()
    parts = [GENERAL]
    if device in F4_DEV:
        parts.append(F4_ITA)
        return "\n".join(parts)
    if target == "BLE":
        parts.append(BLE)
    else:
        parts.append(ESC_STD)
        if chip == CHIP_GD32:
            parts.append(GD32)
            try:
                bl = esc_bootloader_name(device, CHIP_GD32)
                parts.append(f"• This model uses {bl} when GD32 is selected.")
            except ValueError:
                pass
        if chip == CHIP_AT32:
            parts.append(AT32)
            try:
                bl = esc_bootloader_name(device, CHIP_AT32)
                parts.append(f"• This model uses {bl} when AT32 is selected.")
            except ValueError:
                pass
        if chip == CHIP_STM32:
            try:
                bl = esc_bootloader_name(device, CHIP_STM32)
                parts.append(f"• This model uses {bl} for STM32.")
            except ValueError:
                pass
    return "\n".join(parts)
