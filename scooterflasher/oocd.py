#! -*- coding: utf-8 -*-
#!/usr/bin/env python3

import shutil
import os
import subprocess

from typing import Tuple
from scooterflasher import utils

class OpenOCD:
    def __init__(self, openocd_path: str) -> None:
        self.bin_path = self.get_bin_path(openocd_path)
        self.base_args = [self.bin_path, "-s", "oocd/scripts/", "-f", "oocd/scripts/interface/stlink.cfg"]

    @staticmethod
    def get_bin_path(openocd_path: str) -> str:
        # Try to use openocd specified in args
        if openocd_path:
            if os.path.isfile(openocd_path):
                return openocd_path
            
        # Check if openocd provided by program is available
        command = "./oocd/bin/openocd.exe"
        if os.path.isfile(command) and os.name == "nt":
            return command
        
        # Search for openocd in path
        command = shutil.which("openocd")
        if command:
            return command
        
        raise RuntimeError("The location of openocd cannot be found. Please specify it in the arguments.")
    
    def run(self, command) -> bool:
        _process = subprocess.Popen(self.base_args+command,
                                    shell=False,
                                    stderr=subprocess.PIPE)
        
        while True:
            output = _process.stderr.readline().strip()
            return_code = _process.poll()
            if return_code is not None:
                break
            if output:
                failed = self.parse_logs(output.decode("utf-8"))

        return not failed

    def parse_logs(self, output: str) -> bool:
        print(output)
        for error in utils.OPENOCD_ERRORS:
            if isinstance(error["error"], list):
                for text in error['error']:
                    error['error'] = text
                    log, failed = self.parse_error(error, output)
            else:
                log, failed = self.parse_error(error, output)

            if log:
                utils.sfprint(log)
            if failed:
                break

        return failed

    @staticmethod
    def parse_error(error: dict, output: str) -> Tuple[str, bool]:
        text = error['error']
        error_type = error['type']
        if error_type == "equals":
            if output == text:
                return error['log'], error['critical']
        elif error_type == "starts":
            if output.startswith(text):
                return error['log'], error['critical']
        elif error_type == "contains":
            if text in output:
                return error['log'], error['critical']
        else:
            raise ValueError(f"Unknown method of error detection: {error_type}.")
            
        return None, False
