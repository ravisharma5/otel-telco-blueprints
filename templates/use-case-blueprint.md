---
id: "UC-OPS-01"  # UC-<DOMAIN>-<nn>, uppercase domain code
type: "use-case"  # always use-case
title: "<Use case in plain words>"
doc_status: "draft"  # draft | review | done
domain: "network-operations"  # standards-knowledge | network-software | network-operations | agentic-operations | business-assurance | security | research (demo is reserved for test fixtures)
flagship: true  # false = catalog entry
otel_slots: ["llm", "safety"]  # llm | embedding | reranker | safety | decision | classification
autonomy_ceiling: "recommend-with-approval"  # inform | notify | recommend-with-approval | act-within-policy
tmf_an_level_target: 3  # optional; 0-5; a target, never a claim
placement_tier: ["regional"]  # far-edge | regional | core
one_liner: "Recommends fixes with human approval. Needs a tool-calling LLM slot."  # what the use case does, its autonomy ceiling in words, then its main dependency
platform_blueprints: ["PB-04"]  # PB-<nn> ids this use case depends on
agent_school: [301]  # agent-school course numbers (100-999)
clarity_reviewed: "2026-11-07"  # set after the humanizer pass; quoted ISO date
source: ["<source-id>"]  # optional; where the use case came from
---

<!-- One template serves flagships and catalog entries.
     Catalog entries (flagship: false) must fill At a glance, Governance, Sources, and Limitations.
     The other sections may contain only a line that starts with _Stub: <reason>_.
     Writing rules: framework/style-guide.md. Name each component by its role and the Red Hat product used. Write no product support status. -->

# <Use case title>

## At a glance

<!-- budget: 1 table, 7 rows ; purpose: the whole use case before any prose -->

| Field | Value |
|---|---|
| One-liner | Recommends fixes with human approval. Needs a tool-calling LLM slot. |
| Problem | <One line: the operator pain and the KPI it moves> |
| Audience | <Who reads and runs this, for example NOC engineers> |
| OTel slots | <slot: role, for example `llm: tool-calling`; `safety: abstain`> |
| Autonomy ceiling | <inform, notify, recommend with approval, or act within policy> |
| Placement tier | <far-edge, regional, or core> |
| Agent-school courses | <Course numbers with links> |

## Problem and value

<!-- budget: 5 lines ; purpose: what the operator gets and the measurable outcome; label any ROI figure as a target -->

<Who has the problem, what it costs today, and the KPI this use case moves.>

## How it works

<!-- budget: 1 diagram, 8 steps ; purpose: diagram plus numbered flow, and where the decision gate sits -->

![<diagram description>](diagrams/<name>.svg)

<!-- Author with archify; commit the source HTML, candidate.json, and exported SVG in diagrams/ -->

1. <Trigger: what starts the flow>
2. <Model step: which OTel slot does what>
3. <Gate step: the decision gate returns LOOK, NOTIFY, REVIEW, ACT, or STOP>

<!-- State which step holds the decision gate and what happens on STOP. -->

## What you need

<!-- budget: 12 bullets ; purpose: checklist of models, platform blueprints, integrations, tools and data, adaptation, prerequisites -->

- [ ] Models: <OTel slot and minimum size, as a slot, not a fixed checkpoint>
- [ ] Platform blueprints: <PB-nn links>
- [ ] Components: <role in this design>: <Red Hat product used>, one per load-bearing component
- [ ] Integrations: <MCP capabilities with risk class; standards such as TMF, CAMARA, 3GPP>
- [ ] Tools and data: <data sources, consent and privacy notes>
- [ ] Data and adaptation: <task data, SDG recipe, adapter strategy, license and sovereignty>
- [ ] Prerequisites: <cluster, accelerators, access>

Any component can be replaced. The Red Hat products named here show one way to build this design.

## Governance

<!-- budget: 1 table ; purpose: gate outcome per action, approvals, AI Act class -->

| Action | Gate outcome (LOOK/NOTIFY/REVIEW/ACT/STOP) | Approval | AI Act class |
|---|---|---|---|
| <Action the agent can take> | <REVIEW> | <Role that approves> | <Class> |

## Sources

<!-- budget: 1 table ; purpose: the canonical Sources table, one row per key claim -->

<!-- One row per key claim. Basis is model card, research, Red Hat guidance, or industry use case. Source links the URL or repo file; never this page. -->

Each key claim links its source, as set out in [the Sources table](../../../framework/definitions.md#sources-table).

| # | Claim | Basis | Source |
|---|---|---|---|
| 1 | <Claim the model card reports, for example tool-calling support> | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT) |
| 2 | <Claim Red Hat documentation recommends> | Red Hat guidance | [<Red Hat doc or article title>](https://docs.redhat.com/<path>) |

## Deploy and verify

<!-- budget: 5 lines, 5 bullets ; purpose: link the how-to and the reference implementation; related-work links -->

Link the how-to steps and the reference implementation, if one exists.

- Agent-school: <course link>
- NVIDIA or Databricks equivalent: <link>
- LFN project: <link>

## Limitations

<!-- budget: 6 bullets ; purpose: what it does not do and what it does not cover -->

- <What this use case never does on its own>
- <What this design does not cover>
- <Known gap or open question>
