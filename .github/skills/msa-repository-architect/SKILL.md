---
name: msa-repository-architect
description: 'Analyze and improve architecture for this MSA repository. Use for module boundaries, dependencies, refactoring plans, technical design, API contracts, arquitectura, estructura del repositorio or architectural reviews.'
---

# MSA Repository Architect

## Purpose

Assess and evolve the repository architecture without breaking established
measurement-study behavior. Ground recommendations in current code, tests,
and the user's requested scope.

## Workflow

1. Identify the requested outcome, affected workflows, constraints, and evidence
   needed. Inspect the owning modules and relevant tests before proposing a
   structural change. Ask focused questions only when a decision is blocked.
2. Trace the relevant data flow: Streamlit views in `src/app/` and CLI entry
   points in `cli/` coordinate parsers, calculations, presentation, and report
   generation in `src/gage_tracer/`. Confirm actual dependencies in the code.
3. Evaluate responsibilities, public contracts, coupling, failure handling,
   compatibility, testability, and data privacy. Distinguish observed facts
   from assumptions and avoid recommending abstractions without a clear benefit.
4. Compare practical options, including the smallest viable change. Explain
   tradeoffs, migration or compatibility risks, and the tests needed to validate
   each recommendation. Preserve the separation between UI and domain logic.
5. For approved implementation work, keep changes incremental, preserve existing
   CLI and UI contracts unless explicitly changed, and run tests appropriate to
   the affected behavior. Do not alter statistical formulas or study policies
   without explicit scope and validated reference evidence.
6. For a review or design request, present findings and risks first with file
   references, followed by a prioritized recommendation and verification plan.
   Do not edit files when the user asks only for analysis or a proposal.

## Boundaries

- Do not reorganize modules, add dependencies, or migrate interfaces solely for
  stylistic consistency. Explain scope changes and obtain approval when needed.
- Keep private inputs and generated outputs out of version control and external
  services; check provenance and licenses before proposing new dependencies.
- Do not claim statistical, security, or license compliance without evidence;
  identify remaining uncertainty and required specialist review.