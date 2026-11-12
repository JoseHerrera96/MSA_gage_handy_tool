from __future__ import annotations

import base64
from io import StringIO
from pathlib import Path

from gage_tracer.data_parser import paired_input_has_blocks
from gage_tracer.paired_ttest import (
    build_paired_ttest_overview_dataframe,
    calculate_paired_ttest_diagnostics,
    calculate_paired_ttest_metrics,
    create_paired_ttest_dashboard,
    create_paired_ttest_html_overview,
    create_paired_ttest_html_zip,
    paired_input_has_periodic_tabular_rows,
    parse_paired_custom_measurements,
    parse_paired_measurements,
    parse_paired_multicharacteristic_measurements,
    parse_paired_periodic_multicharacteristic_measurements,
    parse_paired_unstructured_measurements,
)


def analyze_paired(text_a, text_b, report_format, start_marker="", end_marker="", name_a="System A", name_b="System B"):
    if report_format not in {"blocks", "periodic", "custom"}:
        raise ValueError("Invalid report format.")
    system_a_name = Path(name_a).stem.replace("PAIRED DATA ", "")
    system_b_name = Path(name_b).stem.replace("PAIRED DATA ", "")
    source_a, source_b = StringIO(text_a), StringIO(text_b)
    numeric = False
    if report_format == "custom":
        analyses = parse_paired_custom_measurements(source_a, source_b, start_marker, end_marker)
        numeric = list(analyses) == ["__custom_numeric_series__"]
    else:
        blocks_a = paired_input_has_blocks(StringIO(text_a)) if report_format == "blocks" else False
        blocks_b = paired_input_has_blocks(StringIO(text_b)) if report_format == "blocks" else False
        if blocks_a != blocks_b:
            raise ValueError("Both systems must use the same paired input format.")
        if blocks_a:
            analyses = parse_paired_multicharacteristic_measurements(source_a, source_b)
        else:
            tabular_a = paired_input_has_periodic_tabular_rows(source_a)
            tabular_b = paired_input_has_periodic_tabular_rows(source_b)
            if tabular_a != tabular_b:
                raise ValueError("Both systems must use the same paired input format.")
            if tabular_a:
                analyses = parse_paired_periodic_multicharacteristic_measurements(source_a, source_b)
            else:
                parser = parse_paired_unstructured_measurements if report_format == "periodic" else parse_paired_measurements
                frame, values_a, values_b, differences = parser(source_a, source_b)
                analyses = {"__numeric_series__": {"paired_df": frame, "system_a": values_a, "system_b": values_b, "differences": differences}}
                numeric = True
    for analysis in analyses.values():
        analysis["metrics"] = calculate_paired_ttest_metrics(analysis["system_a"], analysis["system_b"])
        analysis["diagnostics"] = calculate_paired_ttest_diagnostics(
            analysis["system_a"], analysis["system_b"], system_a_name=system_a_name, system_b_name=system_b_name
        )
    return {"analyses": analyses, "numeric": numeric, "system_a_name": system_a_name, "system_b_name": system_b_name}


def paired_overview(state):
    analyses = state["analyses"]
    if state["numeric"]:
        return {"numeric": True, "characteristics": list(analyses)}
    overview = build_paired_ttest_overview_dataframe(analyses)
    return {
        "numeric": False,
        "characteristics": list(analyses),
        "table": overview.to_dict(orient="split"),
        "significant": int((overview["Holm P-Value"] < 0.05).sum()),
        "warnings": int(((overview["Outlier Status"] != "PASS") | (overview["Normality"] != "PASS")).sum()),
    }


def paired_detail(state, characteristic):
    analysis = state["analyses"][characteristic]
    metrics, diagnostics = analysis["metrics"], analysis["diagnostics"]
    return {
        "metrics": {key: metrics[key] for key in ("N", "Mean_D", "T_Value", "P_Value", "CI_Lower", "CI_Upper")},
        "diagnostics": {key: diagnostics[key] for key in ("Outlier_Count", "Outlier_Status", "Normality_Status", "Sample_Size_Status")},
        "table": analysis["paired_df"].head(10).to_dict(orient="split"),
    }


def paired_export(state, export_format, characteristic=""):
    analyses = state["analyses"]
    name_a, name_b = state["system_a_name"], state["system_b_name"]
    if export_format == "overview" and not state["numeric"]:
        return create_paired_ttest_html_overview(build_paired_ttest_overview_dataframe(analyses), name_a, name_b)
    if export_format == "zip" and not state["numeric"]:
        return base64.b64encode(create_paired_ttest_html_zip(analyses, name_a, name_b)).decode("ascii")
    analysis = analyses[characteristic]
    if export_format == "data":
        return analysis["paired_df"].to_csv(sep="\t", index=False)
    if export_format == "dashboard":
        return create_paired_ttest_dashboard(
            analysis["paired_df"], analysis["metrics"], system_a_name=name_a, system_b_name=name_b,
            characteristic_name=None if state["numeric"] else characteristic,
        )
    raise ValueError("Invalid export format.")