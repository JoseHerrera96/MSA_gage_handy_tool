# Paired T-Test Implementation Summary

## Overview

This document describes the design, architecture, and validation of the **Paired T-Test module**, which adds system-to-system comparison functionality to the existing Type 1 Gage Study tool without any breaking changes.

---

## Design Principles

### 1. **Zero Regression**: No changes to existing Type 1 Gage functionality
- All existing files remain untouched: `data_parser.py`, `calculations.py`, `visualization.py`, `Type_1_gage_handy_tool.py`
- New functionality is completely isolated in the new `paired_ttest.py` module
- Entry point: New standalone script `Paired_T_Test_tool.py` (parallel to the existing tool)

### 2. **Modular Architecture**: Consistent with existing design patterns
- **Parse**: `parse_paired_measurements()` reads two measurement files
- **Calculate**: `calculate_paired_ttest_metrics()` performs pure statistical computations
- **Visualize**: Chart rendering functions (`_render_*`) produce Base64 encoded PNGs
- **Generate**: `create_paired_ttest_dashboard()` creates self-contained HTML

### 3. **Portfolio Grade**: Clean, documented, no corporate identifiers
- Comprehensive docstrings (NumPy-style)
- Type hints throughout
- Proper error handling
- Educational comments explaining statistical formulas

### 4. **Minitab Parity**: Industry-standard statistical output
- Exact formulas for t-statistic, p-values, confidence intervals
- Uses `scipy.stats.t` for numerical accuracy
- Output matches Minitab's paired t-test standards

---

## File Structure

```
src/gage_tracer/
├── __init__.py                    [UPDATED: added paired_ttest exports]
├── data_parser.py                 [UNCHANGED]
├── calculations.py                [UNCHANGED]
├── visualization.py               [UNCHANGED]
└── paired_ttest.py                [NEW: Paired T-Test module]

Paired_T_Test_tool.py              [NEW: Entry point]
Type_1_gage_handy_tool.py          [UNCHANGED]

PAIRED_T_TEST_README.md            [NEW: User documentation]
PAIRED_T_TEST_IMPLEMENTATION_SUMMARY.md [This file]
test_paired_ttest_example.py       [NEW: Validation & example]
```

---

## Module: `src/gage_tracer/paired_ttest.py`

### Functions

#### 1. **`parse_paired_measurements(file_a, file_b)`**
- Reads two measurement files (one value per line)
- Returns: `(paired_df, system_a_list, system_b_list, differences_list)`
- Error handling: Validates file lengths match

#### 2. **`export_paired_data(paired_df, output_path)`**
- Writes paired measurements to TSV (similar to Type 1 parser output)
- Columns: `Observation`, `System_A`, `System_B`, `Difference`
- Precision: 8 decimal places

#### 3. **`calculate_paired_ttest_metrics(system_a, system_b)`**
- **Input**: Two lists of measurements (must have equal length)
- **Output**: Dictionary with all computed statistics
- **Calculations**:
  - Descriptive stats (N, Mean, StDev, SE Mean) for both systems and differences
  - T-test results (t-statistic, p-value, 95% CI)
  - Hypothesis strings for documentation
- **Error handling**: Validates minimum sample size (n ≥ 2)

#### 4. **`_render_histogram_differences(differences)`**
- Creates a histogram of differences with vertical line at zero
- Returns: Base64 encoded PNG string
- Chart styling: Consistent with existing visualization patterns

#### 4. **`_render_individual_value_plot(system_a, system_b)`**
- Creates scatter plot of System A vs System B
- Includes Y=X identity line for reference
- Returns: Base64 encoded PNG string

#### 6. **`_render_boxplot_differences(differences)`**
- Creates boxplot showing distribution of differences
- Includes median, quartiles, mean, and potential outliers
- Returns: Base64 encoded PNG string

#### 7. **`_render_stats_table_chart(metrics)`**
- Renders summary statistics as a visual table (chart image)
- Shows N, Mean, StDev, SE Mean for all three groups
- Returns: Base64 encoded PNG string

#### 8. **`create_paired_ttest_dashboard(paired_df, metrics, output_path)`**
- Generates self-contained HTML file with embedded Base64 charts
- Includes:
  - KPI cards (N, Mean Difference, T-statistic, P-value)
  - Hypothesis definitions
  - Test conclusion with plain-language interpretation
  - Four required visualizations (stats table, histogram, scatter, boxplot)
  - Detailed results table
- No external CSS/JS dependencies (everything embedded)

---

## Entry Point: `Paired_T_Test_tool.py`

### Workflow

1. **Check for input files**: `PAIRED DATA SYSTEM A.txt`, `PAIRED DATA SYSTEM B.txt`
2. **Parse measurements**: Call `parse_paired_measurements()`
3. **Export TSV**: Call `export_paired_data()` → `paired_data.txt`
4. **Calculate metrics**: Call `calculate_paired_ttest_metrics()`
5. **Generate text report**: `Paired_T_Test_Summary.txt` (Minitab-style format)
6. **Generate dashboard**: Call `create_paired_ttest_dashboard()` → `Paired_T_Test_Dashboard.html`

### Output Files

- **`paired_data.txt`**: Intermediate TSV with parsed measurements and differences
- **`Paired_T_Test_Summary.txt`**: Plain-text summary (hypotheses, statistics, conclusion)
- **`Paired_T_Test_Dashboard.html`**: Interactive HTML dashboard

---

## Statistical Formulas (Validation)

### Paired Differences
$$D_i = A_i - B_i$$

### Descriptive Statistics
- Mean difference: $\bar{D} = \frac{\sum D_i}{n}$
- Sample StDev: $s_D = \sqrt{\frac{\sum(D_i - \bar{D})^2}{n-1}}$ (Bessel's correction, ddof=1)
- Standard Error: $SE_D = \frac{s_D}{\sqrt{n}}$

### T-Statistic (Two-Sided Test, H₀: μ_D = 0)
$$t = \frac{\bar{D}}{SE_D}, \quad df = n - 1$$

### P-Value
$$p = 2 \cdot P(T_{df} > |t|) \quad \text{(using scipy.stats.t.sf)}$$

### 95% Confidence Interval
$$CI = \bar{D} \pm t_{\alpha/2, df} \cdot SE_D$$
where $t_{\alpha/2, df}$ is obtained from `scipy.stats.t.ppf(0.975, df)`.

---

## Validation & Test Case

### Ground Truth Example

**Input Data**:
- System A: `[10.1, 10.3, 10.2, 10.4, 10.0]`
- System B: `[10.0, 10.1, 10.3, 10.2, 10.1]`

**Manual Calculation**:
- Differences: `[0.1, 0.2, -0.1, 0.2, -0.1]`
- n = 5
- $\bar{D} = 0.06$
- $s_D \approx 0.1517$ (with ddof=1)
- $SE_D \approx 0.0678$
- $t \approx 0.884$ (df=4)
- p (two-sided) ≈ 0.433
- 95% CI ≈ [-0.128, 0.248]

**Validation Script**: `test_paired_ttest_example.py`
- Runs the full pipeline with known test data
- Validates calculated values against ground truth (within 1% tolerance)
- Confirms no crashes in chart rendering or dashboard generation
- Usage: `python test_paired_ttest_example.py`

---

## Chart Library & Styling

All charts use the same visual design as the Type 1 Gage dashboard:
- **Colors**:
  - Primary data: `#3A3A44` (dark gray)
  - Reference/success: `#1A8754` (green)
  - Attention/alert: `#FF6135` (brand orange)
  - Accent: `#FF420D` (accent orange)
- **Grid**: Light gray (`#E0E0E4`), low opacity for non-competing display
- **Backgrounds**: `#FEFEFE` (off-white)
- **DPI**: 140 for crisp rendering at web scale
- **Engine**: matplotlib with Agg backend (no display server required)

---

## Dependencies

The Paired T-Test module uses:
- `numpy` (array operations)
- `pandas` (DataFrame structure)
- `scipy.stats` (t-distribution, quantiles)
- `matplotlib` (chart rendering)
- Standard library: `math`, `base64`, `pathlib`

**No new dependencies** were added to `requirements.txt` — all are already required by the existing Type 1 Gage tool.

---

## Regression Testing

### Existing Type 1 Gage Study: Unchanged ✓
- `Type_1_gage_handy_tool.py` runs exactly as before
- No modifications to `data_parser.py`
- No modifications to `calculations.py`
- No modifications to `visualization.py`
- Import structure in `__init__.py` only adds new exports (backward compatible)

### Backward Compatibility ✓
```python
# Old imports still work
from gage_tracer import transform_raw_data, calculate_type1_metrics, create_dashboard

# New imports available
from gage_tracer import parse_paired_measurements, calculate_paired_ttest_metrics, create_paired_ttest_dashboard
```

---

## Usage Workflow

### For End Users

1. **Prepare files**:
   - `PAIRED DATA SYSTEM A.txt` (one measurement per line)
   - `PAIRED DATA SYSTEM B.txt` (one measurement per line, same count)

2. **Run analysis**:
   ```bash
   python Paired_T_Test_tool.py
   ```

3. **Review results**:
   - Open `Paired_T_Test_Dashboard.html` in browser

### For Developers

```python
from pathlib import Path
from gage_tracer.paired_ttest import (
    parse_paired_measurements,
    calculate_paired_ttest_metrics,
    create_paired_ttest_dashboard,
)

# Parse
paired_df, sys_a, sys_b, diffs = parse_paired_measurements(
    Path("data_a.txt"),
    Path("data_b.txt"),
)

# Analyze
metrics = calculate_paired_ttest_metrics(sys_a, sys_b)

# Generate report
create_paired_ttest_dashboard(paired_df, metrics, Path("report.html"))
```

---

## Summary

✓ **No regression**: Existing Type 1 Gage functionality completely untouched  
✓ **Minitab parity**: All formulas validated against industry standards  
✓ **Portfolio grade**: Clean code, comprehensive docs, no corporate identifiers  
✓ **Self-contained**: HTML dashboards with embedded Base64 images, no external deps  
✓ **Modular design**: Pure functions, testable, follows existing patterns  
✓ **Validated**: Ground truth test case included

The implementation is production-ready and follows all requested constraints.
