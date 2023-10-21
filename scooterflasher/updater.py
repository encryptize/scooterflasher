#! -*- coding: utf-8 -*-
#!/usr/bin/env python3

import requests
import zipfile
import os
import shutil
import time
import webbrowser

from scooterflasher.utils import XIAOMI_DEV, NINEBOT_DEV, sfprint
from scooterflasher.config import CONFIG_DIRECTORY, check_config, update_config, ask_user
from scooterflasher import version

SCOOTERFLASHER_RELEASES = "https://api.github.com/repos/encryptize/scooterflasher/releases"
FIRMWARE_GIT = "https://api.github.com/repos/scooterhacking/firmware/commits/master"
FIRMWARE_ZIP = "https://github.com/scooterhacking/firmware/archive/refs/heads/master.zip"
FIRMWARE_DIR = os.path.join(CONFIG_DIRECTORY, "binaries", "firmware")
TMP_DIR = os.path.join(CONFIG_DIRECTORY, "tmp", "updates")

def extract_zip(directory, filename) -> None:
    with zipfile.ZipFile(filename, mode='r') as zip_fh:
        zip_fh.extractall(path=directory)

def download_repo() -> str:
    local_filename = os.path.join(TMP_DIR, "master.zip")
    with requests.get(FIRMWARE_ZIP, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            shutil.copyfileobj(r.raw, f)
            
    return local_filename

def update_firmwares() -> None:
    start_time = time.time()
    if os.path.isdir(TMP_DIR):
        shutil.rmtree(TMP_DIR)
    
    os.makedirs(TMP_DIR, exist_ok=True)
    os.makedirs(os.path.join(CONFIG_DIRECTORY, "binaries", "firmware"), exist_ok=True)
    filename = download_repo()
    extract_zip(TMP_DIR, filename)

    for model in NINEBOT_DEV+XIAOMI_DEV:
        model_directory = os.path.join(TMP_DIR, "firmware-master", model)
        for target in ["BLE", "DRV"]:
            work_dir = os.path.join(model_directory, target)
            file = [f for f in os.listdir(work_dir) if f.endswith('.bin')][-1]
            if target == "BLE":
                correct_filename = f"{model}_BLE.bin"
            elif target == "DRV":
                correct_filename = f"{model}_ESC.bin"

            shutil.copy(os.path.join(work_dir, file), os.path.join(FIRMWARE_DIR, correct_filename))

    shutil.rmtree(TMP_DIR)
    end_time = time.time() - start_time
    print(f"Finished in {round(end_time, 2)}s")

def check_update():
    config = check_config()
    if not config['ALLOW_GITHUB_UPDATES']:
        return
    
    if time.time() - config['LAST_CHECK'] < 86400:
        return
    
    last_commits = config['LAST_COMMITS']
    
    # Check updates for ScooterFlasher
    sf_json = requests.get(SCOOTERFLASHER_RELEASES).json()[0]
    if sf_json['tag_name'].strip('v') > version.__version__:
        sfprint(f"An update for ScooterFlasher is available. Look at {sf_json['html_url']}")
        if ask_user("Would you like to open your web browser to check for an update?"):
            webbrowser.open(sf_json['html_url'])

    # Check updates for ScooterHacking Firmware Repository
    fw_json = requests.get(FIRMWARE_GIT).json()
    if last_commits['Firmware'] != fw_json['sha']:
        if ask_user("There is an update available for the firmware database. Do you want to update it now?"):
            update_firmwares()
            config['LAST_COMMITS']['Firmware'] = fw_json['sha']

    config['LAST_CHECK'] = time.time()

    update_config(config)
