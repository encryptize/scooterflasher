#! -*- coding: utf-8 -*-
#!/usr/bin/env python3

import requests
import os
import shutil
import time
import webbrowser

from datetime import datetime
from platform import python_version

from scooterflasher.utils import sfprint
from scooterflasher.config import CONFIG_DIRECTORY, check_config, update_config, ask_user
from scooterflasher import __version__

SCOOTERFLASHER_RELEASES = "https://api.github.com/repos/encryptize/scooterflasher/releases"
FIRMWARE_API = "https://scooterflasher.encryptize.ovh/api/v1/firmwares/"
FIRMWARE_DIR = os.path.join(CONFIG_DIRECTORY, "binaries", "firmware")
REQUESTS_HEADERS = {
    'User-Agent': f'scooterflasher/{__version__} Python/{python_version()} python-requests/{requests.__version__}', 
    'Accept-Encoding': 'gzip, deflate, br', 
    'Accept': '*/*', 
    'Connection': 'keep-alive'
}

def download_firmware(filename: str, url: str) -> str:
    with requests.get(url, stream=True, headers=REQUESTS_HEADERS) as r:
        r.raise_for_status()
        with open(filename, 'wb') as f:
            shutil.copyfileobj(r.raw, f)
            
    return filename

def update_firmwares(data: dict) -> None:
    start_time = time.time()
    for firmware in data['data']:
        fw_model = firmware['model']
        fw_target = firmware['target']
        filename = os.path.join(FIRMWARE_DIR, f"{fw_model}_{fw_target}.bin")
        download_firmware(filename, firmware['url'])
    end_time = time.time() - start_time
    print(f"Finished in {round(end_time, 2)}s")

def check_update():
    config = check_config()
    if not config['ALLOW_UPDATES']:
        return
    
    # Check updates for ScooterFlasher
    if time.time() - config['SF_LAST_CHECK'] > 86400:
        sf_req = requests.get(SCOOTERFLASHER_RELEASES, headers=REQUESTS_HEADERS)
        sf_req.raise_for_status()
        sf_json = sf_req.json()[0]
        if sf_json['tag_name'].strip('v') > __version__:
            sfprint(f"An update for ScooterFlasher is available. Look at {sf_json['html_url']}")
            if ask_user("Would you like to open your web browser to check for an update?"):
                webbrowser.open(sf_json['html_url'])

        config['SF_LAST_CHECK'] = time.time()

    # Check updates for ScooterHacking Firmware Repository
    if time.time() - config['FW_LAST_CHECK'] > 86400:
        fw_req = requests.get(FIRMWARE_API, headers=REQUESTS_HEADERS, params={
            "last_update": datetime.fromtimestamp(config['FW_LAST_CHECK'])
        })
        fw_req.raise_for_status()
        fw_json = fw_req.json()
        if len(fw_json['data']) > 0:
            if ask_user("There is an update available for the firmware database. Do you want to update it now?"):
                update_firmwares(fw_json)
                config['FW_LAST_CHECK'] = datetime.fromisoformat(fw_json['last_update']).timestamp()

    update_config(config)
