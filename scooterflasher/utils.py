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

V2_BLE_PREFIX = [
    "pro2", "1s", "lite", "mi3",
]
NINEBOT_DEV = [
    "max", "esx", "e", "f", "t15", "g2", "f2", "f2plus", "f2pro"
]

FAKEDRV_DEV = [
    "pro2", "1s", "lite", "mi3", "max", "f", "g2", "f2",
] + XIAOMI_V2_DEV

DEFAULT_ESC_SN = {
    "m365": "16133/00000000",
    "pro": "21886/00000000",
    "pro2": "26354/00000000",
    "1s": "25699/00000000",
    "lite": "25600/00000000",
    "mi3": "32124/00000000",
    "4pro": "35802/CHA00000000000",
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

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", "-d", 
                        help="Dev name of scooter. List of models could be find here: https://wiki.scooterhacking.org/doku.php?id=zip3#in-use_values",
                        required=True, type=str.lower, choices=NINEBOT_DEV+XIAOMI_DEV+XIAOMI_V2_DEV)
    parser.add_argument("--target", choices=["BLE", "ESC"], type=str.upper, required=True)
    parser.add_argument("--sn",
                        help="Serial number to set when flashing ESC. Displayed name of scooter when flashing BLE.")
    parser.add_argument("--km",
                        help="Mileage to set when flashing ECU.",
                        default=0, type=float)
    parser.add_argument("--fake-chip", action="store_true",
                        help="GD32 (or AT32 if it's Ninebot) instead of STM32 chip when flashing ECU. 16k RAM instead of 32k RAM for fake dashboard when flashing BLE.")
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
    parser.add_argument('--custom-fw', '--cfw',
                        help="Custom firmware to flash instead of an official")
    parser.add_argument("--custom-ram", "--cram",
                        help="Flash custom RAM dump instead of generated or extracted by program")
    
    args = parser.parse_args()
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
            elif args.device in NINEBOT_DEV:
                args.sn = "NBScooter0000"
    return args
