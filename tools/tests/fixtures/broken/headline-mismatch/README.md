---
id: "UC-DEMO-01"
type: "use-case"
title: "Fictional widget triage (test fixture)"
doc_status: "review"
domain: "demo"
flagship: true
otel_slots: ["llm", "safety"]
model_readiness: "M2"
evidence_level: "E2"
autonomy_ceiling: "recommend-with-approval"
placement_tier: ["regional"]
honest_one_liner: "M2 / E2 / recommend-with-approval. Fictional sample. Method defined, not yet run."
platform_blueprints: ["PB-99"]
agent_school: [301]
---

> Fictional sample for linter tests. Not a real blueprint.

# Fictional widget triage

## At a glance

| Field | Value |
|---|---|
| Honest one-liner | M2 / E2 / recommend-with-approval. Fictional sample. Method defined, not yet run. |
| Problem | Fictional widget alarms pile up faster than the demo team can sort them |
| Audience | Fictional demo NOC engineers |
| OTel slots | `llm`: triage summary; `safety`: abstain on unclear alarms |
| Model readiness and evidence | M2 / E2 |
| Placement tier | Regional |
| Agent-school courses | 301 |

## Problem and value

Fictional demo engineers sort widget alarms by hand.
This fictional use case drafts a triage label for each alarm, and an engineer approves it.
The target KPI is time to first triage, stated here as a target only.

## How it works

![Fictional triage flow](../../valid/use-case/diagrams/flow.svg)

1. A fictional widget alarm arrives at the demo gateway.
2. The `llm` slot drafts a triage label and a one-line reason.
3. The `safety` slot abstains when the alarm text is unclear.
4. The decision gate returns REVIEW, and an engineer approves or rejects the label.

## What you need

- [ ] Models: an `llm` slot with tool calling and a `safety` slot
- [ ] Platform blueprints: the fictional platform fixture (PB-99)
- [ ] Integrations: one fictional alarm feed through the demo gateway
- [ ] Tools and data: 20 fictional replay cases
- [ ] Data and adaptation: none for this fictional sample
- [ ] Prerequisites: the demo runtime on one regional node

## Governance

| Action | Gate outcome (LOOK/NOTIFY/REVIEW/ACT/STOP) | Approval | AI Act class |
|---|---|---|---|
| Draft a triage label | REVIEW | Demo NOC engineer | Limited risk (fictional) |
| Close an alarm | STOP | Not allowed | Not applicable (fictional) |

## Validation

The headline E-level is the minimum over load-bearing rows, as set out in [the minimum rule](../../../../../framework/definitions.md#headline-level-the-minimum-rule).

| # | Claim | Slot / component | Load-bearing | Vendor-reported | GSMA external | Our operator-task eval | E-level | Evidence | Result | Date | Release / revision |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Gate labels match expected labels on replay | `llm` | yes | — | — | replay set, 20 cases | E2 | [replay](../../evidence/replay.jsonl) | 2 of 3 shown cases pass | 2026-11-07 | fictional-model rev 0000000 |
| 2 | Safety slot abstains on unclear alarms | `safety` | yes | — | — | spec written | E1 | [spec](../../evidence/eval-spec.md) | — | 2026-11-07 | — |
| 3 | Model scores 0.9 on a vendor benchmark | `llm` | no | card says 0.9 | — | — | E0 | [card](https://example.invalid/card) | — | 2026-11-07 | — |

## Deploy and verify

No reference implementation exists for this fictional sample.
Run the fictional replay set to repeat row 1.

- Agent-school: course 301 (fictional link target)
- NVIDIA or Databricks equivalent: none for this fictional sample

## Limitations

- This fictional use case never closes an alarm on its own.
- The safety abstain method is defined but not yet run.
- The replay set holds 20 fictional cases only.
