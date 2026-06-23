[33mcommit 9f6f3cb52809bf76b991250c83eac9d89f4a9ce3[m[33m ([m[1;36mHEAD[m[33m -> [m[1;32mNew_patterns_for_start_and_end[m[33m, [m[1;31morigin/main[m[33m, [m[1;31morigin/HEAD[m[33m, [m[1;32mmain[m[33m)[m
Author: Jose Herrera <josexd96@gmail.com>
Date:   Mon Apr 13 12:18:27 2026 -0600

    Revise README: quick start, wording, examples
    
    Simplify and modernize the README: remove vendor-specific references (OGP SmartScope) and tighten the introductory wording; add an explicit dependency install step (pip install -r requirements.txt) in Quick Start; generalize the example input filename from "OGP DATA.txt" to "RAW DATA.txt"; keep the run command for Type_1_gage_handy_tool.py; tidy blockquote formatting and remove the Project Structure section. These changes clarify setup and make the examples more generic and easier to follow.

[33mcommit dc4dccee5300d36743911c61a4fb60145460989f[m
Author: Jose Herrera <josexd96@gmail.com>
Date:   Mon Apr 13 10:38:22 2026 -0600

    Handle missing :END in parser; ignore dashboard
    
    Add Gage_Study_Summary_dashboard.html to .gitignore and make the OGP data parser more robust when files lack ":END" markers. Reset current_repetition after appending on ":END" lines, detect repeated dimension names as the start of a new cycle (append and reset), and flush the last repetition at EOF. These changes prevent data from being merged across cycles and ensure complete repetition groups are recorded even when terminators are missing.

[33mcommit 3a925dc617266dea840ae1b4277d78748b280a70[m
Author: Jose Herrera <josexd96@gmail.com>
Date:   Mon Apr 13 10:36:00 2026 -0600

    Delete Gage_Study_Summary.txt

[33mcommit 626d4e854e9628be654e51dc5c651be9aa77f027[m
Author: Jose Herrera <josexd96@gmail.com>
Date:   Mon Apr 13 10:35:50 2026 -0600

    Delete gage data.txt

[33mcommit 4d79207bbb69d5bf60e305f3198e105e0a04923c[m
Author: Jose Herrera <josexd96@gmail.com>
Date:   Mon Apr 13 10:35:40 2026 -0600

    Delete Gage_Study_Summary_dashboard.html

[33mcommit 8571d65b472269fade5d742effba0d82608ace1e[m
Author: Jose Herrera <josexd96@gmail.com>
Date:   Mon Apr 13 10:35:22 2026 -0600

    Delete RAW DATA.txt

[33mcommit 58fcc9dfb36529060af7122b1c139a64a2243327[m
Author: Jose Herrera <josexd96@gmail.com>
Date:   Thu Apr 9 09:39:09 2026 -0600

    Ignore generated data files in .gitignore
    
    Add entries to .gitignore for generated data files ("gage data.txt", "Gage_Study_Summary.txt", and "RAW DATA.txt") and a section header. Prevents accidental commits of generated/raw data files.

[33mcommit 82317fda69cfe7db716cfab59d5b0d6a2fba9669[m
Author: Jose Herrera <josexd96@gmail.com>
Date:   Wed Apr 8 15:26:14 2026 -0600

    sanitize repo for public release
    
    Prepare repository for public sharing by removing proprietary data
    and branding, and adding licensing.
    
    Changes:
    - Remove OGP DATA.txt (proprietary measurement data)
    - Remove Samtec_logo_png.png (corporate logo)
    - Rename input file reference from "OGP DATA.txt" to "RAW DATA.txt"
    - Update README with disclaimer, generic language, and MIT license note
    - Add LICENSE file
    - Clean up data flow diagram in README
    - Update dashboard and summary outputs to reflect new input filename

[33mcommit 9a3b16a4ec079c7fc2bc24459075fdc99fedb72c[m
Author: Jose Herrera <josexd96@gmail.com>
Date:   Wed Apr 8 14:21:56 2026 -0600

    feat: rebrand dashboard to Samtec corporate identity
    
    Apply Samtec visual identity to the HTML dashboard and matplotlib charts.
    
    Brand integration:
    - Embed Samtec logo (base-64) in header, capped at 40px height
    - Map brand palette to CSS custom properties: #FF6135 primary, #FF420D accent
    - Switch from dark theme to light theme (#FEFEFE page, #FFFFFF cards)
    - Use level-1 box shadows instead of heavy borders for depth
    
    Chart redesign (3-color rule):
    - #3A3A44 dark gray for measurement data lines
    - #FF6135 brand orange for tolerance limits (attention)
    - #B0B0BA light gray for histogram bars and context
    - Neutral grid (#E0E0E4) and spines (#D1D1D6) to avoid competing with data
    
    Accessibility:
    - All text colors meet WCAG 2.2 AA (4.5:1 minimum contrast ratio)
    - #010101 for KPI values and titles on light background
    - #1A8754/#D42B2B for accept/reject status (accessible green/red)
    
    Visual hierarchy (squint test):
    - Pass Rate KPI remains largest element (clamp 36-48px)
    - Logo stays subordinate at 40px max height

[33mcommit 277e7a66168b03c698d1eccaa6b6d86ddab918bd[m
Author: Jose Herrera <josexd96@gmail.com>
Date:   Wed Apr 8 13:57:09 2026 -0600

    refactor: restructure repo to clean architecture with src/ layout
    
    Complete repository restructure from flat single-file scripts into a
    modular clean architecture with strict separation of concerns.
    
    Architecture:
    - Create src/gage_tracer/ package with three SRP modules:
      - data_parser.py — OGP raw-data parsing and TSV export
      - calculations.py — pure statistical functions (Cg, Cgk, bias, %Var)
      - visualization.py — matplotlib charts and HTML dashboard builder
    - Refactor Type_1_gage_handy_tool.py as the sole entry-point orchestrator
    - Add src/gage_tracer/__init__.py with public API re-exports
    
    File organization:
    - Move Gage_report.py, data prep.py to legacy/ (originals kept as backup)
    - Move _debug.py, _debug2.py to tests/ as test_calculations.py, test_tolerances.py
    - Move _analyze_chart.py, _inspect_ref.py to scripts/
    - Move Gage type 1.htm, minitab_ref_chart1.png, gage data.mwx, OGP CAD to docs/
    - Keep user-facing files in root: OGP DATA.txt, gage data.txt, dashboard, summary
    
    Code improvements:
    - Use pathlib.Path for all file references (no more string concatenation)
    - Add type hints with typing.Any throughout
    - Make OGP parser accept any dimension name (gp_height, coplanarity, etc.)
      instead of hardcoding the "C" prefix
    - Fix dimension filtering in orchestrator to use exclude-list instead of
      prefix matching
    - Rewrite all comments and docstrings in English for dev readability
    
    Infrastructure:
    - Add .gitignore (Python, IDE, generated outputs)
    - Add requirements.txt (pandas, numpy, scipy, matplotlib, watchdog)
    - Add README.md with quick start, project structure, data flow, and metrics

[33mcommit c01fb59e380551dcc28f3fc96265b7a8753d393b[m
Author: Jose Herrera <josexd96@gmail.com>
Date:   Wed Apr 8 12:59:53 2026 -0600

    Revamp dashboard UI and update summary timestamp
    
    Refactors the Type 1 Gage Study dashboard (Gage_Study_Summary_dashboard.html): replaces old styles with a new design-token based CSS, reorganizes header/KPI row, adds a responsive summary table and progressive-disclosure detail cards (including an embedded chart), and tweaks copy (title) and timestamps. Also updates the summary text timestamp in Gage_Study_Summary.txt. Gage_report.py and its bytecode were touched as part of this change (compiled cache updated). Improves layout, readability and responsiveness of the report dashboard.

[33mcommit 42e9479d21b93cce7ccf70bd4ea05f0f852e0ab7[m
Author: Jose Herrera <josexd96@gmail.com>
Date:   Wed Apr 8 12:25:59 2026 -0600

    Update Type 1 gage report and dashboard
    
     added Reference, Bias, StdDev, Tol, Cg/Cgk, %Var columns and update timestamps; refresh dashboard HTML timestamp and embedded report content; rename generate_report_once.py to Type_1_gage_handy_tool.py

[33mcommit 7b2211441c9bb46670399890945e48c2cc94b5f9[m
Author: Jose Herrera <josexd96@gmail.com>
Date:   Thu Mar 26 22:51:57 2026 -0600

    release

[33mcommit 579dc43742f5a1dd0c8ff0e0128af5a774167d7f[m
Author: Jose Herrera <josexd96@gmail.com>
Date:   Thu Mar 26 22:43:13 2026 -0600

    Initial commit
