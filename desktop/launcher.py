from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from PIL import Image

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from web.server import AppHandler, ROOT, app_icon, validate_pyodide_runtime


def start_server(runtime_directory: Path) -> ThreadingHTTPServer:
    runtime_directory = runtime_directory.resolve(strict=True)
    allowed = validate_pyodide_runtime(runtime_directory)

    class LocalHandler(AppHandler):
        runtime_allowlist = allowed

        def do_GET(self):
            path = urlsplit(self.path).path
            if self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}":
                self.send_error(403)
                return
            super().do_GET()

        def log_message(self, format, *args):
            pass

    LocalHandler.runtime_directory = runtime_directory
    server = ThreadingHTTPServer(("127.0.0.1", 0), LocalHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def tray_image() -> Image.Image:
    return app_icon().resize((64, 64), Image.Resampling.LANCZOS)


def show_error(message: str) -> None:
    ctypes.windll.user32.MessageBoxW(0, message, "MSA Handy Tool", 0x10)


def app_browsers() -> list[Path]:
    try:
        import winreg
    except ImportError:
        return []

    browsers = []
    for executable in ("msedge.exe", "chrome.exe"):
        for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(root, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{executable}") as key:
                    path = Path(winreg.QueryValueEx(key, "")[0])
                if path.is_file() and path not in browsers:
                    browsers.append(path)
            except OSError:
                continue
    return browsers


def open_app_window(url: str, profile_directory: Path) -> subprocess.Popen | None:
    for browser in app_browsers():
        try:
            return subprocess.Popen([
                str(browser), f"--app={url}", f"--user-data-dir={profile_directory}",
                "--new-window", "--disable-background-mode", "--disable-default-apps",
                "--no-first-run", "--no-default-browser-check",
            ])
        except OSError:
            continue
    return None


def visible_app_windows() -> list[tuple[int, int]]:
    user32 = ctypes.windll.user32
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    windows: list[tuple[int, int]] = []

    @callback_type
    def find_window(handle, unused):
        if not user32.IsWindowVisible(handle):
            return True
        class_name = ctypes.create_unicode_buffer(256)
        title = ctypes.create_unicode_buffer(512)
        user32.GetClassNameW(handle, class_name, len(class_name))
        user32.GetWindowTextW(handle, title, len(title))
        if class_name.value != "Chrome_WidgetWin_1":
            return True
        if title.value == "MSA Handy Tool" or title.value.endswith("| MSA Handy Tool"):
            owner = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(handle, ctypes.byref(owner))
            windows.append((int(handle), owner.value))
        return True

    user32.EnumWindows(find_window, 0)
    return windows


def wait_for_browser_exit(icon, browser_pid: list[int], existing_windows: set[int]) -> None:
    deadline = time.monotonic() + 30
    handle = None
    while time.monotonic() < deadline:
        windows = [(window, process_id) for window, process_id in visible_app_windows() if window not in existing_windows]
        if windows:
            handle, process_id = windows[-1]
            browser_pid[:] = [process_id]
            break
        time.sleep(0.1)
    else:
        icon.stop()
        return

    user32 = ctypes.windll.user32
    while user32.IsWindow(handle):
        time.sleep(0.2)
    icon.stop()


def close_browser_process(browser_pid: list[int], icon=None) -> None:
    if not browser_pid:
        return
    taskkill = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "taskkill.exe"
    subprocess.run(
        [str(taskkill), "/PID", str(browser_pid[0]), "/T", "/F"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def main() -> None:
    try:
        import pystray

        server = start_server(ROOT / "pyodide")
    except Exception as error:
        show_error(f"No se pudo iniciar la aplicacion local:\n{error}")
        return

    url = f"http://127.0.0.1:{server.server_port}/app"
    profile = tempfile.TemporaryDirectory(prefix="msa-browser-", ignore_cleanup_errors=True)
    browser_process = None
    browser_pid: list[int] = []

    def open_browser(icon=None, item=None) -> None:
        nonlocal browser_process
        try:
            if browser_pid:
                return
            existing_windows = {window for window, _ in visible_app_windows()}
            process = open_app_window(url, Path(profile.name))
            if process is None:
                show_error("No se pudo abrir la aplicacion. Instala Microsoft Edge o Google Chrome.")
                if browser_process is None:
                    icon.stop()
            elif browser_process is None:
                browser_process = process
                threading.Thread(target=wait_for_browser_exit, args=(icon, browser_pid, existing_windows), daemon=True).start()
        except Exception:
            show_error("No se pudo abrir la ventana de la aplicacion.")
            if browser_process is None:
                icon.stop()

    def stop(icon, item) -> None:
        icon.stop()

    def setup(icon) -> None:
        try:
            icon.visible = True
        except Exception as error:
            show_error(f"No se pudo mostrar el icono de la aplicacion:\n{error}")
            icon.stop()
            return
        open_browser(icon)

    try:
        icon = pystray.Icon("msa-handy-tool", tray_image(), "MSA Handy Tool", menu=pystray.Menu(
            pystray.MenuItem("Abrir aplicacion", open_browser, default=True),
            pystray.MenuItem("Cerrar servidor", stop),
        ))
        icon.run(setup=setup)
    except Exception as error:
        show_error(f"No se pudo iniciar el icono de la aplicacion:\n{error}")
    finally:
        close_browser_process(browser_pid)
        server.shutdown()
        server.server_close()
        if browser_process is not None and browser_process.poll() is None:
            browser_process.terminate()
            browser_process.wait()
        profile.cleanup()


if __name__ == "__main__":
    main()