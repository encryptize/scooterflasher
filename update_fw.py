#! -*- coding: utf-8 -*-
#!/usr/bin/env python3

from scooterflasher.updater import update_firmwares
from scooterflasher.config import QUESTIONS_TEMPLATE, ask_user

if __name__ == "__main__":
    if ask_user(QUESTIONS_TEMPLATE['ALLOW_UPDATES']):
        update_firmwares()
