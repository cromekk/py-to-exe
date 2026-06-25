from __future__ import annotations

import ctypes
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from tkinter.scrolledtext import ScrolledText
from typing import Callable, List, Optional

from .builder import BuildConfig, BuildError, DataItem, build_executable


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

        self.data_items: List[DataItem] = []
        self.events: queue.Queue = queue.Queue()
        self.worker: Optional[threading.Thread] = None

        self.configure_window()
        self.create_widgets()
        self.poll_events()

    def configure_window(self) -> None:
        self.master.title("Python to EXE Converter")
        self.master.geometry("940x680")
        self.master.minsize(820, 600)
        self.master.configure(bg="#f4f6f8")
        self.master.option_add("*Font", "Segoe UI 10")

        style = ttk.Style(self.master)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10), background="#f4f6f8", foreground="#111827")
        style.configure("Shell.TFrame", background="#f4f6f8")
        style.configure("Top.TFrame", background="#111827")
        style.configure("Top.TLabel", background="#111827", foreground="#ffffff")
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("Muted.TLabel", background="#f4f6f8", foreground="#6b7280")
        style.configure("CardMuted.TLabel", background="#ffffff", foreground="#6b7280")
        style.configure("Card.TLabelframe", background="#ffffff", bordercolor="#d8dee8", relief="solid")
        style.configure("Card.TLabelframe.Label", background="#ffffff", foreground="#111827", font=("Segoe UI Semibold", 10))
        style.configure("TEntry", fieldbackground="#ffffff", bordercolor="#cfd7e3", lightcolor="#cfd7e3", darkcolor="#cfd7e3", padding=6)
        style.configure("TButton", padding=(10, 6), background="#ffffff", bordercolor="#cfd7e3")
        style.configure("Accent.TButton", padding=(14, 8), background="#111827", foreground="#ffffff", bordercolor="#111827")
        style.map("Accent.TButton", background=[("active", "#2563eb"), ("disabled", "#9ca3af")])
        style.configure("Slim.TRadiobutton", background="#ffffff")
        style.configure("Slim.TCheckbutton", background="#ffffff")

        self.pack(fill="both", expand=True)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

    def create_widgets(self) -> None:
        self.create_header()
        self.create_main_area()
        self.create_log_area()

    def create_header(self) -> None:
        frame = ttk.Frame(self, style="Top.TFrame", padding=(16, 12))
        frame.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        frame.columnconfigure(0, weight=1)

        title = ttk.Label(frame, text="Python to EXE Converter", style="Top.TLabel", font=("Segoe UI Semibold", 15))
        title.grid(row=0, column=0, sticky="w")

        self.build_button = ttk.Button(frame, text="Build EXE", style="Accent.TButton", command=self.start_build)
        self.build_button.grid(row=0, column=1, sticky="e")

    def create_main_area(self) -> None:
        grid = ttk.Frame(self, style="Shell.TFrame")
        grid.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        self.create_file_card(grid)
        self.create_options_card(grid)
        self.create_advanced_card(grid)

    def create_file_card(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Files", padding=12, style="Card.TLabelframe")
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        frame.columnconfigure(1, weight=1)

        self.create_path_row(frame, 0, "Script", self.source_var, self.choose_source)
        self.create_path_row(frame, 1, "Output", self.output_var, self.choose_output)
        self.create_path_row(frame, 2, "Icon", self.icon_var, self.choose_icon)

        clear_icon = ttk.Button(frame, text="Clear", command=lambda: self.icon_var.set(""))
        clear_icon.grid(row=2, column=3, sticky="ew", padx=(6, 0))

    def create_options_card(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Build", padding=12, style="Card.TLabelframe")
        frame.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="App name").grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(frame, textvariable=self.name_var).grid(row=0, column=1, sticky="ew", pady=(0, 8))

        ttk.Radiobutton(frame, text="One-file executable", variable=self.package_var, value="onefile", style="Slim.TRadiobutton").grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 0))
        ttk.Radiobutton(frame, text="Folder build", variable=self.package_var, value="folder", style="Slim.TRadiobutton").grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Radiobutton(frame, text="Console app", variable=self.app_type_var, value="console", style="Slim.TRadiobutton").grid(row=3, column=0, columnspan=2, sticky="w", pady=(12, 0))
        ttk.Radiobutton(frame, text="Windowed app (no console)", variable=self.app_type_var, value="windowed", style="Slim.TRadiobutton").grid(row=4, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Checkbutton(frame, text="Clean build", variable=self.clean_var, style="Slim.TCheckbutton").grid(row=5, column=0, columnspan=2, sticky="w", pady=(12, 0))

    def create_advanced_card(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Advanced", padding=12, style="Card.TLabelframe")
        frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        imports_frame = ttk.Frame(frame, style="Card.TFrame")
        imports_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        imports_frame.columnconfigure(0, weight=1)

        ttk.Label(imports_frame, text="Hidden imports", style="CardMuted.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.hidden_imports_box = ScrolledText(imports_frame, height=4, wrap="word", relief="flat", bd=1, font=("Segoe UI", 10))
        self.hidden_imports_box.grid(row=1, column=0, sticky="ew")

        data_frame = ttk.Frame(frame, style="Card.TFrame")
        data_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        data_frame.columnconfigure(0, weight=1)

        ttk.Label(data_frame, text="Data files", style="CardMuted.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.data_list = tk.Listbox(data_frame, height=4, relief="flat", bd=1, bg="#ffffff", fg="#111827", highlightthickness=1, highlightbackground="#cfd7e3", selectbackground="#2563eb")
        self.data_list.grid(row=1, column=0, sticky="ew")

        data_buttons = ttk.Frame(data_frame, style="Card.TFrame")
        data_buttons.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(data_buttons, text="Add file", command=self.add_data_file).pack(side="left")
        ttk.Button(data_buttons, text="Add folder", command=self.add_data_folder).pack(side="left", padx=(6, 0))
        ttk.Button(data_buttons, text="Remove", command=self.remove_data_item).pack(side="left", padx=(6, 0))

        extras = ttk.Frame(frame, style="Card.TFrame")
        extras.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        extras.columnconfigure(1, weight=1)

        ttk.Label(extras, text="Extra PyInstaller args", style="CardMuted.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(extras, textvariable=self.extra_args_var).grid(row=0, column=1, sticky="ew")

    def create_log_area(self) -> None:
        frame = ttk.LabelFrame(self, text="Log", padding=12, style="Card.TLabelframe")
        frame.grid(row=2, column=0, sticky="nsew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.log_box = ScrolledText(frame, wrap="word", height=12, relief="flat", bd=0, bg="#0f172a", fg="#e5e7eb", insertbackground="#ffffff", font=("Cascadia Mono", 9))
        self.log_box.grid(row=0, column=0, sticky="nsew")

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
        path = filedialog.askopenfilename(title="Select icon", filetypes=[("Windows icons", "*.ico"), ("All files", "*.*")])
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
        destination = simpledialog.askstring("Data destination", "Folder inside the app:", initialvalue=".")
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
        except BuildError as error:
            messagebox.showerror("Cannot build", str(error))
            return

        self.log_box.delete("1.0", tk.END)
        self.write_log("Starting build...\n")
        self.build_button.state(["disabled"])

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
                    self.build_button.state(["!disabled"])
                    self.write_log("\nBuild complete.\n")
                    messagebox.showinfo("Build complete", "Created:\n" + value)
                elif event == "failed":
                    self.build_button.state(["!disabled"])
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


