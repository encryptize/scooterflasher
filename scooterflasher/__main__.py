#! -*- coding: utf-8 -*-
#!/usr/bin/env python3

from scooterflasher.core import Flasher
from scooterflasher.utils import parse_args, sfprint
from scooterflasher.updater import check_update

args = parse_args()
flash = Flasher(args.device, args.sn, args.fake_chip, args.custom_fw)
check_update()

if args.target == "ESC":
    flash.flash_esc(args.extract_uid, args.activate_ecu, args.km)
elif args.target == "BLE":
    if args.fast_mode:
        sfprint("Warning! Fast mode requires to remove C16 resistor on dashboard. If flashing doesn't work, try without fast mode enabled.")
    flash.flash_ble(args.fast_mode)
