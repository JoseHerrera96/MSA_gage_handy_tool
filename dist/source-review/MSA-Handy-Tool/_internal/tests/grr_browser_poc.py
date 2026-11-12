from __future__ import annotations

import base64
from io import StringIO

from gage_tracer.calculations import calculate_gage_rr_by_characteristic
from gage_tracer.data_parser import normalize_custom_report_markers, transform_gage_rr_data, transform_gage_rr_grouped_data
from gage_tracer.visualization import build_gage_rr_overview_dataframe, create_gage_rr_html_dashboard, create_gage_rr_html_overview, create_gage_rr_html_zip


def analyze_grr(files, report_format, distribution, report_order="part-major", start_marker="", end_marker=""):
    if report_format not in {"blocks", "periodic", "custom"}:
        raise ValueError("Invalid report format.")
    if distribution not in {"single", "parts", "operators"}:
        raise ValueError("Invalid report distribution.")
    sources = []
    for name, text in files:
        source = StringIO(text)
        if report_format == "custom":
            source = StringIO(normalize_custom_report_markers(source, start_marker, end_marker, source_name=name))
        sources.append((name, source))
    parser_format = {"blocks": "blocks", "periodic": "continuous", "custom": "blocks"}[report_format]
    if distribution == "single":
        if len(sources) != 1:
            raise ValueError("The single-file format requires exactly one file.")
        frame = transform_gage_rr_data(sources[0][1], output_file=None, input_format=parser_format, report_order=report_order)
    else:
        group_by = "part" if distribution == "parts" else "operator"
        frame = transform_gage_rr_grouped_data(sources, group_by=group_by, input_format=parser_format)
    return {"frame": frame, "results": calculate_gage_rr_by_characteristic(frame)}


def grr_overview(state):
    frame, results = state["frame"], state["results"]
    overview = build_gage_rr_overview_dataframe(results)
    counts = overview["Verdict"].value_counts()
    return {
        "table": overview.to_dict(orient="split"),
        "characteristics": list(results),
        "reports": int(frame["Report"].nunique()),
        "counts": {verdict: int(counts.get(verdict, 0)) for verdict in ("PASS", "MARGINAL", "FAIL")},
    }


def grr_detail(state, characteristic):
    result = state["results"][characteristic]
    return {
        "metrics": {key: result[key] for key in ("total_grr_pct", "ndc", "study_variation", "pooled_interaction", "interaction_p_value")},
        "tables": {key: result[key].reset_index().to_dict(orient="split") for key in ("anova_table_with_interaction", "anova_table", "variance_components", "gage_evaluation")},
        "data": state["frame"].to_dict(orient="split"),
    }


def grr_export(state, export_format, characteristic=""):
    frame, results = state["frame"], state["results"]
    if export_format == "data":
        return frame.to_csv(sep="\t", index=False)
    if export_format == "overview":
        return create_gage_rr_html_overview(frame, results)
    if export_format == "dashboard":
        return create_gage_rr_html_dashboard(frame[frame["Characteristic"] == characteristic], results[characteristic])
    if export_format == "zip":
        return base64.b64encode(create_gage_rr_html_zip(frame, results)).decode("ascii")
    raise ValueError("Invalid export format.")