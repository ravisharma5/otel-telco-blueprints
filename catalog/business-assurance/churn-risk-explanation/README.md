---
id: "UC-BIZ-01"
type: "use-case"
title: "Churn risk explanation"
doc_status: done
domain: "business-assurance"
flagship: false
depth: "entry"
adaptation:
  rung: "skills"
  expertise: ["golden-set", "gate-labels", "tool-contracts"]
  bring:
    - {item: "Read tools for your churn model and customer records", domains: ["oss-bss", "customer-care"], mechanism: "tool-contract"}
    - {item: "Retention explanation skill and tool manifests", domains: ["customer-care"], mechanism: "skill-manifest"}
    - {item: "Retention offer ceilings and approver roles", domains: ["customer-care"], mechanism: "gate-policy"}
    - {item: "Gate set of past retention cases your SMEs labelled", domains: ["customer-care"], mechanism: "gate-policy"}
sandbox:
  fit: "none"
  why: "Reads churn scores your own model computes; the agent runs no code"
otel_slots: ["llm", "safety", "decision"]
autonomy_ceiling: "recommend-with-approval"
tmf_an_level_target: 2
placement_tier: ["regional", "core"]
one_liner: "Explains the churn score your own model computes for a customer, and proposes retention offers for approval. Never scores churn itself. Depends on your churn model, called as a tool, and your customer records."
platform_blueprints: ["PB-01", "PB-02", "PB-03", "PB-04", "PB-05", "PB-06", "PB-08", "PB-10", "PB-11"]
clarity_reviewed: "2026-11-16"
agent_school: [202]
card:
  goal: "customers"
  summary: "Explains why your own churn model scores a customer as at risk, and drafts a retention offer for an approver to accept."
  outcome: "Retention teams see why a customer is at risk and act on the strongest cases first."
  audience: "Retention teams, the data protection officer, and risk owners"
  measures: ["Offers accepted by approvers", "Retention among reviewed customers"]
  risk: "It processes customer data, so your data protection officer reviews profiling questions."
placement:
  far-edge: {runs: [], note: "Not used: customer records stay in central systems."}
  regional: {runs: ["safety", "decision", "llm-small"], note: "The Safety check, the gate label, and routine explanations run here."}
  core: {runs: ["llm-large"], note: "The large LLM drafts explanations and offers for complex cases."}
---

<!-- Writing rules: framework/style-guide.md. Name each component by its role and the Red Hat product used. Write no product support status. -->

# Churn risk explanation

## At a glance

| Field | Value |
|---|---|
| One-liner | Explains the churn score your own model computes for a customer, and proposes retention offers for approval. Never scores churn itself. Depends on your churn model, called as a tool, and your customer records. |
| Problem | A churn score alone doesn't tell a retention team why a customer may leave or what to offer; the KPI is the share of offers approvers accept |
| Audience | Retention teams, the data protection officer, and risk owners |
| OTel slots | `llm`: explains the score and drafts offers; `safety`: abstain on weak evidence; `decision`: the gate label |
| Autonomy ceiling | Recommend with approval |
| Placement tier | Regional and core |
| Agent-school courses | 202 in the [agent-school roadmap](https://github.com/open-experiments/agent-school/blob/main/docs/RoadMap.md) |

## Problem and value

Your churn model scores each customer, but a retention team can rarely tell why a score is high or which offer fits.
This entry calls the churn model as a tool, reads the usage, complaint, and contract records behind the score, and explains it in plain words.
Each retention offer goes to an approver; the entry never contacts a customer or changes an account.
The KPIs are the share of offers approvers accept and retention among reviewed customers.
Any gain is a target, measured against a shadow-stage baseline.

## How it works

_Stub: this catalog entry has no worked example or diagram yet._

## What you need

- [ ] Models: the three slots, chosen from the family in [PB-01](../../../platform/intake-model-selection/README.md), each pinned by revision with its licence chain recorded
- [ ] Platform blueprints: evaluation ([PB-02](../../../platform/evaluation-acceptance/README.md)), serving and routing ([PB-04](../../../platform/serving-routing-placement/README.md)), integration ([PB-05](../../../platform/integration/README.md)), safety gating ([PB-06](../../../platform/safety-autonomy-gating/README.md)), and compliance ([PB-10](../../../platform/compliance-operating-model/README.md))
- [ ] Components: one product for each role in the components table
- [ ] Churn model: your own model computes every score and runs as a tool; the LLM explains its output and never computes a score
- [ ] Integrations: read-only tools for the churn model and customer records through the MCP gateway, under the deny-unless-allowed rule in [PB-05](../../../platform/integration/README.md#per-tool-authorization)
- [ ] Privacy: a data protection impact assessment and the [PB-10 privacy map](../../../platform/compliance-operating-model/README.md#privacy-map-for-gdpr-and-eprivacy) for the customer data the tools read
- [ ] Decision engine: vLLM 0.26 or 0.30 on CUDA or ROCm, as the [Decision model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) states
- [ ] Placement: the regional site runs Safety, Decision, and the small LLM. The core runs the large LLM.

| Component role | Red Hat product used |
|---|---|
| Inference engine for every slot | Red Hat AI Inference (vLLM) |
| Serving platform for the slots and your churn model | Red Hat OpenShift AI with KServe |
| Tool gateway for the churn model and customer records | MCP gateway in Red Hat Connectivity Link |
| Customer records | Your choice; this design names no product |

Key flags for each slot, copied from [PB-04](../../../platform/serving-routing-placement/README.md#key-flags-per-slot). Start the small LLM and the Safety slot with their own pinned revisions and no tool-calling flags.

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
| Read tools for your churn model and customer records | OSS and BSS; Customer and care | MCP tool contract | Platform team | [OSS and BSS](../../../platform/bring-your-own-data/README.md#domain-oss-and-bss); [Customer and care](../../../platform/bring-your-own-data/README.md#domain-customer-and-care) |
| Retention explanation skill and tool manifests | Customer and care | Skill or capability manifest | SME | [Customer and care](../../../platform/bring-your-own-data/README.md#domain-customer-and-care) |
| Retention offer ceilings and approver roles | Customer and care | Gate and action-layer policy | Risk owner | [Customer and care](../../../platform/bring-your-own-data/README.md#domain-customer-and-care) |
| Gate set of past retention cases your SMEs labelled | Customer and care | Gate and action-layer policy | Risk owner | [Customer and care](../../../platform/bring-your-own-data/README.md#domain-customer-and-care) |

<!-- generated:what-you-bring end -->

### Sandbox

<!-- generated:sandbox start -->

| Sandbox fit | Trigger on this page | Where to read |
|---|---|---|
| Base sandbox only: the agent reads through the gateways, so its identity, the gateway screen, and the six sandbox controls are enough | Reads churn scores your own model computes; the agent runs no code | [PB-08: when a use case needs a sandbox](../../../platform/security-identity-sandbox/README.md#when-a-use-case-needs-a-sandbox) |

<!-- generated:sandbox end -->

### What you must add

| Gap | What you add | Source |
|---|---|---|
| Churn score | Your own churn model, served and called as a tool, so the model scores and the LLM explains; course 202 teaches this pattern on fraud | [Agent-school 202 Fraud Triage](https://github.com/open-experiments/agent-school/blob/30458bda61cdc1ea939ce7d1fe6b8d425ed2bbad/202-fraud-triage/README.md) |
| Customer data | Usage, complaint, and contract records through TMF629 or your own customer API, because the card's training leaves out OSS/BSS workflow tooling | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training), [TMF629 Customer Management](https://github.com/tmforum-apis/TMF629_CustomerManagement) |
| Profiling review | A review by your data protection officer of any profiling question before the shadow stage; this entry draws no legal conclusion | [EDPB guidelines on automated decision-making and profiling](https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/automated-decision-making-and-profiling_en) |
| Gate labels | A gate set of past retention cases labelled by your retention SMEs, because the Decision label probabilities aren't calibrated for your workload | [OTel-2.0-Decision-26B-A4B-4bit model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) |
| Language scope | Tests in every language your retention teams read explanations in, because the card's quality claims cover English text only | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |

## Governance

Each action request passes the [decision gate](../../../architecture/decision-gate.md), and the outcome never exceeds the policy ceiling for its class.
The outcome is the lower of the model label and the policy ceiling for the capability and risk class, so it never exceeds either. A STOP label forces STOP at every stage.
Every action class begins at the shadow stage, where the outcome is LOOK. A confirmed false ACT drops the use case and its action class back one stage, as [PB-06](../../../platform/safety-autonomy-gating/README.md#staged-autonomy) sets out.

| Action | Gate outcome (LOOK/NOTIFY/REVIEW/ACT/STOP) | Approval | AI Act class |
|---|---|---|---|
| Explain a churn score to the retention team | LOOK, with no action request | None; the retention team decides | [Recorded by your legal team in the classification record](../../../platform/compliance-operating-model/README.md) |
| Add the explanation to the customer's retention case, `notify` | NOTIFY, from the assist stage up | None | [Recorded by your legal team in the classification record](../../../platform/compliance-operating-model/README.md) |
| Propose a retention offer, `write_high` | REVIEW, from the recommend stage up | The `approver` role | [Recorded by your legal team in the classification record](../../../platform/compliance-operating-model/README.md) |
| Any request the label marks STOP | STOP | None | [Recorded by your legal team in the classification record](../../../platform/compliance-operating-model/README.md) |

| Parameter | What it controls | Who sets it | How to calibrate |
|---|---|---|---|
| LLM groundedness floor | The lowest share of explanation lines that the churn model output and records support | Risk owner, with subject-matter expert (SME) review | [Evaluation and acceptance](../../../platform/evaluation-acceptance/README.md): score SME-checked explanations of past cases with a calibrated judge |
| Safety abstain-recall floor | The lowest share of insufficient-context items where the Safety slot abstains | Risk owner, with SME review | Remove the churn score or records from items and measure correct abstention |
| Decision false-ACT budget | The highest false-ACT rate accepted on retention offers | Risk owner | [Evaluation and acceptance](../../../platform/evaluation-acceptance/README.md#false-act-method): use the false-ACT method on a gate set of past offers |
| Ceiling for high-risk writes | The highest outcome for retention offers | Risk owner | Keep it at REVIEW until the risk owner signs off on canary evidence |
| Required approver role per action class | Which role approves REVIEW for each action class | Risk owner | Check approval times and overrides per class in the trace |
| Trace archive retention period | How long archived prompts and tool payloads are kept before deletion | Data protection officer | Set from the retention period the applicable law and your audit needs require |

This page gives no default values. Each owner sets the value with SME review and versions it with the policy that `policy_version` names.

## Sources

Each key claim links its source, as set out in [the Sources table](../../../framework/definitions.md#sources-table).

| # | Claim | Basis | Source |
|---|---|---|---|
| 1 | The 31B training leaves out operator engineering artifacts, such as customer and equipment configuration records, and OSS/BSS workflow tooling | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| 2 | For high-impact operational use, deploy the 31B with retrieval, source attribution, validation checks, and human review | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#intended-use) |
| 3 | The 31B targets English-language use, and all its quality claims are text-only | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |
| 4 | Use the Decision model's label probabilities for confidence thresholds and routing; serve it on vLLM 0.26 or 0.30 | model card | [OTel-2.0-Decision-26B-A4B-4bit model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) |
| 5 | The Safety model is trained to refuse when retrieved context is insufficient | model card | [OTel-LLM-12B-Safety model card](https://huggingface.co/farbodtavakkoli/OTel-LLM-12B-Safety) |
| 6 | Course 202 builds an agent that calls a trained fraud model as a tool: the model scores, the agent reasons, and a human approves | project documentation | [Agent-school 202 Fraud Triage](https://github.com/open-experiments/agent-school/blob/30458bda61cdc1ea939ce7d1fe6b8d425ed2bbad/202-fraud-triage/README.md) |
| 7 | TMF629 is the TM Forum Open API for creating, updating, retrieving, and deleting customer records, with event notifications | project documentation | [TMF629 Customer Management](https://github.com/tmforum-apis/TMF629_CustomerManagement) |
| 8 | The EDPB endorsed the Article 29 Working Party guidelines on automated individual decision-making and profiling under the GDPR | project documentation | [EDPB guidelines on automated decision-making and profiling](https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/automated-decision-making-and-profiling_en) |

## Deploy and verify

_Stub: this catalog entry has no deploy steps yet._

## Limitations

- It never scores churn; your own model does, and the LLM explains the score it returns.
- It never contacts a customer or changes an account; an approver reviews every retention offer.
- It draws no legal conclusion on profiling; your data protection officer and legal team do.
- The Decision label probabilities count as uncalibrated until you calibrate them on your own cases.
- The quality claims cover English only, so explanations in another language need their own evaluation.
