---
title: "Review checklist"
doc_status: done
clarity_reviewed: "2026-11-09"
---

# Review checklist

## At a glance

| Field | Value |
|---|---|
| When to use it | Before you set `doc_status: done` on any blueprint or framework doc |
| Pass 1 | Automated checks: `make lint` (structure linter plus Vale) |
| Pass 2 | Clarity pass with the `humanizer` skill and the reader questions below |
| What blocks | Errors fail CI. Warnings don't |
| How to record it | Set `clarity_reviewed: "YYYY-MM-DD"` and `doc_status: done` in front matter |
| Rules it enforces | The [style guide](style-guide.md) |

## Automated checks

Run `make lint` from the repo root. Fix every error, and fix or justify every warning in the PR.

| Code | Severity | What it checks |
|---|---|---|
| FM001 | error | No front matter |
| FM002 | error | Front matter fails its schema, or its `type` does not belong in the folder it sits in |
| RF001 | error | Facet (autonomy ceiling or placement tier) missing or invalid |
| SC001 | error | Sections missing or out of order, or at a glance isn't first |
| SC002 | error | A section a catalog entry must fill is a stub |
| AG001 | error | A required at-a-glance row is missing |
| BG001 | error | A section or page is over budget |
| VT001 | error | Sources table missing |
| VT002 | error | Sources table header isn't canonical |
| VT004 | error | Source link is missing, does not resolve, leaves the repo, or points at the page itself |
| VT007 | error | Basis is not model card, research, Red Hat guidance, or industry use case |
| LK001 | error | Link target missing |
| LK002 | error | Link anchor missing |
| DG001 | error | Referenced diagram file missing |
| CR001 | error | `doc_status: done` without `clarity_reviewed`; CI blocks it |
| CR002 | error | `clarity_reviewed` on a non-blueprint doc is not an ISO date |
| ID001 | error | Two blueprints share an id |
| XR001 | error | `platform_blueprints` names a platform with no blueprint (full-repo runs) |
| IO001 | error | File cannot be read as UTF-8 text |
| `Blueprints.OTelTracing` | error | "OTel" used to mean tracing, for example `OTel collector` or `OTLP` |
| `Blueprints.Unevidenced` | error | Claim words with no evidence, for example `proven` or bare `validated` |
| `Blueprints.InlineStatus` | error | Product support label in a doc, for example `GA` or `Technology Preview`. Blueprints make no product support claims |
| `Google.*` | per rule level | Google developer style rules (v0.7.1), with overrides commented in `.vale.ini` |

## Clarity pass (humanizer)

1. Run the `humanizer` skill on the doc and accept or reject each change.
2. Answer the reader questions:
   - [ ] Can a reader state the decision and the next action after the at-a-glance table?
   - [ ] Is there any paragraph that could be a table?
   - [ ] Is there any sentence that adds no action?
   - [ ] Are AI-writing tells removed (inflated significance, rule-of-three padding, em-dash overuse, promotional tone)?
   - [ ] Is every component named by its role and the Red Hat product used, with the standard replaceable line, and no product support label?
   - [ ] Does every new page have a line in the `mkdocs.yml` `nav`, and does every link into `tools/` or `schemas/` use the GitHub URL, not a relative path?
3. Re-run `make lint` and fix anything the edits broke.
4. Set `clarity_reviewed: "YYYY-MM-DD"` and `doc_status: done` in front matter.

The linter fails with CR001 if a doc has `doc_status: done` and no `clarity_reviewed` date.

## Before external delivery

- Re-check each product name and version a blueprint cites against current Red Hat documentation.
- Confirm every blueprint carries the standard replaceable line and passes `make lint` with no errors.
