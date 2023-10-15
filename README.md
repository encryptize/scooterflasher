
# ScooterFlasher

ScooterFlasher is a simple wrapper for OpenOCD that allows you to easily reflash firmware on your scooter using ST-Link.

# Special thanks
Before you start reading the instructions for using this program, I would like to thank the [ScooterHacking](https://scooterhacking.org/) team incredibly for creating [ReFlasher](https://www.scooterhacking.org/forum/viewtopic.php?f=14&t=676). It's mainly based on it, but ScooterFlasher's goal is cross-platform. At the cost of the lack of a GUI (but maybe one will appear someday).
# How I can use it?
It's easy! All you need is to have Python version 3.11 at least installed on your computer (maybe that works with any older 3.x, not tested) and the [OpenOCD](https://openocd.org/) program, with which it is possible to communicate via ST-Link.

 1. Clone repo
 ```bash
 git clone https://github.com/Encryptize/scooterflasher.git
 cd scooterflasher
 ```
 2. Install requests
 ```bash
 pip install requests
 ```
 3. Download firmware base during first flash, or do it manually with:
  ```bash
 python update_fw.py
 ```
4. Now you are ready to use ScooterFlasher!

# Examples
Flash ESC in Xiaomi Mi3 with GD32 using CFW, activate it and set mileage to 997km:
```bash
python -m scooterflasher --device mi3 --target ESC --sn 32124/00000000 --fake-chip --km 997 --activate-ecu --cfw your_cfw.bin
```
Flash BLE in Ninebot Max:
```bash
python -m scooterflasher --device max --target BLE --sn NBScooter0000
```
Flash BLE in Xiaomi Pro 2 with fast mode:
```bash
python -m scooterflasher --device pro2 --target BLE --sn MiScooter0000 --fast-mode
```
You can find more available options for ScooterFlasher using:
```bash
python -m scooterflasher --help
```

# TODO

 - [ ] AT32 Support for Ninebot's ESC
 - [ ] Fix the update system for ScooterFlasher
 - [ ] GUI Support
