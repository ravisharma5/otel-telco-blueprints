---
id: "UC-AGOPS-03"
type: "use-case"
title: "Policy-following operations agents"
doc_status: done
domain: "agentic-operations"
flagship: false
depth: "entry"
adaptation:
  rung: "skills"
  expertise: ["golden-set", "gate-labels", "tool-contracts"]
  bring:
    - {item: "Change policies as action classes with ceilings", domains: ["transport-ip", "ran", "core-cnf"], mechanism: "gate-policy"}
    - {item: "Change procedures as skills with manifests", domains: ["transport-ip"], mechanism: "skill-manifest"}
    - {item: "Change-approval and closure record tools", domains: ["oss-bss"], mechanism: "tool-contract"}
    - {item: "Gate set of past changes your approvers labelled", domains: ["oss-bss"], mechanism: "gate-policy"}
otel_slots: ["llm", "decision", "safety"]
autonomy_ceiling: "recommend-with-approval"
tmf_an_level_target: 2
placement_tier: ["regional", "core"]
one_liner: "Runs operations agents under written policies: each proposed change names its action class, and the decision gate holds it to that class's ceiling. Recommends with approval only. Depends on orchestration and change control that live outside the model."
platform_blueprints: ["PB-01", "PB-02", "PB-03", "PB-04", "PB-05", "PB-06", "PB-07", "PB-08", "PB-09", "PB-11"]
clarity_reviewed: "2026-11-16"
agent_school: [301, 303, 401]
card:
  goal: "change"
  summary: "Agents propose operations changes under written policies. Each policy names an action class and its ceiling, and an approver signs off every change."
  outcome: "Teams add agents to change work without losing control: each change follows a written policy and leaves an audit record."
  audience: "Operations and change teams, approvers, and risk owners"
  measures: ["Changes proposed within policy", "Approver overrides"]
  risk: "An agent could stray outside its policy, so the gate and an approver check changes."
placement:
  far-edge: {runs: [], note: "Not used: the agents and the gate run at regional and core sites."}
  regional: {runs: ["decision", "safety"], note: "The gate label and the Safety check run here."}
  core: {runs: ["llm-large"], note: "The large LLM runs the agents and writes each change proposal."}
---

<!-- Writing rules: framework/style-guide.md. Name each component by its role and the Red Hat product used. Write no product support status. -->

# Policy-following operations agents

## At a glance

| Field | Value |
|---|---|
| One-liner | Runs operations agents under written policies: each proposed change names its action class, and the decision gate holds it to that class's ceiling. Recommends with approval only. Depends on orchestration and change control that live outside the model. |
| Problem | Operations policies live in documents that agents can't follow reliably; the KPI is the share of changes proposed within policy |
| Audience | Operations and change teams, approvers, and risk owners |
| OTel slots | `llm`: the agent; `decision`: the gate label; `safety`: checks the evidence behind a proposal |
| Autonomy ceiling | Recommend with approval |
| Placement tier | Regional and core |
| Agent-school courses | 301, 303, and 401 in the [agent-school roadmap](https://github.com/open-experiments/agent-school/blob/main/docs/RoadMap.md) |

## Problem and value

Operations policies say who may change what, when, and with whose approval, but they sit in documents an agent can't enforce on itself.
This entry writes each policy as an action class with a ceiling and sends every proposed change through the [decision gate](../../../architecture/decision-gate.md).
Orchestration and change control stay outside the model, so the policy holds even when the agent is wrong.
The KPIs are the share of changes proposed within policy and the approver override rate.
Any gain is a target, measured against a shadow-stage baseline.

## How it works

_Stub: this catalog entry has no worked example or diagram yet._

## What you need

- [ ] Models: the three slots, chosen from the family in [PB-01](../../../platform/intake-model-selection/README.md), each pinned by revision with its licence chain recorded
- [ ] Platform blueprints: evaluation ([PB-02](../../../platform/evaluation-acceptance/README.md)), serving and routing ([PB-04](../../../platform/serving-routing-placement/README.md)), integration ([PB-05](../../../platform/integration/README.md)), safety gating ([PB-06](../../../platform/safety-autonomy-gating/README.md)), the action layer ([PB-07](../../../platform/action-layer/README.md)), tool identity and sandbox ([PB-08](../../../platform/security-identity-sandbox/README.md)), and quality operations ([PB-09](../../../platform/quality-operations/README.md))
- [ ] Components: one product for each role in the components table
- [ ] Policies: each written as an action class with a ceiling in the stage register, as [PB-06](../../../platform/safety-autonomy-gating/README.md#staged-autonomy) sets out
- [ ] Write path: the agent's only write tool is the action request, and only the action layer holds write credentials
- [ ] Tool access: the gateway applies the deny-unless-allowed rule in [PB-05](../../../platform/integration/README.md#per-tool-authorization)
- [ ] Agent identity: a workload identity bound to each agent's tool roles, as PB-08 sets out
- [ ] Decision engine: vLLM 0.26 or 0.30 on CUDA or ROCm, as the [Decision model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) states
- [ ] Traces: tool calls, gate decisions, and approvals, as PB-09 sets out
- [ ] Placement: the regional site runs Decision and Safety. The core runs the large LLM.

| Component role | Red Hat product used |
|---|---|
| Inference engine for every slot | Red Hat AI Inference (vLLM) |
| Serving platform | Red Hat OpenShift AI with KServe |
| Tool gateway for per-tool authorization | MCP gateway in Red Hat Connectivity Link |
| Action orchestration: gate, approval, rollout, and audit | Automation Orchestrator for Red Hat Ansible Automation Platform |
| Execution with the only write credentials | Job templates in Red Hat Ansible Automation Platform |

Key flags for each slot, copied from [PB-04](../../../platform/serving-routing-placement/README.md#key-flags-per-slot). Start the Safety slot with its own pinned revision and no tool-calling flags.

```text
# LLM 31B (pin the revision; text-only; tool calling)
--revision <sha> --enable-auto-tool-choice --tool-call-parser gemma4 \
--limit-mm-per-prompt '{"image": 0, "audio": 0}'
# Decision (card recipe)
--revision <sha> --max-logprobs 64 --enable-prefix-caching --max-model-len 16384
```

Any component can be replaced. The Red Hat products named here show one way to build this design.

### What you bring

<!-- generated:what-you-bring start -->

| Model change | Your expertise | How far to climb |
|---|---|---|
| No model change: a skill per role and a capability manifest per tool | A golden set your experts label; gate labels from your approvers; a contract for each tool | Configure first, and train only on a measured gap, as [PB-03 Adaptation](../../../platform/adaptation/README.md) sets out |

| Item | Network component | Mechanism | Owner | Matrix row |
|---|---|---|---|---|
| Change policies as action classes with ceilings | Transport and IP; RAN; 5G core CNFs | Gate and action-layer policy | Risk owner | [Transport and IP](../../../platform/bring-your-own-data/README.md#domain-transport-and-ip); [RAN](../../../platform/bring-your-own-data/README.md#domain-ran); [5G core CNFs](../../../platform/bring-your-own-data/README.md#domain-5g-core-cnfs) |
| Change procedures as skills with manifests | Transport and IP | Skill or capability manifest | SME | [Transport and IP](../../../platform/bring-your-own-data/README.md#domain-transport-and-ip) |
| Change-approval and closure record tools | OSS and BSS | MCP tool contract | Platform team | [OSS and BSS](../../../platform/bring-your-own-data/README.md#domain-oss-and-bss) |
| Gate set of past changes your approvers labelled | OSS and BSS | Gate and action-layer policy | Risk owner | [OSS and BSS](../../../platform/bring-your-own-data/README.md#domain-oss-and-bss) |

<!-- generated:what-you-bring end -->

### What you must add

| Gap | What you add | Source |
|---|---|---|
| Orchestration | Orchestration and change control outside the model, because the card says the model alone doesn't guarantee correct or safe tool execution | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#tool-use-and-instruction-following) |
| Procedure evaluation | Your change procedures tested on a stateful mock before the shadow stage, because the card reports no check against methods of procedure | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#operational-procedure-mop-validation-not-performed) |
| Outcome scoring | Scenarios scored on the resulting network state, because the card reports no benchmark of closed-loop task completion | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#autonomous-operational-task-completion-not-benchmarked) |
| Change records | Your change-approval and closure records as tools or retrieval, because the card's training leaves out change-management tooling | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| Gate labels | A gate set of past changes labelled by your approvers, because the Decision label probabilities aren't calibrated for your workload | [OTel-2.0-Decision-26B-A4B-4bit model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) |
| Language scope | Tests in every language your policies and proposals use, because the card's quality claims cover English text only | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |

## Governance

Each action request passes the [decision gate](../../../architecture/decision-gate.md), and the outcome never exceeds the policy ceiling for its class.
The outcome is the lower of the model label and the policy ceiling for the capability and risk class, so it never exceeds either. A STOP label forces STOP at every stage.
Every action class begins at the shadow stage, where the outcome is LOOK. A confirmed false ACT drops the use case and its action class back one stage, as [PB-06](../../../platform/safety-autonomy-gating/README.md#staged-autonomy) sets out.

| Action | Gate outcome (LOOK/NOTIFY/REVIEW/ACT/STOP) | Approval | AI Act class |
|---|---|---|---|
| Post a proposal note on the change record, `notify` | NOTIFY, from the assist stage up | None | Recorded by your legal team in the classification record |
| Propose a reversible change within policy, `write_low` | REVIEW, from the recommend stage up | The `approver` role | Recorded by your legal team in the classification record |
| Propose a change that affects many customers, `write_high` | REVIEW, from the recommend stage up | The `approver` role | Recorded by your legal team in the classification record |
| Any action the label marks STOP | STOP | None | Recorded by your legal team in the classification record |

| Parameter | What it controls | Who sets it | How to calibrate |
|---|---|---|---|
| Ceiling per risk class | The highest outcome each action class may reach | Risk owner, with subject-matter expert (SME) review | [Evaluation and acceptance](../../../platform/evaluation-acceptance/README.md): review the gate set for each class and the human review load |
| Required approver role per action class | Which role approves REVIEW for each action class | Risk owner | Check approval times and overrides per class in the trace |
| Decision false-ACT budget | The highest false-ACT rate accepted on change proposals | Risk owner | [Evaluation and acceptance](../../../platform/evaluation-acceptance/README.md#false-act-method): use the false-ACT method on a gate set of past changes |
| Safety abstain-recall floor | The lowest share of insufficient-context items where the Safety slot abstains | Risk owner, with SME review | Remove the evidence from items and measure correct abstention |
| Minimum share of no-write scenarios | The lowest share of scenarios whose correct answer changes nothing | SME | Sample past changes and count those where people only looked or escalated |
| Override rate ceiling | The share of human overrides that sends a use case back one stage | Business owner | Count overrides per use case and action class in the trace |

This page gives no default values. Each owner sets the value with SME review and versions it with the policy that `policy_version` names.

## Sources

Each key claim links its source, as set out in [the Sources table](../../../framework/definitions.md#sources-table).

| # | Claim | Basis | Source |
|---|---|---|---|
| 1 | Agentic use needs an external tool runtime, checked tool schemas, permission controls, audit logging, and human review, and the model alone doesn't guarantee correct or safe tool execution | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#tool-use-and-instruction-following) |
| 2 | The card reports no check of the 31B against methods of procedure such as configuration changes and failovers | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#operational-procedure-mop-validation-not-performed) |
| 3 | The card reports no evaluation of closed-loop task completion scored on the resulting network state | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#autonomous-operational-task-completion-not-benchmarked) |
| 4 | The 31B training leaves out incident and change-management tooling, change-approval systems and closure records included | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| 5 | The 31B targets English-language use, and all its quality claims are text-only | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |
| 6 | Use the Decision model's label probabilities for confidence thresholds and routing; serve it on vLLM 0.26 or 0.30 | model card | [OTel-2.0-Decision-26B-A4B-4bit model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) |

## Deploy and verify

_Stub: this catalog entry has no deploy steps yet._

## Limitations

- No agent changes the network on its own; an approver accepts every change through the action layer.
- A policy holds only if it's written as an action class; prose policies in the prompt don't count.
- The card reports no check against change procedures, so test proposals on a stateful mock first.
- The Decision label probabilities count as uncalibrated until you calibrate them on your own changes.
- The quality claims cover English only, so proposals in another language need their own evaluation.
