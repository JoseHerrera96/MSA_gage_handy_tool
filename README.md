# MSA Handy Tool

MSA Handy Tool is a Windows application for Measurement System Analysis. It supports Type 1 Gage Study, crossed Gage R&R, and Paired T workflows, with input validation, visual results, and downloadable reports.

[Download MSA Handy Tool v1.0.0 beta](https://github.com/JoseHerrera96/MSA_gage_handy_tool/releases/download/v1.0.0-beta/MSA-Handy-Tool.zip)

## Download and Run

1. Download the ZIP file.
2. Extract the complete archive into a new folder.
3. Open `MSA-Handy-Tool.exe` while keeping the `_internal` folder beside it.

The packaged application requires 64 bit Windows 10 or 11 and a local installation of Microsoft Edge or Google Chrome. It does not require Python or an internet connection for its analysis workflows.

The executable starts a local server and opens the interface in an isolated browser window. Measurement files are processed locally in the browser. The server is not designed to receive uploaded measurements.

This is an unsigned beta build, so Windows may display a security warning. Results should be validated for the user's measurement process before operational use.

## What the Application Provides

* Type 1 capability and bias analysis
* Crossed Gage R&R analysis with ANOVA, variance components, interaction handling, and NDC
* Paired T analysis with diagnostics and support for multiple characteristics
* Input previews and validation errors before analysis
* Study overviews, metric tables, charts, and downloadable reports
* Example inputs generated from within the interface

The application accepts supported text files with BEGIN and END markers, periodic reports, or custom whole line markers. Gage R&R also supports one file, files grouped by part, and files grouped by operator. Paired T supports numeric series and paired characteristic blocks.

## Repository Overview

The downloadable ZIP contains one application: `MSA-Handy-Tool.exe`.

The repository also contains source code for developers. The browser server and the `msa` command line interface can be run from a development checkout, but they are not separate applications in the ZIP.

* `src/gage_tracer/` contains parsing, calculations, presentation, charts, and report generation.
* `src/web/` contains the local web interface, Pyodide adapters, and browser server.
* `desktop/` contains the Windows launcher and packaging script.
* `cli/` provides the command line entry points.
* `data/examples/` contains synthetic inputs.
* `tests/` contains numerical, browser, and desktop checks.

## Source Installation and CLI

Python 3.10 or later is required for source development. Install the package from the repository root:

```powershell
python -m pip install -e .
```

The `msa` command provides the same three studies:

```powershell
msa type1 --input path/to/type1.txt --output outputs/type1
msa grr --input path/to/gage_rr.txt --output outputs/gage_rr
msa paired --system-a path/to/system_a.txt --system-b path/to/system_b.txt --output outputs/paired
```

Use `msa type1`, `msa grr`, or `msa paired` with `--help` for all supported options. The CLI writes generated data and reports to the selected output directory.

## Data and Examples

Use **Download example** inside the application to obtain a synthetic file or file group that matches the selected study and input format. Source examples are stored in `data/examples/` and can be regenerated with:

```powershell
python data/examples/generate_input_modes.py
```

Do not commit production measurement data. Local private inputs belong in `data/private/`, and generated reports belong in `outputs/`; both locations are excluded from version control.

## Browser Development Server

Start the source interface from the repository root:

```powershell
python -m web.server
```

Open `http://127.0.0.1:8765/app` in a browser. This development mode loads Pyodide 0.27.7 from jsDelivr.

For an offline development run, provide an extracted [Pyodide 0.27.7 distribution](https://github.com/pyodide/pyodide/releases/tag/0.27.7) that contains `pyodide-lock.json`:

```powershell
python -m web.server --pyodide-dir "C:\path\to\pyodide"
```

## Testing

Run the Python suite with:

```powershell
python -m pytest -q
```

With Playwright installed and a local Pyodide directory available, the browser comparison script can exercise all three studies in Chrome and Edge:

```powershell
python tests/browser_type1_check.py --pyodide-dir "C:\path\to\pyodide" --include-other-studies
```

## Building the Windows Distribution

Install `pyinstaller==6.22.3` and `pystray==0.19.5`, then obtain the official Pyodide 0.27.7 core archive and package directory from the [Pyodide release](https://github.com/pyodide/pyodide/releases/tag/0.27.7).

```powershell
python desktop/build.py --core-archive "C:\path\to\pyodide-core-0.27.7.tar.bz2" --packages-dir "C:\path\to\pyodide-packages" --system-ucrt --output dist\current
```

The packaged application is written below the selected output directory. Before redistribution, run the packaged application check and review `desktop/THIRD_PARTY_NOTICES.md` together with the bundled licenses.

```powershell
python tests/check_desktop_executable.py dist\current\MSA-Handy-Tool\MSA-Handy-Tool.exe
```

## Supported Input Organization

The application validates each selected file and shows a preview before analysis.

* Type 1 accepts a single file containing marked reports, periodic reports, or custom report markers.
* Crossed Gage R&R accepts a balanced study in one file or in files grouped by part or operator. The selected collection order must match the upload configuration.
* Paired T accepts two corresponding files. The data may represent one measurement series or multiple named characteristics.

Use the generated examples in the application to confirm the expected structure before preparing a new dataset. Detailed workflow notes are available in [docs/workflows/gage_rr_README.md](docs/workflows/gage_rr_README.md), [docs/workflows/paired_ttest_README.md](docs/workflows/paired_ttest_README.md), and [docs/specifications/PLAN_OPCIONES_ENTRADA_DATOS.md](docs/specifications/PLAN_OPCIONES_ENTRADA_DATOS.md).

## License

The application is distributed under the [MIT License](LICENSE). See
`desktop/THIRD_PARTY_NOTICES.md` and the bundled licenses for third-party terms.


