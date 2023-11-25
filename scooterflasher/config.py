#! -*- coding: utf-8 -*-
#!/usr/bin/env python3

import os
import json

CONFIG_DIRECTORY = os.path.join(os.path.expanduser("~"), ".scooterflasher")
CONFIG_LOCATION = os.path.join(CONFIG_DIRECTORY, "config.json")
CONFIG_TEMPLATE = {
    "ALLOW_UPDATES": False,
    "SF_LAST_CHECK": 0,
    "FW_LAST_CHECK": 0
}
QUESTIONS_TEMPLATE = {
    "ALLOW_UPDATES": "This program offers the ability to inform you of updates to the program and the database of files used to flash the scooters. For this purpose, it connects to the servers of GitHub.com, scooterflasher.encryptize.ovh and ScooterHacking.org. Do you agree to automatically check for the availability of updates each time you run the program, at most once a day?"
}

def ask_user(question: str) -> bool:
    choice = input(f"{question} (y/N): ")
    return choice.lower() in ("y", "yes")

def update_config(data: dict) -> None:
    json.dump(data, open(CONFIG_LOCATION, 'w', encoding='utf-8'))

def check_config() -> dict:
    if not os.path.isdir(CONFIG_DIRECTORY):
        os.mkdir(CONFIG_DIRECTORY)
    if os.path.isfile(CONFIG_LOCATION):
        config_file = json.load(open(CONFIG_LOCATION, 'r', encoding='utf-8'))
    else:
         config_file = {}

    need_to_update = False

    for k in CONFIG_TEMPLATE.keys():
        if k not in config_file and k in QUESTIONS_TEMPLATE:
            need_to_update = True
            config_file[k] = ask_user(QUESTIONS_TEMPLATE[k])
        elif k not in config_file and k not in QUESTIONS_TEMPLATE:
            config_file[k] = CONFIG_TEMPLATE[k]

    if need_to_update:
        update_config(config_file)

    return config_file
