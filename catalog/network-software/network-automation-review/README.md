---
id: "UC-SW-02"
type: "use-case"
title: "Network automation review"
doc_status: done
domain: "network-software"
flagship: false
depth: "entry"
adaptation:
  rung: "retrieval"
  expertise: ["golden-set", "gate-labels", "corpus"]
  bring:
    - {item: "Vendor command-line and NOS references", domains: ["transport-ip"], mechanism: "rag-corpus"}
    - {item: "Change repository with past reviewed changes", domains: ["transport-ip"], mechanism: "rag-corpus"}
    - {item: "Rollout ceilings and approver roles", domains: ["transport-ip"], mechanism: "gate-policy"}
sandbox:
  fit: "execution"
  why: "Runs YANG validation, NETCONF validate, and Ansible check mode"
otel_slots: ["embedding", "reranker", "safety", "decision", "llm"]
autonomy_ceiling: "recommend-with-approval"
tmf_an_level_target: 2
placement_tier: ["regional", "core"]
one_liner: "Reviews network automation changes and recommends approval to a human approver. Never applies a change itself. Depends on schema checks and dry runs outside the model and on the Safety and Decision slots."
platform_blueprints: ["PB-01", "PB-02", "PB-03", "PB-04", "PB-05", "PB-06", "PB-07", "PB-08", "PB-11"]
clarity_reviewed: "2026-11-17"
agent_school: [301]
card:
  goal: "change"
  summary: "Reviews proposed network automation changes against schema checks, dry runs, and your standards, then recommends approval to the change approver."
  outcome: "Reviewers catch broken playbooks and configurations before rollout, and approve sound changes sooner."
  audience: "Network automation engineers, change approvers, and risk owners"
  measures: ["Defects caught before rollout", "Time to review a change"]
  risk: "A missed defect could reach the network, so an approver signs off every change."
placement:
  far-edge: {runs: [], note: "Not used: change review doesn't need to run at the cell site."}
  regional: {runs: ["embedding", "reranker", "safety", "decision"], note: "Retrieval, the Safety check, and the gate label run here."}
  core: {runs: ["llm-large"], note: "The large LLM writes each review note."}
---

<!-- Writing rules: framework/style-guide.md. Name each component by its role and the Red Hat product used. Write no product support status. -->

# Network automation review

## At a glance

| Field | Value |
|---|---|
| One-liner | Reviews network automation changes and recommends approval to a human approver. Never applies a change itself. Depends on schema checks and dry runs outside the model and on the Safety and Decision slots. |
| Problem | Playbooks, YANG configurations, and automation packages wait in review queues, and defects slip through; the KPI is defects caught before rollout |
| Audience | Network automation engineers, change approvers, and risk owners |
| OTel slots | `embedding` and `reranker`: retrieval of your standards and vendor documents; `safety`: abstain on weak evidence; `decision`: the gate label; `llm`: writes the review note |
| Autonomy ceiling | Recommend with approval |
| Placement tier | Regional and core |
| Agent-school courses | 301 in the [agent-school roadmap](https://github.com/open-experiments/agent-school/blob/main/docs/RoadMap.md) |

## Problem and value

Network automation changes, such as Ansible playbooks, NETCONF configurations, and intent packages, queue for engineering review.
Reviewers check each one against schemas, vendor documents, and house standards by hand, and defects still reach rollout.
This entry runs the schema checks and dry runs as tools, writes a cited review note, and recommends approval or rejection to an approver.
The KPIs are defects caught before rollout and time to review a change.
Any gain is a target, measured against a shadow-stage baseline.

## How it works

_Stub: this catalog entry has no worked example or diagram yet._

## What you need

- [ ] Models: the five slots, chosen from the family in [PB-01](../../../platform/intake-model-selection/README.md), each pinned by revision with its licence chain recorded
- [ ] Platform blueprints: evaluation ([PB-02](../../../platform/evaluation-acceptance/README.md)), serving and routing ([PB-04](../../../platform/serving-routing-placement/README.md)), integration ([PB-05](../../../platform/integration/README.md)), safety gating ([PB-06](../../../platform/safety-autonomy-gating/README.md)), the action layer ([PB-07](../../../platform/action-layer/README.md)), and the sandbox ([PB-08](../../../platform/security-identity-sandbox/README.md))
- [ ] Components: one product for each role in the components table
- [ ] Checks: the YANG validation, NETCONF validate, and Ansible check mode run in the sandbox, outside the model, and the review cites their output
- [ ] Integrations: read-only access to the change repository and the check tools, denied unless allowed, as [PB-05](../../../platform/integration/README.md) sets out
- [ ] Approval: every rollout goes through the action layer, and the approver accepts or rejects it there
- [ ] Decision engine: vLLM 0.26 or 0.30 on CUDA or ROCm, as the [Decision model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) states
- [ ] Placement: the regional site runs Embedding, Reranker, Safety, and Decision. The core runs the large LLM.

| Component role | Red Hat product used |
|---|---|
| Inference engine for every slot | Red Hat AI Inference (vLLM) |
| Serving platform | Red Hat OpenShift AI with KServe |
| Action orchestration: gate, approval, rollout, and audit | Automation Orchestrator for Red Hat Ansible Automation Platform |
| Dry runs of playbook changes | Red Hat Ansible Automation Platform |
| Sandbox for the check tools | OpenShift sandboxed containers |
| Vector store for standards and vendor documents | Your choice; this design names no product |

Key flags for each slot, copied from [PB-04](../../../platform/serving-routing-placement/README.md#key-flags-per-slot). Start the Safety slot with its own pinned revision and no tool-calling flags.

```text
# LLM 31B (pin the revision; text-only; tool calling)
--revision <sha> --enable-auto-tool-choice --tool-call-parser gemma4 \
--limit-mm-per-prompt '{"image": 0, "audio": 0}'
# Decision (card recipe)
--revision <sha> --max-logprobs 64 --enable-prefix-caching --max-model-len 16384
# Classification (Gemma3TextForSequenceClassification) and Reranker (num_labels=1)
--runner pooling --convert classify        # endpoints /classify, /v1/score, /rerank
# Embedding
--runner pooling --convert embed           # endpoint /v1/embeddings
```

Any component can be replaced. The Red Hat products named here show one way to build this design.

### What you bring

<!-- generated:what-you-bring start -->

| Model change | Your expertise | How far to climb |
|---|---|---|
| No model change: retrieval over your corpus | A golden set your experts label; gate labels from your approvers; your domain corpus | Configure first, and train only on a measured gap, as [PB-03 Adaptation](../../../platform/adaptation/README.md) sets out |

| Item | Network component | Mechanism | Owner | Matrix row |
|---|---|---|---|---|
| Vendor command-line and NOS references | Transport and IP | RAG corpus | Operations engineer | [Transport and IP](../../../platform/bring-your-own-data/README.md#domain-transport-and-ip) |
| Change repository with past reviewed changes | Transport and IP | RAG corpus | Operations engineer | [Transport and IP](../../../platform/bring-your-own-data/README.md#domain-transport-and-ip) |
| Rollout ceilings and approver roles | Transport and IP | Gate and action-layer policy | Risk owner | [Transport and IP](../../../platform/bring-your-own-data/README.md#domain-transport-and-ip) |

<!-- generated:what-you-bring end -->

### Sandbox

<!-- generated:sandbox start -->

| Sandbox fit | Trigger on this page | Where to read |
|---|---|---|
| Sandbox the tools and code: run them in their own micro-VM | Runs YANG validation, NETCONF validate, and Ansible check mode | [PB-08: when a use case needs a sandbox](../../../platform/security-identity-sandbox/README.md#when-a-use-case-needs-a-sandbox) |

<!-- generated:sandbox end -->

### What you must add

| Gap | What you add | Source |
|---|---|---|
| Checks outside the model | Schema validation and dry runs as tools, because a NETCONF device validates a full configuration for syntax and semantic errors before it applies it | [RFC 6241 validate capability](https://www.rfc-editor.org/rfc/rfc6241#section-8.6) |
| Procedure evaluation | A set of past changes your engineers reviewed, scored before the shadow stage, because the card reports no validation against methods of procedure | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#operational-procedure-mop-validation-not-performed) |
| Vendor documents | Vendor command-line and NOS references in retrieval, because the card's training leaves them out | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| Gate labels | A gate set of past changes labelled by your approvers, because the Decision label probabilities aren't calibrated for your workload | [OTel-2.0-Decision-26B-A4B-4bit model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) |
| Language scope | Tests in every language your engineers write change notes in, because the card's quality claims cover English text only | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |

## Governance

Each action request passes the [decision gate](../../../architecture/decision-gate.md), and the outcome never exceeds the policy ceiling for its class.
The outcome is the lower of the model label and the policy ceiling for the capability and risk class, so it never exceeds either. A STOP label forces STOP at every stage.
Every action class begins at the shadow stage, where the outcome is LOOK.

| Action | Gate outcome (LOOK/NOTIFY/REVIEW/ACT/STOP) | Approval | AI Act class |
|---|---|---|---|
| Post a review note on the change, `notify` | NOTIFY, from the assist stage up | None | Recorded by your legal team in the classification record |
| Recommend a reviewed change for rollout, `write_high` | REVIEW, from the recommend stage up | The `approver` role | Recorded by your legal team in the classification record |
| Any action the label marks STOP | STOP | None | Recorded by your legal team in the classification record |

| Parameter | What it controls | Who sets it | How to calibrate |
|---|---|---|---|
| Decision false-ACT budget | The highest false-ACT rate accepted on rollout recommendations | Risk owner | [Evaluation and acceptance](../../../platform/evaluation-acceptance/README.md#false-act-method): use the false-ACT method on a gate set of past changes |
| Decision REVIEW band | The probability range that sends a recommendation to a human | Risk owner, with subject-matter expert (SME) review | Set from the calibration curve and the human review load |
| Ceiling for notify requests | The highest outcome for review notes | Risk owner, with SME review | Review notes for duplicates and noise |
| Ceiling for high-risk writes | The highest outcome for rollouts | Risk owner | Keep it at REVIEW until the risk owner signs off on canary evidence |
| Required approver role per action class | Which role approves REVIEW for each action class | Risk owner | Check approval times and overrides per class in the trace |
| Safety abstain-recall floor | The lowest share of insufficient-context items where the Safety slot abstains | Risk owner, with SME review | Remove the relevant standards and vendor passages from items and measure correct abstention |

This page gives no default values. Each owner sets the value with SME review and versions it with the policy that `policy_version` names.

| Activity | Responsible | Accountable | Consulted | Informed |
|---|---|---|---|---|
| Approve a REVIEW request | Approver | Business owner | SME | Operations engineer |

## Sources

Each key claim links its source, as set out in [the Sources table](../../../framework/definitions.md#sources-table).

| # | Claim | Basis | Source |
|---|---|---|---|
| 1 | The 31B lists network configuration assistance among its intended uses, and agentic use only where a larger system provides verified tools and validation | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#intended-use) |
| 2 | The card reports no check of the 31B against methods of procedure; such use needs its own procedure-based evaluation | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#operational-procedure-mop-validation-not-performed) |
| 3 | The 31B training leaves out vendor command-line and NOS documents | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| 4 | The 31B targets English-language use, and all its quality claims are text-only | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |
| 5 | Use the Decision model's label probabilities for confidence thresholds and routing; serve it on vLLM 0.26 or 0.30 | model card | [OTel-2.0-Decision-26B-A4B-4bit model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) |
| 6 | In check mode, Ansible makes no changes on remote systems and reports the changes it would make | project documentation | [Ansible check mode](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_checkmode.html) |
| 7 | A NETCONF device with the validate capability checks a full configuration for syntax and semantic errors before applying it | project documentation | [RFC 6241 validate capability](https://www.rfc-editor.org/rfc/rfc6241#section-8.6) |
| 8 | YANG models configuration data, state data, and notifications for network management protocols | project documentation | [RFC 7950](https://www.rfc-editor.org/rfc/rfc7950) |
| 9 | Nephio automates network functions on Kubernetes and treats intent as configuration data | project documentation | [Nephio documentation](https://docs.nephio.org/docs/) |

## Deploy and verify

_Stub: this catalog entry has no deploy steps yet._

## Limitations

- The entry never applies a change on its own; an approver accepts every rollout through the action layer.
- Its review cites the check tools; it doesn't replace them.
- The card reports no validation against methods of procedure, so test review quality on your own changes first.
- The Decision engine runs on the card's vLLM versions, so check your engine against that list.
- The quality claims cover English only, so change notes in another language need their own evaluation.
