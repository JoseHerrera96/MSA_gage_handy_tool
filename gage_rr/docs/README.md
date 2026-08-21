# Crossed Gage R&R

This directory contains the documentation for the multireport crossed Gage R&R workflow.

## Input Contract

The raw file uses `:BEGIN` and `:END` to delimit reports. Every report must contain the same set of named measurement characteristics. The report order defines the crossed design:

1. All trials for Part 1, Operator 1.
2. Continue through each part for Operator 1.
3. Repeat the same part and trial order for each additional operator.

The report count must satisfy:

$$\text{reports} = \text{operators} \times \text{parts} \times \text{trials}$$

Each named characteristic is analyzed independently. For example, 63 reports with three characteristics and a $3 \times 7 \times 3$ design produce three independent crossed Gage R&R reports.

## Command Line

```powershell
python cli/Gage_RR_tool.py --operators 3 --trials 3
```

The command writes a shared normalized TSV to `data/`, then creates one TXT, PNG, and HTML report per characteristic in `reports/` and `dashboards/`.

## Repository Convention

- `raw/` contains input files or synthetic fixtures.
- `templates/` contains reusable source templates, including the Excel design template.
- `data/`, `reports/`, and `dashboards/` contain reproducible generated output and are ignored by Git.