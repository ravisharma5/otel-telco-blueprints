---
type: "reference"
title: "Fictional reference page (test fixture)"
question: "How should the fictional gate route a demo request?"
doc_status: "review"
platform_blueprints: ["PB-99"]
otel_slots: ["decision"]
clarity_reviewed: "2026-11-07"
---

> Fictional sample for linter tests. Not a real page.

# Fictional reference page

## At a glance

| Field | Value |
|---|---|
| Question answered | How should the fictional gate route a demo request? |
| Answer | Score the request once, then route it by label |
| Audience | Fictional demo architects |
| OTel slots | `decision` |
| Platform blueprints | PB-99 |

## The question

You need one rule for routing fictional demo requests.
Without it, each demo team writes its own.

## The principle

Score each request once and act on the label.
Keep the scoring step separate from the action step.

## The design

| Label | Who acts | What runs |
|---|---|---|
| LOOK | Demo agent | A read-only demo query |
| STOP | Nobody | Nothing |

```mermaid
flowchart LR
  A[Demo request] --> B[Fictional gate]
  B --> C[Demo action]
```

1. The demo agent sends the request to the fictional gate.
2. The gate returns a label.
3. The demo agent acts on the label.

## Trade-offs and limits

| Trade-off | Why it matters |
|---|---|
| One extra call per request | Adds a small delay to each demo request |

## Used by

- Fictional widget triage
- Fictional demo copilot
