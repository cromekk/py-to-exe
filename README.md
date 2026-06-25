# Python to EXE Converter

A clean Windows GUI for turning Python files into `.exe` files with PyInstaller.

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

Choose a Python file, output folder, EXE name, optional icon, and build mode. Advanced options let you add hidden imports, data files, folders, or extra PyInstaller options.

## Extras

- Check Setup shows your Python and PyInstaller status.
- Copy Build Command copies the PyInstaller command to your clipboard.
- Open Output Folder opens the selected output folder.
- Save Log stores the build log as a text file.

## Quick fixes

- `python` not found: reinstall Python with PATH enabled or try `py`.
- EXE closes instantly: build with **Console window visible** and read the error.
- Missing module: install it with `python -m pip install package-name`.
- Missing assets: add them under **Files or folders your app needs**.
