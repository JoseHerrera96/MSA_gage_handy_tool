import pandas as pd

from gage_tracer.calculations import calculate_gage_rr_crossed


def test_gage_rr_variance_components_include_operator_row():
    records = []
    for part in range(1, 4):
        for operator in range(1, 4):
            for trial in range(1, 3):
                value = part + 0.2 * (operator - 2) + 0.05 * (trial - 1)
                records.append({
                    "Part": part,
                    "Operator": operator,
                    "Measurement": value,
                })

    df = pd.DataFrame(records)
    result = calculate_gage_rr_crossed(df, tolerance=10.0)
    sources = result["variance_components"]["Source"].tolist()

    assert "Operator" in sources
    assert "Repeatability" in sources
    assert "Reproducibility" in sources
    assert "Part-to-Part" in sources
    assert "Total Variation" in sources
