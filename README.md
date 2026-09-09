
# ScooterFlasher

ScooterFlasher is an OpenOCD / ST-Link SWD flasher for Xiaomi and Ninebot scooters (CLI + GUI).

Based on [ScooterHacking ReFlasher](https://www.scooterhacking.org/forum/viewtopic.php?f=14&t=676) — thanks!

## Requirements

- Python ≥ 3.10
- [OpenOCD](https://openocd.org/) on `PATH` (Linux/macOS). Windows users can use the bundled `oocd/bin/openocd.exe`.
- AT32 ESC support needs a build with AT32 scripts ([openocd-at32](https://github.com/encryptize/openocd-at32); Windows build is bundled).

```bash
git clone https://github.com/scooterteam/scooterflasher.git
cd scooterflasher
pip install -r requirements.txt   # runtime: requests + PySide6
# optional CI/dev freeze: pip install -r requirements-build.txt
```

App firmware for most models is downloaded on first run into `~/.scooterflasher/binaries/firmware/`. Bootloaders (and 4proita STM32F4 images) ship in-repo under `binaries/`.

## GUI

```bash
python -m scooterflasher
# or
python -m scooterflasher --gui
```

## CLI examples

```bash
# Xiaomi Mi3 ESC with GD32 + custom FW
python -m scooterflasher --device mi3 --target ESC --sn 32124/00000000 --fake-chip --km 997 --activate-ecu --cfw your_cfw.bin

# Ninebot Max BLE
python -m scooterflasher --device max --target BLE --sn NBScooter0000

# 4 Pro ITA (STM32F4 ESC) — unlock + POR, then flash
python -m scooterflasher --device 4proita --target ESC --unlock-f4
# power-cycle ESC, then:
python -m scooterflasher --device 4proita --target ESC

# Custom jump-boot + app on 4proita
python -m scooterflasher --device 4proita --target ESC --cbl jump.bin --cfw app.bin

# Attach to an already-running OpenOCD (Tcl port 6666)
python -m scooterflasher --attach --device m365 --target ESC --sn 16133/00000000
```

### 4proita (STM32F4)

`4proita` is the **Xiaomi 4 Pro F4 motor ESC** (`STM32F400CBT6`). It is **not** the same as `4pro` (F1/AT32 userdata layout).

- OpenOCD target: `stm32f4x`
- Default flash: combined jump-boot ‖ app at `0x08000000`
- After `--unlock-f4`, do a **true power cycle** before flashing (NRST is not enough)
- SN/UUID are in I2C EEPROM (not written by this tool)

## Releases

Tag `v*` pushes build GUI binaries via GitHub Actions (Linux / macOS / Windows), same pattern as BWFlasher.

## License

GPL-3.0 (see `LICENSE`).
