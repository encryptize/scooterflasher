#! -*- coding: utf-8 -*-
#!/usr/bin/env python3

import argparse
import sys

XIAOMI_DEV = [
    "m365", "pro", "pro2", "1s", "lite", "mi3",
]

XIAOMI_V2_DEV = [
    "4pro", "4proplus", "4promax"
]

# Xiaomi 4 Pro F4 ESC (STM32F400CBT6 / F410 stand-in) - not the F1/AT32 "4pro"
F4_DEV = [
    "4proita",
]

V2_BLE_PREFIX = [
    "pro2", "1s", "lite", "mi3",
]
NINEBOT_DEV = [
    "max", "esx", "e", "f", "t15", "g2", "f2", "f2plus", "f2pro"
]

FAKEDRV_DEV = [
    "pro2", "1s", "lite", "mi3", "max", "f", "g2", "f2",
] + XIAOMI_V2_DEV

ALL_DEVICES = NINEBOT_DEV + XIAOMI_DEV + XIAOMI_V2_DEV + F4_DEV

# BLE not supported / not wired in this tool
NO_BLE_DEV = set(F4_DEV) | {"g2"}


def supports_ble(device: str) -> bool:
    return device not in NO_BLE_DEV


def supports_drv(device: str) -> bool:
    return True  # all listed models have an ESC/DRV path


def supports_fake_chip(device: str, target: str = "ESC") -> bool:
    if device in F4_DEV:
        return False
    if target == "BLE":
        return True  # 16k RAM layout
    return device in FAKEDRV_DEV


def supports_unlock(device: str, target: str = "ESC") -> bool:
    """Unlock applies to DRV/ESC only (RDP / GD32 / F4)."""
    return target == "ESC"

DEFAULT_ESC_SN = {
    "m365": "16133/00000000",
    "pro": "21886/00000000",
    "pro2": "26354/00000000",
    "1s": "25699/00000000",
    "lite": "25600/00000000",
    "mi3": "32124/00000000",
    "4pro": "35802/CHA00000000000",
    "4proita": "",  # SN in I2C EEPROM - not written over SWD
    "max": "N4GSD0000C0000",
    "esx": "N2GSD0000C0000",
    "e": "N2GQD0000C0000",
    "f": "N5GED0000C0000",
    "t15": "N3GCD0000C0000",
    "g2": "01GXD0000C0000",
    "f2": "NAGAA0000C0000",
    "f2plus": "NAGFA0000C0000",
    "f2pro": "NAGRA0000C0000",
    "4proplus": "49316/CHAL0000000000",
    "4promax": "50967/CHAL0000000000"
}

OPENOCD_ERRORS = [
    {
        "error": "Error: open failed",
        "log": "Couldn't connect to ST-Link",
        "type": "equals",
        "critical": True
    },
    {
        "error": "Info : STLINK",
        "log": "Found ST-Link",
        "type": "starts",
        "critical": False
    },
    {
        "error": "Error: init mode failed (unable to connect to the target)",
        "log": "Couldn't connect to target",
        "type": "equals",
        "critical": True
    },
    {
        "error": "dumped 12 bytes",
        "log": "Got UID for activation",
        "type": "starts",
        "critical": False
    },
    {
        "error": ["Mass erase complete", "mass erase complete"],
        "log": "Erased chip",
        "type": "contains",
        "critical": False
    },
    {
        "error": ["stm32x unlocked.", "A reset or power cycle"],
        "log": "Disabled RDP",
        "type": "equals",
        "critical": False
    },
    {
        "error": ["wrote", "** Programming Finished **"],
        "log": "todo writes",
        "type": "starts",
        "critical": False
    },
    {
        "error": ["Error: error waiting for target flash write algorithm",
                  "Error: error writing to flash ",
                  "Error: Failed to write to nrf5 flash",
                  "Error: Failed to enable read-only operation"
                  ],
        "log": "Error writing to flash (target disconnected?)",
        "type": "starts",
        "critical": True
    },
    {
        "error": "Error: jtag status contains invalid mode value - communication failure",
        "log": "Lost connection",
        "type": "equals",
        "critical": True
    },
    {
        "error": "Error: timed out while waiting for target halted",
        "log": "Ignore the halt error - it is expected when unlocking GD32.",
        "type": "equals",
        "critical": False
    },
    {
        "error": "Error",
        "log": "Unknown error, check logs",
        "type": "starts",
        "critical": True
    }
]

def sfprint(*objs, **kwargs):
    print("[ScooterFlasher]", *objs, **kwargs)

def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="ScooterFlasher - ST-Link / OpenOCD SWD flasher"
    )
    parser.add_argument("--gui", action="store_true", help="Launch the GUI")
    parser.add_argument("--device", "-d",
                        help="Device model",
                        type=str.lower, choices=ALL_DEVICES)
    parser.add_argument("--target", choices=["BLE", "ESC"], type=str.upper)
    parser.add_argument("--sn",
                        help="Serial number to set when flashing ESC. Displayed name of scooter when flashing BLE.")
    parser.add_argument("--km",
                        help="Mileage to set when flashing ECU.",
                        default=0, type=float)
    parser.add_argument("--fake-chip", action="store_true",
                        help="GD32 (Xiaomi) or AT32 (Ninebot/V2) instead of STM32. 16k RAM BLE when flashing dashboard.")
    parser.add_argument("--extract-data", action="store_true",
                        help="Extract all data from ECU during flash. If enabled, there is no need to complete the data for the controller.")
    parser.add_argument("--extract-uid", action="store_true",
                        help="Extract chip UID during flashing")
    parser.add_argument("--activate-ecu", action="store_true",
                        help="Activate ECU during flashing")
    parser.add_argument("--fast-mode", "-fm", action="store_true",
                        help="Use 1000kHz instead of 450kHz (Applies to BLE only)")
    parser.add_argument("--openocd",
                        help="Location of openocd binary.")
    parser.add_argument("--attach", action="store_true",
                        help="Attach to an already-running OpenOCD Tcl RPC (port 6666)")
    parser.add_argument('--custom-fw', '--cfw', '--fw',
                        required=False,
                        help="Firmware .bin to flash (required unless --unlock)")
    parser.add_argument("--custom-bootloader", "--cbl",
                        help="Bootloader image override (ESC). Default: shipped DRV boot. "
                             "F4: jump boot @ 0x08000000; app (--cfw) @ 0x08004000")
    parser.add_argument("--custom-ram", "--cram",
                        help="Flash custom RAM dump instead of generated or extracted by program")
    parser.add_argument("--unlock", "--unlock-f4", action="store_true",
                        help="Unlock only (F4 / GD32 / STM32 RDP as appropriate for device); do not flash")
    parser.add_argument("--dry-run", action="store_true",
                        help="Log OpenOCD commands without starting OpenOCD or writing flash")

    args = parser.parse_args(argv)

    if args.gui:
        return args

    if not args.device or not args.target:
        parser.error("--device and --target are required (or pass --gui)")

    if args.device in F4_DEV:
        if args.target != "ESC":
            parser.error("4proita is STM32F4 ESC only (no BLE target)")
        if args.fake_chip:
            parser.error("4proita is STM32F4 - --fake-chip does not apply")
        args.sn = args.sn or ""

    if not args.unlock and not args.custom_fw:
        parser.error("Firmware is required: pass --cfw / --fw (unless --unlock)")

    if args.device in F4_DEV:
        return args

    if args.target == "ESC":
        if not args.extract_data and not args.custom_ram and not args.sn:
            sfprint(f"No serial number is given, the program will use the default one. {DEFAULT_ESC_SN[args.device]} for {args.device}")
            args.sn = DEFAULT_ESC_SN[args.device]
    elif args.target == "BLE":
        if args.device == "g2":
            sfprint(f"BLE flashing is not currently supported for this model ({args.device})!")
            sys.exit(1)
        if not args.sn:
            sfprint("No displayed name is given for the display. The program will use the default one.")
            if args.device in XIAOMI_DEV:
                args.sn = "MIScooter0000"
            elif args.device in NINEBOT_DEV + XIAOMI_V2_DEV:
                args.sn = "NBScooter0000"
    return args
