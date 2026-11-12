from __future__ import annotations

from io import BytesIO
from itertools import product
from zipfile import ZIP_DEFLATED, ZipFile

from gage_tracer.study_config import GRR_DESIGN


def _render_reports(reports: list[list[str]], report_format: str) -> str:
    if report_format == "blocks":
        return "\n".join(":BEGIN\n" + "\n".join(report) + "\n:END" for report in reports) + "\n"
    if report_format == "custom":
        return "\n".join("REPORT\n" + "\n".join(report) + "\nREPORT" for report in reports) + "\n"
    if report_format == "periodic":
        return "\n".join("\n".join(report) for report in reports) + "\n"
    raise ValueError(f"Unknown example format: {report_format}")


def build_input_examples(
    study: str,
    report_format: str,
    distribution: str = "single",
    report_order: str = "part-major",
) -> dict[str, str]:
    if study == "type1":
        reports = [
            [f'"Diameter"\t{10 + (index % 7 - 3) * 0.0007 + index * 0.00001:.5f}\t10.00000\t0.10000\t-0.10000']
            for index in range(20)
        ]
        return {"type1.txt": _render_reports(reports, report_format)}

    if study == "paired":
        examples = {}
        for system in ("a", "b"):
            reports = []
            for index in range(20):
                adjustment = 0.0004 if system == "b" else 0.0
                difference = ((index * 7) % 9 - 4) * 0.00015 if system == "b" else 0.0
                reports.append([
                    f"Diameter\t{10 + index * 0.002 + adjustment + difference:.5f}\t10.00000\t0.10000\t-0.10000",
                    f"Height\t{5 + index * 0.001 + adjustment - difference:.5f}",
                ])
            examples[f"system_{system}.txt"] = _render_reports(reports, report_format)
        return examples

    if study != "grr":
        raise ValueError(f"Unknown example study: {study}")
    if distribution not in {"single", "parts", "operators"}:
        raise ValueError(f"Unknown Gage R&R distribution: {distribution}")
    if report_order not in {"part-major", "operator-major"}:
        raise ValueError(f"Unknown Gage R&R report order: {report_order}")

    parts = range(1, GRR_DESIGN.parts + 1)
    operators = range(1, GRR_DESIGN.operators + 1)
    trials = range(1, GRR_DESIGN.trials_per_part + 1)

    def report(part: int, operator: int, trial: int) -> list[str]:
        value = 10 + part * 0.01 + operator * 0.0005 + (trial - 2) * 0.0003
        return [f"Diameter\t{value:.5f}\t10.00000\t0.20000\t-0.20000"]

    if distribution == "parts":
        return {
            f"part_{part:02}.txt": _render_reports(
                [report(part, operator, trial) for operator, trial in product(operators, trials)], report_format
            )
            for part in parts
        }
    if distribution == "operators":
        return {
            f"operator_{operator:02}.txt": _render_reports(
                [report(part, operator, trial) for part, trial in product(parts, trials)], report_format
            )
            for operator in operators
        }
    if report_order == "part-major":
        reports = [report(part, operator, trial) for part, operator, trial in product(parts, operators, trials)]
    else:
        reports = [report(part, operator, trial) for operator, part, trial in product(operators, parts, trials)]
    return {"gage_rr.txt": _render_reports(reports, report_format)}


def render_input_examples(
    st,
    study: str,
    report_format: str,
    distribution: str = "single",
    report_order: str = "part-major",
) -> None:
    state_key = f"{study}_examples_open"
    if st.button("View example", key=f"{study}_examples_button", icon=":material/description:"):
        st.session_state[state_key] = not st.session_state.get(state_key, False)
    if st.session_state.get(state_key, False) is not True:
        return

    examples = build_input_examples(study, report_format, distribution, report_order)
    st.caption("Synthetic example data. The preview shows the first 24 lines of the selected file.")
    if report_format == "custom":
        st.caption("For these files, enter REPORT as both the start and end marker.")
    if study == "grr" and distribution == "single":
        st.caption(f"Report sequence: {report_order}.")
    if study == "grr" and distribution != "single":
        st.caption("Upload each numbered file to the matching part or operator field.")
    names = list(examples)
    selected = names[0] if len(names) == 1 else st.selectbox(
        "Example file", names, key=f"{study}_example_file_{distribution}"
    )
    st.code("\n".join(examples[selected].splitlines()[:24]), language=None)
    st.download_button(
        "Download selected file", examples[selected], file_name=selected,
        mime="text/plain", key=f"{study}_example_download",
    )
    if len(examples) > 1:
        archive = BytesIO()
        with ZipFile(archive, "w", ZIP_DEFLATED) as zipped:
            for name, contents in examples.items():
                zipped.writestr(name, contents)
        st.download_button(
            "Download all examples (.zip)", archive.getvalue(),
            file_name=f"{study}_examples.zip", mime="application/zip",
            key=f"{study}_examples_zip",
        )