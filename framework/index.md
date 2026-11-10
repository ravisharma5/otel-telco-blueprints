---
type: "reference"
title: "Readiness questions"
question: "What must an operator answer before running OTel models in production?"
doc_status: "draft"
platform_blueprints: ["PB-01", "PB-02", "PB-03", "PB-04", "PB-05", "PB-06", "PB-07", "PB-08", "PB-09", "PB-10"]
otel_slots: ["llm", "embedding", "reranker", "safety", "decision", "classification"]
---

# Readiness questions

## At a glance

| Field | Value |
|---|---|
| Question answered | What must an operator answer before running OTel models in production? |
| Answer | Ten questions, from model intake to operating model. A use case is ready for production when each one has a checkable answer |
| Audience | Operator architects, platform owners, and risk and compliance leads |
| OTel slots | All six: LLM, Embedding, Reranker, Safety, Decision, Classification |
| Platform blueprints | PB-01 to PB-10 |

## The question

What must you answer before an OTel-based use case leaves the pilot?
Without a fixed list, teams skip the hard parts, such as evaluation on their own data, autonomy gating, and compliance, and find the gaps in production.

## The principle

Each question has a "ready" criterion that you can check: you show a reviewer the artifact that proves it.
A platform blueprint answers each question with a design and its acceptance checks.
A use case is ready for production when all ten criteria hold for that use case.

## The design

### The ten questions

| # | Question | What ready means | Answered by |
|---|---|---|---|
| 1 | Intake: which checkpoints may you run, and where do they come from? | Every checkpoint in use is pinned to a revision hash, has a recorded licence chain, and is served from your own registry as a signed image | PB-01 |
| 2 | Evaluation: how do you know a model is good enough for this use case? | Each slot has acceptance thresholds measured on your data and tool contracts, signed off by a named owner, and re-run on every model, prompt, tool, or adapter change | PB-02 |
| 3 | Adaptation: how do you fit the model to your network? | You climb from retrieval to skills, LoRA, and OSFT only when an evaluation gap calls for it, and every adapter is bound to one base revision and re-evaluated after a base upgrade | PB-03 |
| 4 | Serving and placement: where and how does each slot run? | Each slot has a sized deployment on named hardware, a placement tier, a latency target, and a fallback for when it is down | PB-04 |
| 5 | Integration: how do agents reach your network and business systems? | Agents reach systems only through standards-based tools (TM Forum, CAMARA, 3GPP) behind one gateway. Tools are read-only by default and have versioned contracts and conformance tests | PB-05 |
| 6 | Autonomy gating: what may the agent do without a human? | Each action class has a declared autonomy level, a gate outside the model decides each step, a named approver handles REVIEW, and every change is verified and can roll back | PB-06, PB-07 |
| 7 | Security: how do you stop misuse of agents and tools? | Each agent has its own short-lived identity, the gateway authorizes every tool call, secrets never reach the model context, untrusted content is screened for prompt injection, and the stack runs air-gapped when required | PB-08 |
| 8 | Quality operations: how do you notice when quality drops? | Every episode is traced end to end with OpenTelemetry, drift signals such as abstention rate, gate labels, and human overrides have thresholds and owners, and AI incidents follow your NOC and SOC process | PB-09 |
| 9 | Compliance and sovereignty: can you show the use case meets the rules and keeps data where it must stay? | Each use case has an EU AI Act classification record, a GDPR, NIS2, and CAMARA consent mapping, and a data residency statement backed by in-country inference | PB-10 |
| 10 | Operating model: who owns the use case, and how does it grow? | The use case has a named accountable owner, a RACI, a staged rollout plan (shadow, assist, recommend, act), and a measured value case | PB-10 |

PB-06 and PB-07 together answer autonomy gating: PB-06 sets the gate described on the [decision gate](../architecture/decision-gate.md) page, and PB-07 runs the action layer behind it. PB-10 answers both compliance and the operating model.

### How to use the questions

1. Pick one use case.
2. For each question, find the artifact that shows the criterion holds, such as the pinned revision list, the evaluation report, or the RACI.
3. Mark each question without an artifact as a gap, and open the platform blueprint that answers it.
4. Close the gaps for questions 6 and 9 before the agent takes any action beyond reading and notifying.

## Trade-offs and limits

| Trade-off | What to do |
|---|---|
| Readiness is per use case, not per platform | Reuse platform answers (intake, serving, security), and answer evaluation, autonomy, and compliance again for each use case |
| A question can have more than one owner | Name one accountable owner per question for each use case, even when two platform blueprints answer it |
| Readiness expires when the model changes; the [OTel model cards](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT) say weights may be updated over time | Pin revisions, and rerun questions 1 to 3 on every new OTel revision before you promote it |
| Ten questions add work to a pilot | For a read-only pilot, answer questions 1, 2, 4, and 7 first, and the rest before the pilot acts |

## Used by

- PB-01 to PB-10: each platform blueprint answers one or two of these questions
- [Architecture overview](../architecture/index.md): the six OTel slots mapped onto Red Hat products
- [Decision gate](../architecture/decision-gate.md): the gate that answers autonomy gating
- [Adaptation ladder](../architecture/adaptation-ladder.md): the climb that answers adaptation
- [Placement tiers](../architecture/placement.md): the tiers that answer serving and placement
- [Crosswalk](../architecture/crosswalk.md): how this design lines up with the agent blueprint table
- [Definitions](definitions.md): the autonomy ceiling and component naming
- [Glossary](glossary.md): the terms used on this page
- [Style guide](style-guide.md): the shape of each blueprint page
- [Review checklist](review-checklist.md): the checks every page passes
