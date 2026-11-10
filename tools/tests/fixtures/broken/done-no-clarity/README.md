---
id: "UC-DEMO-01"
type: "use-case"
title: "Fictional widget triage (test fixture)"
doc_status: "done"
domain: "demo"
flagship: true
otel_slots: ["llm", "safety"]
autonomy_ceiling: "recommend-with-approval"
placement_tier: ["regional"]
one_liner: "Drafts fictional triage labels with human approval. Needs a tool-calling LLM slot."
platform_blueprints: ["PB-99"]
agent_school: [301]
---

> Fictional sample for linter tests. Not a real blueprint.

# Fictional widget triage

## At a glance

| Field | Value |
|---|---|
| One-liner | Drafts fictional triage labels with human approval. Needs a tool-calling LLM slot. |
| Problem | Fictional widget alarms pile up faster than the demo team can sort them |
| Audience | Fictional demo NOC engineers |
| OTel slots | `llm`: triage summary; `safety`: abstain on unclear alarms |
| Autonomy ceiling | Recommend with approval |
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

## Sources

Each key claim links its source, as set out in [the Sources table](../../../../../framework/definitions.md#sources-table).

| # | Claim | Basis | Source |
|---|---|---|---|
| 1 | The fictional model supports tool calling | model card | [fictional card](https://example.invalid/card) |
| 2 | Demo teams triage widget alarms with a replay set | industry use case | [replay set](../../sources/replay.jsonl) |
| 3 | An abstain step lowers wrong triage labels | research | [eval spec](../../sources/eval-spec.md) |

## Deploy and verify

No reference implementation exists for this fictional sample.
Run the fictional replay set in row 2 to check the gate labels.

- Agent-school: course 301 (fictional link target)
- NVIDIA or Databricks equivalent: none for this fictional sample

## Limitations

- This fictional use case never closes an alarm on its own.
- The safety slot abstains on unclear alarms instead of guessing.
- The replay set holds 20 fictional cases only.
