---
id: "UC-DEMO-02"
type: "use-case"
title: "Fictional widget lookup (test fixture)"
doc_status: "review"
domain: "demo"
flagship: false
depth: "entry"
adaptation:
  rung: "skills"
  expertise: ["golden-set", "tool-contracts"]
  bring:
    - {item: "Fictional widget alarm tools", domains: ["oss-bss"], mechanism: "tool-contract"}
    - {item: "Fictional triage procedure", domains: ["oss-bss"], mechanism: "skill-manifest"}
sandbox:
  fit: "none"
  why: "Reads fictional widget records; the agent runs no code"
otel_slots: ["llm"]
autonomy_ceiling: "inform"
placement_tier: ["core"]
one_liner: "Answers fictional widget questions and only informs. Needs an LLM slot."
platform_blueprints: ["PB-99"]
agent_school: []
card:
  goal: "answer"
  summary: "Answers fictional widget questions from one demo corpus and takes no action."
  outcome: "Fictional engineers stop looking up widget facts by hand."
  audience: "Fictional demo engineers and their business owner"
  measures: ["Time to answer"]
  risk: "A wrong fictional answer misleads an engineer until they check the corpus."
placement:
  core:
    runs: ["llm-small"]
    note: ""
---

> Fictional catalog entry for linter tests. Not a real blueprint.

# Fictional widget lookup

## At a glance

| Field | Value |
|---|---|
| One-liner | Answers fictional widget questions and only informs. Needs an LLM slot. |
| Problem | Fictional engineers look up widget facts by hand |
| Audience | Fictional demo engineers and their business owner |
| OTel slots | `llm`: answers widget questions |
| Autonomy ceiling | Inform |
| Placement tier | Core |
| Agent-school courses | None: no agent-school course covers this use case yet. See the [agent-school roadmap](https://github.com/open-experiments/agent-school/blob/main/docs/RoadMap.md) |

## Problem and value

Fictional demo engineers look up widget facts by hand.
This fictional entry answers widget questions from one corpus and takes no action.
The KPI is time to answer, stated here as a target only.

## How it works

_Stub: fictional catalog entry; it has no worked example._

## What you need

- [ ] Models: an `llm` slot pinned by revision
- [ ] Platform blueprints: the fictional platform fixture (PB-99)
- [ ] Data: the fictional replay set in the Sources table

| Component role | Red Hat product used |
|---|---|
| Inference engine for the LLM slot | Demo runtime (fictional) |

Any component can be replaced. The Red Hat products named here show one way to build this design.

### What you must add

| Gap | What you add | Source |
|---|---|---|
| Task data | Widget questions with answers your engineers checked | [replay set](../../sources/replay.jsonl) |
| Language scope | Test every language your engineers use, because the card names the languages it covers | [model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |

## Governance

| Action | Gate outcome (LOOK/NOTIFY/REVIEW/ACT/STOP) | Approval | AI Act class |
|---|---|---|---|
| Answer a widget question | LOOK | None | Minimal risk (fictional) |

| Parameter | What it controls | Who sets it | How to calibrate |
|---|---|---|---|
| Answer groundedness floor | The lowest share of answers the corpus supports | Risk owner | Score fictional checked answers |

This page gives no default values.

## Sources

Each key claim links its source, as set out in [the Sources table](../../../../../framework/definitions.md#sources-table).

| # | Claim | Basis | Source |
|---|---|---|---|
| 1 | The model card names the languages the model covers | model card | [model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |
| 2 | Demo teams look up widget facts with a replay set | industry use case | [replay set](../../sources/replay.jsonl) |

## Deploy and verify

_Stub: fictional catalog entry; it has no deploy steps._

## Limitations

- This fictional entry only informs; it takes no action.
- This fictional entry covers widget facts only.
