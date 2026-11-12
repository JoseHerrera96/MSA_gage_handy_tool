---
name: msa-statistical-review
description: 'Review and validate MSA statistical calculations and interpretation. Use for Type 1 capability and bias, crossed Gage R&R ANOVA, paired t tests, uncertainty, Minitab comparison, formulas, revision estadistica or numerical regressions.'
---

# MSA Statistical Review

## Procedure

1. Define the study, metric, inputs, assumptions, and expected decision. Trace
   the calculation through `src/gage_tracer/calculations.py`,
   `paired_ttest.py`, `study_config.py`, and relevant presentation code.
2. Identify units, tolerance definitions, sample size, design and degrees of
   freedom, method choices, and edge cases. Verify formulas and thresholds
   against explicit, applicable references; distinguish repository policy from
   a general statistical requirement.
3. Run focused existing tests, including `tests/test_modular_domain.py`,
   `tests/test_paired_ttest_example.py`, or
   `tests/test_gage_rr_minitab_structure.py` as applicable. Add or propose
   independent, reproducible numerical comparisons when a formula changes.
4. When comparing external reports, establish that data, settings, methods,
   units, rounding and reference provenance match. Treat files under
   `docs/references/` as potentially useful examples, not automatic ground
   truth or permission to redistribute their contents.
5. Check numerical edge cases and the interpretation presented to users,
   including warnings and uncertainty. A nonsignificant paired t test is not
   evidence of equivalence. Report findings, expected versus observed values,
   tolerances, references, and limitations without claiming unsupported accuracy.

## Boundaries

- Do not change formulas, thresholds, or conclusions solely to match a visual
  reference. Explain incompatible methods and obtain a decision when needed.
- Do not expose private measurements or send them to external services.
  Statistical validation does not replace review by a qualified specialist.