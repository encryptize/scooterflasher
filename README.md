
# ScooterFlasher

ScooterFlasher is a simple wrapper for OpenOCD that allows you to easily reflash firmware on your scooter using ST-Link.

# Special thanks
Before you start reading the instructions for using this program, I would like to thank the [ScooterHacking](https://scooterhacking.org/) team incredibly for creating [ReFlasher](https://www.scooterhacking.org/forum/viewtopic.php?f=14&t=676). It's mainly based on it, but ScooterFlasher's goal is cross-platform. At the cost of the lack of a GUI (but maybe one will appear someday).
# How I can use it?
It's easy! All you need is to have Python version 3.11 at least installed on your computer (maybe that works with any older 3.x, not tested) and the [OpenOCD](https://openocd.org/) program, with which it is possible to communicate via ST-Link. If you need AT32 (new MCU in Ninebot's ECUs) support, you need a custom build of OpenOCD. For Windows it's in the repository by default, Linux and macOS users need to build it by themselves from the repository [OpenOCD-AT32](https://github.com/encryptize/openocd-at32).

 1. Clone repo
 ```bash
 git clone https://github.com/Encryptize/scooterflasher.git
 cd scooterflasher
 ```
 2. Install requests
 ```bash
 pip install requests
 ```
 3. Download firmware base during first flash.
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
```
python -m scooterflasher -h
usage: __main__.py [-h] --device {max,esx,e,f,t15,g2,4pro,f2,m365,pro,pro2,1s,lite,mi3,4proplus,4promax} --target {BLE,ESC} [--sn SN] [--km KM] [--fake-chip]
                   [--extract-data] [--extract-uid] [--activate-ecu] [--fast-mode] [--openocd OPENOCD] [--custom-fw CUSTOM_FW] [--custom-ram CUSTOM_RAM]

options:
  -h, --help            show this help message and exit
  --device {max,esx,e,f,t15,g2,4pro,f2,m365,pro,pro2,1s,lite,mi3,4proplus,4promax}, -d {max,esx,e,f,t15,g2,4pro,f2,m365,pro,pro2,1s,lite,mi3,4proplus,4promax}
                        Dev name of scooter. List of models could be find here: https://wiki.scooterhacking.org/doku.php?id=zip3#in-use_values
  --target {BLE,ESC}
  --sn SN               Serial number to set when flashing ESC. Displayed name of scooter when flashing BLE.
  --km KM               Mileage to set when flashing ECU.
  --fake-chip           GD32 (or AT32 if it's Ninebot) instead of STM32 chip when flashing ECU. 16k RAM instead of 32k RAM for fake dashboard when flashing BLE.
  --extract-data        Extract all data from ECU during flash. If enabled, there is no need to complete the data for the controller.
  --extract-uid         Extract chip UID during flashing
  --activate-ecu        Activate ECU during flashing
  --fast-mode, -fm      Use 1000kHz instead of 450kHz (Applies to BLE only)
  --openocd OPENOCD     Location of openocd binary.
  --custom-fw CUSTOM_FW, --cfw CUSTOM_FW
                        Custom firmware to flash instead of an official
  --custom-ram CUSTOM_RAM, --cram CUSTOM_RAM
                        Flash custom RAM dump instead of generated or extracted by program
```

# TODO

 - [x] AT32 Support for Ninebot's ESC
 - [x] Fix the update system for ScooterFlasher
 - [ ] GUI Support
