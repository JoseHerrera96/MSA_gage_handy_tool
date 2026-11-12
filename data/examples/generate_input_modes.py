"""Generate upload examples from the existing sample measurement files."""

from pathlib import Path


EXAMPLES = Path(__file__).resolve().parent
OUTPUT = EXAMPLES / "input_modes"
FORMATS = ("blocks", "periodic", "custom")


def read_reports(path: Path) -> list[list[str]]:
    reports = []
    current = None
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        marker = line.split("\t", 1)[0].strip().strip('"').upper()
        if marker == ":BEGIN":
            if current is not None:
                raise ValueError(f"Nested report in {path}")
            current = []
        elif marker == ":END":
            if current is None:
                raise ValueError(f"Unmatched report end in {path}")
            reports.append(current)
            current = None
        elif current is not None:
            fields = line.split("\t")
            if len(fields) >= 5:
                try:
                    float(fields[1])
                except ValueError:
                    continue
                current.append("\t".join(fields[:5]))
    return reports


def render_reports(reports: list[list[str]], report_format: str) -> str:
    if report_format == "blocks":
        return "\n".join(":BEGIN\n" + "\n".join(rows) + "\n:END" for rows in reports) + "\n"
    if report_format == "custom":
        return "\n".join("REPORT\n" + "\n".join(rows) + "\nREPORT" for rows in reports) + "\n"
    return "\n".join("\n".join(rows) for rows in reports) + "\n"


def write_example(relative_path: str, content: str) -> None:
    destination = OUTPUT / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8", newline="\n")


def main() -> None:
    type1_reports = read_reports(EXAMPLES / "type1" / "RAW DATA.txt")[:20]
    grr_reports = read_reports(EXAMPLES / "gage_rr" / "GAGE RR DATA.txt")
    if len(type1_reports) != 20 or len(grr_reports) != 90:
        raise ValueError("Expected at least 20 complete Type 1 reports and exactly 90 GRR reports.")
    if not all(report for report in type1_reports + grr_reports):
        raise ValueError("A source report has no measurement rows.")

    for report_format in FORMATS:
        write_example(f"type1/{report_format}.txt", render_reports(type1_reports, report_format))
        write_example(f"gage_rr/{report_format}/single.txt", render_reports(grr_reports, report_format))
        for part in range(10):
            write_example(
                f"gage_rr/{report_format}/parts/part_{part + 1:02}.txt",
                render_reports(grr_reports[part * 9:(part + 1) * 9], report_format),
            )
        for operator in range(3):
            operator_reports = [
                grr_reports[part * 9 + operator * 3 + trial]
                for part in range(10)
                for trial in range(3)
            ]
            write_example(
                f"gage_rr/{report_format}/operators/operator_{operator + 1}.txt",
                render_reports(operator_reports, report_format),
            )

    for system in ("A", "B"):
        values = (EXAMPLES / "paired" / f"PAIRED DATA SYSTEM {system}.txt").read_text(
            encoding="utf-8-sig"
        ).splitlines()[:20]
        if len(values) != 20:
            raise ValueError(f"Expected 20 measurements for System {system}.")
        numeric_reports = [[value] for value in values]
        write_example(f"paired/blocks/system_{system.lower()}.txt", "\n".join(values) + "\n")
        write_example(
            f"paired/periodic/system_{system.lower()}.txt",
            "System measurements\n" + render_reports(numeric_reports, "periodic"),
        )
        write_example(
            f"paired/custom/system_{system.lower()}.txt",
            render_reports(numeric_reports, "custom"),
        )
        source = EXAMPLES / "paired" / f"OGP DATA _{system if system == 'A' else 'b'}.txt"
        tabular_reports = [
            ["\t".join(row.split("\t")[:2]) for row in report]
            for report in read_reports(source)
        ]
        if len(tabular_reports) < 2 or not all(tabular_reports):
            raise ValueError(f"Expected multiple nonempty paired reports for System {system}.")
        for report_format in ("blocks", "custom"):
            write_example(
                f"paired/{report_format}/multicharacteristic_{system.lower()}.txt",
                render_reports(tabular_reports, report_format),
            )


if __name__ == "__main__":
    main()