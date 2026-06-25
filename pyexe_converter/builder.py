from __future__ import annotations

import importlib
import importlib.util
import os
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Tuple


LogHandler = Callable[[str], None]


class BuildError(RuntimeError):
    pass


@dataclass(frozen=True)
class DataItem:
    source: Path
    destination: str = "."


@dataclass(frozen=True)
class BuildConfig:
    source: Path
    output: Path
    one_file: bool
    windowed: bool
    name: str = ""
    icon: Optional[Path] = None
    hidden_imports: Tuple[str, ...] = ()
    data_items: Tuple[DataItem, ...] = ()
    clean: bool = True
    extra_args: str = ""


def build_executable(config: BuildConfig, log: LogHandler) -> Path:
    validate_config(config)
    ensure_pyinstaller(log)

    with tempfile.TemporaryDirectory(prefix="pyinstaller-build-") as temp_dir:
        command = pyinstaller_command(config, Path(temp_dir))
        log("Running PyInstaller:\n")
        log(format_command(command) + "\n\n")

        result = run_command(command, log, cwd=config.source.parent)

    if result != 0:
        raise BuildError("PyInstaller failed. Check the build log above.")

    return expected_exe_path(config)


def validate_config(config: BuildConfig) -> None:
    if not config.source.is_file() or config.source.suffix.lower() != ".py":
        raise BuildError("Choose a valid Python file ending in .py.")

    if not config.output.is_dir():
        raise BuildError("Choose a valid output folder.")

    if config.icon and (not config.icon.is_file() or config.icon.suffix.lower() != ".ico"):
        raise BuildError("Choose a valid .ico file for the EXE icon.")

    if config.name and has_bad_filename_char(config.name):
        raise BuildError("The EXE name contains a character Windows cannot use in file names.")

    for item in config.data_items:
        if not item.source.exists():
            raise BuildError("One of the added data paths does not exist.")

        destination = Path(item.destination.strip() or ".")
        if destination.is_absolute() or ".." in destination.parts:
            raise BuildError("Data destinations must be relative folders inside the EXE.")

    parse_extra_args(config.extra_args)


def has_bad_filename_char(value: str) -> bool:
    return any(char in value for char in '<>:"/\\|?*')


def pyinstaller_available() -> bool:
    return importlib.util.find_spec("PyInstaller") is not None


def ensure_pyinstaller(log: LogHandler) -> None:
    if pyinstaller_available():
        log("PyInstaller found.\n")
        return

    log("PyInstaller not found. Installing it now...\n")
    result = run_command([sys.executable, "-m", "pip", "install", "pyinstaller"], log)

    if result != 0:
        raise BuildError("PyInstaller could not be installed. Check pip and your internet connection.")

    importlib.invalidate_caches()

    if not pyinstaller_available():
        raise BuildError("PyInstaller was installed, but Python still cannot load it.")

    log("PyInstaller installed.\n")


def pyinstaller_command(config: BuildConfig, temp_dir: Path) -> List[str]:
    command = [sys.executable, "-m", "PyInstaller"]
    command.extend(parse_extra_args(config.extra_args))
    command.append("--noconfirm")

    if config.clean:
        command.append("--clean")

    command.extend(
        [
            "--distpath",
            str(config.output),
            "--workpath",
            str(temp_dir / "work"),
            "--specpath",
            str(temp_dir / "spec"),
        ]
    )

    if config.one_file:
        command.append("--onefile")

    if config.name.strip():
        command.extend(["--name", config.name.strip()])

    if config.icon:
        command.extend(["--icon", str(config.icon)])

    for hidden_import in config.hidden_imports:
        command.extend(["--hidden-import", hidden_import])

    for item in config.data_items:
        destination = item.destination.strip() or "."
        command.extend(["--add-data", f"{item.source}{os.pathsep}{destination}"])

    command.append("--windowed" if config.windowed else "--console")
    command.append(str(config.source))

    return command


def command_preview(config: BuildConfig) -> str:
    validate_config(config)
    command = pyinstaller_command(config, Path("pyinstaller-temp"))
    return format_command(command)


def format_command(command: List[str]) -> str:
    return subprocess.list2cmdline(command)


def parse_extra_args(value: str) -> List[str]:
    if not value.strip():
        return []

    try:
        return shlex.split(value)
    except ValueError as error:
        raise BuildError("Extra PyInstaller arguments are not formatted correctly.") from error


def run_command(command: List[str], log: LogHandler, cwd: Optional[Path] = None) -> int:
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd) if cwd else None,
    )

    if process.stdout:
        for line in process.stdout:
            log(line)

    return process.wait()


def expected_exe_path(config: BuildConfig) -> Path:
    exe_name = f"{config.name.strip() or config.source.stem}.exe"

    if config.one_file:
        return config.output / exe_name

    return config.output / (config.name.strip() or config.source.stem) / exe_name
