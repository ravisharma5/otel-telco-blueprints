---
id: "PB-99"
type: "platform"
title: "Fictional platform capability (test fixture)"
readiness_question: "What does it take to serve the fictional demo slot?"
doc_status: "review"
otel_slots: ["llm"]
model_readiness: "n/a"
evidence_level: "E1"
placement_tier: ["regional"]
honest_one_liner: "E1. Fictional sample. Acceptance method defined, not yet run."
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
| Honest one-liner | E1. Fictional sample. Acceptance method defined, not yet run. |
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

- Config artifact: [acceptance spec](evidence/eval-spec.md)

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

## Validation and acceptance

The headline E-level is the minimum over load-bearing rows, as set out in [the minimum rule](../../../../../framework/definitions.md#headline-level-the-minimum-rule).

| # | Claim | Slot / component | Load-bearing | Vendor-reported | GSMA external | Our operator-task eval | E-level | Evidence | Result | Date | Release / revision |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Demo runtime answers within 200 ms at p95 | demo-runtime | yes | — | — | spec written | E1 | [spec](evidence/eval-spec.md) | — | 2026-11-07 | — |
| 2 | Demo runtime handles 100 requests per second | demo-runtime | no | vendor says 100 rps | — | — | E0 | [notes](https://example.invalid/demo-runtime) | — | 2026-11-07 | — |

- Gate: p95 latency under 200 ms on 100 fictional requests.

## Operating model

| Activity | Responsible | Accountable | Consulted | Informed |
|---|---|---|---|---|
| Rollback | Demo platform engineer | Demo platform lead | Demo NOC | Demo users |

## Risks and limitations

| Risk | Likelihood | Mitigation |
|---|---|---|
| The acceptance method has not been run | High | Run it once a cluster exists |

## Used by and next steps

- Used by: [fictional widget triage](../use-case/README.md)
- Agent-school: course 201 (fictional link target)
