#! -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""ScooterFlasher GUI (PySide6)."""

from __future__ import annotations

import os
import sys
import traceback

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QIcon, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from scooterflasher.config import CONFIG_DIRECTORY
from scooterflasher.core import Flasher
from scooterflasher.instructions import instructions_for
from scooterflasher.paths import TOOL_ROOT
from scooterflasher.styles import DARK_THEME
from scooterflasher.utils import (
    ALL_DEVICES,
    DEFAULT_ESC_SN,
    F4_DEV,
)
from scooterflasher.version import __version__


def resource_path(*parts: str) -> str:
    base = getattr(sys, "_MEIPASS", str(TOOL_ROOT))
    return os.path.join(base, "resources", *parts)


class FlashWorker(QThread):
    log = Signal(str)
    done = Signal(bool, str)

    def __init__(self, opts: dict):
        super().__init__()
        self.opts = opts

    def run(self):
        try:
            flasher = Flasher(
                device=self.opts["device"],
                sn=self.opts.get("sn") or "",
                fake_chip=self.opts.get("fake_chip", False),
                extract_data=self.opts.get("extract_data", False),
                custom_fw=self.opts.get("custom_fw") or None,
                custom_ram=self.opts.get("custom_ram") or None,
                custom_bootloader=self.opts.get("custom_bootloader") or None,
                openocd_path=self.opts.get("openocd") or None,
                attach=self.opts.get("attach", False),
                log=lambda m: self.log.emit(str(m)),
            )
            if self.opts.get("unlock_f4"):
                flasher.unlock_f4()
            elif self.opts["target"] == "ESC":
                flasher.flash_esc(
                    extract_uid=self.opts.get("extract_uid", False),
                    activate_ecu=self.opts.get("activate_ecu", False),
                    mileage=float(self.opts.get("km") or 0),
                    unlock_f4=False,
                )
            else:
                flasher.flash_ble(self.opts.get("fast_mode", False))
            try:
                if not self.opts.get("attach"):
                    flasher.openocd.stop()
            except Exception:
                pass
            self.done.emit(True, "Done")
        except Exception as e:
            self.log.emit(traceback.format_exc())
            self.done.emit(False, str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"ScooterFlasher {__version__}")
        self.setObjectName("mainWindow")
        self.setMinimumSize(760, 700)
        icon = resource_path("app.ico")
        if os.path.isfile(icon):
            self.setWindowIcon(QIcon(icon))

        root = QWidget()
        root.setObjectName("mainWindow")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(20, 18, 20, 14)
        layout.setSpacing(12)

        title = QLabel("ScooterFlasher")
        title.setObjectName("titleLabel")
        subtitle = QLabel(f"SWD · OpenOCD · v{__version__}")
        subtitle.setObjectName("subtitleLabel")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        form_box = QGroupBox("Target")
        form = QFormLayout(form_box)
        form.setSpacing(10)
        form.setContentsMargins(8, 12, 8, 8)

        self.device = QComboBox()
        self.device.addItems(ALL_DEVICES)
        self.target = QComboBox()
        self.target.addItems(["ESC", "BLE"])
        self.sn = QLineEdit()
        self.km = QLineEdit("0")
        self.fake_chip = QCheckBox("Fake chip (GD32 / AT32 / 16k BLE)")
        self.extract_uid = QCheckBox("Extract UID")
        self.activate_ecu = QCheckBox("Activate ECU")
        self.extract_data = QCheckBox("Extract ESC data from RAM")
        self.fast_mode = QCheckBox("BLE fast mode")
        self.attach = QCheckBox("Attach to running OpenOCD (:6666)")
        self.custom_fw = QLineEdit()
        self.custom_fw.setPlaceholderText("optional .bin")
        self.custom_bl = QLineEdit()
        self.custom_bl.setPlaceholderText("optional bootloader .bin")
        self.openocd_path = QLineEdit()
        self.openocd_path.setPlaceholderText("auto-detect if empty")

        def browse_btn(slot):
            b = QPushButton("Browse")
            b.setObjectName("browseButton")
            b.clicked.connect(slot)
            return b

        fw_row = QHBoxLayout()
        fw_row.setSpacing(8)
        fw_row.addWidget(self.custom_fw)
        fw_row.addWidget(browse_btn(lambda: self._browse(self.custom_fw)))

        bl_row = QHBoxLayout()
        bl_row.setSpacing(8)
        bl_row.addWidget(self.custom_bl)
        bl_row.addWidget(browse_btn(lambda: self._browse(self.custom_bl)))

        ocd_row = QHBoxLayout()
        ocd_row.setSpacing(8)
        ocd_row.addWidget(self.openocd_path)
        ocd_row.addWidget(browse_btn(lambda: self._browse(self.openocd_path, binary=True)))

        form.addRow("Device", self.device)
        form.addRow("Target", self.target)
        form.addRow("SN / BLE name", self.sn)
        form.addRow("Mileage (km)", self.km)
        form.addRow(self.fake_chip)
        form.addRow(self.extract_uid)
        form.addRow(self.activate_ecu)
        form.addRow(self.extract_data)
        form.addRow(self.fast_mode)
        form.addRow(self.attach)
        form.addRow("Custom firmware", fw_row)
        form.addRow("Custom bootloader", bl_row)
        form.addRow("OpenOCD binary", ocd_row)
        layout.addWidget(form_box)

        btns = QHBoxLayout()
        btns.setSpacing(10)
        self.btn_flash = QPushButton("Flash")
        self.btn_flash.setObjectName("flashButton")
        self.btn_unlock = QPushButton("Unlock F4")
        self.btn_unlock.setObjectName("unlockButton")
        self.btn_flash.clicked.connect(self.on_flash)
        self.btn_unlock.clicked.connect(self.on_unlock_f4)
        btns.addWidget(self.btn_flash, 2)
        btns.addWidget(self.btn_unlock, 1)
        layout.addLayout(btns)

        help_label = QLabel("Instructions")
        help_label.setObjectName("sectionLabel")
        layout.addWidget(help_label)
        self.help = QTextEdit()
        self.help.setObjectName("helpView")
        self.help.setReadOnly(True)
        self.help.setMaximumHeight(150)
        layout.addWidget(self.help)

        log_label = QLabel("Log")
        log_label.setObjectName("sectionLabel")
        layout.addWidget(log_label)
        self.log = QTextEdit()
        self.log.setObjectName("logView")
        self.log.setReadOnly(True)
        layout.addWidget(self.log, 1)

        status = QStatusBar()
        self.setStatusBar(status)
        status.showMessage("Ready · ST-Link SWD")

        self.device.currentTextChanged.connect(self._refresh_help)
        self.target.currentTextChanged.connect(self._refresh_help)
        self.fake_chip.toggled.connect(self._refresh_help)
        self.device.currentTextChanged.connect(self._on_device)
        self._on_device(self.device.currentText())
        self._refresh_help()
        self._worker: FlashWorker | None = None

        os.makedirs(os.path.join(CONFIG_DIRECTORY, "binaries", "firmware"), exist_ok=True)
        os.makedirs(os.path.join(CONFIG_DIRECTORY, "tmp"), exist_ok=True)

    def _browse(self, line: QLineEdit, binary: bool = False):
        if binary:
            path, _ = QFileDialog.getOpenFileName(self, "OpenOCD", "", "All (*)")
        else:
            path, _ = QFileDialog.getOpenFileName(self, "Binary", "", "BIN (*.bin);;All (*)")
        if path:
            line.setText(path)

    def _on_device(self, device: str):
        is_f4 = device in F4_DEV
        self.btn_unlock.setEnabled(is_f4)
        self.fake_chip.setEnabled(not is_f4)
        if is_f4:
            self.fake_chip.setChecked(False)
            self.target.setCurrentText("ESC")
            self.sn.setPlaceholderText("not used (EEPROM)")
            self.sn.setText("")
            self.statusBar().showMessage("4proita · STM32F4 · unlock → POR → flash")
        else:
            self.sn.setPlaceholderText("")
            if not self.sn.text():
                self.sn.setText(DEFAULT_ESC_SN.get(device, ""))
            self.statusBar().showMessage("Ready · ST-Link SWD")

    def _refresh_help(self):
        self.help.setPlainText(
            instructions_for(
                self.device.currentText(),
                self.target.currentText(),
                self.fake_chip.isChecked(),
            )
        )

    def _append(self, msg: str):
        self.log.moveCursor(QTextCursor.End)
        self.log.insertPlainText(msg + "\n")
        self.log.moveCursor(QTextCursor.End)

    def _opts(self, unlock_f4: bool = False) -> dict:
        return {
            "device": self.device.currentText(),
            "target": self.target.currentText(),
            "sn": self.sn.text().strip(),
            "km": self.km.text().strip() or "0",
            "fake_chip": self.fake_chip.isChecked(),
            "extract_uid": self.extract_uid.isChecked(),
            "activate_ecu": self.activate_ecu.isChecked(),
            "extract_data": self.extract_data.isChecked(),
            "fast_mode": self.fast_mode.isChecked(),
            "attach": self.attach.isChecked(),
            "custom_fw": self.custom_fw.text().strip(),
            "custom_bootloader": self.custom_bl.text().strip(),
            "openocd": self.openocd_path.text().strip(),
            "unlock_f4": unlock_f4,
        }

    def _start(self, opts: dict):
        if self._worker and self._worker.isRunning():
            QMessageBox.warning(self, "Busy", "A flash job is already running.")
            return
        device = opts["device"]
        if device in F4_DEV and opts["target"] != "ESC":
            QMessageBox.critical(self, "Error", "4proita is STM32F4 ESC only.")
            return
        self.btn_flash.setEnabled(False)
        self.btn_unlock.setEnabled(False)
        self.statusBar().showMessage("Flashing…")
        self._append("--- start ---")
        self._worker = FlashWorker(opts)
        self._worker.log.connect(self._append)
        self._worker.done.connect(self._finished)
        self._worker.start()

    def on_flash(self):
        self._start(self._opts(unlock_f4=False))

    def on_unlock_f4(self):
        if self.device.currentText() not in F4_DEV:
            QMessageBox.information(self, "F4", "Select device 4proita (STM32F4).")
            return
        self._start(self._opts(unlock_f4=True))

    def _finished(self, ok: bool, msg: str):
        self.btn_flash.setEnabled(True)
        self.btn_unlock.setEnabled(self.device.currentText() in F4_DEV)
        self._append(("OK: " if ok else "FAIL: ") + msg)
        self.statusBar().showMessage("Done" if ok else "Failed")
        if ok:
            QMessageBox.information(self, "ScooterFlasher", msg)
        else:
            QMessageBox.critical(self, "ScooterFlasher", msg)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_THEME)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
