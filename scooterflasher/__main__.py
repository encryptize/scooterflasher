#! -*- coding: utf-8 -*-
#!/usr/bin/env python3

import os
import sys


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)

    from scooterflasher.config import CONFIG_DIRECTORY
    from scooterflasher.utils import parse_args, sfprint, F4_DEV

    for d in ["binaries/firmware", "binaries/bootloader", "tmp"]:
        os.makedirs(os.path.join(CONFIG_DIRECTORY, d), exist_ok=True)

    # Default to GUI when no CLI args
    if not argv:
        from scooterflasher.gui import main as gui_main
        return gui_main()

    args = parse_args(argv)
    if args.gui:
        from scooterflasher.gui import main as gui_main
        return gui_main()

    from scooterflasher.core import Flasher
    from scooterflasher.updater import check_update

    flash = Flasher(
        args.device,
        args.sn or "",
        args.fake_chip,
        args.extract_data,
        args.custom_fw,
        args.custom_ram,
        args.openocd,
        custom_bootloader=args.custom_bootloader,
        attach=args.attach,
    )

    try:
        check_update()
    except Exception as e:
        sfprint(f"Update check skipped: {e}")

    try:
        if args.unlock_f4:
            if args.device not in F4_DEV:
                sfprint("--unlock-f4 is only for 4proita (STM32F4)")
                return 1
            flash.unlock_f4()
            return 0
        if args.target == "ESC":
            flash.flash_esc(args.extract_uid, args.activate_ecu, args.km, unlock_f4=False)
        elif args.target == "BLE":
            if args.fast_mode:
                sfprint(
                    "Warning! Fast mode requires to remove C16 resistor on dashboard. "
                    "If flashing doesn't work, try without fast mode enabled."
                )
            flash.flash_ble(args.fast_mode)
        return 0
    finally:
        if not args.attach:
            try:
                flash.openocd.stop()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
