#! -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""Persistent OpenOCD process manager + Tcl RPC session."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import threading
import time
from typing import Callable

from scooterflasher.paths import OOCD_SCRIPTS, TOOL_ROOT, posix
from scooterflasher.rpc import DEFAULT_HOST, DEFAULT_PORT, OpenOcdRpc
from scooterflasher.utils import OPENOCD_ERRORS, sfprint

LogFn = Callable[[str], None]


TARGET_CFGS = {
    "stm32f1x": "target/stm32f1x.cfg",
    "stm32f1x-nocpuid": "target/stm32f1x-nocpuid.cfg",
    "at32": "target/at32.cfg",
    "stm32f4x": "target/stm32f4x.cfg",
    "nrf51": "target/nrf51.cfg",
    "nrf51-fast": "target/nrf51-fast.cfg",
}

# F4 kit uses SRST; many F1/nRF boards do not wire it — leave target default.
SRST_TARGETS = {"stm32f4x"}


class OpenOCD:
    """Starts or attaches to OpenOCD and talks over Tcl RPC (port 6666)."""

    def __init__(
        self,
        openocd_path: str | None = None,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        log: LogFn | None = None,
    ) -> None:
        self.bin_path = self.get_bin_path(openocd_path)
        self.host = host
        self.port = port
        self.log = log or sfprint
        self._proc: subprocess.Popen | None = None
        self._target_key: str | None = None
        self._rpc: OpenOcdRpc | None = None
        self._reader: threading.Thread | None = None
        self._critical = False
        self._owned = False

    @staticmethod
    def get_bin_path(openocd_path: str | None) -> str:
        if openocd_path and os.path.isfile(openocd_path):
            return openocd_path

        bundled = TOOL_ROOT / "oocd" / "bin" / "openocd.exe"
        if bundled.is_file() and os.name == "nt":
            return str(bundled)

        command = shutil.which("openocd")
        if command:
            return command

        raise RuntimeError(
            "OpenOCD binary not found. Install openocd or pass --openocd PATH."
        )

    @property
    def running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    @property
    def port_open(self) -> bool:
        try:
            with socket.create_connection((self.host, self.port), timeout=0.2):
                return True
        except OSError:
            return False

    def attach(self) -> None:
        """Use an already-running OpenOCD Tcl RPC server (no spawn)."""
        if not self.port_open:
            raise RuntimeError(
                f"No OpenOCD on {self.host}:{self.port}. "
                "Start it first or call start(target)."
            )
        self._owned = False
        self._target_key = self._target_key or "attached"
        self._reconnect_rpc()
        self.log(f"Attached to OpenOCD at {self.host}:{self.port}")

    def start(self, target_key: str, interface: str = "stlink") -> None:
        if target_key not in TARGET_CFGS:
            raise ValueError(f"Unknown target {target_key!r}")

        if self.running and self._target_key == target_key and self._rpc:
            return

        # Reuse external server if port already up and we are not switching targets
        if not self.running and self.port_open and self._target_key in (None, target_key, "attached"):
            self._target_key = target_key
            self._owned = False
            self._reconnect_rpc()
            self.log(f"Using existing OpenOCD ({target_key}) on {self.host}:{self.port}")
            return

        self.stop()
        self._critical = False

        scripts = posix(OOCD_SCRIPTS)
        args = [
            self.bin_path,
            "-s",
            scripts,
            "-f",
            f"interface/{interface}.cfg",
            "-c",
            "transport select hla_swd",
            "-f",
            TARGET_CFGS[target_key],
        ]
        if target_key in SRST_TARGETS:
            args += ["-c", "reset_config srst_only srst_nogate"]
        args += [
            "-c",
            "gdb_port disabled",
            "-c",
            f"tcl_port {self.port}",
            "-c",
            "telnet_port 4444",
        ]

        self.log(f"Starting OpenOCD ({target_key})…")
        self._proc = subprocess.Popen(
            args,
            cwd=str(TOOL_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self._owned = True
        self._target_key = target_key
        self._reader = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader.start()
        self._wait_for_port(timeout=12.0)
        self._reconnect_rpc()
        if self._critical:
            raise RuntimeError("OpenOCD reported a critical error during start")
        self.log(f"OpenOCD ready on {self.host}:{self.port}")

    def stop(self) -> None:
        if self._rpc is not None:
            try:
                self._rpc.close()
            except OSError:
                pass
            self._rpc = None

        if self._owned and self._proc is not None:
            if self._proc.poll() is None:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
                    self._proc.wait(timeout=3)
            self._proc = None
        elif self._proc is not None and self._proc.poll() is not None:
            self._proc = None

        self._owned = False
        self._target_key = None

    def reconnect(self) -> None:
        """Re-open RPC after OpenOCD was restarted (e.g. F4 POR)."""
        self._wait_for_port(timeout=12.0)
        self._reconnect_rpc()

    def rpc(self) -> OpenOcdRpc:
        if self._rpc is None:
            self._reconnect_rpc()
        assert self._rpc is not None
        return self._rpc

    def _reconnect_rpc(self) -> None:
        if self._rpc is not None:
            try:
                self._rpc.close()
            except OSError:
                pass
        client = OpenOcdRpc(self.host, self.port)
        client.connect()
        self._rpc = client

    def _read_stdout(self) -> None:
        assert self._proc is not None and self._proc.stdout is not None
        for line in self._proc.stdout:
            text = line.rstrip()
            if not text:
                continue
            print(text)
            log, failed = self._match_error(text)
            if log:
                self.log(log)
            if failed:
                self._critical = True

    def _match_error(self, output: str) -> tuple[str | None, bool]:
        for error in OPENOCD_ERRORS:
            patterns = error["error"] if isinstance(error["error"], list) else [error["error"]]
            for text in patterns:
                hit = False
                if error["type"] == "equals" and output == text:
                    hit = True
                elif error["type"] == "starts" and output.startswith(text):
                    hit = True
                elif error["type"] == "contains" and text in output:
                    hit = True
                if hit:
                    return error["log"], bool(error["critical"])
        return None, False

    def _wait_for_port(self, timeout: float) -> None:
        deadline = time.time() + timeout
        last_err: Exception | None = None
        while time.time() < deadline:
            if self._owned and self._proc is not None and self._proc.poll() is not None:
                raise RuntimeError(
                    f"OpenOCD exited early (code {self._proc.returncode})."
                )
            try:
                with socket.create_connection((self.host, self.port), timeout=0.3):
                    return
            except OSError as e:
                last_err = e
                time.sleep(0.2)
        raise RuntimeError(f"OpenOCD Tcl port {self.port} not ready: {last_err}")
