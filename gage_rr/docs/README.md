# Crossed Gage R&R

This directory contains the documentation for the multireport crossed Gage R&R workflow.

## Input Contract

The fixed study design is 10 parts x 3 operators x 3 trials, so the input must represent exactly 90 reports. The parser accepts either of these layouts:

- **Explicit blocks:** 90 reports delimited by `:BEGIN` and `:END` (quoted or unquoted), with optional headers and footers.
- **Continuous stream:** one file containing 90 consecutive repetitions, with optional headers and footers. The parser detects the next repetition when the first characteristic tag appears again.

Every repetition must contain the same set of named measurement characteristics. Tags are preserved exactly: `C1_1`, `C1_2`, `C1`, and `LENGHT` are four independent characteristics. The report order defines the crossed design:

1. All trials for Part 1, Operator 1.
2. Continue through each part for Operator 1.
3. Repeat the same part and trial order for each additional operator.

Each named characteristic is analyzed independently and receives its own crossed Gage R&R report.

## Command Line

```powershell
python cli/Gage_RR_tool.py
```

The command writes a shared normalized TSV to `data/`, then creates one TXT, PNG, and HTML report per characteristic in `reports/` and `dashboards/`.

## Repository Convention

- `raw/` contains input files or synthetic fixtures.
- `templates/` contains reusable source templates, including the Excel design template.
- `data/`, `reports/`, and `dashboards/` contain reproducible generated output and are ignored by Git.