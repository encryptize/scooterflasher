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
    NINEBOT_DEV,
    XIAOMI_DEV,
    XIAOMI_V2_DEV,
    supports_ble,
    supports_fake_chip,
    supports_unlock,
)
from scooterflasher.version import __version__


def resource_path(*parts: str) -> str:
    base = getattr(sys, "_MEIPASS", str(TOOL_ROOT))
    return os.path.join(base, "resources", *parts)


# UI label → internal target
TARGET_DRV = "DRV"
TARGET_BLE = "BLE"


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
            if self.opts.get("unlock_only"):
                flasher.unlock()
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
        self.form = QFormLayout(form_box)
        self.form.setSpacing(10)
        self.form.setContentsMargins(8, 12, 8, 8)

        self.device = QComboBox()
        self.device.addItems(ALL_DEVICES)
        self.target = QComboBox()

        self.sn = QLineEdit()
        self.km = QLineEdit("0")
        self.fake_chip = QCheckBox("Fake chip (GD32 Xiaomi / AT32 Ninebot · 16k BLE)")
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

        self.fw_row = QWidget()
        fw_l = QHBoxLayout(self.fw_row)
        fw_l.setContentsMargins(0, 0, 0, 0)
        fw_l.setSpacing(8)
        fw_l.addWidget(self.custom_fw)
        fw_l.addWidget(browse_btn(lambda: self._browse(self.custom_fw)))

        self.bl_row = QWidget()
        bl_l = QHBoxLayout(self.bl_row)
        bl_l.setContentsMargins(0, 0, 0, 0)
        bl_l.setSpacing(8)
        bl_l.addWidget(self.custom_bl)
        bl_l.addWidget(browse_btn(lambda: self._browse(self.custom_bl)))

        self.ocd_row = QWidget()
        ocd_l = QHBoxLayout(self.ocd_row)
        ocd_l.setContentsMargins(0, 0, 0, 0)
        ocd_l.setSpacing(8)
        ocd_l.addWidget(self.openocd_path)
        ocd_l.addWidget(browse_btn(lambda: self._browse(self.openocd_path, binary=True)))

        self.form.addRow("Device", self.device)
        self.form.addRow("Flash", self.target)
        self.form.addRow("SN / BLE name", self.sn)
        self.form.addRow("Mileage (km)", self.km)
        self.form.addRow(self.fake_chip)
        self.form.addRow(self.extract_uid)
        self.form.addRow(self.activate_ecu)
        self.form.addRow(self.extract_data)
        self.form.addRow(self.fast_mode)
        self.form.addRow(self.attach)
        self.form.addRow("Custom firmware", self.fw_row)
        self.form.addRow("Custom bootloader", self.bl_row)
        self.form.addRow("OpenOCD binary", self.ocd_row)
        layout.addWidget(form_box)

        btns = QHBoxLayout()
        btns.setSpacing(10)
        self.btn_flash = QPushButton("Flash")
        self.btn_flash.setObjectName("flashButton")
        self.btn_unlock = QPushButton("Unlock")
        self.btn_unlock.setObjectName("unlockButton")
        self.btn_flash.clicked.connect(self.on_flash)
        self.btn_unlock.clicked.connect(self.on_unlock)
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

        self.device.currentTextChanged.connect(self._sync_ui)
        self.target.currentTextChanged.connect(self._sync_ui)
        self.fake_chip.toggled.connect(self._sync_ui)
        self._sync_ui()
        self._worker: FlashWorker | None = None

        os.makedirs(os.path.join(CONFIG_DIRECTORY, "binaries", "firmware"), exist_ok=True)
        os.makedirs(os.path.join(CONFIG_DIRECTORY, "tmp"), exist_ok=True)

    def _set_row_visible(self, field, visible: bool):
        field.setVisible(visible)
        label = self.form.labelForField(field)
        if label is not None:
            label.setVisible(visible)

    def _internal_target(self) -> str:
        """Map UI Flash selection to ESC/BLE."""
        return "BLE" if self.target.currentText() == TARGET_BLE else "ESC"

    def _rebuild_targets(self, device: str):
        current = self.target.currentText()
        self.target.blockSignals(True)
        self.target.clear()
        self.target.addItem(TARGET_DRV)
        if supports_ble(device):
            self.target.addItem(TARGET_BLE)
        # restore if still valid
        idx = self.target.findText(current)
        self.target.setCurrentIndex(idx if idx >= 0 else 0)
        self.target.blockSignals(False)

    def _sync_ui(self, *_args):
        device = self.device.currentText()
        self._rebuild_targets(device)
        target = self._internal_target()
        is_f4 = device in F4_DEV
        is_drv = target == "ESC"
        is_ble = target == "BLE"

        # SN: DRV (non-F4) or BLE name
        show_sn = (is_drv and not is_f4) or is_ble
        self._set_row_visible(self.sn, show_sn)
        if is_ble:
            self.form.labelForField(self.sn).setText("BLE name")
            self.sn.setPlaceholderText("display name")
        elif is_drv and not is_f4:
            self.form.labelForField(self.sn).setText("Serial number")
            self.sn.setPlaceholderText("")
            if not self.sn.text():
                self.sn.setText(DEFAULT_ESC_SN.get(device, ""))
        if is_f4:
            self.sn.clear()

        self._set_row_visible(self.km, is_drv and not is_f4)
        show_fake = supports_fake_chip(device, target)
        self._set_row_visible(self.fake_chip, show_fake)
        if not show_fake:
            self.fake_chip.setChecked(False)
        elif is_f4:
            self.fake_chip.setChecked(False)

        self._set_row_visible(self.extract_uid, is_drv and not is_f4)
        self._set_row_visible(self.activate_ecu, is_drv and not is_f4)
        self._set_row_visible(self.extract_data, is_drv and not is_f4)
        self._set_row_visible(self.fast_mode, is_ble)

        # Custom BL useful for DRV (incl. F4); BLE bootloaders rarely overridden but allow
        self._set_row_visible(self.bl_row, True)
        self._set_row_visible(self.fw_row, True)
        self._set_row_visible(self.ocd_row, True)
        self._set_row_visible(self.attach, True)

        show_unlock = supports_unlock(device, target)
        self.btn_unlock.setVisible(show_unlock)
        self.btn_unlock.setEnabled(show_unlock)
        if is_f4:
            self.btn_unlock.setToolTip("STM32F4 RDP clear — then power-cycle before Flash")
            self.statusBar().showMessage("4proita · STM32F4 · Unlock → POR → Flash")
        elif is_drv and self.fake_chip.isChecked() and supports_fake_chip(device, "ESC"):
            if device in XIAOMI_DEV:
                self.btn_unlock.setToolTip("GD32 option-byte unlock")
                self.statusBar().showMessage("Ready · GD32 unlock")
            elif device in NINEBOT_DEV + XIAOMI_V2_DEV:
                self.btn_unlock.setToolTip("AT32: no separate unlock — use Flash")
                self.statusBar().showMessage("Ready · AT32 (unlock via Flash)")
            else:
                self.btn_unlock.setToolTip("Unlock chip protection")
                self.statusBar().showMessage("Ready · ST-Link SWD")
        elif is_drv:
            self.btn_unlock.setToolTip("STM32 RDP unlock (stm32f1x)")
            self.statusBar().showMessage("Ready · ST-Link SWD")
        else:
            self.statusBar().showMessage("Ready · BLE / nRF51")

        self._refresh_help()

    def _browse(self, line: QLineEdit, binary: bool = False):
        if binary:
            path, _ = QFileDialog.getOpenFileName(self, "OpenOCD", "", "All (*)")
        else:
            path, _ = QFileDialog.getOpenFileName(self, "Binary", "", "BIN (*.bin);;All (*)")
        if path:
            line.setText(path)

    def _refresh_help(self):
        self.help.setPlainText(
            instructions_for(
                self.device.currentText(),
                self._internal_target(),
                self.fake_chip.isChecked(),
            )
        )

    def _append(self, msg: str):
        self.log.moveCursor(QTextCursor.End)
        self.log.insertPlainText(msg + "\n")
        self.log.moveCursor(QTextCursor.End)

    def _opts(self, unlock_only: bool = False) -> dict:
        return {
            "device": self.device.currentText(),
            "target": self._internal_target(),
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
            "unlock_only": unlock_only,
        }

    def _start(self, opts: dict):
        if self._worker and self._worker.isRunning():
            QMessageBox.warning(self, "Busy", "A flash job is already running.")
            return
        device = opts["device"]
        if device in F4_DEV and opts["target"] != "ESC":
            QMessageBox.critical(self, "Error", "4proita is STM32F4 DRV only.")
            return
        self.btn_flash.setEnabled(False)
        self.btn_unlock.setEnabled(False)
        self.statusBar().showMessage("Working…")
        self._append("--- start ---")
        self._worker = FlashWorker(opts)
        self._worker.log.connect(self._append)
        self._worker.done.connect(self._finished)
        self._worker.start()

    def on_flash(self):
        self._start(self._opts(unlock_only=False))

    def on_unlock(self):
        if self._internal_target() != "ESC":
            QMessageBox.information(self, "Unlock", "Unlock applies to DRV only.")
            return
        self._start(self._opts(unlock_only=True))

    def _finished(self, ok: bool, msg: str):
        self.btn_flash.setEnabled(True)
        self.btn_unlock.setEnabled(supports_unlock(self.device.currentText(), self._internal_target()))
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
