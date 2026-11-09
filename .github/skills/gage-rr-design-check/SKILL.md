---
name: gage-rr-design-check
description: 'Validate crossed Gage R&R study designs and report assignments. Use for 90 reports, parts, operators, trials, grouped uploads, report order, diseno GRR or balanced-design regressions.'
---

# Gage R&R Design Check

## Procedure

1. Inspect `GRR_DESIGN` in `src/gage_tracer/study_config.py` and the current
   parsing and assignment paths in `data_parser.py` and `src/app/views/grr_view.py`.
   Do not assume the fixed design cannot change in a future version.
2. For the current design, verify 10 parts, 3 operators, 3 trials per
   part-operator pair, and 90 reports. Check characteristic completeness and
   uniqueness for every report, as well as consistent specifications when
   required by the actual parser and analysis.
3. Verify the selected distribution: one file with 90 reports, 10 part files
   with 9 reports each, or 3 operator files with 30 reports each. For untagged
   single files honor the chosen part-major or operator-major sequence. Check
   grouped files use their documented internal ordering.
4. Compare normalized part, operator, trial, characteristic and measurement
   assignments across equivalent datasets; do not require report numbers to
   match across distributions when their enumeration differs. Test invalid
   counts, missing or duplicate characteristics, incompatible formats, and
   labels or ordering conflicts where supported.
5. Run relevant cases in `tests/test_modular_domain.py` and
   `tests/test_fixture_data.py`, then report the design, modes checked,
   discrepancies, and limitations. Do not silently infer physical identity or
   collection order from values alone.