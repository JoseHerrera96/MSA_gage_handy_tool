# Type 1 Gage Study — Automated Report Tool

Independent Python tool for processing raw **OGP SmartScope** measurement
data, running a *Type 1 Gage Study* statistical analysis, and generating
an interactive HTML dashboard.

> This repository is a **generic, standalone analysis utility** for
> educational use and professional demonstration. It is **not affiliated
> with, endorsed by, or released on behalf of any company or employer**.

---

## Quick Start

1. Export **your own** measurement file from an OGP SmartScope system using
   its standard text-output format.
2. Save that file in this folder as **`OGP DATA.txt`**.
3. Run the main script:

```bash
python Type_1_gage_handy_tool.py
```

4. The following files will be generated automatically:

| File                                | Description                    |
| ----------------------------------- | ------------------------------ |
| `gage data.txt`                     | Parsed measurement table (TSV) |
| `Gage_Study_Summary.txt`            | Plain-text summary report      |
| `Gage_Study_Summary_dashboard.html` | Interactive HTML dashboard     |

Open the `.html` file in any browser to review the results.

---

## Project Structure

```text
Data_tracer/
├── Type_1_gage_handy_tool.py          ← Entry point
├── OGP DATA.txt                       ← User-supplied OGP export
├── gage data.txt                      ← Generated parsed data
├── Gage_Study_Summary.txt             ← Generated text report
├── Gage_Study_Summary_dashboard.html  ← Generated dashboard
├── src/gage_tracer/
│   ├── data_parser.py                 ← OGP file parsing
│   ├── calculations.py                ← Statistical calculations
│   └── visualization.py               ← Charts and HTML output
├── scripts/                           ← Analysis utilities
├── tests/                             ← Verification tests
├── requirements.txt
└── README.md
```

---

## Data Flow

```text
RAW DATA.txt  ──→  data_parser  ──→  gage data.txt
                                          │
                                          ▼
                                    calculations  ──→  Gage_Study_Summary.txt
                                          │                        │
                                          ▼                        │
                                    visualization  ←───────────────┘
                                          │
                                          ▼
                                    dashboard.html
```

---

## Calculated Metrics

| Metric                  | Formula                                       |
| ----------------------- | --------------------------------------------- |
| **Cg**                  | (0.2 × Tolerance) / (6 × σ)                   |
| **Cgk**                 | (0.1 × Tolerance − \|Bias\|) / (3 × σ)       |
| **%Var(Repeatability)** | (6σ / Tolerance) × 100                        |
| **%Var(R + Bias)**      | (6 × √(σ² + Bias²) / Tolerance) × 100         |
| **Bias**                | Mean − Reference                              |
| **T-statistic**         | Bias / (σ / √n)                               |
| **P-Value**             | 2 × P(t > \|T\|), df = n − 1                 |

Acceptance criteria: **Cg ≥ 1.33 and Cgk ≥ 1.33**.

---

## Requirements

- Python 3.10+
- Install dependencies with `pip install -r requirements.txt`

---

## License

This project is released under the **MIT License**.
It is provided for **educational purposes** and **professional portfolio /
demonstration use**. See the `LICENSE` file for details.

