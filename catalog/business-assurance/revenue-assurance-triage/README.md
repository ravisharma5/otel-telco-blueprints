---
id: "UC-BIZ-02"
type: "use-case"
title: "Revenue assurance triage"
doc_status: done
domain: "business-assurance"
flagship: false
depth: "entry"
adaptation:
  rung: "skills"
  expertise: ["golden-set", "gate-labels", "tool-contracts"]
otel_slots: ["llm", "safety", "decision"]
autonomy_ceiling: "recommend-with-approval"
tmf_an_level_target: 2
placement_tier: ["regional", "core"]
one_liner: "Explains the cases your own fraud or revenue assurance model flags, and proposes a hold or an escalation for approval. Never scores a case itself. Depends on your detection model, called as a tool, and your billing records."
platform_blueprints: ["PB-01", "PB-02", "PB-04", "PB-05", "PB-06", "PB-07", "PB-10"]
clarity_reviewed: "2026-11-16"
agent_school: [202]
card:
  goal: "customers"
  summary: "Explains each case your own fraud or revenue assurance model flags, and proposes a hold or an escalation for an analyst to approve."
  outcome: "Analysts work flagged cases faster, with the billing evidence for each proposal in one place."
  audience: "Revenue assurance and fraud analysts, approvers, and risk owners"
  measures: ["Time to work a flagged case", "Proposals accepted by approvers"]
  risk: "A wrong hold blocks a genuine customer, so an approver signs off each one."
placement:
  far-edge: {runs: [], note: "Not used: billing records stay in central systems."}
  regional: {runs: ["safety", "decision", "llm-small"], note: "The Safety check, the gate label, and routine case notes run here."}
  core: {runs: ["llm-large"], note: "The large LLM explains complex cases and drafts each proposal."}
---

<!-- Writing rules: framework/style-guide.md. Name each component by its role and the Red Hat product used. Write no product support status. -->

# Revenue assurance triage

## At a glance

| Field | Value |
|---|---|
| One-liner | Explains the cases your own fraud or revenue assurance model flags, and proposes a hold or an escalation for approval. Never scores a case itself. Depends on your detection model, called as a tool, and your billing records. |
| Problem | Detection models flag more billing cases than analysts can explain by hand; the KPI is time to work a flagged case |
| Audience | Revenue assurance and fraud analysts, approvers, and risk owners |
| OTel slots | `llm`: explains each case and drafts proposals; `safety`: abstain on weak evidence; `decision`: the gate label |
| Autonomy ceiling | Recommend with approval |
| Placement tier | Regional and core |
| Agent-school courses | 202 in the [agent-school roadmap](https://github.com/open-experiments/agent-school/blob/main/docs/RoadMap.md) |

## Problem and value

Your fraud and revenue assurance models flag billing cases faster than analysts can gather the evidence behind each one.
This entry calls the detection model as a tool, reads the billing and usage records behind the flag, and writes a case explanation.
It proposes to clear, hold, or escalate each case, and an approver decides each one.
The KPIs are time to work a flagged case and the share of proposals approvers accept.
Any gain is a target, measured against a shadow-stage baseline.

## How it works

_Stub: this catalog entry has no worked example or diagram yet._

## What you need

- [ ] Models: the three slots, chosen from the family in [PB-01](../../../platform/intake-model-selection/README.md), each pinned by revision with its licence chain recorded
- [ ] Platform blueprints: evaluation ([PB-02](../../../platform/evaluation-acceptance/README.md)), serving and routing ([PB-04](../../../platform/serving-routing-placement/README.md)), integration ([PB-05](../../../platform/integration/README.md)), safety gating ([PB-06](../../../platform/safety-autonomy-gating/README.md)), the action layer ([PB-07](../../../platform/action-layer/README.md)), and compliance ([PB-10](../../../platform/compliance-operating-model/README.md))
- [ ] Components: one product for each role in the components table
- [ ] Detection model: your own fraud or revenue assurance model scores every case and runs as a tool; the LLM explains its output and never computes a score
- [ ] Integrations: read-only tools for the detection model and billing records through the MCP gateway, under the deny-unless-allowed rule in [PB-05](../../../platform/integration/README.md#per-tool-authorization)
- [ ] Approval: every clearance, hold, and escalation goes through the action layer, and the approver accepts or rejects it there
- [ ] Controls: your own leakage and fraud categories, which this entry takes from you rather than from an industry framework
- [ ] Privacy: the [PB-10 privacy map](../../../platform/compliance-operating-model/README.md#privacy-map-for-gdpr-and-eprivacy) for the subscriber billing data the tools read
- [ ] Decision engine: vLLM 0.26 or 0.30 on CUDA or ROCm, as the [Decision model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) states
- [ ] Placement: the regional site runs Safety, Decision, and the small LLM. The core runs the large LLM.

| Component role | Red Hat product used |
|---|---|
| Inference engine for every slot | Red Hat AI Inference (vLLM) |
| Serving platform for the slots and your detection model | Red Hat OpenShift AI with KServe |
| Tool gateway for the detection model and billing records | MCP gateway in Red Hat Connectivity Link |
| Action orchestration: gate, approval, and audit | Automation Orchestrator for Red Hat Ansible Automation Platform |
| Billing records | Your choice; this design names no product |

Key flags for each slot, copied from [PB-04](../../../platform/serving-routing-placement/README.md#key-flags-per-slot). Start the small LLM and the Safety slot with their own pinned revisions and no tool-calling flags.

```text
# LLM 31B (pin the revision; text-only; tool calling)
--revision <sha> --enable-auto-tool-choice --tool-call-parser gemma4 \
--limit-mm-per-prompt '{"image": 0, "audio": 0}'
# Decision (card recipe)
--revision <sha> --max-logprobs 64 --enable-prefix-caching --max-model-len 16384
```

Any component can be replaced. The Red Hat products named here show one way to build this design.

### What you must add

| Gap | What you add | Source |
|---|---|---|
| Fraud signal | Your own fraud or revenue assurance model, served and called as a tool, so the model scores and the LLM explains, as course 202 teaches | [Agent-school 202 Fraud Triage](https://github.com/open-experiments/agent-school/blob/30458bda61cdc1ea939ce7d1fe6b8d425ed2bbad/202-fraud-triage/README.md) |
| Billing data | Billing, usage, and account records read through checked tools, because the card leaves operator records and BSS tooling out of training | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| Hold and escalate | Every hold and escalation sent to an approver, because the card asks for human review in high-impact use | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#intended-use) |
| Gate labels | A gate set of past cases labelled by your analysts, because the Decision label probabilities aren't calibrated for your workload | [OTel-2.0-Decision-26B-A4B-4bit model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) |
| Language scope | Tests in every language your analysts read cases in, because the card's quality claims cover English text only | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |

## Governance

Each action request passes the [decision gate](../../../architecture/decision-gate.md), and the outcome never exceeds the policy ceiling for its class.
The outcome is the lower of the model label and the policy ceiling for the capability and risk class, so it never exceeds either. A STOP label forces STOP at every stage.
Every action class begins at the shadow stage, where the outcome is LOOK. A confirmed false ACT drops the use case and its action class back one stage, as [PB-06](../../../platform/safety-autonomy-gating/README.md#staged-autonomy) sets out.

| Action | Gate outcome (LOOK/NOTIFY/REVIEW/ACT/STOP) | Approval | AI Act class |
|---|---|---|---|
| Explain a flagged case to the analyst | LOOK, with no action request | None; the analyst decides | [Recorded by your legal team in the classification record](../../../platform/compliance-operating-model/README.md) |
| Add a case note, `notify` | NOTIFY, from the assist stage up | None | [Recorded by your legal team in the classification record](../../../platform/compliance-operating-model/README.md) |
| Propose to clear a case or escalate it to the fraud team, `write_low` | REVIEW, from the recommend stage up | The `approver` role | [Recorded by your legal team in the classification record](../../../platform/compliance-operating-model/README.md) |
| Propose a hold on a charge or account, `write_high` | REVIEW, from the recommend stage up | The `approver` role | [Recorded by your legal team in the classification record](../../../platform/compliance-operating-model/README.md) |
| Any request the label marks STOP | STOP | None | [Recorded by your legal team in the classification record](../../../platform/compliance-operating-model/README.md) |

| Parameter | What it controls | Who sets it | How to calibrate |
|---|---|---|---|
| LLM groundedness floor | The lowest share of case explanation lines that the model output and records support | Risk owner, with subject-matter expert (SME) review | [Evaluation and acceptance](../../../platform/evaluation-acceptance/README.md): score SME-checked explanations of past cases with a calibrated judge |
| Decision false-ACT budget | The highest false-ACT rate accepted on clearances, holds, and escalations | Risk owner | [Evaluation and acceptance](../../../platform/evaluation-acceptance/README.md#false-act-method): use the false-ACT method on a gate set of past cases |
| Ceiling for low-risk writes | The highest outcome for clearances and escalations | Risk owner | Raise it only after a canary window with no false ACT label |
| Ceiling for high-risk writes | The highest outcome for holds | Risk owner | Keep it at REVIEW until the risk owner signs off on canary evidence |
| Required approver role per action class | Which role approves REVIEW for each action class | Risk owner | Check approval times and overrides per class in the trace |
| Trace archive retention period | How long archived prompts and tool payloads are kept before deletion | Data protection officer | Set from the retention period the applicable law and your audit needs require |

This page gives no default values. Each owner sets the value with SME review and versions it with the policy that `policy_version` names.

## Sources

Each key claim links its source, as set out in [the Sources table](../../../framework/definitions.md#sources-table).

| # | Claim | Basis | Source |
|---|---|---|---|
| 1 | The 31B training leaves out operator customer and equipment configuration records and OSS/BSS tooling | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| 2 | The tool-use training holds general examples only, and agentic use needs an external tool runtime with checked tool schemas and human review | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#tool-use-and-instruction-following) |
| 3 | For high-impact operational use, deploy the 31B with retrieval, source attribution, validation checks, and human review | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#intended-use) |
| 4 | The 31B targets English-language use, and all its quality claims are text-only | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |
| 5 | Use the Decision model's label probabilities for confidence thresholds and routing; serve it on vLLM 0.26 or 0.30 | model card | [OTel-2.0-Decision-26B-A4B-4bit model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) |
| 6 | The Safety model is trained to refuse when retrieved context is insufficient | model card | [OTel-LLM-12B-Safety model card](https://huggingface.co/farbodtavakkoli/OTel-LLM-12B-Safety) |
| 7 | Course 202 builds an agent that calls a trained fraud model as a tool and routes each case to clear, hold, or escalate, with human approval on escalation | project documentation | [Agent-school 202 Fraud Triage](https://github.com/open-experiments/agent-school/blob/30458bda61cdc1ea939ce7d1fe6b8d425ed2bbad/202-fraud-triage/README.md) |

## Deploy and verify

_Stub: this catalog entry has no deploy steps yet._

## Limitations

- It never scores a case; your own detection model does, and the LLM explains the score it returns.
- It never holds a charge or account on its own; an approver accepts every clearance, hold, and escalation through the action layer.
- It draws no conclusion that a customer committed fraud; analysts and your legal team do.
- The Decision label probabilities count as uncalibrated until you calibrate them on your own cases.
- The quality claims cover English only, so explanations in another language need their own evaluation.
