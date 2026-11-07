---
name: ip-data-safety-review
description: 'Review intellectual property, licensing, sensitive data and secret exposure risks. Use before publishing, sharing, adding dependencies, auditing examples or references, propiedad intelectual, privacidad, licencias or datos confidenciales.'
---

# Intellectual Property and Data Safety Review

## Scope and Safety

Agree on the requested scope and intended audience before reviewing. Start with
repository metadata and tracked or staged paths; inspecting ignored private
content or Git history requires explicit authorization. Do not transmit files
or snippets to external services, install scanners, or perform network lookups
without authorization. Treat filenames and paths as potentially sensitive.

## Procedure

1. Inspect the project license, dependency declarations and relevant tracked
   files. Identify examples, references, assets, generated reports and code
   whose origin or permission to distribute is unclear; do not assume public,
   generated, ignored or example content is freely reusable.
2. For dependencies and assets, collect available provenance, versions,
   license evidence, attribution obligations and possible compatibility issues.
   Distinguish declared metadata from verified licensing and flag missing or
   ambiguous evidence for human review rather than deciding legal compliance.
3. Check exposure risks for confidential measurements, identifiers, customer
   metadata, credentials and tokens within the authorized scope. Prefer tools
   that suppress matching values; never print, quote, upload or persist secret
   values. Limit output to redacted locations and the type of concern.
4. Examine relevant Git tracking and ignore rules, including `data/examples/`,
   `data/private/`, `outputs/`, and references when in scope. An ignore rule
   does not remove a previously tracked file or erase Git history. Do not inspect
   history unless authorized; state clearly when it was not checked.
5. Report findings by severity with redacted locations, evidence, uncertainty,
   possible impact and recommended next action. Identify checks not performed
   and refer legal, licensing, privacy or security decisions to a qualified
   human when warranted. No findings is not a guarantee of safety or compliance.

## Boundaries

- Never delete, untrack, rewrite history, revoke credentials, or publish
  changes automatically. Obtain authorization before remediation; for suspected
  exposed credentials recommend secure rotation through the appropriate owner.
- Do not disclose private inputs in reports, screenshots, examples or chats.