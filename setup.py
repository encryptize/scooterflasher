import pathlib
from setuptools import setup

HERE = pathlib.Path(__file__).parent
README = (HERE / "README.md").read_text(encoding="utf-8")
ABOUT = {}
with open(HERE / "scooterflasher" / "version.py", encoding="utf-8") as f:
    exec(f.read(), ABOUT)

setup(
    name="scooterflasher",
    version=ABOUT["__version__"],
    description="ST-Link / OpenOCD SWD flasher for Xiaomi and Ninebot scooters",
    long_description=README,
    long_description_content_type="text/markdown",
    author="ScooterTeam",
    url="https://github.com/scooterteam/scooterflasher",
    python_requires=">=3.10, <4",
    license="GPL-3.0-or-later",
    packages=["scooterflasher"],
    install_requires=["requests", "PySide6"],
    entry_points={
        "console_scripts": [
            "scooterflasher=scooterflasher.__main__:main",
        ]
    },
    keywords=["Xiaomi", "Ninebot", "Scooter", "ST-Link", "OpenOCD", "ScooterFlasher"],
)
