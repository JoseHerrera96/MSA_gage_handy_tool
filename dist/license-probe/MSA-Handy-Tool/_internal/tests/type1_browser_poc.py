from __future__ import annotations

import json
import math
from io import StringIO

import numpy as np
import pandas as pd

from gage_tracer.data_parser import normalize_custom_report_markers, transform_raw_data
from gage_tracer.presentation import build_type1_summary, format_type1_dataframe, metric_status
from gage_tracer.study_config import TYPE1_CAPABILITY_THRESHOLD
from gage_tracer.visualization import create_dashboard


def analyze_type1(text: str, report_format: str, start_marker: str = "", end_marker: str = "", source_name: str = "Input") -> dict:
    if report_format not in {"blocks", "periodic", "custom"}:
        raise ValueError("Invalid report format.")
    source = StringIO(text)
    if report_format == "custom":
        source = StringIO(normalize_custom_report_markers(source, start_marker, end_marker, source_name=source_name))
        parser_format = "blocks"
    else:
        parser_format = report_format
    frame = transform_raw_data(source, output_file=None, input_format=parser_format)
    summary = build_type1_summary(frame)
    if not summary:
        raise ValueError("No valid measurement dimensions were found in the uploaded file.")

    summary_frame = pd.DataFrame(summary)
    mean_cg = summary_frame["Cg"].mean()
    mean_cgk = summary_frame["Cgk"].mean()
    accepted = int((summary_frame["Status"] == "ACCEPT").sum())
    total = len(summary_frame)
    return {
        "summary": summary,
        "table": format_type1_dataframe(summary_frame).reset_index().to_dict(orient="split"),
        "observations": sorted(int(count) for count in summary_frame["Observations"].unique()),
        "metrics": {
            "dimensions": total,
            "mean_cg": f"{mean_cg:.3f}",
            "mean_cgk": f"{mean_cgk:.3f}",
            "cg_status": metric_status(mean_cg, TYPE1_CAPABILITY_THRESHOLD),
            "cgk_status": metric_status(mean_cgk, TYPE1_CAPABILITY_THRESHOLD),
            "pass_rate": f"{accepted}/{total} ({accepted * 100 / total:.0f}%)",
            "threshold": TYPE1_CAPABILITY_THRESHOLD,
        },
        "tsv": frame.to_csv(sep="\t", index=False),
        "html": create_dashboard(frame, summary, output_path=None),
    }


def browser_json(value) -> str:
    def normalize(item):
        if isinstance(item, np.generic):
            return normalize(item.item())
        if isinstance(item, float) and not math.isfinite(item):
            return str(item)
        if isinstance(item, dict):
            return {key: normalize(element) for key, element in item.items()}
        if isinstance(item, (list, tuple)):
            return [normalize(element) for element in item]
        return item

    return json.dumps(normalize(value), allow_nan=False)