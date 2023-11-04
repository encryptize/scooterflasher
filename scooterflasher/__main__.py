#! -*- coding: utf-8 -*-
#!/usr/bin/env python3

import os

from scooterflasher.core import Flasher
from scooterflasher.utils import parse_args, sfprint
from scooterflasher.config import CONFIG_DIRECTORY
from scooterflasher.updater import check_update

for dir in ["binaries/firmware", "tmp"]:
    os.makedirs(os.path.join(CONFIG_DIRECTORY, dir), exist_ok=True)

args = parse_args()
flash = Flasher(args.device, args.sn, args.fake_chip, args.extract_data, args.custom_fw, args.openocd)
check_update()

if args.target == "ESC":
    flash.flash_esc(args.extract_uid, args.activate_ecu, args.km)
elif args.target == "BLE":
    if args.fast_mode:
        sfprint("Warning! Fast mode requires to remove C16 resistor on dashboard. If flashing doesn't work, try without fast mode enabled.")
    flash.flash_ble(args.fast_mode)
