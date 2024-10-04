import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QComboBox, QRadioButton, QCheckBox, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox
from scooterflasher.core import Flasher
from scooterflasher.utils import parse_args, sfprint
from scooterflasher.config import CONFIG_DIRECTORY
from scooterflasher.updater import check_update

class ScooterFlasherApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('ScooterFlasher')

        # Device
        device_label = QLabel('Device:')
        self.device_combo = QComboBox()
        devices = ["max", "esx", "e", "f", "t15", "g2", "4pro", "f2", "m365", "pro", "pro2", "1s", "lite", "mi3", "4proplus", "4promax"]
        self.device_combo.addItems(devices)

        # Serial Number
        sn_label = QLabel('Serial Number:')
        self.sn_edit = QLineEdit()

        # Target
        target_label = QLabel('Target:')
        self.esc_radio = QRadioButton('ESC')
        self.esc_radio.setChecked(True)
        self.ble_radio = QRadioButton('BLE')

        # Fast Mode
        self.fast_mode_check = QCheckBox('Fast Mode')

        # Flash Button
        flash_button = QPushButton('Flash')
        flash_button.clicked.connect(self.flash)

        # Layouts
        layout = QVBoxLayout()
        layout.addWidget(device_label)
        layout.addWidget(self.device_combo)
        layout.addWidget(sn_label)
        layout.addWidget(self.sn_edit)
        layout.addWidget(target_label)
        layout.addWidget(self.esc_radio)
        layout.addWidget(self.ble_radio)
        layout.addWidget(self.fast_mode_check)
        layout.addWidget(flash_button)

        self.setLayout(layout)

    def flash(self):
        device = self.device_combo.currentText()
        sn = self.sn_edit.text()
        target = 'ESC' if self.esc_radio.isChecked() else 'BLE'
        fast_mode = self.fast_mode_check.isChecked()

        if not sn:
            QMessageBox.critical(self, 'Error', 'Serial Number is required!')
            return

        args = parse_args()
        flash = Flasher(device, sn, args.fake_chip, args.extract_data, args.custom_fw, args.custom_ram, args.openocd)
        check_update()

        if target == 'ESC':
            flash.flash_esc(args.extract_uid, args.activate_ecu, args.km)
        elif target == 'BLE':
            if fast_mode:
                sfprint("Warning! Fast mode requires to remove C16 resistor on dashboard. If flashing doesn't work, try without fast mode enabled.")
            flash.flash_ble(fast_mode)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ScooterFlasherApp()
    ex.show()
    sys.exit(app.exec_())