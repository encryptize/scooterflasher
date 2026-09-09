#! -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""Dark modern theme for ScooterFlasher GUI."""

# Slate base + teal accent (not purple / cream AI defaults)
DARK_THEME = """
QWidget {
    font-family: "Segoe UI", "Inter", "SF Pro Text", "Ubuntu", sans-serif;
    font-size: 13px;
    color: #e2e8f0;
    background-color: transparent;
}

QMainWindow, QWidget#mainWindow {
    background-color: #0b1220;
}

QLabel#titleLabel {
    font-size: 20px;
    font-weight: 600;
    color: #f8fafc;
    letter-spacing: 0.3px;
    padding: 4px 0 0 0;
}

QLabel#subtitleLabel {
    font-size: 12px;
    color: #64748b;
    padding-bottom: 8px;
}

QLabel#sectionLabel {
    font-size: 11px;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    padding-top: 4px;
}

QGroupBox {
    background-color: #111827;
    border: 1px solid #1e293b;
    border-radius: 10px;
    margin-top: 14px;
    padding: 16px 14px 12px 14px;
    font-weight: 600;
    color: #cbd5e1;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 8px;
    color: #5eead4;
}

QLabel {
    background: transparent;
    color: #cbd5e1;
}

QLineEdit, QComboBox, QSpinBox {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px 10px;
    color: #f1f5f9;
    selection-background-color: #0d9488;
    selection-color: #042f2e;
    min-height: 18px;
}

QLineEdit:focus, QComboBox:focus {
    border: 1px solid #2dd4bf;
}

QLineEdit:disabled, QComboBox:disabled {
    color: #64748b;
    background-color: #0b1220;
}

QComboBox::drop-down {
    border: none;
    width: 28px;
}

QComboBox QAbstractItemView {
    background-color: #0f172a;
    border: 1px solid #334155;
    selection-background-color: #134e4a;
    selection-color: #ccfbf1;
    outline: none;
    padding: 4px;
}

QCheckBox {
    spacing: 8px;
    color: #cbd5e1;
    padding: 3px 0;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid #475569;
    background-color: #0f172a;
}

QCheckBox::indicator:checked {
    background-color: #14b8a6;
    border-color: #2dd4bf;
}

QCheckBox::indicator:disabled {
    background-color: #1e293b;
    border-color: #334155;
}

QPushButton {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 9px 16px;
    color: #e2e8f0;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #334155;
    border-color: #64748b;
}

QPushButton:pressed {
    background-color: #0f172a;
}

QPushButton:disabled {
    color: #64748b;
    background-color: #111827;
    border-color: #1e293b;
}

QPushButton#browseButton {
    min-width: 72px;
    max-width: 88px;
    padding: 8px 10px;
    font-weight: 500;
}

QPushButton#flashButton {
    background-color: #0f766e;
    border: 1px solid #14b8a6;
    color: #ecfeff;
    min-height: 22px;
    font-size: 14px;
}

QPushButton#flashButton:hover {
    background-color: #0d9488;
    border-color: #5eead4;
}

QPushButton#flashButton:pressed {
    background-color: #115e59;
}

QPushButton#unlockButton {
    background-color: #1c1917;
    border: 1px solid #a8a29e;
    color: #fafaf9;
}

QPushButton#unlockButton:hover {
    background-color: #292524;
    border-color: #fbbf24;
    color: #fef3c7;
}

QPushButton#unlockButton:disabled {
    border-color: #292524;
    color: #57534e;
}

QTextEdit {
    background-color: #020617;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 10px;
    color: #94a3b8;
    font-family: "JetBrains Mono", "Fira Code", "Cascadia Code", "Consolas", monospace;
    font-size: 12px;
    selection-background-color: #134e4a;
}

QTextEdit#logView {
    color: #a7f3d0;
}

QTextEdit#helpView {
    color: #94a3b8;
}

QScrollBar:vertical {
    background: #0b1220;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #334155;
    border-radius: 5px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QStatusBar {
    background: #0b1220;
    color: #64748b;
    border-top: 1px solid #1e293b;
}

QMessageBox {
    background-color: #111827;
}

QMessageBox QLabel {
    color: #e2e8f0;
}
"""
