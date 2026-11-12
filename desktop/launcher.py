from __future__ import annotations

import ctypes
import sys
import threading
import webbrowser
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from PIL import Image, ImageDraw

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

from browser_poc_server import ProofHandler, ROOT, validate_pyodide_runtime


def start_server(runtime_directory: Path) -> ThreadingHTTPServer:
    runtime_directory = runtime_directory.resolve(strict=True)
    allowed = validate_pyodide_runtime(runtime_directory)

    class LocalHandler(ProofHandler):
        runtime_allowlist = allowed

        def do_GET(self):
            path = urlsplit(self.path).path
            if self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}":
                self.send_error(403)
                return
            if path in {"/", "/baseline.json", "/tests/browser_poc.py"}:
                self.send_error(404)
                return
            super().do_GET()

        def log_message(self, format, *args):
            pass

    LocalHandler.runtime_directory = runtime_directory
    server = ThreadingHTTPServer(("127.0.0.1", 0), LocalHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def tray_image() -> Image.Image:
    image = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((4, 4, 124, 124), radius=25, fill="#202124")
    draw.line([(24, 94), (24, 36), (64, 77), (104, 36), (104, 94)], fill="#f58220", width=12, joint="curve")
    return image.resize((64, 64), Image.Resampling.LANCZOS)


def show_error(message: str) -> None:
    ctypes.windll.user32.MessageBoxW(0, message, "MSA Handy Tool", 0x10)


def main() -> None:
    try:
        import pystray

        server = start_server(ROOT / "pyodide")
    except Exception as error:
        show_error(f"No se pudo iniciar la aplicacion local:\n{error}")
        return

    url = f"http://127.0.0.1:{server.server_port}/app"

    def open_browser(icon=None, item=None) -> None:
        try:
            if not webbrowser.open(url):
                show_error(f"No se pudo abrir el navegador. Abre esta direccion:\n{url}")
        except Exception:
            show_error(f"No se pudo abrir el navegador. Abre esta direccion:\n{url}")

    def stop(icon, item) -> None:
        icon.stop()

    def setup(icon) -> None:
        try:
            icon.visible = True
        except Exception as error:
            show_error(f"No se pudo mostrar el icono de la aplicacion:\n{error}")
            icon.stop()
            return
        open_browser()

    try:
        icon = pystray.Icon("msa-handy-tool", tray_image(), "MSA Handy Tool", menu=pystray.Menu(
            pystray.MenuItem("Abrir aplicacion", open_browser, default=True),
            pystray.MenuItem("Cerrar servidor", stop),
        ))
        icon.run(setup=setup)
    except Exception as error:
        show_error(f"No se pudo iniciar el icono de la aplicacion:\n{error}")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()