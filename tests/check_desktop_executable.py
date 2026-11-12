from __future__ import annotations

import argparse
import ctypes
import os
import re
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from browser_type1_check import ProofHandler, run_browser, synthetic_cases, validate_pyodide_runtime


def wait_for_port(process: subprocess.Popen) -> int:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Launcher exited during startup: {process.returncode}")
        output = subprocess.check_output([os.path.join(os.environ["SystemRoot"], "System32", "netstat.exe"), "-ano", "-p", "tcp"], text=True)
        for line in output.splitlines():
            match = re.match(r"\s*TCP\s+127\.0\.0\.1:(\d+)\s+\S+\s+LISTENING\s+(\d+)\s*$", line, re.I)
            if match and int(match.group(2)) == process.pid:
                return int(match.group(1))
        threading.Event().wait(0.2)
    raise TimeoutError("Launcher did not open a loopback port")


def close_tray_menu(process_id: int) -> None:
    user32 = ctypes.windll.user32
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    user32.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]

    def windows():
        found = []

        @callback_type
        def find_window(handle, unused):
            owner = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(handle, ctypes.byref(owner))
            if owner.value == process_id:
                name = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(handle, name, len(name))
                found.append((handle, name.value, bool(user32.IsWindowVisible(handle))))
            return True

        user32.EnumWindows(find_window, 0)
        return found

    existing = windows()
    if any(visible for _, _, visible in existing):
        raise RuntimeError("Launcher has an unexpected visible control window")
    tray_windows = [handle for handle, name, _ in existing if name.startswith("msa-handy-tool") and name.endswith("SystemTrayIcon")]
    if len(tray_windows) != 2:
        raise RuntimeError("Tray windows not found")
    for handle in tray_windows:
        user32.PostMessageW(handle, 0x40B, 0, 0x205)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        menus = [handle for handle, name, visible in windows() if name == "#32768" and visible]
        if menus:
            user32.PostMessageW(menus[0], 0x0100, 0x28, 0)
            user32.PostMessageW(menus[0], 0x0100, 0x28, 0)
            user32.PostMessageW(menus[0], 0x0100, 0x0D, 0)
            return
        threading.Event().wait(0.1)
    raise RuntimeError("Tray context menu did not open")


def verify_tray_source(executable: Path, environment: dict) -> None:
    with tempfile.TemporaryDirectory(prefix="msa-tray-source-check-") as temporary:
        directory = Path(temporary)
        bundle = directory / "bundle"
        shutil.copytree(executable.parent, bundle)
        marker = directory / "source-loaded.txt"
        source = bundle / "_internal" / "pystray" / "__init__.py"
        with source.open("a", encoding="utf-8") as file:
            file.write(f"\nwith open({str(marker)!r}, 'w', encoding='utf-8') as marker_file:\n    marker_file.write('loaded')\n")
        process = subprocess.Popen([str(bundle / executable.name)], cwd=directory, env=environment)
        try:
            wait_for_port(process)
            close_tray_menu(process.pid)
            if process.wait(timeout=10) != 0 or marker.read_text(encoding="utf-8") != "loaded":
                raise RuntimeError("Modified tray source did not run correctly")
            print("Modified tray source loaded and exited successfully")
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)


def main() -> None:
    parser = argparse.ArgumentParser(description="Exercise a packaged Windows app with synthetic data.")
    parser.add_argument("executable", type=Path)
    parser.add_argument("--tray-only", action="store_true", help="Check the tray menu without running browser comparisons.")
    parser.add_argument("--verify-tray-source", action="store_true", help="Check that a modified copy of the bundled tray source is loaded.")
    arguments = parser.parse_args()
    executable = arguments.executable.resolve(strict=True)
    ProofHandler.runtime_allowlist = validate_pyodide_runtime(executable.parent / "_internal" / "pyodide")
    environment = os.environ.copy()
    environment["PATH"] = os.path.join(environment["SYSTEMROOT"], "System32") + os.pathsep + environment["SYSTEMROOT"]
    environment.pop("PYTHONHOME", None)
    environment.pop("PYTHONPATH", None)
    process = subprocess.Popen([str(executable)], cwd=tempfile.gettempdir(), env=environment)
    try:
        port = wait_for_port(process)
        base_url = f"http://127.0.0.1:{port}"
        if not arguments.tray_only:
            browsers = [Path(os.environ["ProgramFiles"]) / "Google/Chrome/Application/chrome.exe", Path(os.environ["ProgramFiles(x86)"]) / "Microsoft/Edge/Application/msedge.exe"]
            for browser in browsers:
                run_browser(browser, base_url, synthetic_cases(), "synthetic.txt", True)
                print(f"{browser.name}: packaged application comparisons passed")
        close_tray_menu(process.pid)
        if process.wait(timeout=10) != 0:
            raise RuntimeError("Launcher exited with an error")
        with socket.socket() as connection:
            connection.settimeout(1)
            if connection.connect_ex(("127.0.0.1", port)) == 0:
                raise RuntimeError("Launcher port is still listening")
        print("Launcher closed cleanly with no Python on PATH")
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
    if arguments.verify_tray_source:
        verify_tray_source(executable, environment)


if __name__ == "__main__":
    main()