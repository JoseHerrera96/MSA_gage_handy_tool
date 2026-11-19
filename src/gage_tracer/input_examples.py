from __future__ import annotations

from itertools import product

from .study_config import GRR_DESIGN


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
