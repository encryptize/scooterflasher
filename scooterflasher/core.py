#! -*- coding: utf-8 -*-
#!/usr/bin/env python3
# ScooterFlasher is mostly inspired with ReFlasher created by ScooterHacking.org
# You can read more about their project at https://scooterhack.in/reflasher
# Many thanks to them! Without their project,
# creating ScooterFlasher would have been a much more difficult task!
# <3 ScooterHacking.org <3

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Callable

from scooterflasher.config import CONFIG_DIRECTORY
from scooterflasher.oocd import OpenOCD
from scooterflasher.paths import BOOTLOADER_DIR, FIRMWARE_DIR, TOOL_ROOT, posix
from scooterflasher.rpc import POR_INSTRUCTIONS, rdp_level
from scooterflasher.utils import (
    FAKEDRV_DEV,
    F4_DEV,
    NINEBOT_DEV,
    V2_BLE_PREFIX,
    XIAOMI_DEV,
    XIAOMI_V2_DEV,
    sfprint,
)

LogFn = Callable[[str], None]

ESC_FLASH_BASE = 0x08000000
ESC_APP_OFFSET = 0x1000
F4_FLASH_BASE = 0x08000000
F4_APP_BASE = 0x08004000


class Flasher:
    def __init__(
        self,
        device: str,
        sn: str = "",
        fake_chip: bool = False,
        extract_data: bool = False,
        custom_fw: str | None = None,
        custom_ram: str | None = None,
        openocd_path: str | None = None,
        custom_bootloader: str | None = None,
        log: LogFn | None = None,
        openocd: OpenOCD | None = None,
        attach: bool = False,
    ) -> None:
        self.device = device
        self.sn = sn or ""
        self.fake_chip = fake_chip
        self.extract_data = extract_data
        self.custom_fw = custom_fw
        self.custom_ram = custom_ram
        self.custom_bootloader = custom_bootloader
        self.attach = attach
        self.log = log or sfprint
        self.openocd = openocd or OpenOCD(openocd_path, log=self.log)

    def _say(self, msg: str) -> None:
        self.log(msg)

    def _target_key(self, *, ble: bool = False, fast_mode: bool = False) -> str:
        if ble:
            return "nrf51-fast" if fast_mode else "nrf51"
        if self.device in F4_DEV:
            return "stm32f4x"
        if self.fake_chip and self.device in XIAOMI_DEV:
            return "stm32f1x-nocpuid"
        if self.fake_chip and self.device in NINEBOT_DEV + XIAOMI_V2_DEV:
            return "at32"
        return "stm32f1x"

    def _ensure(self, *, ble: bool = False, fast_mode: bool = False):
        key = self._target_key(ble=ble, fast_mode=fast_mode)
        if self.attach:
            self.openocd.attach()
        else:
            self.openocd.start(key)
        return self.openocd.rpc()

    def unlock_gd32(self) -> None:
        self._say("Unlocking GD32")
        rpc = self._ensure()
        rpc.init_halt()
        rpc.send("mdw 0x40022100")
        rpc.mww(0x40022004, 0x45670123)
        rpc.mww(0x40022004, 0xCDEF89AB)
        rpc.mww(0x4002200C, 0x34)
        rpc.mww(0x4002200C, 0x1)
        rpc.mww(0x40022008, 0x45670123)
        rpc.mww(0x40022008, 0xCDEF89AB)
        rpc.send("mdw 0x40022100")
        rpc.mww(0x40022100, 0x220)
        rpc.mww(0x40022100, 0x260)
        rpc.send("mdw 0x4002200C")
        rpc.mww(0x4002200C, 0x200)
        rpc.mww(0x4002200C, 0x210)
        rpc.mww(0x1FFFF800, 0xFFFF00A5)
        rpc.send("mdw 0x4002200C")
        rpc.mww(0x40022010, 0x80)
        self._say("GD32 unlock sequence sent")

    def unlock_stm32(self) -> None:
        """Clear STM32F1 RDP (standard ESC)."""
        self._say("Unlocking STM32 (stm32f1x unlock 0)")
        rpc = self._ensure()
        rpc.init_halt()
        rpc.send("flash probe 0")
        rpc.send("stm32f1x unlock 0")
        rpc.send("reset halt")
        self._say("STM32 unlock done (power-cycle if flash still locked)")

    def unlock_f4(self) -> str:
        """Clear STM32F4 RDP on 4proita. Caller must POR before flashing."""
        self._say("Unlocking 4proita STM32F4 (stm32f2x unlock 0)")
        rpc = self._ensure()
        ok = rpc.unlock_rdp(log=self._say)
        if not ok:
            raise RuntimeError("F4 unlock failed")
        if not self.attach:
            self.openocd.stop()
        self._say(POR_INSTRUCTIONS)
        return POR_INSTRUCTIONS

    def unlock(self) -> str | None:
        """Pick unlock path for the current scooter / chip options."""
        if self.device in F4_DEV:
            return self.unlock_f4()
        if self.fake_chip and self.device in XIAOMI_DEV:
            self.unlock_gd32()
            return None
        if self.fake_chip and self.device in NINEBOT_DEV + XIAOMI_V2_DEV:
            raise RuntimeError(
                "AT32 has no separate unlock step — use Flash (mass-erase is included)."
            )
        self.unlock_stm32()
        return None

    def read_uid_stm32(self) -> bool:
        self._say("Reading STM32 UID")
        uid_file = Path(CONFIG_DIRECTORY) / "tmp" / "uid.bin"
        uid_file.parent.mkdir(parents=True, exist_ok=True)
        rpc = self._ensure()
        rpc.init_halt()
        rpc.send("flash probe 0")
        rpc.send("stm32f1x unlock 0")
        rpc.send("reset halt")
        rpc.dump_image(uid_file, 0x1FFFF7E8, 12)
        return uid_file.is_file() and uid_file.stat().st_size >= 12

    def flash_stm32(self) -> None:
        self._say("Writing ESC (STM32/GD32/AT32)")
        bootloader_file = self.get_bootloader_path("ESC")
        firmware_file = self.get_firmware_path("ESC")
        user_data = (
            self.get_cuted_ram_path()
            if self.extract_data or self.custom_ram
            else self.get_userdata_location()
        )

        rpc = self._ensure()
        rpc.init_halt()
        rpc.send("flash probe 0")
        if not (self.fake_chip and self.device in XIAOMI_DEV):
            if self.fake_chip and self.device in NINEBOT_DEV + XIAOMI_V2_DEV:
                pass  # AT32: skip stm32f1x unlock
            else:
                rpc.send("stm32f1x unlock 0")
                rpc.send("reset halt")
        if self.fake_chip and self.device in NINEBOT_DEV + XIAOMI_V2_DEV:
            rpc.send("flash erase_sector 0 0 last")
        else:
            rpc.send("stm32f1x mass_erase 0")

        rpc.program(bootloader_file, ESC_FLASH_BASE)
        rpc.program(firmware_file, ESC_FLASH_BASE + ESC_APP_OFFSET)
        if self.device in NINEBOT_DEV + XIAOMI_V2_DEV:
            rpc.program(user_data, 0x0801C000)
        elif self.device in XIAOMI_DEV:
            rpc.program(user_data, 0x0800F800)
        rpc.reset_run()
        self._say("ESC flash done")

    def flash_f4(self, *, unlock_first: bool = False) -> None:
        """4proita STM32F4: program combined boot‖app at 0x08000000."""
        if self.device not in F4_DEV:
            raise RuntimeError(f"{self.device} is not an STM32F4 (4proita) device")
        if unlock_first:
            self.unlock_f4()
            raise RuntimeError(
                "F4 unlock done — power-cycle ESC, restart OpenOCD, then flash without --unlock-f4"
            )

        self._say("Writing 4proita ESC (STM32F4)")
        rpc = self._ensure()
        rpc.init_halt()
        _, rdp = rpc.read_rdp()
        if rdp is not None and rdp != 0xAA:
            self._say(
                f"WARNING: RDP 0x{rdp:02X} ({rdp_level(rdp)}). "
                "Unlock + POR first if program/verify fails."
            )

        boot = self.get_bootloader_path("ESC")
        fw = self.get_firmware_path("ESC")

        if self.custom_bootloader and self.custom_fw:
            self._say(f"Bootloader @ 0x{F4_FLASH_BASE:08X}: {boot}")
            self._say(f"App @ 0x{F4_APP_BASE:08X}: {fw}")
            rpc.program(boot, F4_FLASH_BASE)
            rpc.program(fw, F4_APP_BASE)
        else:
            self._say(f"Image @ 0x{F4_FLASH_BASE:08X}: {fw}")
            rpc.program(fw, F4_FLASH_BASE)

        rpc.reset_run()
        self._say("4proita STM32F4 flash done")

    def flash_nrf51(self, fast_mode: bool) -> None:
        self._say("Writing BLE (nRF51)")
        bootloader_file = self.get_bootloader_path("BLE")
        firmware_file = self.get_firmware_path("BLE")
        user_data = self.get_userdata_location()
        uicr_file = self.get_uicr_file()

        rpc = self._ensure(ble=True, fast_mode=fast_mode)
        rpc.init_halt()
        rpc.send("nrf51 mass_erase")
        rpc.program(bootloader_file, 0x00000000)
        if self.fake_chip or self.device not in V2_BLE_PREFIX:
            rpc.program(firmware_file, 0x18000)
            rpc.program(user_data, 0x23400)
        else:
            rpc.program(firmware_file, 0x1B000)
            rpc.program(user_data, 0x3B800)
        rpc.program(uicr_file, 0x10001000)
        rpc.reset_run()
        self._say("BLE flash done")

    def dump_ram_stm32(self) -> None:
        if self.fake_chip and self.device in XIAOMI_DEV:
            self._say("Warning: GD32 RAM dump is less tested — report issues if it fails.")
        ram_file = self.get_ram_path()
        rpc = self._ensure()
        rpc.init_halt()
        rpc.dump_image(ram_file, 0x20000000, 0x7D00)

    def flash_esc(
        self,
        extract_uid: bool = False,
        activate_ecu: bool = False,
        mileage: float = 0,
        unlock_f4: bool = False,
    ) -> None:
        if self.device in F4_DEV:
            self.flash_f4(unlock_first=unlock_f4)
            return

        if self.fake_chip and self.device not in FAKEDRV_DEV:
            raise RuntimeError(f"{self.device} doesn't have a fake chip")
        if not self.extract_data and not self.custom_ram:
            if mileage < 0 or mileage > 30000:
                raise ValueError("Mileage must be between 0 and 30000km")
            if len(self.sn) != 14 and self.device not in XIAOMI_V2_DEV:
                raise ValueError(f"SN must be 14-chars long. {self.sn}")
            elif len(self.sn) != 20 and self.device in XIAOMI_V2_DEV:
                raise ValueError(f"SN must be 20-chars long. {self.sn}")
            if self.device in XIAOMI_DEV:
                if not re.match(r"[0-9]{5}\/[0-9]{8}", self.sn):
                    raise ValueError(f"Invalid SN format. {self.sn}")
            elif self.device in XIAOMI_V2_DEV:
                if not re.match(r"[0-9]{5}\/[A-Z0-9]{14}", self.sn):
                    raise ValueError(f"Invalid SN format. {self.sn}")
            elif self.device in NINEBOT_DEV:
                if not re.match(r"[A-Z0-9]{14}", self.sn):
                    raise ValueError(f"Invalid SN format. {self.sn}")

        if self.fake_chip and self.device in XIAOMI_DEV:
            self.unlock_gd32()

        if self.extract_data:
            self.dump_ram_stm32()
            self.parse_userdata_esc_ram()
        elif self.custom_ram:
            self.parse_userdata_esc_ram()
        else:
            if extract_uid:
                if not self.read_uid_stm32():
                    raise RuntimeError("Failed to read chip UID")
            self.generate_userdata_esc(extract_uid, activate_ecu, mileage)

        if self.fake_chip and self.device in XIAOMI_DEV:
            self.unlock_gd32()

        self.flash_stm32()
        self._say("All done")

    def flash_ble(self, fast_mode: bool) -> None:
        if self.device in F4_DEV:
            raise RuntimeError("4proita is STM32F4 ESC only — no BLE target")
        if len(self.sn) <= 0 or len(self.sn) > 13:
            raise ValueError(
                f"The scooter name must have at least one character, and up to 13. {self.sn}"
            )
        self.generate_userdata_ble()
        self.flash_nrf51(fast_mode)
        self._say("All done")

    def generate_userdata_esc(self, extract_uid: bool, activate_ecu: bool, mileage: float) -> str:
        userdata = bytearray(1023)
        userdata[0:3] = b"\x5C\x51\xEE\x07"

        sn_offset = 168 if self.device in XIAOMI_V2_DEV else 32
        userdata[sn_offset : sn_offset + len(self.sn)] = self.sn.encode(encoding="ascii")
        if extract_uid:
            with open(os.path.join(CONFIG_DIRECTORY, "tmp", "uid.bin"), mode="rb") as uf:
                userdata[436 : 436 + 12] = uf.read()
        if activate_ecu:
            userdata[59] = 8
        userdata[82 : 82 + 4] = int(mileage * 1000).to_bytes(4, "little")

        tmp_userdata = self.get_userdata_location()
        with open(tmp_userdata, mode="wb") as f_data:
            f_data.write(userdata)

        self._say("Generated user data page")
        return tmp_userdata

    def parse_userdata_esc_ram(self) -> str:
        ram_path = self.get_ram_path() if not self.custom_ram else self.custom_ram
        if not os.path.isfile(ram_path):
            raise RuntimeError("No RAM dump file found")

        with open(ram_path, mode="rb") as fh:
            ram_content = fh.read()

        offset = 0
        conf_sig = b"\x5C\x51\xEE\x07"
        for i in range(len(ram_content)):
            if i + len(conf_sig) > len(ram_content) - 1:
                break
            if ram_content[i : i + len(conf_sig)] == conf_sig:
                offset = i

        userdata = ram_content[offset:][:512]
        sn_offset = 32
        sn_len = 20
        if self.device in XIAOMI_V2_DEV:
            sn_offset = 168
            sn_len = 20
        stat = int.from_bytes(userdata[58 : 58 + 2], "big")
        data = {
            "ESC_SN": userdata[sn_offset : sn_offset + sn_len].decode("ascii", errors="replace"),
            "ESC_UUID": userdata[436 : 436 + 12].hex().upper(),
            "ESC_TOTAL_MILEAGE": int.from_bytes(userdata[82 : 82 + 4], "little") / 1000,
            "ESC_STAT": "Activated (8)" if stat == 8 else stat,
        }

        self._say("Found the following information from the controller:")
        for k, v in data.items():
            self._say(f"{k}: {v}")

        cuted_ram = self.get_cuted_ram_path()
        with open(cuted_ram, "wb") as fh:
            fh.write(userdata)

        return cuted_ram

    def generate_userdata_ble(self) -> str:
        userdata = bytearray(23)
        userdata[0:1] = b"U\xaa"
        userdata[8 : 8 + len(self.sn)] = self.sn.encode(encoding="ascii")

        tmp_userdata = self.get_userdata_location()
        with open(tmp_userdata, mode="wb") as f_data:
            f_data.write(userdata)

        self._say("Generated user data page")
        return tmp_userdata

    def _resolve_binary(self, *candidates: Path) -> str:
        for c in candidates:
            if c.is_file():
                return posix(c)
        raise FileNotFoundError(
            "Missing binary. Tried:\n  " + "\n  ".join(str(c) for c in candidates)
        )

    def get_bootloader_path(self, target: str) -> str:
        if self.custom_bootloader:
            return posix(self.custom_bootloader)

        if self.device in F4_DEV and target == "ESC":
            return self._resolve_binary(
                BOOTLOADER_DIR / "mi_DRV_STM32F4.bin",
                Path(CONFIG_DIRECTORY) / "binaries" / "bootloader" / "mi_DRV_STM32F4.bin",
            )

        if self.device in XIAOMI_DEV:
            brand = "mi"
        elif self.device in NINEBOT_DEV + XIAOMI_V2_DEV:
            brand = "nb"
        else:
            brand = "mi"

        if target == "ESC":
            if self.fake_chip and self.device in XIAOMI_DEV:
                bootloader_file = f"{brand}_DRV_GD32.bin"
            elif self.fake_chip and self.device in NINEBOT_DEV + XIAOMI_V2_DEV:
                bootloader_file = f"{brand}_DRV_AT32.bin"
            else:
                bootloader_file = f"{brand}_DRV.bin"
        elif target == "BLE":
            bootloader_file = (
                f"{brand}_BLE.bin"
                if self.fake_chip or self.device not in V2_BLE_PREFIX
                else f"{brand}_BLE_V2.bin"
            )
        else:
            raise ValueError(target)

        return self._resolve_binary(
            Path(CONFIG_DIRECTORY) / "binaries" / "bootloader" / bootloader_file,
            BOOTLOADER_DIR / bootloader_file,
            TOOL_ROOT / "binaries" / "bootloader" / bootloader_file,
        )

    def get_firmware_path(self, target: str) -> str:
        if self.custom_fw:
            return posix(self.custom_fw)

        if self.device in F4_DEV and target == "ESC":
            # Single shipped image: jump-boot ‖ app (mi_DRV_STM32F4.bin)
            return self._resolve_binary(
                BOOTLOADER_DIR / "mi_DRV_STM32F4.bin",
                Path(CONFIG_DIRECTORY) / "binaries" / "bootloader" / "mi_DRV_STM32F4.bin",
            )

        device = "f2" if self.device.startswith("f2") else self.device
        firmware_file = f"{device}_{target}.bin"
        return self._resolve_binary(
            Path(CONFIG_DIRECTORY) / "binaries" / "firmware" / firmware_file,
            FIRMWARE_DIR / firmware_file,
        )

    def get_uicr_file(self) -> str:
        uicr_file = (
            "UICR.bin"
            if self.fake_chip or self.device not in V2_BLE_PREFIX
            else "UICR_32K.bin"
        )
        stem = uicr_file.replace(".bin", "")
        return self._resolve_binary(
            Path(CONFIG_DIRECTORY) / "binaries" / uicr_file,
            TOOL_ROOT / "binaries" / uicr_file,
            TOOL_ROOT / "binaries" / stem,
            Path(CONFIG_DIRECTORY) / "binaries" / stem,
        )

    @staticmethod
    def get_userdata_location() -> str:
        return posix(Path(CONFIG_DIRECTORY) / "tmp" / "data_tmp.bin")

    @staticmethod
    def get_ram_path() -> str:
        return posix(Path(CONFIG_DIRECTORY) / "tmp" / "RAM.bin")

    @staticmethod
    def get_cuted_ram_path() -> str:
        return posix(Path(CONFIG_DIRECTORY) / "tmp" / "RAM_cuted.bin")
