from __future__ import annotations

import importlib.util
import base64
import json
import math
import re
import sys
from html.parser import HTMLParser
from io import BytesIO, StringIO
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gage_tracer.calculations import calculate_gage_rr_by_characteristic
from gage_tracer.data_parser import transform_gage_rr_data, transform_raw_data
from gage_tracer.paired_ttest import (
    calculate_paired_ttest_diagnostics,
    calculate_paired_ttest_metrics,
    create_paired_ttest_html_zip,
    parse_paired_periodic_multicharacteristic_measurements,
)
from gage_tracer.presentation import build_type1_summary
from gage_tracer.visualization import create_dashboard, create_gage_rr_html_zip


def load_examples():
    path = ROOT / "src" / "app" / "components" / "input_examples.py"
    spec = importlib.util.spec_from_file_location("browser_poc_examples", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_input_examples


def serializable(value):
    if isinstance(value, pd.DataFrame):
        return serializable(value.to_dict(orient="split"))
    if isinstance(value, np.ndarray):
        return serializable(value.tolist())
    if isinstance(value, np.generic):
        return serializable(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {str(key): serializable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serializable(item) for item in value]
    return value


class ReportText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ignored = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.ignored += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.ignored -= 1

    def handle_data(self, data):
        if not self.ignored:
            self.parts.append(data)


def html_summary(html):
    parser = ReportText()
    parser.feed(html)
    text = " ".join(" ".join(parser.parts).split())
    text = re.sub(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", "<timestamp>", text)
    images = []
    for encoded in re.findall(r"data:image/png;base64,([A-Za-z0-9+/=]+)", html):
        image = base64.b64decode(encoded)
        with Image.open(BytesIO(image)) as decoded:
            nonblank = any(low != high for low, high in decoded.convert("RGB").getextrema())
        if not nonblank:
            raise ValueError("Report contains a blank chart")
        images.append({
            "png": image.startswith(b"\x89PNG\r\n\x1a\n"),
            "nonblank": nonblank,
            "width": int.from_bytes(image[16:20], "big"),
            "height": int.from_bytes(image[20:24], "big"),
        })
    return {"html": "<html" in html.lower(), "text": text, "images": images}


def archive_summary(data):
    with ZipFile(BytesIO(data)) as archive:
        return {name: html_summary(archive.read(name).decode("utf-8")) for name in archive.namelist()}


def run_browser_poc():
    examples = load_examples()

    type1_input = examples("type1", "periodic")
    type1_frame = transform_raw_data(StringIO(type1_input["type1.txt"]), input_format="periodic")
    type1_summary = build_type1_summary(type1_frame)
    type1_html = create_dashboard(type1_frame, type1_summary)

    grr_input = examples("grr", "periodic")
    grr_frame = transform_gage_rr_data(StringIO(grr_input["gage_rr.txt"]), input_format="continuous")
    grr_results = calculate_gage_rr_by_characteristic(grr_frame)
    grr_archive = create_gage_rr_html_zip(grr_frame, grr_results)

    paired_input = examples("paired", "periodic")
    paired = parse_paired_periodic_multicharacteristic_measurements(
        StringIO(paired_input["system_a.txt"]), StringIO(paired_input["system_b.txt"])
    )
    for analysis in paired.values():
        analysis["metrics"] = calculate_paired_ttest_metrics(analysis["system_a"], analysis["system_b"])
        analysis["diagnostics"] = calculate_paired_ttest_diagnostics(analysis["system_a"], analysis["system_b"])
    paired_archive = create_paired_ttest_html_zip(paired, "System A", "System B")

    return serializable({
        "type1": {
            "frame": type1_frame,
            "summary": type1_summary,
            "report": html_summary(type1_html),
        },
        "grr": {"frame": grr_frame, "results": grr_results, "archive": archive_summary(grr_archive)},
        "paired": {"analyses": paired, "archive": archive_summary(paired_archive)},
    })


if __name__ == "__main__":
    print(json.dumps(run_browser_poc(), allow_nan=False, sort_keys=True))