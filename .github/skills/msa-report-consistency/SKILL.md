---
name: msa-report-consistency
description: 'Check consistency of MSA results across Streamlit, CLI, text reports and HTML dashboards. Use for report discrepancies, exports, visualizations, warnings, metric formatting or consistencia de informes.'
---

# MSA Report Consistency

## Procedure

1. Identify the study, input, and surfaces being compared. Trace shared
   calculations through `src/gage_tracer/presentation.py`, visualization
   modules, the relevant Streamlit view, and the CLI entry point.
2. Run equivalent inputs and settings through the relevant paths. Compare
   normalized observations, metrics, units, thresholds, verdicts, warnings,
   chart labels, and available exports. Account for intentional differences
   such as display precision or supported input modes; do not equate different
   input data or study settings.
3. Verify that formatted values correspond to the same underlying results and
   that diagnostic limitations remain visible. In Paired T, a nonsignificant
   result is not proof of equivalence; check the same meaning survives export.
4. Use nearby tests such as `tests/test_cli.py`,
   `tests/test_modular_domain.py`, `tests/test_paired_ttest_example.py`, and
   `tests/test_gage_rr_minitab_structure.py`. Inspect generated HTML and UI only
   when relevant, using appropriate synthetic fixtures.
5. Report discrepancies with source locations, observed and expected behavior,
   verification performed, and any surfaces not checked. Never silently adjust
   domain calculations merely to make reports appear consistent.

## Privacy

Do not upload or reproduce private measurement data in screenshots, generated
artifacts, or external tools. Respect the user's existing output files.