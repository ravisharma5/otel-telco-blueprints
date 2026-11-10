---
id: "PB-04"  # PB-<nn>
type: "platform"  # always platform
title: "<Platform capability in plain words>"
readiness_question: "<The operator question this blueprint answers>"
doc_status: "draft"  # draft | review | done
layers: ["safety-governance", "action"]  # optional; layer names from the architecture overview, in kebab case
table1_rows: [13]  # optional; row numbers in the readiness table
extension_rows: ["E2"]  # optional; extension rows E<n>
otel_slots: ["llm"]  # llm | embedding | reranker | safety | decision | classification
placement_tier: ["core"]  # far-edge | regional | core
one_liner: "Gives each team an OpenAI-compatible endpoint with per-team token limits. Depends on a gateway with token rate limiting."  # what the blueprint does, then its main dependency
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

<!-- budget: 1 table, 7 rows ; purpose: one-liner, question answered, audience, top 3 decisions -->

| Field | Value |
|---|---|
| One-liner | Gives each team an OpenAI-compatible endpoint with per-team token limits. Depends on a gateway with token rate limiting. |
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
| <Decision 1> | <Option A; option B> | <Option A> | <Reason, with a source link> |

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

## Sources and acceptance

<!-- budget: 1 table, 10 bullets ; purpose: the canonical Sources table plus operator acceptance gates -->

<!-- One row per key claim. Basis is model card, research, Red Hat guidance, industry use case, or project documentation. Source links the URL or repo file; never this page. -->

Each key claim links its source, as set out in [the Sources table](../../framework/definitions.md#sources-table).

| # | Claim | Basis | Source |
|---|---|---|---|
| 1 | <Claim the model card reports, for example a context length> | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT) |
| 2 | <Claim Red Hat documentation recommends> | Red Hat guidance | [<Red Hat doc or article title>](https://docs.redhat.com/<path>) |

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
