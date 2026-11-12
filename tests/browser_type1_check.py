from __future__ import annotations

import argparse
import base64
import math
import numbers
import os
import re
import threading
from http.server import ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit
from zipfile import ZipFile

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

from browser_poc import archive_summary, html_summary, load_examples
from browser_poc_server import ProofHandler, SOURCES, validate_pyodide_runtime
from grr_browser_poc import analyze_grr, grr_export, grr_overview
from paired_browser_poc import analyze_paired, paired_export, paired_overview
from type1_browser_poc import analyze_type1


class QuietProofHandler(ProofHandler):
    def log_message(self, format, *args):
        pass


def check_dark_charts(html):
    images = re.findall(r"data:image/png;base64,([A-Za-z0-9+/=]+)", html)
    for encoded in images:
        with Image.open(BytesIO(base64.b64decode(encoded))) as image:
            pixels = np.asarray(image.convert("RGB").resize((64, 64)))
            if pixels[0, 0].max() >= 90 or np.all(pixels > 230, axis=2).mean() >= 0.15:
                raise AssertionError("Downloaded chart has a light background")
    return len(images)


def synthetic_cases():
    examples = load_examples()
    cases = [(mode, examples("type1", mode)["type1.txt"], "REPORT", "REPORT") for mode in ("blocks", "periodic", "custom")]
    lines = []
    for index in range(1000):
        lines.append(f"Diameter\t{10 + (index % 7 - 3) * 0.0007:.5f}\t10\t0.1\t-0.1")
        lines.append(f"Height\t{5 + (index % 9 - 4) * 0.0003:.5f}\t5\t0.1\t-0.1")
    cases.append(("periodic", "\n".join(lines) + "\n", "", ""))
    return cases


def check_case(page, case, filename):
    mode, text, start_marker, end_marker = case
    native = analyze_type1(text, mode, start_marker, end_marker, filename)
    page.locator(f'input[name="format"][value="{mode}"]').check()
    if mode == "custom":
        page.locator("#start-marker").fill(start_marker)
        page.locator("#end-marker").fill(end_marker)
    page.locator("#file").set_input_files({"name": filename, "mimeType": "text/plain", "buffer": text.encode("utf-8")})
    page.locator("#analyze").click()
    page.wait_for_function("document.querySelector('#status').textContent === 'Analysis complete.' || document.querySelector('#status').classList.contains('error')", timeout=120000)
    if page.locator("#status").get_attribute("class") == "error":
        raise AssertionError("Browser analysis failed")

    metrics = native["metrics"]
    expected_metrics = [str(metrics["dimensions"]), metrics["mean_cg"], metrics["mean_cgk"], metrics["cg_status"], metrics["cgk_status"], metrics["pass_rate"]]
    actual_metrics = [page.locator(f"#{name}").inner_text() for name in ("dimensions", "cg", "cgk", "cg-status", "cgk-status", "pass-rate")]
    if actual_metrics != expected_metrics:
        raise AssertionError("Browser metrics differ from native Python")
    rows = page.locator("#summary tbody tr").all()
    if len(rows) != len(native["table"]["data"]):
        raise AssertionError("Browser dimension count differs")
    for row, expected in zip(rows, native["table"]["data"]):
        actual = row.locator("td").all_inner_texts()
        for observed, value in zip(actual, expected):
            if isinstance(value, (int, float)) and math.isfinite(value):
                if not math.isclose(float(observed), value, rel_tol=1e-6, abs_tol=1e-8):
                    raise AssertionError("Browser table differs from native Python")
            elif observed != str(value):
                raise AssertionError("Browser table differs from native Python")

    with page.expect_download(timeout=120000) as data_download:
        page.locator("#tsv").click()
    data = data_download.value
    if data.suggested_filename != "gage data.txt":
        raise AssertionError("Unexpected data download filename")
    data_text = data.path().read_bytes().decode("utf-8").replace("\r\n", "\n")
    data.delete()
    if data_text != native["tsv"].replace("\r\n", "\n"):
        raise AssertionError("Downloaded data differs from native Python")

    with page.expect_download(timeout=120000) as report_download:
        page.locator("#html").click()
    report = report_download.value
    if report.suggested_filename != "Gage_Study_Summary_dashboard.html":
        raise AssertionError("Unexpected dashboard download filename")
    report_text = report.path().read_bytes().decode("utf-8")
    report.delete()
    expected_report, actual_report = html_summary(native["html"]), html_summary(report_text)
    if expected_report["text"] != actual_report["text"] or len(expected_report["images"]) != len(actual_report["images"]):
        raise AssertionError("Downloaded dashboard differs from native Python")
    if not check_dark_charts(report_text):
        raise AssertionError("Downloaded dashboard has no charts")


def compare_table(page, expected):
    columns = page.locator("#tables table").first.locator("thead th").all_inner_texts()
    if columns != expected["columns"]:
        raise AssertionError("Browser table columns differ from native Python")
    rows = page.locator("#tables table").first.locator("tbody tr").all()
    if len(rows) != len(expected["data"]):
        raise AssertionError("Browser table row count differs from native Python")
    for row, expected_row in zip(rows, expected["data"]):
        for observed, value in zip(row.locator("td").all_inner_texts(), expected_row):
            if isinstance(value, bool):
                matched = observed == str(value).lower()
            elif isinstance(value, numbers.Real) and math.isfinite(value):
                matched = math.isclose(float(observed), value, rel_tol=1e-6, abs_tol=1e-8)
            else:
                matched = observed == ("" if value is None else str(value))
            if not matched:
                raise AssertionError("Browser table differs from native Python")


def upload_synthetic(page, files):
    inputs = page.locator('#files input[type="file"]')
    if inputs.count() != len(files):
        raise AssertionError("Unexpected grouped input count")
    for index, (name, text) in enumerate(files):
        inputs.nth(index).set_input_files({"name": name, "mimeType": "text/plain", "buffer": text.encode("utf-8")})
    page.locator("#analyze").click()
    page.wait_for_function("document.querySelector('#status').textContent === 'Analysis complete.' || document.querySelector('#status').classList.contains('error')", timeout=120000)
    if page.locator("#status").inner_text() != "Analysis complete.":
        raise AssertionError("Browser study analysis failed")


def check_study_download(page, expected_archive):
    with page.expect_download(timeout=120000) as download_info:
        page.get_by_role("button", name="Download all reports (.zip)").click()
    download = download_info.value
    actual_archive = download.path().read_bytes()
    download.delete()
    expected, actual = archive_summary(expected_archive), archive_summary(actual_archive)
    if expected.keys() != actual.keys():
        raise AssertionError("Browser archive filenames differ from native Python")
    for name in expected:
        if expected[name]["text"] != actual[name]["text"] or len(expected[name]["images"]) != len(actual[name]["images"]):
            raise AssertionError("Browser archive report differs from native Python")
    with ZipFile(BytesIO(actual_archive)) as archive:
        chart_count = sum(check_dark_charts(archive.read(name).decode("utf-8")) for name in archive.namelist())
    if not chart_count:
        raise AssertionError("Downloaded archive has no charts")


def check_other_studies(page, base_url):
    examples = load_examples()
    page.goto(base_url + "/grr", wait_until="domcontentloaded", timeout=120000)
    page.wait_for_function("document.querySelector('#status').textContent === 'Ready' || document.querySelector('#status').classList.contains('error')", timeout=120000)
    if page.locator("#status").inner_text() != "Ready":
        raise AssertionError(f"Gage R&R browser runtime initialization failed: {page.locator('#status').inner_text()}")
    for mode in ("blocks", "periodic", "custom"):
        for distribution, order in (("single", "part-major"), ("single", "operator-major"), ("parts", "part-major"), ("operators", "part-major")):
            page.locator("#distribution").select_option(distribution)
            if distribution == "single":
                page.locator("#order").select_option(order)
            page.locator(f'input[name="format"][value="{mode}"]').check()
            if mode == "custom":
                page.locator("#start-marker").fill("REPORT")
                page.locator("#end-marker").fill("REPORT")
            files = list(examples("grr", mode, distribution, order).items())
            native = analyze_grr(files, mode, distribution, order, "REPORT", "REPORT")
            upload_synthetic(page, files)
            compare_table(page, grr_overview(native)["table"])
    check_study_download(page, base64.b64decode(grr_export(native, "zip")))

    page.goto(base_url + "/paired", wait_until="domcontentloaded", timeout=120000)
    page.wait_for_function("document.querySelector('#status').textContent === 'Ready' || document.querySelector('#status').classList.contains('error')", timeout=120000)
    if page.locator("#status").inner_text() != "Ready":
        raise AssertionError("Paired T browser runtime initialization failed")
    for mode in ("blocks", "periodic", "custom"):
        page.locator(f'input[name="format"][value="{mode}"]').check()
        if mode == "custom":
            page.locator("#start-marker").fill("REPORT")
            page.locator("#end-marker").fill("REPORT")
        files = list(examples("paired", mode).items())
        native = analyze_paired(files[0][1], files[1][1], mode, "REPORT", "REPORT", files[0][0], files[1][0])
        upload_synthetic(page, files)
        compare_table(page, paired_overview(native)["table"])
    check_study_download(page, base64.b64decode(paired_export(native, "zip")))


def check_unified_app(page, base_url):
    runtime_requests = []
    page.on("request", lambda request: runtime_requests.append(request.url) if urlsplit(request.url).path.endswith("/pyodide.mjs") else None)
    page.goto(base_url + "/app", wait_until="domcontentloaded", timeout=120000)
    page.wait_for_function("document.querySelector('#status')?.textContent === 'Ready' || document.querySelector('#status')?.classList.contains('error')", timeout=120000)
    if page.locator("#status").inner_text() != "Ready":
        raise AssertionError("Unified app initialization failed")
    check_case(page, synthetic_cases()[0], "synthetic_private_filename.txt")
    page.once("dialog", lambda dialog: dialog.dismiss())
    page.get_by_role("button", name="Gage R&R", exact=True).click()
    if page.get_by_role("button", name="Type 1", exact=True).get_attribute("aria-pressed") != "true":
        raise AssertionError("Canceling navigation did not preserve the current study")
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Gage R&R", exact=True).click()
    page.wait_for_function("document.querySelector('#status')?.textContent === 'Ready'", timeout=120000)
    examples = load_examples()
    files = list(examples("grr", "blocks", "single", "part-major").items())
    upload_synthetic(page, files)
    grr = grr_overview(analyze_grr(files, "blocks", "single"))
    compare_table(page, grr["table"])
    page.locator("#report").select_option(grr["characteristics"][0])
    check_charts(page, 1)
    if page.locator("#tables table").last.locator("tbody tr").count() != 90:
        raise AssertionError("Gage R&R data preview did not contain all 90 reports")
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Paired T", exact=True).click()
    page.wait_for_function("document.querySelector('#status')?.textContent === 'Ready'", timeout=120000)
    files = list(examples("paired", "blocks").items())
    upload_synthetic(page, files)
    native = analyze_paired(files[0][1], files[1][1], "blocks", name_a=files[0][0], name_b=files[1][0])
    paired = paired_overview(native)
    compare_table(page, paired["table"])
    page.locator("#report").select_option(paired["characteristics"][0])
    check_charts(page, 7)
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Type 1", exact=True).click()
    page.wait_for_function("document.querySelector('#status')?.textContent === 'Ready'", timeout=120000)
    if page.locator("#file").input_value() or page.locator("#results").is_visible():
        raise AssertionError("Switching studies did not clear the previous inputs and results")
    if len(runtime_requests) != 1:
        raise AssertionError(f"Unified app loaded Pyodide {len(runtime_requests)} times")


def check_charts(page, count):
    page.get_by_role("button", name="Show charts" if count == 1 else "Show full report").click(timeout=120000)
    page.wait_for_function("document.querySelector('#status').textContent === 'Charts ready.' || document.querySelector('#status').classList.contains('error')", timeout=120000)
    if page.locator("#status").inner_text() != "Charts ready.":
        raise AssertionError("Chart preview generation failed")
    page.wait_for_function("[...document.querySelectorAll('#charts img')].every(image => image.complete && image.naturalWidth > 0)", timeout=120000)
    if page.locator("#charts img").count() != count:
        raise AssertionError("Unexpected chart count")
    if count == 7:
        for name, heading in (("Summary Report", "Comments"), ("Diagnostic Report", "Severe outlier summary"), ("Report Card", "Input quality")):
            page.get_by_role("button", name=name, exact=True).click()
            if not page.locator("#charts .report-panel:visible").get_by_text(heading, exact=False).count():
                raise AssertionError(f"Missing paired report section: {name}")


def run_browser(executable, base_url, cases, filename, include_other_studies):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=str(executable), headless=True, args=["--disable-background-networking", "--no-first-run"])
        context = browser.new_context(accept_downloads=True)
        blocked = []
        requests = []
        sockets = []

        def route_request(route):
            url = route.request.url
            if url.startswith(base_url + "/") or url.startswith("blob:"):
                route.continue_()
            else:
                blocked.append(True)
                route.abort()

        context.route("**/*", route_request)
        page = context.new_page()
        page.on("request", lambda request: requests.append((request.method, urlsplit(request.url), request.post_data)))
        page.on("websocket", lambda socket: sockets.append(True))
        page.goto(base_url + "/type1", wait_until="domcontentloaded", timeout=120000)
        page.wait_for_function("document.querySelector('#status').textContent === 'Ready' || document.querySelector('#status').classList.contains('error')", timeout=120000)
        if page.locator("#status").inner_text() != "Ready":
            raise AssertionError("Browser runtime initialization failed")
        for case in cases:
            check_case(page, case, filename)
        if include_other_studies:
            check_other_studies(page, base_url)
            check_unified_app(page, base_url)
        allowed_paths = set(SOURCES) | {"/app", "/browser-app.js", "/type1", "/type1.js", "/grr", "/paired", "/msa.js", "/runtime.js", "/runtime-config.json"}
        allowed_paths.update(f"/runtime/{name}" for name in ProofHandler.runtime_allowlist)
        if blocked or sockets or any(method != "GET" or parsed.query or body or parsed.path not in allowed_paths for method, parsed, body in requests):
            raise AssertionError("Unexpected browser network activity")
        context.close()
        browser.close()


def main():
    parser = argparse.ArgumentParser(description="Compare Type 1 browser downloads with native Python locally.")
    parser.add_argument("--pyodide-dir", type=Path, required=True)
    parser.add_argument("--input", type=Path, help="Optional local Type 1 file; never sent to the server")
    parser.add_argument("--format", choices=("blocks", "periodic", "custom"), default="blocks")
    parser.add_argument("--start-marker", default="")
    parser.add_argument("--end-marker", default="")
    parser.add_argument("--browser", type=Path, action="append", help="Browser executable; repeat to test multiple browsers")
    parser.add_argument("--include-other-studies", action="store_true", help="Also test synthetic Gage R&R and Paired T workflows")
    arguments = parser.parse_args()
    directory = arguments.pyodide_dir.resolve(strict=True)
    ProofHandler.runtime_directory = directory
    ProofHandler.runtime_allowlist = validate_pyodide_runtime(directory)
    server = ThreadingHTTPServer(("127.0.0.1", 0), QuietProofHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    if arguments.input:
        cases = [(arguments.format, arguments.input.read_bytes().decode("utf-8", errors="replace"), arguments.start_marker, arguments.end_marker)]
        filename = arguments.input.name
    else:
        cases = synthetic_cases()
        filename = "synthetic_private_filename.txt"
    browsers = arguments.browser or [Path(os.environ["ProgramFiles"]) / "Google/Chrome/Application/chrome.exe", Path(os.environ["ProgramFiles(x86)"]) / "Microsoft/Edge/Application/msedge.exe"]
    try:
        for executable in browsers:
            run_browser(executable, f"http://127.0.0.1:{server.server_port}", cases, filename, arguments.include_other_studies)
            suffix = ", plus Gage R&R and Paired T" if arguments.include_other_studies else ""
            print(f"{executable.name}: {len(cases)} Type 1 comparison(s){suffix} passed")
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == "__main__":
    main()