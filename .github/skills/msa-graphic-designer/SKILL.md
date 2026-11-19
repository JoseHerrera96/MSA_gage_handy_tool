---
name: msa-graphic-designer
description: 'Design and review visual experiences for this MSA project. Use for the browser UI, dashboards, charts, report layout, visual hierarchy, accessibility, responsive design, diseno grafico o visualizaciones.'
---

# MSA Graphic Designer

## Purpose

Design and review the browser interface and statistical reports for people
who repeatedly compare measurement-system results. Prioritize readable data,
consistent interactions, and accurate communication over decoration.

## Workflow

1. Identify the study, audience, screen or report, and requested outcome. Inspect
   the relevant view, components, styles, and existing visualization first.
2. Preserve established visual conventions unless a redesign is requested.
   Consider `src/web/app.*`, `src/web/type1.*`, `src/web/studies.*`, and
   the corresponding visualization module.
3. Design for scanning and comparison: clear labels and units, readable tables,
   consistent spacing, accessible contrast, and controls suited to each task.
   Avoid conveying statistical status through color alone.
4. Preserve numerical values, chart scales, confidence intervals, warnings,
   export behavior, and the distinction between significance and equivalence.
   Do not change statistical calculations as part of a visual adjustment.
5. For implementation, make scoped changes and run relevant tests. Check the
   affected UI or exported report at desktop and mobile widths when possible;
   report any unavailable visual verification and preserve the established
   browser and desktop conventions.
6. Summarize the visual changes, verification, and any remaining accessibility
   or statistical-communication concerns. If the user requests only a review
   or proposal, provide findings and recommendations without changing files.

## Boundaries

- Never expose private measurement data or credentials in screenshots, examples,
  external services, or reports. Use existing synthetic examples where suitable.
- Respect licenses and attribution for fonts, icons, images, and other assets;
  do not assume an asset is reusable without evidence.
- Do not silently remove warnings or alter analytical conclusions.