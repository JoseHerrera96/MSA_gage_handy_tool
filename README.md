# Data Tracer — Integrated MSA Suite

A polished measurement system analysis (MSA) toolkit for Type 1 Gage Study and Paired T-Test workflows. This repository combines a unified Streamlit UI with standalone CLI entry points and decoupled core analytics logic.

## Repository Overview

- `streamlit_app.py` — Unified Streamlit entrypoint for interactive MSA workflows.
- `cli/Type_1_gage_handy_tool.py` — Standalone CLI for Type 1 Gage Study processing.
- `cli/Paired_T_Test_tool.py` — Standalone CLI for paired t-test comparison.
- `src/app.py` — Streamlit application module with the core UI implementation.
- `src/gage_tracer/` — Core library with parsing, calculation, and dashboard rendering.
- `gage_type1/` — Structured output directories for Type 1 results.
- `paired_ttest/` — Structured output directories for Paired T-Test results.
- `paired_ttest/docs/` — Technical documentation index and implementation guides.
- `tests/` — Validation tests for key analytical components.

## Clean Final Structure

```text
.
├── LICENSE
├── README.md
├── requirements.txt
├── streamlit_app.py
├── cli/
│   ├── Type_1_gage_handy_tool.py
│   └── Paired_T_Test_tool.py
├── src/
│   ├── app.py
│   └── gage_tracer/
│       ├── calculations.py
│       ├── data_parser.py
│       ├── paired_ttest.py
│       ├── visualization.py
│       └── __init__.py
├── gage_type1/
│   ├── raw/
│   ├── data/
│   ├── reports/
│   └── dashboards/
├── paired_ttest/
│   ├── raw/
│   ├── data/
│   ├── reports/
│   ├── dashboards/
│   └── docs/
└── tests/
```

## Getting Started

### Interactive UI

Launch the portfolio-grade Streamlit application:

```bash
streamlit run streamlit_app.py
```

or locally with the repo virtual environment:

```bash
.venv\Scripts\python.exe streamlit_app.py
```

The UI provides:
- Dark-themed MSA workflow selection
- In-memory file upload support
- Live metric panels
- Exportable HTML dashboards

### CLI Workflows

#### Type 1 Gage Study
Place the raw measurement input and run:

```bash
python cli/Type_1_gage_handy_tool.py
```

#### Paired T-Test
Place the paired measurement files and run:

```bash
python cli/Paired_T_Test_tool.py
```

## Notes

- This repo is intended for clean, production-like presentation.
- Temporary debug files have been removed.
- All documentation and artifacts are free of proprietary or corporate identifiers.
