---
name: msa-validate-inputs
description: 'Validate MSA input formats and parsers. Use for Type 1, Gage R&R or Paired T uploads, report markers, periodic reports, custom delimiters, input equivalence, validacion de entradas or parser regressions.'
---

# MSA Input Validation

## Procedure

1. Identify the study, selected input mode, upload distribution, expected
   output, and any reported error. Inspect the corresponding view and parser in
   `src/app/views/`, `src/gage_tracer/data_parser.py`, or `paired_ttest.py`.
2. Check the actual contract for `BEGIN/END markers`, periodic inputs, or
   `Customized` markers. For custom inputs confirm whole-line matching, balanced
   blocks, same-marker behavior, and handling of content outside reports.
3. Check numeric finiteness, required columns, report completeness, consistent
   characteristics, and meaningful error locations. For Paired T verify both
   systems have compatible structures and correctly ordered observations.
   For GRR verify the selected file distribution and ordering.
4. Compare equivalent normalized results across relevant formats and exercise
   malformed, incomplete, duplicate, or ambiguous inputs. Reuse
   `tests/test_modular_domain.py`, `tests/test_fixture_data.py`, and existing
   examples rather than assuming a format from a filename.
5. Run the focused tests; for the example suite use the project interpreter
   with `python -m unittest discover -s tests -p test_fixture_data.py`. Expand
   coverage when a change affects multiple workflows. Report the checked modes,
   failures, and any unverified paths.

## Boundaries

- Never silently discard a measurement or reorder pairs to force a valid result.
  Follow the selected mode's documented handling of non-report content.
- Do not publish, upload, or quote private input data. Use suitable test
  fixtures or synthetic data, and distinguish a format review from a guarantee
  that real observations were collected or paired correctly.