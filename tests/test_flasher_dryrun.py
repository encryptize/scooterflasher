#! -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""Dry-run / unit tests for ScooterFlasher (no hardware, mocked OpenOCD)."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from scooterflasher.core import ESC_APP_OFFSET, ESC_FLASH_BASE, F4_APP_BASE, F4_FLASH_BASE, Flasher
from scooterflasher.paths import BOOTLOADER_DIR, TOOL_ROOT
from scooterflasher.utils import (
    parse_args,
    supports_ble,
    supports_fake_chip,
    supports_unlock,
)


def _rpc_mock():
    rpc = MagicMock()
    rpc.send.return_value = ""
    rpc.unlock_rdp.return_value = True
    rpc.read_rdp.return_value = (0x0FFFAA00, 0xAA)
    rpc.program.return_value = ""
    return rpc


def _oocd_mock(rpc=None):
    rpc = rpc or _rpc_mock()
    oocd = MagicMock()
    oocd.start = MagicMock()
    oocd.attach = MagicMock()
    oocd.stop = MagicMock()
    oocd.rpc.return_value = rpc
    return oocd, rpc


class TestCapabilityHelpers(unittest.TestCase):
    def test_4proita_is_drv_only(self):
        self.assertFalse(supports_ble("4proita"))
        self.assertTrue(supports_unlock("4proita", "ESC"))
        self.assertFalse(supports_unlock("4proita", "BLE"))
        self.assertFalse(supports_fake_chip("4proita", "ESC"))

    def test_mi3_supports_ble_and_gd32(self):
        self.assertTrue(supports_ble("mi3"))
        self.assertTrue(supports_fake_chip("mi3", "ESC"))
        self.assertTrue(supports_fake_chip("mi3", "BLE"))

    def test_g2_no_ble(self):
        self.assertFalse(supports_ble("g2"))


class TestParseArgs(unittest.TestCase):
    def test_4proita_rejects_ble(self):
        with self.assertRaises(SystemExit):
            parse_args(["--device", "4proita", "--target", "BLE"])

    def test_4proita_rejects_fake_chip(self):
        with self.assertRaises(SystemExit):
            parse_args(["--device", "4proita", "--target", "ESC", "--fake-chip"])

    def test_unlock_flag(self):
        args = parse_args(["--device", "4proita", "--target", "ESC", "--unlock"])
        self.assertTrue(args.unlock)

    def test_default_sn(self):
        args = parse_args(["--device", "m365", "--target", "ESC"])
        self.assertEqual(args.sn, "16133/00000000")


class TestTargetSelection(unittest.TestCase):
    def test_4proita_uses_stm32f4x(self):
        f = Flasher("4proita", openocd=MagicMock())
        self.assertEqual(f._target_key(), "stm32f4x")

    def test_gd32_uses_nocpuid(self):
        f = Flasher("mi3", fake_chip=True, openocd=MagicMock())
        self.assertEqual(f._target_key(), "stm32f1x-nocpuid")

    def test_at32_target(self):
        f = Flasher("4pro", fake_chip=True, openocd=MagicMock())
        self.assertEqual(f._target_key(), "at32")

    def test_ble_fast(self):
        f = Flasher("pro2", openocd=MagicMock())
        self.assertEqual(f._target_key(ble=True, fast_mode=True), "nrf51-fast")


class TestUnlockDryRun(unittest.TestCase):
    def test_unlock_dispatches_f4(self):
        oocd, rpc = _oocd_mock()
        f = Flasher("4proita", openocd=oocd)
        out = f.unlock()
        self.assertIsNotNone(out)
        rpc.unlock_rdp.assert_called_once()
        oocd.start.assert_called_with("stm32f4x")
        oocd.stop.assert_called()

    def test_unlock_dispatches_gd32(self):
        oocd, rpc = _oocd_mock()
        f = Flasher("mi3", fake_chip=True, openocd=oocd)
        f.unlock()
        oocd.start.assert_called_with("stm32f1x-nocpuid")
        # GD32 poke hits option-byte region
        addrs = [c.args[0] for c in rpc.mww.call_args_list]
        self.assertIn(0x1FFFF800, addrs)

    def test_unlock_dispatches_stm32(self):
        oocd, rpc = _oocd_mock()
        f = Flasher("m365", openocd=oocd)
        f.unlock()
        cmds = [c.args[0] for c in rpc.send.call_args_list]
        self.assertIn("stm32f1x unlock 0", cmds)

    def test_unlock_at32_errors(self):
        oocd, _ = _oocd_mock()
        f = Flasher("max", fake_chip=True, openocd=oocd)
        with self.assertRaises(RuntimeError):
            f.unlock()


class TestFlashDryRun(unittest.TestCase):
    def test_flash_f4_combined_image(self):
        oocd, rpc = _oocd_mock()
        fw = BOOTLOADER_DIR / "mi_DRV_STM32F4.bin"
        self.assertTrue(fw.is_file(), f"missing {fw}")
        f = Flasher("4proita", openocd=oocd)
        f.flash_esc()
        oocd.start.assert_called_with("stm32f4x")
        rpc.program.assert_called()
        args, _kwargs = rpc.program.call_args
        self.assertEqual(args[1], F4_FLASH_BASE)

    def test_flash_f4_custom_boot_and_app(self):
        oocd, rpc = _oocd_mock()
        with tempfile.TemporaryDirectory() as td:
            boot = Path(td) / "jump.bin"
            app = Path(td) / "app.bin"
            boot.write_bytes(b"\x00" * 64)
            app.write_bytes(b"\x11" * 64)
            f = Flasher(
                "4proita",
                openocd=oocd,
                custom_bootloader=str(boot),
                custom_fw=str(app),
            )
            f.flash_esc()
            calls = rpc.program.call_args_list
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[0].args[1], F4_FLASH_BASE)
            self.assertEqual(calls[1].args[1], F4_APP_BASE)

    def test_flash_stm32_layout(self):
        oocd, rpc = _oocd_mock()
        with tempfile.TemporaryDirectory() as td:
            fw = Path(td) / "m365_ESC.bin"
            fw.write_bytes(b"\x22" * 128)
            # Point firmware lookup at temp via custom_fw; bootloader from repo
            f = Flasher(
                "m365",
                sn="16133/00000000",
                openocd=oocd,
                custom_fw=str(fw),
            )
            f.flash_esc(extract_uid=False, activate_ecu=True, mileage=12.5)
            addrs = [c.args[1] for c in rpc.program.call_args_list]
            self.assertEqual(addrs[0], ESC_FLASH_BASE)
            self.assertEqual(addrs[1], ESC_FLASH_BASE + ESC_APP_OFFSET)
            self.assertEqual(addrs[2], 0x0800F800)  # Mi userdata

    def test_userdata_generation(self):
        oocd, _ = _oocd_mock()
        f = Flasher("mi3", sn="32124/00000000", openocd=oocd)
        path = f.generate_userdata_esc(extract_uid=False, activate_ecu=True, mileage=1.0)
        data = Path(path).read_bytes()
        self.assertEqual(data[0:3], b"\x5c\x51\xee")
        self.assertEqual(data[59], 8)
        self.assertEqual(int.from_bytes(data[82:86], "little"), 1000)


class TestBinaryResolution(unittest.TestCase):
    def test_4proita_bins_resolve(self):
        f = Flasher("4proita", openocd=MagicMock())
        boot = f.get_bootloader_path("ESC")
        fw = f.get_firmware_path("ESC")
        self.assertTrue(Path(boot).is_file())
        self.assertTrue(Path(fw).is_file())
        self.assertTrue("mi_DRV_STM32F4" in boot)

    def test_gd32_bootloader_name(self):
        f = Flasher("mi3", fake_chip=True, openocd=MagicMock())
        path = f.get_bootloader_path("ESC")
        self.assertIn("GD32", path)


class TestOpenOcdTargetMap(unittest.TestCase):
    def test_target_cfgs_exist(self):
        from scooterflasher.oocd import TARGET_CFGS
        from scooterflasher.paths import OOCD_SCRIPTS

        for key, rel in TARGET_CFGS.items():
            cfg = OOCD_SCRIPTS / rel
            self.assertTrue(cfg.is_file(), f"missing OpenOCD cfg for {key}: {cfg}")


if __name__ == "__main__":
    os.chdir(TOOL_ROOT)
    unittest.main(verbosity=2)
