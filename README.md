# Type 1 Gage Study — Automated Report Tool

Independent Python tool for processing raw measurement data, running a 
*Type 1 Gage Study* statistical analysis, and generating an interactive 
HTML dashboard.

> This repository is a **generic, standalone analysis utility**. It is **not 
> affiliated with, endorsed by, or released on behalf of any company or employer**.

---

## Quick Start

1. For the first time install dependencies:

```bash
pip install -r requirements.txt
```

2. Export **your own** measurement file from your measurement system using its standard text-output format.
3. Save that file in this folder as **`RAW DATA.txt`**.
4. Run the main script:

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

