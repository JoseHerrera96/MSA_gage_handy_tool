from __future__ import annotations

import argparse
import hashlib
import json
import sys
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit

from PIL import Image, ImageDraw

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
PYODIDE_VERSION = "0.27.7"
CDN_RUNTIME = f"https://cdn.jsdelivr.net/pyodide/v{PYODIDE_VERSION}/full/"


def app_icon() -> Image.Image:
  image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
  draw = ImageDraw.Draw(image)
  draw.rounded_rectangle((8, 8, 248, 248), radius=52, fill="#202124")
  draw.line([(46, 187), (46, 72), (128, 150), (210, 72), (210, 187)], fill="#f58220", width=24, joint="curve")
  draw.line([(86, 207), (170, 207)], fill="#79c9ba", width=8)
  return image.resize((128, 128), Image.Resampling.LANCZOS)


@lru_cache(maxsize=1)
def app_icon_png() -> bytes:
  buffer = BytesIO()
  app_icon().save(buffer, format="PNG")
  return buffer.getvalue()


SOURCES = {
    f"/src/gage_tracer/{name}.py": ROOT / "src" / "gage_tracer" / f"{name}.py"
    for name in (
        "__init__", "calculations", "data_parser", "input_examples", "paired_ttest",
        "paired_visualization", "presentation", "study_config", "visualization",
    )
}
SOURCES["/src/web/adapters/type1.py"] = ROOT / "src" / "web" / "adapters" / "type1.py"
SOURCES["/src/web/adapters/gage_rr.py"] = ROOT / "src" / "web" / "adapters" / "gage_rr.py"
SOURCES["/src/web/adapters/paired.py"] = ROOT / "src" / "web" / "adapters" / "paired.py"


def pyodide_runtime_allowlist(lock):
  if lock.get("info", {}).get("version") != PYODIDE_VERSION:
    raise ValueError(f"Expected Pyodide {PYODIDE_VERSION}.")
  allowed = {"pyodide.mjs", "pyodide.asm.js", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"}
  for package in lock.get("packages", {}).values():
    name = package.get("file_name", "")
    if isinstance(name, str) and name and "/" not in name and "\\" not in name and Path(name).suffix in {".whl", ".zip"}:
      allowed.add(name)
  return allowed


def validate_pyodide_runtime(directory):
  directory = directory.resolve(strict=True)
  lock = json.loads((directory / "pyodide-lock.json").read_text(encoding="utf-8"))
  allowed = pyodide_runtime_allowlist(lock)
  for name in ("pyodide.mjs", "pyodide.asm.js", "pyodide.asm.wasm", "python_stdlib.zip"):
    candidate = (directory / name).resolve()
    if candidate.parent != directory or not candidate.is_file():
      raise ValueError(f"Missing local Pyodide runtime file: {name}")
  pending = ["numpy", "pandas", "scipy", "matplotlib"]
  checked = set()
  while pending:
    name = pending.pop()
    if name in checked:
      continue
    checked.add(name)
    package = lock.get("packages", {}).get(name)
    if not package or package.get("file_name") not in allowed:
      raise ValueError(f"Invalid local Pyodide package: {name}")
    candidate = (directory / package["file_name"]).resolve()
    if candidate.parent != directory or not candidate.is_file():
      raise ValueError(f"Missing local Pyodide package: {name}")
    if hashlib.sha256(candidate.read_bytes()).hexdigest() != package.get("sha256"):
      raise ValueError(f"Local Pyodide package checksum mismatch: {name}")
    pending.extend(package.get("depends", []))
  return allowed

class AppHandler(BaseHTTPRequestHandler):
    runtime_directory = None
    runtime_allowlist = set()

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/app":
          body = (ROOT / "src" / "web" / "app.html").read_bytes()
          content_type = "text/html; charset=utf-8"
        elif path == "/app-icon.png":
          body, content_type = app_icon_png(), "image/png"
        elif path == "/browser-app.js":
          body = (ROOT / "src" / "web" / "app.js").read_bytes()
          content_type = "text/javascript; charset=utf-8"
        elif path == "/type1":
          body = (ROOT / "src" / "web" / "type1.html").read_bytes()
          content_type = "text/html; charset=utf-8"
        elif path == "/type1.js":
          body = (ROOT / "src" / "web" / "type1.js").read_bytes()
          content_type = "text/javascript; charset=utf-8"
        elif path == "/runtime.js":
          body = (ROOT / "src" / "web" / "runtime.js").read_bytes()
          content_type = "text/javascript; charset=utf-8"
        elif path in {"/grr", "/paired"}:
          body = (ROOT / "src" / "web" / "studies.html").read_bytes()
          content_type = "text/html; charset=utf-8"
        elif path == "/msa.js":
          body = (ROOT / "src" / "web" / "studies.js").read_bytes()
          content_type = "text/javascript; charset=utf-8"
        elif path == "/runtime-config.json":
          body = json.dumps({"indexURL": "/runtime/" if self.runtime_directory else CDN_RUNTIME}).encode("utf-8")
          content_type = "application/json"
        elif path.startswith("/runtime/") and self.runtime_directory:
          name = path.removeprefix("/runtime/")
          candidate = (self.runtime_directory / name).resolve()
          if name not in self.runtime_allowlist or candidate.parent != self.runtime_directory or not candidate.is_file():
            self.send_error(404)
            return
          body = candidate.read_bytes()
          content_type = {".mjs": "text/javascript", ".js": "text/javascript", ".wasm": "application/wasm", ".json": "application/json"}.get(candidate.suffix, "application/octet-stream")
        elif path in SOURCES:
            body, content_type = SOURCES[path].read_bytes(), "text/plain; charset=utf-8"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        if path in {"/app", "/type1", "/grr", "/paired"}:
          external = "" if self.runtime_directory else " https://cdn.jsdelivr.net"
          self.send_header("Content-Security-Policy", f"default-src 'none'; script-src 'self'{external} 'unsafe-eval' 'wasm-unsafe-eval'; connect-src 'self'{external} blob:; style-src 'unsafe-inline'; img-src 'self' data: blob:; object-src 'none'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Serve the local MSA browser application on localhost.")
    parser.add_argument("--pyodide-dir", type=Path, help="Local Pyodide 0.27.7 full distribution directory")
    options = parser.parse_args()
    if options.pyodide_dir:
        AppHandler.runtime_directory = options.pyodide_dir.resolve(strict=True)
        AppHandler.runtime_allowlist = validate_pyodide_runtime(AppHandler.runtime_directory)
    print("Browser app available at http://127.0.0.1:8765/app", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8765), AppHandler).serve_forever()