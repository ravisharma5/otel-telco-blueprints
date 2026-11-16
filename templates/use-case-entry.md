---
id: "UC-OPS-02"  # UC-<DOMAIN>-<nn>, uppercase domain code
type: "use-case"  # always use-case
title: "<Use case in plain words>"
doc_status: "draft"  # draft | review | done
domain: "network-operations"  # standards-knowledge | network-software | network-operations | agentic-operations | business-assurance | security | research (demo is reserved for test fixtures)
flagship: false  # a catalog entry is never a flagship
depth: "entry"  # entry = one page (Page budget: 550 prose words); How it works and Deploy and verify stay stubs
otel_slots: ["llm", "safety"]  # llm | embedding | reranker | safety | decision | classification
autonomy_ceiling: "recommend-with-approval"  # inform | notify | recommend-with-approval | act-within-policy
tmf_an_level_target: 2  # optional; 0-5; a target, never a claim
placement_tier: ["regional"]  # far-edge | regional | core
one_liner: "Recommends fixes with human approval. Needs a tool-calling LLM slot."  # what the use case does, its autonomy ceiling in words, then its main dependency
platform_blueprints: ["PB-04"]  # PB-<nn> ids this use case depends on
agent_school: [301]  # course numbers from tools/bplint/agent-school-courses.yaml; when none fits, write [] and put "None: no agent-school course covers this use case yet" in the Agent-school courses cell
clarity_reviewed: "2026-11-15"  # set after the humanizer pass; quoted ISO date
source: ["<source-id>"]  # optional; where the use case came from
also_covers: ["<merged application>"]  # optional; applications merged into this page, each 12 words or fewer; the Recipes overview lists them
card:  # required; the summary card on the explorer home page, in plain words
  goal: "<The goal, in 8 words or fewer>"  # will be one goal id from data/explorer/goals.yaml
  summary: "<What it does, in 25 words or fewer>"
  outcome: "<What changes for the operator, in 20 words or fewer>"
  audience: "<Who it serves, in 12 words or fewer>"
  measures: ["<First measure, 6 words or fewer>"]  # one to three measures
  risk: "<The main risk, in 15 words or fewer>"
placement:  # required; list all three tiers; runs lists roles: llm-small | llm-large | embedding | reranker | safety | decision | classification
  far-edge: {runs: [], note: "<Why this tier runs nothing, in 15 words or fewer>"}
  regional: {runs: ["llm-small", "safety"], note: "<What runs here, in 15 words or fewer>"}
  core: {runs: [], note: "<Why this tier runs nothing, in 15 words or fewer>"}
---

<!-- Catalog-entry template. Page budget: 550 prose words.
     An entry fills At a glance, Problem and value, What you need, Governance, Sources, and Limitations.
     How it works and Deploy and verify hold one line that starts with _Stub: <reason>_. An entry carries no diagram.
     Writing rules: framework/style-guide.md. Name each component by its role and the Red Hat product used. Write no product support status.
     Vale tips: start the text after a bullet label in lowercase; refer to tables by name, never as "above" or "below". -->

# <Use case title>

## At a glance

<!-- budget: 1 table, 7 rows ; purpose: the whole use case before any prose -->

| Field | Value |
|---|---|
| One-liner | Recommends fixes with human approval. Needs a tool-calling LLM slot. |
| Problem | <One line: the operator pain and the KPI it moves> |
| Audience | <Who reads and runs this, for example operations engineers and approvers> |
| OTel slots | <slot: role, for example `llm`: tool calling; `safety`: abstain> |
| Autonomy ceiling | <inform, notify, recommend with approval, or act within policy> |
| Placement tier | <far-edge, regional, or core> |
| Agent-school courses | <Course numbers> in the [agent-school roadmap](https://github.com/open-experiments/agent-school/blob/main/docs/RoadMap.md) |

## Problem and value

<!-- budget: 5 lines ; purpose: what the operator gets and the measurable outcome; label any ROI figure as a target -->

<Who has the problem, what it costs today, and the KPI this use case moves.>

## How it works

<!-- budget: 1 diagram, 8 steps ; an entry stubs this section and carries no diagram; a recipe fills it -->

_Stub: this catalog entry has no worked example or diagram yet._

## What you need

<!-- budget: 12 bullets ; purpose: checklist of models, platform blueprints, integrations, tools and data, adaptation, prerequisites -->

<!-- Start the text after each label in lowercase. The tables and the flags fence don't count as bullets. -->

- [ ] Models: <the slots in `otel_slots`, each pinned by revision with its licence chain recorded>
- [ ] Platform blueprints: <the pages for PB-nn, with links>
- [ ] Components: one product for each role in the components table
- [ ] Integrations: <read-only or write tools with their risk class; standards such as TMF, CAMARA, 3GPP>
- [ ] Tools and data: <data sources, consent and privacy notes>
- [ ] Prerequisites: <cluster, accelerators, access>
- [ ] Decision engine: <copy the Decision slot engine prerequisite from PB-04 word for word; keep this bullet only when `otel_slots` includes `decision`>

| Component role | Red Hat product used |
|---|---|
| <Role in this design> | <Red Hat product used> |

<!-- Copy the PB-04 "Key flags per slot" blocks line for line, only for this page's slots, and add no flag PB-04 or PB-03 lacks.
     For a slot PB-04 has no block for, such as Safety, say how to start it (its own pinned revision, no tool-calling flags). -->

Key flags for each slot, copied from [PB-04](../../../platform/serving-routing-placement/README.md#key-flags-per-slot).

```text
# <PB-04 block header for the slot>
<flag lines copied from PB-04>
```

Any component can be replaced. The Red Hat products named here show one way to build this design.

### What you must add

<!-- One row per gap the operator must fill before production: task data, evaluation, integrations, and language scope at least.
     Paraphrase the public model-card caveat that creates the gap, and repeat in the Source cell a link from the Sources table.
     The language-scope row cites the model card anchor, for example the 31B card #supported-language-and-modality.
     Never quote private notes. -->

| Gap | What you add | Source |
|---|---|---|

## Governance

<!-- budget: 3 tables ; purpose: gate outcome per action, named parameters, optional RACI -->

<!-- Keep the gate link sentence on every page. When the page sends action requests, copy the first two sentences of the PB-06 gate rules after it. -->

Each action request passes the [decision gate](../../../architecture/decision-gate.md), and the outcome never exceeds the policy ceiling for its class.

<!-- One row per action and risk class. The AI Act class cell links the classification record your legal team keeps; never state the class. -->

| Action | Gate outcome (LOOK/NOTIFY/REVIEW/ACT/STOP) | Approval | AI Act class |
|---|---|---|---|
| <Action the agent can take, with its risk class> | <REVIEW> | <Generic role that approves, such as the approver> | <Link to the classification record> |

<!-- Copy each parameter row from the platform page that defines it: same name, same owner (business owner, approver, risk owner, or model owner). Never write a value. -->

| Parameter | What it controls | Who sets it | How to calibrate |
|---|---|---|---|

This page gives no default values. Each owner sets the value with SME review and versions it with the policy that `policy_version` names.

<!-- Optional: a RACI table copied from the platform pages, with generic roles only. -->

## Sources

<!-- budget: 1 table ; purpose: the canonical Sources table, one row per key claim -->

<!-- One row per key claim. Basis is model card, research, Red Hat guidance, industry use case, or project documentation. Source links the URL or repo file; never this page. -->

Each key claim links its source, as set out in [the Sources table](../../../framework/definitions.md#sources-table).

| # | Claim | Basis | Source |
|---|---|---|---|
| 1 | <The language scope the model card states> | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |
| 2 | <Claim Red Hat documentation recommends> | Red Hat guidance | [<Red Hat doc or article title>](https://docs.redhat.com/<path>) |

## Deploy and verify

<!-- budget: 5 lines, 5 bullets ; an entry stubs this section; the agent-school roadmap link lives in At a glance -->

_Stub: this catalog entry has no deploy steps yet._

## Limitations

<!-- budget: 6 bullets ; purpose: what it does not do and what it does not cover -->

<!-- Say what the design does not cover in plain words. Avoid legal conclusions such as calling a variant "out of scope" with is or are. -->

- <What the use case never does on its own>
- <What it does not cover>
