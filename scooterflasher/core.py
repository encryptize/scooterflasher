#! -*- coding: utf-8 -*-
#!/usr/bin/env python3
# ScooterFlasher is mostly inspired with ReFlasher created by ScooterHacking.org
# You can read more about their project at https://scooterhack.in/reflasher
# Many thanks to them! Without their project, 
# creating ScooterFlasher would have been a much more difficult task!
# <3 ScooterHacking.org <3

import os

from scooterflasher.utils import sfprint, XIAOMI_DEV, NINEBOT_DEV, V2_BLE_PREFIX
from scooterflasher.oocd import OpenOCD
from scooterflasher.config import CONFIG_DIRECTORY

class Flasher:
    def __init__(self, device: str, sn: str, fake_chip: bool = False, custom_fw: str = None) -> None:
        self.device = device
        self.sn = sn
        self.fake_chip = fake_chip
        self.custom_fw = custom_fw
        self.openocd = OpenOCD()

    def unlock_gd32(self):
        sfprint("Unlocking GD32")
        args = ["-f", "oocd/scripts/target/stm32f1x-nocpuid.cfg", '-c "init"', '-c "reset halt"', '-c "exit"']
        return self.openocd.run(args)
    
    def read_uid_stm32(self):
        sfprint("Reading STM32 UID")
        uid_file = os.path.join(CONFIG_DIRECTORY, "uid.bin")
        if self.fake_chip and self.device in XIAOMI_DEV:
            args = ["-f", "oocd/scripts/target/stm32f1x-nocpuid.cfg", '-c "init"', '-c "reset halt"']
        else:
            args = ["-f", "oocd/scripts/target/stm32f1x.cfg", '-c "init"']

        args += ['-c "flash probe 0"', '-c "stm32f1x unlock 0"', '-c "reset halt"', 
                 '-c "dump_image ' + uid_file + ' 0x1FFFF7E8 12"', '-c "exit"']

        return self.openocd.run(args)

    def flash_stm32(self):
        sfprint("Writing to chip")
        if self.device in XIAOMI_DEV:
            brand = "mi"
        elif self.device in NINEBOT_DEV:
            brand = "nb"
        
        bootloader_file = self.get_bootloader_path("ESC", brand)
        firmware_file = self.get_firmware_path("ESC")
        user_data = self.get_userdata_location()

        if self.fake_chip and self.device in XIAOMI_DEV:
            args = ["-f", "oocd/scripts/target/stm32f1x-nocpuid.cfg", '-c "init"', '-c "reset halt"']
        else:
            args = ["-f", "oocd/scripts/target/stm32f1x.cfg", '-c "init"']

        if not self.fake_chip or self.device not in XIAOMI_DEV:
            args += ['-c "reset halt"']
        
        args += ['-c "flash probe 0"', '-c "stm32f1x unlock 0"', '-c "reset halt"', '-c "stm32f1x mass_erase 0"',
                 '-c "flash write_bank 0 ' + bootloader_file + '"',
                 '-c "flash write_bank 0 ' + firmware_file + ' 0x1000"']
        
        if self.device in NINEBOT_DEV:
            args += ['-c "flash write_bank 0 ' + user_data + ' 0x1C000"']
        elif self.device in XIAOMI_DEV:
            args += ['-c "flash write_bank 0 ' + user_data + ' 0xF800"']

        args += ['-c "reset run"', '-c "exit"']
        return self.openocd.run(args)

    def flash_nrf51(self, fast_mode: bool):
        sfprint("Writing to chip")

        if self.device in XIAOMI_DEV:
            brand = "mi"
        elif self.device in NINEBOT_DEV:
            brand = "nb"
        
        bootloader_file = self.get_bootloader_path("BLE", brand)
        firmware_file = self.get_firmware_path("BLE")
        user_data = self.get_userdata_location()
        uicr_file = self.get_uicr_file()

        args = ['-f', 'oocd/scripts/target/nrf51-fast.cfg' if fast_mode else 'oocd/scripts/target/nrf51.cfg',
                '-c "init"', '-c "reset halt"', '-c "nrf51 mass_erase 0"',
                '-c "program ' + bootloader_file + ' 0x000000 verify"']
        if self.fake_chip or self.device not in V2_BLE_PREFIX:
            args += ['-c "program ' + firmware_file + ' 0x18000 verify"',
                     '-c "program ' + user_data + ' 0x23400 verify"']
        else:
            args += ['-c "program ' + firmware_file + ' 0x1B000 verify"',
                     '-c "program ' + user_data + ' 0x3B800 verify"']
            
        args += ['-c "program ' + uicr_file + ' 0x10001000 verify"', '-c "reset run"', '-c "exit"']
        return self.openocd.run(args)


    def flash_esc(self, extract_uid: bool, activate_ecu: bool, mileage: int = 0):
        if self.fake_chip and self.device in XIAOMI_DEV:
            # if not unlocked, stop
            if not self.unlock_gd32():
                return
        
        if extract_uid:
            # if not extracted, stop
            if not self.read_uid_stm32():
                return
            
        self.generate_userdata_esc(extract_uid, activate_ecu, mileage)
        
        if self.fake_chip and self.device in XIAOMI_DEV:
            # if not unlocked, stop
            if not self.unlock_gd32():
                return
            
        if self.flash_stm32():
            sfprint("All done")

    def flash_ble(self, fast_mode: bool):
        self.generate_userdata_ble()
        if self.flash_nrf51(fast_mode):
            sfprint("All done")
        
    def generate_userdata_esc(self, extract_uid: bool, activate_ecu: bool, mileage: int):
        userdata = bytearray(1023)
        userdata[0:1] = b'\Q'

        userdata[32:32+len(self.sn)] = self.sn.encode(encoding="ascii")
        if extract_uid:
            with open(os.path.join(CONFIG_DIRECTORY, "tmp", "uid.bin"), mode='rb') as uf:
                userdata[436:436+12] = uf.read()
        if activate_ecu:
            userdata[59] = 8
        userdata[82:82+4] = mileage.to_bytes(4, "little")

        tmp_userdata = self.get_userdata_location()
        with open(tmp_userdata, mode='wb') as f_data:
            f_data.write(userdata)

        sfprint("Generated user data page")
        return tmp_userdata
    
    def generate_userdata_ble(self):
        userdata = bytearray(23)
        userdata[0:1] = b'U\xaa'
        userdata[8:8+len(self.sn)] = self.sn.encode(encoding="ascii")

        tmp_userdata = self.get_userdata_location()
        with open(tmp_userdata, mode='wb') as f_data:
            f_data.write(userdata)

        sfprint("Generated user data page")
        return tmp_userdata
    
    def get_bootloader_path(self, target, brand):
        if target == "ESC":
            if self.fake_chip and self.device in XIAOMI_DEV:
                bootloader_file = f"{brand}_DRV_GD32.bin" 
            elif self.fake_chip and self.device in NINEBOT_DEV:
                bootloader_file = f"{brand}_DRV_AT32.bin" 
            else:
                bootloader_file = f"{brand}_DRV.bin"
        elif target == "BLE":
            bootloader_file = f"{brand}_BLE.bin" if self.fake_chip or self.device not in V2_BLE_PREFIX else f"{brand}_BLE_V2.bin"
        if os.path.exists(os.path.join(CONFIG_DIRECTORY, "binaries", "bootloader", bootloader_file)):
            return os.path.join(CONFIG_DIRECTORY, "binaries", "bootloader", bootloader_file)
        else:
            return os.path.join("./binaries/bootloader", bootloader_file)

    def get_firmware_path(self, target):
        firmware_file = self.custom_fw if self.custom_fw else f"{self.device}_{target}.bin"
        return os.path.join(CONFIG_DIRECTORY, "binaries", "firmware", firmware_file)
    
    def get_uicr_file(self):
        uicr_file = "UICR.bin" if self.fake_chip or self.device not in V2_BLE_PREFIX else "UICR_32K.bin"
        if os.path.exists(os.path.join(CONFIG_DIRECTORY, "binaries", uicr_file)):
            return os.path.join(CONFIG_DIRECTORY, "binaries", uicr_file)
        else:
            return os.path.join("./binaries", uicr_file)
    
    @staticmethod
    def get_userdata_location():
        return os.path.join(CONFIG_DIRECTORY, "tmp", "data_tmp.bin")