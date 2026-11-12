from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
PYODIDE_VERSION = "0.27.7"
CDN_RUNTIME = f"https://cdn.jsdelivr.net/pyodide/v{PYODIDE_VERSION}/full/"
SOURCES = {
    f"/src/gage_tracer/{name}.py": ROOT / "src" / "gage_tracer" / f"{name}.py"
    for name in (
        "__init__", "calculations", "data_parser", "paired_ttest",
        "paired_visualization", "presentation", "study_config", "visualization",
    )
}
SOURCES["/src/app/components/input_examples.py"] = ROOT / "src" / "app" / "components" / "input_examples.py"
SOURCES["/tests/browser_poc.py"] = ROOT / "tests" / "browser_poc.py"
SOURCES["/tests/type1_browser_poc.py"] = ROOT / "tests" / "type1_browser_poc.py"
SOURCES["/tests/grr_browser_poc.py"] = ROOT / "tests" / "grr_browser_poc.py"
SOURCES["/tests/paired_browser_poc.py"] = ROOT / "tests" / "paired_browser_poc.py"


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

PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Browser calculation proof</title></head>
<body><h1>Browser calculation proof</h1><p>Synthetic data only.</p>
<button id="run">Run comparison</button><pre id="status">Ready</pre>
<script type="module">
import { loadPyodide } from "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/pyodide.mjs";
const sourcePaths = [
  "__init__", "calculations", "data_parser", "paired_ttest", "paired_visualization",
  "presentation", "study_config", "visualization"
].map(name => `/src/gage_tracer/${name}.py`);
sourcePaths.push("/src/app/components/input_examples.py", "/tests/browser_poc.py");
const status = document.getElementById("status");
const compare = (expected, actual, path, differences) => {
  if (typeof expected === "number" && typeof actual === "number") {
    if (Math.abs(expected - actual) > 1e-8 + 1e-6 * Math.max(Math.abs(expected), Math.abs(actual)))
      differences.push(`${path}: ${expected} != ${actual}`);
  } else if (Array.isArray(expected) && Array.isArray(actual)) {
    if (expected.length !== actual.length) differences.push(`${path}: different lengths`);
    for (let index = 0; index < Math.min(expected.length, actual.length); index++)
      compare(expected[index], actual[index], `${path}[${index}]`, differences);
  } else if (expected && actual && typeof expected === "object" && typeof actual === "object") {
    const keys = new Set([...Object.keys(expected), ...Object.keys(actual)]);
    for (const key of keys) compare(expected[key], actual[key], `${path}.${key}`, differences);
  } else if (expected !== actual) {
    differences.push(`${path}: ${JSON.stringify(expected)} != ${JSON.stringify(actual)}`);
  }
};
document.getElementById("run").addEventListener("click", async () => {
  delete status.dataset.finished;
  document.getElementById("run").disabled = true;
  try {
    status.textContent = "Loading Python and scientific packages...";
    const pyodide = await loadPyodide();
    await pyodide.loadPackage(["numpy", "pandas", "scipy", "matplotlib"]);
    const sources = await Promise.all(sourcePaths.map(async path => {
      const response = await fetch(path);
      if (!response.ok) throw new Error(`Could not load ${path}`);
      return [path, await response.text()];
    }));
    for (const [path, contents] of sources) {
      const destination = `/project${path}`;
      pyodide.FS.mkdirTree(destination.slice(0, destination.lastIndexOf("/")));
      pyodide.FS.writeFile(destination, contents, {encoding: "utf8"});
    }
    status.textContent = "Running synthetic studies and generating reports...";
    const browserResult = JSON.parse(await pyodide.runPythonAsync(
      "import json, runpy; proof = runpy.run_path('/project/tests/browser_poc.py'); json.dumps(proof['run_browser_poc'](), allow_nan=False, sort_keys=True)"
    ));
    const baselineResponse = await fetch("/baseline.json");
    if (!baselineResponse.ok) throw new Error("Could not load local baseline");
    const baseline = await baselineResponse.json();
    const results = {};
    for (const study of ["type1", "grr", "paired"]) {
      const differences = [];
      compare(baseline[study], browserResult[study], study, differences);
      const visualDifferences = differences.filter(item => item.includes(".images["));
      const otherDifferences = differences.filter(item => !item.includes(".images["));
      results[study] = {
        metricsAndTextMatch: otherDifferences.length === 0,
        imageDimensionsMatch: visualDifferences.length === 0,
        visualDifferences,
        otherDifferences,
      };
    }
    globalThis.browserProofResult = results;
    status.textContent = JSON.stringify(results, null, 2);
    status.dataset.finished = "true";
  } catch (error) {
    status.textContent = String(error);
    status.dataset.finished = "error";
  } finally {
    document.getElementById("run").disabled = false;
  }
});
</script></body></html>'''


class ProofHandler(BaseHTTPRequestHandler):
    runtime_directory = None
    runtime_allowlist = set()

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/":
            body, content_type = PAGE.encode("utf-8"), "text/html; charset=utf-8"
        elif path == "/app":
          body = (ROOT / "tests" / "browser_app.html").read_bytes()
          content_type = "text/html; charset=utf-8"
        elif path == "/browser-app.js":
          body = (ROOT / "tests" / "browser_app.js").read_bytes()
          content_type = "text/javascript; charset=utf-8"
        elif path == "/type1":
          body = (ROOT / "tests" / "type1_browser_poc.html").read_bytes()
          content_type = "text/html; charset=utf-8"
        elif path == "/type1.js":
          body = (ROOT / "tests" / "type1_browser_poc.js").read_bytes()
          content_type = "text/javascript; charset=utf-8"
        elif path == "/runtime.js":
          body = (ROOT / "tests" / "browser_runtime.js").read_bytes()
          content_type = "text/javascript; charset=utf-8"
        elif path in {"/grr", "/paired"}:
          body = (ROOT / "tests" / "msa_browser_poc.html").read_bytes()
          content_type = "text/html; charset=utf-8"
        elif path == "/msa.js":
          body = (ROOT / "tests" / "msa_browser_poc.js").read_bytes()
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
        elif path == "/baseline.json":
          body = json.dumps(importlib.import_module("browser_poc").run_browser_poc(), allow_nan=False, sort_keys=True).encode("utf-8")
          content_type = "application/json"
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
          self.send_header("Content-Security-Policy", f"default-src 'none'; script-src 'self'{external} 'unsafe-eval' 'wasm-unsafe-eval'; connect-src 'self'{external} blob:; style-src 'unsafe-inline'; img-src data: blob:; object-src 'none'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Serve isolated browser-processing prototypes on localhost.")
    parser.add_argument("--pyodide-dir", type=Path, help="Local Pyodide 0.27.7 full distribution directory")
    options = parser.parse_args()
    if options.pyodide_dir:
        ProofHandler.runtime_directory = options.pyodide_dir.resolve(strict=True)
        ProofHandler.runtime_allowlist = validate_pyodide_runtime(ProofHandler.runtime_directory)
    print("Browser proof available at http://127.0.0.1:8765", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8765), ProofHandler).serve_forever()