# Python to EXE Converter

A clean Windows GUI for turning Python scripts into `.exe` files with PyInstaller.

## Setup

Install Python from <https://www.python.org/downloads/windows/> and enable **Add python.exe to PATH** during setup.

PyInstaller installs automatically when the app needs it. Manual install:

```powershell
python -m pip install pyinstaller
```

## Run

```powershell
python py_to_exe_converter.py
```

Pick a script, output folder, app name, icon, build mode, and any advanced options you need.

## Options

- `.ico` icon for the final EXE
- one-file or folder build
- console or windowed mode
- hidden imports
- added data files or folders
- extra PyInstaller arguments

## Quick fixes

- `python` not found: reinstall Python with PATH enabled or try `py`.
- EXE closes instantly: build as a console app and read the error.
- Missing module: install it with `python -m pip install package-name`.
- Missing assets: add them in **Data files** or use `--add-data`.
