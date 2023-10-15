#! -*- coding: utf-8 -*-
#!/usr/bin/env python3

from scooterflasher.updater import update_firmwares
from scooterflasher.config import ask_user

if __name__ == "__main__":
    if ask_user("This program, in order to update the firmware database, connects to the servers of the GitHub.com service. Do you agree to this?"):
        update_firmwares()
