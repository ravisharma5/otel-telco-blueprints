---
id: "UC-OPS-01"  # UC-<DOMAIN>-<nn>, uppercase domain code
type: "use-case"  # always use-case
title: "<Use case in plain words>"
doc_status: "draft"  # draft | review | done
domain: "network-operations"  # standards-knowledge | network-software | network-operations | agentic-operations | business-assurance | security | research (demo is reserved for test fixtures)
flagship: true  # false = catalog entry
otel_slots: ["llm", "safety"]  # llm | embedding | reranker | safety | decision | classification
model_readiness: "M2"  # M0 | M1 | M2 | M3
evidence_level: "E1"  # E0 | E1 | E2 | E3 | E4; minimum over load-bearing validation rows
autonomy_ceiling: "recommend-with-approval"  # inform | notify | recommend-with-approval | act-within-policy
tmf_an_level_target: 3  # optional; 0-5; a target, never a claim
placement_tier: ["regional"]  # far-edge | regional | core
honest_one_liner: "M2 / E1 / recommend-with-approval. Needs a tool-calling slot. Method defined, not yet run."  # M / E / ceiling. Main blocker. What has been shown.
platform_blueprints: ["PB-04"]  # PB-<nn> ids this use case depends on
agent_school: [301]  # agent-school course numbers (100-999)
clarity_reviewed: "2026-11-07"  # set after the humanizer pass; quoted ISO date
source: ["<source-id>"]  # optional; where the use case came from
---

<!-- One template serves flagships and catalog entries.
     Catalog entries (flagship: false) must fill At a glance, Governance, Validation, and Limitations.
     The other sections may contain only a line that starts with _Stub: <reason>_.
     Writing rules: framework/style-guide.md. Name each component by its role and the Red Hat product used. Write no product support status. -->

# <Use case title>

## At a glance

<!-- budget: 1 table, 7 rows ; purpose: the whole readiness story before any prose -->

| Field | Value |
|---|---|
| Honest one-liner | M2 / E1 / recommend-with-approval. Needs a tool-calling slot. Method defined, not yet run. |
| Problem | <One line: the operator pain and the KPI it moves> |
| Audience | <Who reads and runs this, for example NOC engineers> |
| OTel slots | <slot: role, for example `llm: tool-calling`; `safety: abstain`> |
| Model readiness and evidence | <M-level and E-level, for example M2 / E1> |
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

## Validation

<!-- budget: 1 table ; purpose: the canonical validation table; Vendor-reported and GSMA external are context and never raise the E-level -->

<!-- Evidence files go in evidence/ next to the blueprint or in a parent evidence/ folder up to the repo root, never the blueprint itself. Load-bearing is exactly yes or no. -->

The headline E-level is the minimum over load-bearing rows, as set out in [the minimum rule](../../../framework/definitions.md#headline-level-the-minimum-rule).

| # | Claim | Slot / component | Load-bearing | Vendor-reported | GSMA external | Our operator-task eval | E-level | Evidence | Result | Date | Release / revision |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | <Claim> | <slot or component id> | yes | <vendor figure or —> | <GSMA figure or —> | <operator-task result or —> | E1 | [<spec>](evidence/<file>) | <result or —> | <YYYY-MM-DD> | <release or revision; required from E2> |

## Deploy and verify

<!-- budget: 5 lines, 5 bullets ; purpose: link the how-to and state reference implementation status; related-work links -->

<Link to the how-to steps. State whether a reference implementation exists and at which E-level.>

- Agent-school: <course link>
- NVIDIA or Databricks equivalent: <link>
- LFN project: <link>

## Limitations

<!-- budget: 6 bullets ; purpose: what it does not do and what has not been shown -->

- <What this use case never does on its own>
- <What has not been run or measured>
- <Known gap or open question>
