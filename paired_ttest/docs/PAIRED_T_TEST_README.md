# Paired T-Test Analysis Tool

This tool performs a paired comparison study between two measurement systems (System A vs. System B). It follows Minitab standards for statistical rigor and reporting.

## Quick Start

### 1. Prepare Your Data

For the CLI, place both files in `paired_ttest/raw/`. Existing root-level input
files are still accepted as a legacy fallback. In Streamlit, upload both files.

- **`PAIRED DATA SYSTEM A.txt`**: One measurement per line (System A values)
- **`PAIRED DATA SYSTEM B.txt`**: One measurement per line (System B values)

**Single characteristic**: Each nonblank line must contain exactly one finite
numeric measurement. Both files must contain at least two values and have the
same number of values. Values are paired by line order; blank lines are ignored.

**Multiple characteristics**: Use matching `:BEGIN`/`:END` report blocks in
both files. Each block represents one paired observation. Inside a block, each
measurement row must have this tab-separated structure:

```text
<characteristic><TAB><finite numeric measurement>[<TAB><ignored metadata>...]
```

`<TAB>` means a literal tab character. The first field is the characteristic
label; the second is the measured value. Any later fields, such as GRR nominal
or tolerance values, are ignored. The optional `PATTERN:`, `DISPLAY:`, and
`UNIT:` metadata lines are allowed inside blocks. Do not add a column-header row
inside a block.

Every block must contain each characteristic exactly once, and all blocks in
both files must have the same exact characteristic labels. Rows are matched by
label, so their order within a block may differ. Blocks are matched by their
position in the files, so block 1 in System A must describe the same observation
as block 1 in System B. Both files need the same block count and at least two
blocks. Blank lines are allowed; measurement rows outside a block are not.

Example for each system (use literal tabs in place of `<TAB>`):

```text
:BEGIN
PATTERN: STUDY-01
DISPLAY: Paired sample
UNIT: mm
"C1"<TAB>0.3540
"C2"<TAB>10.2500
:END
:BEGIN
"C1"<TAB>0.3542
"C2"<TAB>10.2510
:END
```

**Example**:

`PAIRED DATA SYSTEM A.txt`:
```
10.1
10.3
10.2
10.4
10.0
```

`PAIRED DATA SYSTEM B.txt`:
```
10.0
10.1
10.3
10.2
10.1
```

### 2. Run the Analysis

```bash
python Paired_T_Test_tool.py
```

### 3. Review the Results

The tool generates three output files:

| File                             | Description                                      |
| -------------------------------- | ------------------------------------------------ |
| `paired_data.txt`                | Parsed measurements + computed differences (TSV) |
| `Paired_T_Test_Summary.txt`      | Plain-text statistical report (Minitab-style)    |
| `Paired_T_Test_Dashboard.html`   | Interactive HTML dashboard with embedded charts  |

Open the `.html` file in any web browser to view the dashboard.

For block-based multi-characteristic input, the study overview is shown first.
It reports raw and Holm-adjusted p-values, mean differences, confidence
intervals, standardized effects, and outlier, normality, and sample-size
diagnostics. Select a characteristic to open its usual detailed report. The
overview and all per-characteristic dashboards are available as HTML and as a
ZIP archive.

Holm-adjusted p-values account for testing multiple characteristics. A result
that is not statistically significant does not establish that the systems are
equivalent.

---

## Statistical Formulas

### Hypothesis Test

- **Null Hypothesis (H₀)**: μ_A = μ_B (equivalently, μ_Difference = 0)
- **Alternative Hypothesis (H₁)**: μ_A ≠ μ_B (two-sided test)
- **Significance Level (α)**: 0.05

### Computations

**Differences**: $D_i = A_i - B_i$

**Sample Statistics**:
- Mean difference: $\bar{D} = \frac{\sum D_i}{n}$
- Standard deviation: $s_D = \sqrt{\frac{\sum(D_i - \bar{D})^2}{n-1}}$ (Bessel's correction)
- Standard error: $SE_D = \frac{s_D}{\sqrt{n}}$

**T-Statistic** (df = n − 1):
$$t = \frac{\bar{D}}{SE_D}$$

**P-Value** (two-sided):
$$p = 2 \cdot P(T_{df} > |t|)$$

**95% Confidence Interval for μ_Difference**:
$$CI = \bar{D} \pm t_{\alpha/2, df} \cdot SE_D$$

---

## Output Description

### 1. `paired_data.txt` (Intermediate TSV)

Contains columns:
- `Observation`: Row number (1, 2, 3, ...)
- `System_A`: Measurement from System A
- `System_B`: Measurement from System B
- `Difference`: System A − System B

Format: Tab-separated, 8 decimal places.

### 2. `Paired_T_Test_Summary.txt` (Text Report)

Minitab-style formatted report with:
- Hypothesis definitions
- Descriptive statistics table (N, Mean, StDev, SE Mean) for each system and differences
- T-test results (T-statistic, DF, P-value)
- 95% confidence interval for the mean difference
- Statistical conclusion (Reject/Fail to Reject H₀)

### 3. `Paired_T_Test_Dashboard.html` (Interactive Dashboard)

A self-contained HTML file with:
- **Summary Statistics Table**: Visual representation of N, Mean, StDev, SE Mean
- **Histogram of Differences**: Shows the distribution of differences with a vertical reference line at zero
- **Individual Value Plot (Scatter)**: Plots System A vs. System B with a Y=X identity line
- **Boxplot of Differences**: Shows median, quartiles, and outliers of the differences
- **Key Performance Indicators**: Displays N, Mean Difference, T-statistic, P-value
- **Test Conclusion**: Plain-language interpretation of results at α = 0.05

All charts and images are embedded as Base64, making the file completely self-contained (no external dependencies).

---

## Decision Rules

### Interpretation of P-Value

- **If p < 0.05**: Reject H₀ → Systems are **significantly different**
- **If p ≥ 0.05**: Fail to reject H₀ → **No significant difference** detected

### Confidence Interval Interpretation

- If the **95% CI includes zero**: Suggests no significant difference (consistent with p ≥ 0.05)
- If the **95% CI excludes zero**: Suggests significant difference (consistent with p < 0.05)

---

## Advanced: Modular API

If you want to use the paired t-test functions directly in your Python code:

```python
from src.gage_tracer.paired_ttest import (
    parse_paired_measurements,
    calculate_paired_ttest_metrics,
    create_paired_ttest_dashboard,
)
from pathlib import Path

# Parse measurements
paired_df, system_a, system_b, diffs = parse_paired_measurements(
    Path("PAIRED DATA SYSTEM A.txt"),
    Path("PAIRED DATA SYSTEM B.txt"),
)

# Calculate metrics
metrics = calculate_paired_ttest_metrics(system_a, system_b)

# Generate dashboard
create_paired_ttest_dashboard(paired_df, metrics, Path("output.html"))
```

---

## Validation & Accuracy

The tool uses SciPy's `scipy.stats.t` for all probability calculations, ensuring:
- **T-distribution accuracy**: Critical values and p-values match industry standards (Minitab, SAS/JMP)
- **Confidence intervals**: Computed using the exact t critical value for the given degrees of freedom
- **Bessel's correction**: Sample standard deviations use n−1 (unbiased estimator)

All formulas have been validated against Minitab's paired t-test output.

---

## Requirements

- Python 3.10+
- Dependencies (from `requirements.txt`):
  - pandas>=2.0
  - numpy>=1.24
  - scipy>=1.10
  - matplotlib>=3.7

---

## License

This tool is provided as a portfolio / educational tool under the MIT License. It is independent and not affiliated with any company or proprietary system.
