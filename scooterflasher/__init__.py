#! -*- coding: utf-8 -*-
#!/usr/bin/env python3

import os

from scooterflasher.config import CONFIG_DIRECTORY

for dir in ["binaries/firmware", "tmp"]:
    os.makedirs(os.path.join(CONFIG_DIRECTORY, dir), exist_ok=True)