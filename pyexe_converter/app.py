from __future__ import annotations

import ctypes
import os
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from tkinter.scrolledtext import ScrolledText
from typing import Callable, List, Optional

from .builder import (
    BuildConfig,
    BuildError,
    DataItem,
    build_executable,
    command_preview,
    pyinstaller_available,
    validate_config,
)


class ConverterApp(ttk.Frame):
    def __init__(self, master: tk.Tk) -> None:
        super().__init__(master, padding=18, style="Shell.TFrame")

        self.master = master
        self.source_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.icon_var = tk.StringVar()
        self.package_var = tk.StringVar(value="onefile")
        self.app_type_var = tk.StringVar(value="console")
        self.clean_var = tk.BooleanVar(value=True)
        self.extra_args_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")

        self.data_items: List[DataItem] = []
        self.events: queue.Queue = queue.Queue()
        self.worker: Optional[threading.Thread] = None
        self.last_exe_path: Optional[Path] = None

        self.configure_window()
        self.create_widgets()
        self.poll_events()

    def configure_window(self) -> None:
        self.master.title("Python to EXE Converter")
        self.size_window_to_screen()
        self.master.configure(bg="#eef2f7")
        self.master.option_add("*Font", "{Segoe UI} 10")

        style = ttk.Style(self.master)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10), background="#eef2f7", foreground="#111827")
        style.configure("Shell.TFrame", background="#eef2f7")
        style.configure("Header.TFrame", background="#101827")
        style.configure("Header.TLabel", background="#101827", foreground="#ffffff")
        style.configure("HeaderMuted.TLabel", background="#101827", foreground="#aab3c2")
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("CardMuted.TLabel", background="#ffffff", foreground="#5f6b7a")
        style.configure("Status.TLabel", background="#eef2f7", foreground="#536173")
        style.configure("Card.TLabelframe", background="#ffffff", borderwidth=1, relief="solid", bordercolor="#c9d2df")
        style.configure("Card.TLabelframe.Label", background="#ffffff", foreground="#111827", font=("Segoe UI", 10, "bold"))
        style.configure("TEntry", fieldbackground="#ffffff", bordercolor="#cbd5e1", lightcolor="#cbd5e1", darkcolor="#cbd5e1", padding=7)
        style.configure("TButton", padding=(10, 6), background="#ffffff", bordercolor="#cbd5e1")
        style.configure("Accent.TButton", padding=(16, 8), background="#2563eb", foreground="#ffffff", bordercolor="#2563eb")
        style.configure("Ghost.TButton", padding=(10, 6), background="#101827", foreground="#ffffff", bordercolor="#3b4556")
        style.configure("Slim.TRadiobutton", background="#ffffff")
        style.configure("Slim.TCheckbutton", background="#ffffff")
        style.map("Accent.TButton", background=[("active", "#1d4ed8"), ("disabled", "#93a4bd")])
        style.map("Ghost.TButton", background=[("active", "#1f2937")])

        self.pack(fill="both", expand=True)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=2)

    def size_window_to_screen(self) -> None:
        self.master.update_idletasks()
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        available_width = max(screen_width - 80, 760)
        available_height = max(screen_height - 100, 620)
        width = min(max(1180, int(screen_width * 0.86)), available_width)
        height = min(max(820, int(screen_height * 0.88)), available_height)
        x = max((screen_width - width) // 2, 0)
        y = max((screen_height - height) // 2, 0)

        self.master.geometry(f"{width}x{height}+{x}+{y}")
        self.master.minsize(min(1040, width), min(720, height))
        self.master.after(120, self.maximize_window)

    def maximize_window(self) -> None:
        if sys.platform == "win32":
            try:
                self.master.state("zoomed")
            except tk.TclError:
                pass

    def create_widgets(self) -> None:
        self.create_header()
        self.create_main_area()
        self.create_log_area()
        self.create_status_bar()

    def create_header(self) -> None:
        frame = ttk.Frame(self, style="Header.TFrame", padding=(18, 14))
        frame.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        frame.columnconfigure(0, weight=1)

        title = ttk.Label(frame, text="Python to EXE Converter", style="Header.TLabel", font=("Segoe UI", 16, "bold"))
        title.grid(row=0, column=0, sticky="w")

        subtitle = ttk.Label(frame, text="Build clean Windows executables with PyInstaller", style="HeaderMuted.TLabel")
        subtitle.grid(row=1, column=0, sticky="w", pady=(2, 0))

        ttk.Button(frame, text="Check Setup", style="Ghost.TButton", command=self.check_setup).grid(row=0, column=1, rowspan=2, sticky="e", padx=(0, 8))
        self.build_button = ttk.Button(frame, text="Build EXE", style="Accent.TButton", command=self.start_build)
        self.build_button.grid(row=0, column=2, rowspan=2, sticky="e")

    def create_main_area(self) -> None:
        grid = ttk.Frame(self, style="Shell.TFrame")
        grid.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        self.create_input_card(grid)
        self.create_build_card(grid)
        self.create_advanced_card(grid)

    def create_input_card(self, parent: ttk.Frame) -> None:
        frame = self.card(parent, "Input and output", row=0, column=0, padx=(0, 7))
        frame.columnconfigure(1, weight=1)

        self.create_path_row(frame, 0, "Python file", self.source_var, self.choose_source)
        self.create_path_row(frame, 1, "Output folder", self.output_var, self.choose_output)
        self.create_path_row(frame, 2, "EXE icon (.ico)", self.icon_var, self.choose_icon)

        ttk.Button(frame, text="Clear", command=lambda: self.icon_var.set("")).grid(row=2, column=3, sticky="ew", padx=(6, 0), pady=(0, 8))
        ttk.Button(frame, text="Open Output Folder", command=self.open_output_folder).grid(row=3, column=1, sticky="w", pady=(4, 0), padx=(10, 0))

    def create_build_card(self, parent: ttk.Frame) -> None:
        frame = self.card(parent, "EXE settings", row=0, column=1, padx=(7, 0))
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="EXE name").grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(frame, textvariable=self.name_var).grid(row=0, column=1, sticky="ew", pady=(0, 8), padx=(10, 0))

        ttk.Radiobutton(frame, text="Single EXE file", variable=self.package_var, value="onefile", style="Slim.TRadiobutton").grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Radiobutton(frame, text="EXE folder with support files", variable=self.package_var, value="folder", style="Slim.TRadiobutton").grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Radiobutton(frame, text="Console window visible", variable=self.app_type_var, value="console", style="Slim.TRadiobutton").grid(row=3, column=0, columnspan=2, sticky="w", pady=(12, 0))
        ttk.Radiobutton(frame, text="Windowed app, no console", variable=self.app_type_var, value="windowed", style="Slim.TRadiobutton").grid(row=4, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Checkbutton(frame, text="Start from a clean PyInstaller build", variable=self.clean_var, style="Slim.TCheckbutton").grid(row=5, column=0, columnspan=2, sticky="w", pady=(12, 0))

        ttk.Button(frame, text="Copy Build Command", command=self.copy_build_command).grid(row=6, column=0, columnspan=2, sticky="w", pady=(14, 0))

    def create_advanced_card(self, parent: ttk.Frame) -> None:
        frame = self.card(parent, "Advanced options", row=1, column=0, columnspan=2, pady=(14, 0))
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        imports_frame = ttk.Frame(frame, style="Card.TFrame")
        imports_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        imports_frame.columnconfigure(0, weight=1)

        ttk.Label(imports_frame, text="Hidden imports, one per line", style="CardMuted.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.hidden_imports_box = ScrolledText(imports_frame, height=4, wrap="word", relief="solid", bd=1, font=("Segoe UI", 10), bg="#ffffff", highlightthickness=1, highlightbackground="#cbd5e1")
        self.hidden_imports_box.grid(row=1, column=0, sticky="ew")

        data_frame = ttk.Frame(frame, style="Card.TFrame")
        data_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        data_frame.columnconfigure(0, weight=1)

        ttk.Label(data_frame, text="Files or folders your app needs", style="CardMuted.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.data_list = tk.Listbox(data_frame, height=4, relief="solid", bd=1, bg="#ffffff", fg="#111827", highlightthickness=1, highlightbackground="#cbd5e1", selectbackground="#2563eb")
        self.data_list.grid(row=1, column=0, sticky="ew")

        data_buttons = ttk.Frame(data_frame, style="Card.TFrame")
        data_buttons.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(data_buttons, text="Add File", command=self.add_data_file).pack(side="left")
        ttk.Button(data_buttons, text="Add Folder", command=self.add_data_folder).pack(side="left", padx=(6, 0))
        ttk.Button(data_buttons, text="Remove", command=self.remove_data_item).pack(side="left", padx=(6, 0))

        extras = ttk.Frame(frame, style="Card.TFrame")
        extras.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        extras.columnconfigure(1, weight=1)

        ttk.Label(extras, text="Extra PyInstaller options", style="CardMuted.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(extras, textvariable=self.extra_args_var).grid(row=0, column=1, sticky="ew")

    def create_log_area(self) -> None:
        frame = self.card(self, "Build log", row=2, column=0, sticky="nsew")
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        toolbar = ttk.Frame(frame, style="Card.TFrame")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        toolbar.columnconfigure(0, weight=1)

        ttk.Label(toolbar, text="Progress and PyInstaller output", style="CardMuted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(toolbar, text="Clear Log", command=self.clear_log).grid(row=0, column=1, padx=(8, 0))
        ttk.Button(toolbar, text="Save Log", command=self.save_log).grid(row=0, column=2, padx=(6, 0))

        self.log_box = ScrolledText(frame, wrap="word", height=9, relief="flat", bd=0, bg="#0f172a", fg="#e5e7eb", insertbackground="#ffffff", font=("Cascadia Mono", 9))
        self.log_box.grid(row=1, column=0, sticky="nsew")

    def create_status_bar(self) -> None:
        ttk.Label(self, textvariable=self.status_var, style="Status.TLabel").grid(row=3, column=0, sticky="ew", pady=(8, 0))

    def card(self, parent: ttk.Widget, title: str, **grid_options) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text=title, padding=14, style="Card.TLabelframe")
        options = {"sticky": "nsew"}
        options.update(grid_options)
        frame.grid(**options)
        return frame

    def create_path_row(self, parent: ttk.Frame, row: int, label: str, variable: tk.StringVar, command: Callable[[], None]) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=(0, 8), padx=(10, 8))
        ttk.Button(parent, text="Browse", command=command).grid(row=row, column=2, sticky="ew", pady=(0, 8))

    def choose_source(self) -> None:
        path = filedialog.askopenfilename(title="Select Python file", filetypes=[("Python files", "*.py"), ("All files", "*.*")])
        if path:
            self.source_var.set(path)
            if not self.name_var.get().strip():
                self.name_var.set(Path(path).stem)

    def choose_output(self) -> None:
        path = filedialog.askdirectory(title="Select output folder")
        if path:
            self.output_var.set(path)

    def choose_icon(self) -> None:
        path = filedialog.askopenfilename(title="Select EXE icon", filetypes=[("Windows icons", "*.ico"), ("All files", "*.*")])
        if path:
            self.icon_var.set(path)

    def add_data_file(self) -> None:
        path = filedialog.askopenfilename(title="Add data file")
        if path:
            self.add_data_item(Path(path))

    def add_data_folder(self) -> None:
        path = filedialog.askdirectory(title="Add data folder")
        if path:
            self.add_data_item(Path(path))

    def add_data_item(self, source: Path) -> None:
        destination = simpledialog.askstring("Data destination", "Folder inside the EXE:", initialvalue=".")
        if destination is None:
            return

        item = DataItem(source=source, destination=destination.strip() or ".")
        self.data_items.append(item)
        self.refresh_data_list()

    def remove_data_item(self) -> None:
        selection = self.data_list.curselection()
        if not selection:
            return

        del self.data_items[selection[0]]
        self.refresh_data_list()

    def refresh_data_list(self) -> None:
        self.data_list.delete(0, tk.END)
        for item in self.data_items:
            self.data_list.insert(tk.END, f"{item.source}  ->  {item.destination}")

    def start_build(self) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("Build running", "Wait for the current build to finish.")
            return

        try:
            config = self.current_config()
            validate_config(config)
        except BuildError as error:
            messagebox.showerror("Cannot build", str(error))
            return

        self.last_exe_path = None
        self.clear_log()
        self.write_log("Starting build...\n")
        self.set_busy(True)

        self.worker = threading.Thread(target=self.run_build, args=(config,), daemon=True)
        self.worker.start()

    def current_config(self) -> BuildConfig:
        hidden_imports = self.hidden_imports_box.get("1.0", tk.END).replace(",", "\n")

        return BuildConfig(
            source=Path(self.source_var.get()),
            output=Path(self.output_var.get()),
            one_file=self.package_var.get() == "onefile",
            windowed=self.app_type_var.get() == "windowed",
            name=self.name_var.get().strip(),
            icon=Path(self.icon_var.get()) if self.icon_var.get().strip() else None,
            hidden_imports=tuple(value.strip() for value in hidden_imports.splitlines() if value.strip()),
            data_items=tuple(self.data_items),
            clean=self.clean_var.get(),
            extra_args=self.extra_args_var.get(),
        )

    def run_build(self, config: BuildConfig) -> None:
        try:
            exe_path = build_executable(config, self.queue_log)
        except Exception as error:
            self.events.put(("failed", str(error)))
        else:
            self.events.put(("finished", str(exe_path)))

    def check_setup(self) -> None:
        pyinstaller_text = "installed" if pyinstaller_available() else "not installed yet"
        message = f"Python: {sys.version.split()[0]}\nPyInstaller: {pyinstaller_text}"
        self.write_log("\nSetup check\n" + message + "\n")
        messagebox.showinfo("Setup check", message)

    def copy_build_command(self) -> None:
        try:
            command = command_preview(self.current_config())
        except BuildError as error:
            messagebox.showerror("Cannot copy command", str(error))
            return

        self.master.clipboard_clear()
        self.master.clipboard_append(command)
        self.status_var.set("Build command copied to clipboard")
        self.write_log("\nBuild command copied to clipboard.\n")

    def open_output_folder(self) -> None:
        path = self.output_folder_to_open()

        if not path or not path.exists():
            messagebox.showerror("Output folder", "Choose an output folder first.")
            return

        os.startfile(str(path))

    def output_folder_to_open(self) -> Optional[Path]:
        if self.last_exe_path:
            return self.last_exe_path.parent

        if self.output_var.get().strip():
            return Path(self.output_var.get())

        return None

    def save_log(self) -> None:
        text = self.log_box.get("1.0", tk.END).strip()
        if not text:
            messagebox.showinfo("Save log", "The log is empty.")
            return

        path = filedialog.asksaveasfilename(title="Save build log", defaultextension=".txt", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if path:
            Path(path).write_text(text + "\n", encoding="utf-8")
            self.status_var.set("Build log saved")

    def clear_log(self) -> None:
        self.log_box.delete("1.0", tk.END)

    def set_busy(self, busy: bool) -> None:
        if busy:
            self.build_button.state(["disabled"])
            self.status_var.set("Building...")
        else:
            self.build_button.state(["!disabled"])
            self.status_var.set("Ready")

    def queue_log(self, message: str) -> None:
        self.events.put(("log", message))

    def write_log(self, message: str) -> None:
        self.log_box.insert(tk.END, message)
        self.log_box.see(tk.END)

    def poll_events(self) -> None:
        try:
            while True:
                event, value = self.events.get_nowait()

                if event == "log":
                    self.write_log(value)
                elif event == "finished":
                    self.set_busy(False)
                    self.last_exe_path = Path(value)
                    self.status_var.set("Build complete")
                    self.write_log("\nBuild complete.\n")
                    messagebox.showinfo("Build complete", "Created:\n" + value)
                elif event == "failed":
                    self.set_busy(False)
                    self.status_var.set("Build failed")
                    self.write_log("\nBuild failed.\n" + value + "\n")
                    messagebox.showerror("Build failed", value)
        except queue.Empty:
            pass

        self.master.after(100, self.poll_events)


def enable_dpi_awareness() -> None:
    if sys.platform != "win32":
        return

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def main() -> None:
    enable_dpi_awareness()
    root = tk.Tk()
    ConverterApp(root)
    root.mainloop()


