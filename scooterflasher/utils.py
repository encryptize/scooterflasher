#! -*- coding: utf-8 -*-
#!/usr/bin/env python3

import argparse

XIAOMI_DEV = [
    "m365", "pro", "pro2", "1s", "lite", "mi3"
]
V2_BLE_PREFIX = [
    "pro2", "1s", "lite", "mi3"
]
NINEBOT_DEV = [
    "max", "esx", "e", "f", "t15"
]

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
                        required=True, type=str.lower, choices=NINEBOT_DEV+XIAOMI_DEV)
    parser.add_argument("--target", choices=["BLE", "ESC"], type=str.upper, required=True)
    parser.add_argument("--sn",
                        help="Serial number to set when flashing ESC. Displayed name of scooter when flashing BLE.",
                        required=True)
    parser.add_argument("--km",
                        help="Mileage to set when flashing ECU.",
                        default=0, type=float)
    parser.add_argument("--fake-chip", action="store_true",
                        help="GD32 (or AT32 if it's Ninebot) instead of STM32 chip when flashing ECU. 16k RAM instead of 32k RAM for fake dashboard when flashing BLE.")
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
    
    args = parser.parse_args()
    return args
