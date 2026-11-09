---
id: "PB-04"  # PB-<nn>
type: "platform"  # always platform
title: "<Platform capability in plain words>"
readiness_question: "<The operator question this blueprint answers>"
doc_status: "draft"  # draft | review | done
layers: ["L6", "L7"]  # optional; reference-architecture layers L<n>
table1_rows: [13]  # optional; row numbers in the readiness table
extension_rows: ["E2"]  # optional; extension rows E<n>
otel_slots: ["llm"]  # llm | embedding | reranker | safety | decision | classification
model_readiness: "n/a"  # always n/a: platform blueprints carry no model-readiness level
evidence_level: "E1"  # E0 | E1 | E2 | E3 | E4; minimum over load-bearing validation rows
placement_tier: ["core"]  # far-edge | regional | core
honest_one_liner: "E1. Needs a gateway with per-team token limits. Method defined, not yet run."  # E-level. Main blocker. What has been shown.
top_decisions:  # 1-3 items; the same three appear in At a glance
  - "<Decision 1>"
  - "<Decision 2>"
  - "<Decision 3>"
agent_school: [301]  # agent-school course numbers (100-999)
clarity_reviewed: "2026-11-07"  # set after the humanizer pass; quoted ISO date
---

<!-- Writing rules: framework/style-guide.md. Name each component by its role and the Red Hat product used. Write no product support status. -->

# <Platform blueprint title>

## At a glance

<!-- budget: 1 table, 7 rows ; purpose: question answered, audience, evidence, top 3 decisions -->

| Field | Value |
|---|---|
| Honest one-liner | E1. Needs a gateway with per-team token limits. Method defined, not yet run. |
| Question answered | <The readiness question in one line> |
| Audience | <Platform engineers, architects, or both> |
| OTel slots | <Slots this capability serves> |
| Placement tier | <far-edge, regional, or core> |
| Top 3 decisions | <Decision 1>; <Decision 2>; <Decision 3> |
| Agent-school courses | <Course numbers with links> |

## The operator question

<!-- budget: 3 lines ; purpose: one sentence, and why it blocks production -->

<The question in one sentence, and what blocks production until you answer it.>

## Decisions you must make

<!-- budget: 1 table ; purpose: MADR-style decision, options, recommendation, because -->

| Decision | Options | Recommendation | Because |
|---|---|---|---|
| <Decision 1> | <Option A; option B> | <Option A> | <Reason, with E-level or link> |

## Reference design

<!-- budget: 1 diagram, 8 steps, 8 bullets ; purpose: diagram, numbered flow, and config-artifact links -->

![<diagram description>](diagrams/<name>.svg)

<!-- Author with archify; commit the source HTML, candidate.json, and exported SVG in diagrams/ -->

1. <Step 1>
2. <Step 2>
3. <Step 3>

- Config artifact: <link to policy YAML, gateway objects, gate contract, or Helm values>

## Components

<!-- budget: 1 table ; purpose: each component's role in this design and the Red Hat product used -->

| Component role | Red Hat product used |
|---|---|
| <What the component does in this design> | <Red Hat product> |

Any component can be replaced. The Red Hat products named here show one way to build this design.

## OTel slot guidance

<!-- budget: 1 table ; purpose: slot, candidate checkpoints, known model-card limits -->

| Slot | Candidate checkpoints | Notes |
|---|---|---|
| <slot> | <Checkpoint family, pinned by revision> | <Known limit or sizing note> |

## Validation and acceptance

<!-- budget: 1 table, 10 bullets ; purpose: the canonical validation table plus acceptance gates; Vendor-reported and GSMA external never raise the E-level -->

<!-- Evidence files go in evidence/ next to the blueprint or in a parent evidence/ folder up to the repo root, never the blueprint itself. Load-bearing is exactly yes or no. -->

The headline E-level is the minimum over load-bearing rows, as set out in [the minimum rule](../../framework/definitions.md#headline-level-the-minimum-rule).

| # | Claim | Slot / component | Load-bearing | Vendor-reported | GSMA external | Our operator-task eval | E-level | Evidence | Result | Date | Release / revision |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | <Claim> | <slot or component id> | yes | <vendor figure or —> | <GSMA figure or —> | <operator-task result or —> | E1 | [<spec>](evidence/<file>) | <result or —> | <YYYY-MM-DD> | <release or revision; required from E2> |

- Gate: <metric, threshold, and how to run the check>

## Operating model

<!-- budget: 1 table ; purpose: who owns what (RACI) -->

| Activity | Responsible | Accountable | Consulted | Informed |
|---|---|---|---|---|
| <Activity, for example rollback> | <Role> | <Role> | <Role> | <Role> |

## Risks and limitations

<!-- budget: 1 table ; purpose: risk, likelihood, mitigation; known gaps stated plainly -->

| Risk | Likelihood | Mitigation |
|---|---|---|
| <Risk or known gap> | <Low, medium, or high> | <Mitigation or "none yet"> |

## Used by and next steps

<!-- budget: 12 bullets ; purpose: links only, including related work: agent-school, NVIDIA and Databricks blueprints, LFN -->

- Used by: <use-case blueprint link>
- Agent-school: <course link>
- NVIDIA or Databricks equivalent: <link>
- LFN project: <link>
