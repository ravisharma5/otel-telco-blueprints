---
id: "PB-99"
type: "platform"
title: "Fictional platform capability (test fixture)"
readiness_question: "What does it take to serve the fictional demo slot?"
doc_status: "review"
otel_slots: ["llm"]
placement_tier: ["regional"]
one_liner: "Serves the fictional demo slot on one regional node. Depends on the demo runtime."
top_decisions:
  - "Pick a fictional runtime"
  - "Pick a placement tier"
  - "Pick an accelerator operator"
agent_school: [201]
---

> Fictional sample for linter tests. Not a real blueprint.

# Fictional platform capability

## At a glance

| Field | Value |
|---|---|
| One-liner | Serves the fictional demo slot on one regional node. Depends on the demo runtime. |
| Question answered | What does it take to serve the fictional demo slot? |
| Audience | Fictional demo platform engineers |
| OTel slots | `llm` |
| Placement tier | Regional |
| Top 3 decisions | Pick a fictional runtime; pick a placement tier; pick an accelerator operator |
| Agent-school courses | 201 |

## The operator question

You need to know what it takes to serve the fictional demo slot on one regional node.
Until you answer it, the fictional use case has nowhere to run.

## Decisions you must make

| Decision | Options | Recommendation | Because |
|---|---|---|---|
| Pick a fictional runtime | Demo runtime; none | Demo runtime | Only fictional runtime in this sample |
| Pick a placement tier | Regional; core | Regional | Keeps fictional data on site |
| Pick an accelerator operator | Demo operator; none | Demo operator | The demo runtime needs it |

## Reference design

![Fictional reference design](diagrams/design.svg)

1. The demo operator enables the fictional accelerator.
2. The demo runtime loads the fictional model.
3. Callers send requests to the demo runtime endpoint.

- Config artifact: [acceptance spec](../../sources/acceptance-spec.md)

## Components

| Component role | Red Hat product used |
|---|---|
| Serves the fictional model | Demo runtime |
| Enables the fictional accelerator | Demo operator |

Any component can be replaced. The Red Hat products named here show one way to build this design.

## OTel slot guidance

| Slot | Candidate checkpoints | Notes |
|---|---|---|
| `llm` | Fictional model, pinned by revision | Fictional sizing only |

## Sources and acceptance

Each key claim links its source, as set out in [the Sources table](../../../../../framework/definitions.md#sources-table).

| # | Claim | Basis | Source |
|---|---|---|---|
| 1 | The fictional model fits on one demo accelerator | model card | [fictional card](https://example.invalid/card) |
| 2 | Demo runtime targets 200 ms at p95 | Red Hat guidance | [acceptance spec](../../sources/acceptance-spec.md) |

- Gate: p95 latency under 200 ms on 100 fictional requests.

## Operating model

| Activity | Responsible | Accountable | Consulted | Informed |
|---|---|---|---|---|
| Rollback | Demo platform engineer | Demo platform lead | Demo NOC | Demo users |

## Risks and limitations

| Risk | Likelihood | Mitigation |
|---|---|---|
| The fictional runtime drops requests under load | Medium | Add a second replica |

## Used by and next steps

- Used by: [fictional widget triage](../use-case/README.md)
- Agent-school: course 201 (fictional link target)
