---
name: msa-example-generator
description: 'Create or validate MSA input examples and fixtures. Use for example datasets, synthetic samples, report formats, grouped Gage R&R examples, test fixtures or generacion de ejemplos.'
---

# MSA Example Generator

## Procedure

1. Identify the study, input format, expected observations and desired invalid
   cases. Read the relevant parser, documented format, and existing tests before
   creating data. Use the existing example generator at
   `data/examples/generate_input_modes.py` only when it fits the requested task.
2. Prefer newly generated synthetic measurements or existing samples whose
   provenance and permission to reuse have been verified. Do not assume that
   data is synthetic or redistributable merely because it is in an examples or
   references directory. Never derive public examples from private inputs
   without explicit authorization and a suitable anonymization review.
3. Preserve the target contract: measurement columns and report boundaries,
   matched paired observations, and GRR part/operator/trial assignments. For
   equivalent modes, derive each representation from the same observations.
4. Validate examples with the actual parsers and compare expected counts and
   normalized results. Run `python -m unittest discover -s tests -p test_fixture_data.py`
   using the project interpreter and add focused tests for new cases.
5. Document which files to upload, required selection, markers, and ordering.
   Explain whether data is synthetic, adapted, or of unverified provenance.

## Boundaries

- The existing generator writes over its output paths. Inspect those paths and
  preserve user changes; use an isolated copy or obtain approval before any
  overwrite. Do not delete, publish, or upload data without authorization.
- Do not include secrets, identifying metadata, or unlicensed copied material.