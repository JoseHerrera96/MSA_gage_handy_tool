# Type 1 Gage Study — Automated Report Tool

Internal quality tool for processing raw **OGP SmartScope** measurement
data, running a *Type 1 Gage Study* statistical analysis (with Minitab
parity), and generating an interactive HTML dashboard.

---

## Quick Start

1. Place your raw data file as **`OGP DATA.txt`** in this folder.
2. Run the main script:

```bash
python Type_1_gage_handy_tool.py
```

3. The following files will be generated automatically:

| File                                 | Description                          |
| ------------------------------------ | ------------------------------------ |
| `gage data.txt`                      | Parsed measurement table (TSV)       |
| `Gage_Study_Summary.txt`             | Minitab-style text summary           |
| `Gage_Study_Summary_dashboard.html`  | Interactive HTML dashboard           |

Open the `.html` file in any browser to view the visual report.

---

## Project Structure

```
Data_tracer/
├── Type_1_gage_handy_tool.py   ← Entry point (run this)
├── OGP DATA.txt                ← Raw OGP data (user input)
├── gage data.txt               ← Parsed data (generated)
├── Gage_Study_Summary.txt      ← Text report (generated)
├── Gage_Study_Summary_dashboard.html  ← Dashboard (generated)
│
├── src/gage_tracer/            ← Internal package (clean architecture)
│   ├── __init__.py
│   ├── data_parser.py          — OGP file parsing
│   ├── calculations.py         — Pure statistical functions
│   └── visualization.py        — Matplotlib charts + HTML
│
├── docs/                       ← Documentation and reference files
├── tests/                      ← Verification scripts
├── scripts/                    ← Analysis utilities
├── requirements.txt
└── README.md
```

---

## Data Flow

```
OGP DATA.txt  ──→  data_parser  ──→  gage data.txt
                                          │
                                          ▼
                                    calculations  ──→  Gage_Study_Summary.txt
                                          │
                                          ▼
                                    visualization ──→  dashboard.html
```

---

## Calculated Metrics 

| Metric                      | Formula                                            |
| --------------------------- | -------------------------------------------------- |
| **Cg**                      | (0.2 × Tolerance) / (6 × σ)                       |
| **Cgk**                     | (0.1 × Tolerance − \|Bias\|) / (3 × σ)            |
| **%Var(Repeatability)**     | (6σ / Tolerance) × 100                             |
| **%Var(R + Bias)**          | (6 × √(σ² + Bias²) / Tolerance) × 100             |
| **Bias**                    | Mean − Reference                                   |
| **T-statistic**             | Bias / (σ / √n)                                    |
| **P-Value**                 | 2 × P(t > \|T\|), df = n − 1                      |

Acceptance criteria: **Cg ≥ 1.33 AND Cgk ≥ 1.33**.

---

## Requirements

- Python 3.10+
- Dependencies: `pip install -r requirements.txt`
