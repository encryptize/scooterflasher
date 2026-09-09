#! -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""OpenOCD Tcl RPC client (persistent session on port 6666)."""

from __future__ import annotations

import pathlib
import re
import socket
from typing import Callable

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 6666
FLASH_OPTCR = 0x40023C14

LogFn = Callable[[str], None]


class OpenOcdRpc:
    COMMAND_TOKEN = "\x1a"

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self._host = host
        self._port = port
        self._buffer_size = 4096
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._connected = False

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def connect(self) -> None:
        self._socket.connect((self._host, self._port))
        self._connected = True

    def close(self) -> None:
        if self._connected:
            try:
                self._socket.close()
            except OSError:
                pass
            self._connected = False
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def send(self, cmd: str) -> str:
        data = (cmd + self.COMMAND_TOKEN).encode("utf-8")
        self._socket.sendall(data)
        return self._recv()

    def _recv(self) -> str:
        token = self.COMMAND_TOKEN.encode("utf-8")
        data = bytearray()
        while True:
            tmp = self._socket.recv(self._buffer_size)
            if not tmp:
                break
            data.extend(tmp)
            if token in data:
                break
        if data.endswith(token):
            data = data[: -len(token)]
        return data.decode("utf-8", errors="replace").strip()

    def cmd(self, line: str) -> str:
        return self.send(line)

    def init_halt(self) -> None:
        self.send("init")
        self.send("reset halt")

    def reset_run(self) -> None:
        self.send("reset run")

    def mww(self, address: int, value: int) -> str:
        return self.send(f"mww 0x{address:x} 0x{value:x}")

    def mrw(self, address: int) -> int | None:
        reply = self.send(f"mrw 0x{address:08x}")
        m = re.search(r"(?:0x)?([0-9A-Fa-f]+)", reply)
        if not m:
            return None
        return int(m.group(1), 16)

    def program(self, path: str | pathlib.Path, address: int | None = None, verify: bool = True) -> str:
        p = pathlib.Path(path).resolve()
        if not p.is_file():
            raise FileNotFoundError(p)
        parts = ["program", p.as_posix()]
        if verify:
            parts.append("verify")
        if address is not None:
            parts.append(f"0x{address:x}")
        return self.send(" ".join(parts))

    def dump_image(self, path: str | pathlib.Path, address: int, size: int) -> str:
        p = pathlib.Path(path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        return self.send(f"dump_image {p.as_posix()} 0x{address:x} 0x{size:x}")

    def read_rdp(self) -> tuple[int | None, int | None]:
        optcr = self.mrw(FLASH_OPTCR)
        if optcr is None:
            return None, None
        return optcr, (optcr >> 8) & 0xFF

    def unlock_rdp(self, log: LogFn | None = None) -> bool:
        """STM32F4 RDP clear via stm32f2x unlock 0 (from 4pro-f4-stlink kit)."""
        say = log or (lambda m: None)
        self.init_halt()
        say("--- before unlock ---")
        _, rdp_before = self.read_rdp()
        if rdp_before is not None:
            say(f"RDP: 0x{rdp_before:02X} → {rdp_level(rdp_before)}")
        self.send("stm32f2x options_read 0")

        if rdp_before == 0xCC:
            say("RDP level 2 — irreversible; unlock will not work.")
            return False
        if rdp_before == 0xAA:
            say("OPTCR already shows RDP level 0 (still POR if flash looks protected).")

        say("--- unlock ---")
        reply = self.send("stm32f2x unlock 0")
        if "failed" in reply.lower():
            say(f"Unlock reported failure: {reply or '(see OpenOCD console)'}")
            return False

        say("--- after unlock ---")
        _, rdp_after = self.read_rdp()
        self.send("stm32f2x options_read 0")
        if rdp_after is not None and rdp_after != 0xAA:
            say(f"NOTE: OPTCR.RDP still 0x{rdp_after:02X} — POR required for reload.")
        return True


def rdp_level(rdp: int) -> str:
    if rdp == 0xAA:
        return "0 (no protection)"
    if rdp == 0xCC:
        return "2 (permanent)"
    return "1 (read protection)"


POR_INSTRUCTIONS = """\
POWER CYCLE REQUIRED (RM0401 §3.6.3)
1. Stop OpenOCD if still attached.
2. Cut ESC power / unplug battery (true POR — NRST alone is not enough).
3. Restore power, restart OpenOCD for the F4 target.
4. Flash the image (do not unlock again unless RDP returned).
"""
