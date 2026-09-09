#! -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""Contextual flashing instructions for the GUI / CLI help."""

from scooterflasher.utils import F4_DEV, NINEBOT_DEV, XIAOMI_DEV, XIAOMI_V2_DEV

GENERAL = """\
ScooterFlasher — ST-Link SWD flasher (OpenOCD Tcl RPC on port 6666).

1. Wire SWDIO / SWCLK / GND / 3V3 (and NRST if available).
2. Power the board (or power from ST-Link 3V3 if the design allows).
3. Pick device + target, then Flash (or Unlock F4 first for 4proita).

OpenOCD is started automatically, or use Attach if you already started it.
"""

F4_ITA = """\
4proita = Xiaomi 4 Pro F4 ESC (STM32F400CBT6 ≈ F410) — STM32F4 only.

• Target: ESC only (no BLE in this tool).
• Default image: jump-boot ‖ app @ 0x08000000 (patched: no auto-RDP).
• Custom bootloader + custom FW: boot @ 0x08000000, app @ 0x08004000.
• SN/UUID live in I2C EEPROM — not written over SWD.
• Unlock flow: Unlock F4 → true power-cycle (POR) → restart OpenOCD → Flash.
  NRST alone is not enough after RDP clear (RM0401 §3.6.3).
• Do not use --fake-chip (that is GD32/AT32).
"""

GD32 = """\
GD32 (Xiaomi ESC, --fake-chip):
• Uses stm32f1x-nocpuid + register unlock poke, then mi_DRV_GD32.bin.
• Halt timeout messages during unlock are often expected.
"""

AT32 = """\
AT32 (Ninebot / 4pro F1-class with --fake-chip):
• Needs OpenOCD with AT32 support (bundled Windows build, or openocd-at32).
• Uses nb_DRV_AT32.bin bootloader.
"""

BLE = """\
BLE (nRF51):
• Mass-erase + SoftDevice/boot layout + UICR.
• Fast mode needs C16 removed on many dashboards.
• --fake-chip selects 16k RAM layout / UICR.bin.
"""

ESC_STD = """\
ESC (STM32 F1-class):
• Writes bootloader @ 0x08000000, app @ +0x1000, userdata @ 0xF800 (Mi) or 0x1C000 (NB/V2).
• Optional: extract UID, activate ECU, set SN/km, or restore from RAM dump.
"""


def instructions_for(device: str, target: str = "ESC", fake_chip: bool = False) -> str:
    parts = [GENERAL]
    if device in F4_DEV:
        parts.append(F4_ITA)
        return "\n".join(parts)
    if target == "BLE":
        parts.append(BLE)
    else:
        parts.append(ESC_STD)
        if fake_chip and device in XIAOMI_DEV:
            parts.append(GD32)
        if fake_chip and device in NINEBOT_DEV + XIAOMI_V2_DEV:
            parts.append(AT32)
    return "\n".join(parts)
