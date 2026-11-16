---
id: "UC-RES-01"
type: "use-case"
title: "KPI root-cause reasoning"
doc_status: done
domain: "research"
flagship: false
depth: "entry"
adaptation:
  rung: "head-retrain"
  expertise: ["taxonomy", "golden-set", "gate-labels"]
  bring:
    - {item: "Root-cause taxonomy and SME-confirmed degradations", domains: ["ran"], mechanism: "classification-labels"}
    - {item: "KPI reasoning skill over your computed KPI data", domains: ["ran"], mechanism: "skill-manifest"}
    - {item: "Parameter change ceilings and approver roles", domains: ["ran"], mechanism: "gate-policy"}
otel_slots: ["classification", "llm", "safety", "decision"]
autonomy_ceiling: "recommend-with-approval"
tmf_an_level_target: 2
placement_tier: ["regional", "core"]
one_liner: "Reasons from a detected KPI degradation to its likely root cause, and recommends parameter changes to a human approver. Never changes the network itself. Depends on your KPI data, a retrained Classification head, and your own evaluation set."
platform_blueprints: ["PB-01", "PB-02", "PB-03", "PB-04", "PB-06", "PB-07", "PB-11"]
clarity_reviewed: "2026-11-16"
agent_school: [201]
card:
  goal: "incidents"
  summary: "Takes a KPI degradation your monitoring already found, reasons to its likely root cause, and proposes a parameter change for approval."
  outcome: "Engineers get a reasoned root cause and a proposed fix for each degradation, ready to check."
  audience: "Network performance engineers, change approvers, and risk owners"
  measures: ["Time to a confirmed root cause", "Proposals accepted by approvers"]
  risk: "A wrong root cause means a wrong change, so an approver signs off each one."
placement:
  far-edge: {runs: [], note: "Not used: the counters behind each KPI are collected regionally."}
  regional: {runs: ["classification", "safety", "decision"], note: "Root-cause labels, the Safety check, and the gate label run here."}
  core: {runs: ["llm-large"], note: "The large LLM writes the reasoning and each parameter proposal."}
---

<!-- Writing rules: framework/style-guide.md. Name each component by its role and the Red Hat product used. Write no product support status. -->

# KPI root-cause reasoning

## At a glance

| Field | Value |
|---|---|
| One-liner | Reasons from a detected KPI degradation to its likely root cause, and recommends parameter changes to a human approver. Never changes the network itself. Depends on your KPI data, a retrained Classification head, and your own evaluation set. |
| Problem | Finding why a KPI degraded takes an expert many steps across counters and configuration; the KPI is time to a confirmed root cause |
| Audience | Network performance engineers, change approvers, and risk owners |
| OTel slots | `classification`: labels the likely root cause; `llm`: writes the reasoning and proposals; `safety`: abstain on weak evidence; `decision`: the gate label |
| Autonomy ceiling | Recommend with approval |
| Placement tier | Regional and core |
| Agent-school courses | 201 in the [agent-school roadmap](https://github.com/open-experiments/agent-school/blob/main/docs/RoadMap.md) |

## Problem and value

Your monitoring finds that a KPI such as accessibility or throughput has degraded, but finding why takes an expert many steps.
This entry starts from that degradation, labels the likely root cause, explains the reasoning step by step, and proposes a parameter change for an approver.
It differs from [RAN and RF health checks](../../network-operations/ran-rf-health-checks/README.md), which watch cell counters to find degrading cells in the first place.
The KPIs are time to a confirmed root cause and the share of proposals approvers accept; any gain is a target, measured against a shadow-stage baseline.
This is a research item: the reasoning needs your own data and evaluation first.

## How it works

_Stub: this catalog entry has no worked example or diagram yet._

## What you need

- [ ] Models: the four slots, chosen from the family in [PB-01](../../../platform/intake-model-selection/README.md), each pinned by revision with its licence chain recorded
- [ ] Platform blueprints: evaluation ([PB-02](../../../platform/evaluation-acceptance/README.md)), adaptation ([PB-03](../../../platform/adaptation/README.md)), serving and routing ([PB-04](../../../platform/serving-routing-placement/README.md)), safety gating ([PB-06](../../../platform/safety-autonomy-gating/README.md)), and the action layer ([PB-07](../../../platform/action-layer/README.md))
- [ ] Components: one product for each role in the components table
- [ ] KPI data: your KPI series, counters, and configuration for the degraded scope, computed by your own tested tools; the LLM never computes the numbers
- [ ] Classification head: retrained on your root-cause taxonomy, as [PB-03](../../../platform/adaptation/README.md) sets out
- [ ] Approval: every parameter change goes through the action layer, and the approver accepts or rejects it there
- [ ] Decision engine: vLLM 0.26 or 0.30 on CUDA or ROCm, as the [Decision model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) states
- [ ] Placement: the regional site runs Classification, Safety, and Decision. The core runs the large LLM.

| Component role | Red Hat product used |
|---|---|
| Inference engine for every slot | Red Hat AI Inference (vLLM) |
| Serving platform | Red Hat OpenShift AI with KServe |
| Training for the Classification head | Training Hub in Red Hat OpenShift AI |
| Action orchestration: gate, approval, rollout, and audit | Automation Orchestrator for Red Hat Ansible Automation Platform |

Key flags for each slot, copied from [PB-04](../../../platform/serving-routing-placement/README.md#key-flags-per-slot). Start the Safety slot with its own pinned revision and no tool-calling flags.

```text
# LLM 31B (pin the revision; text-only; tool calling)
--revision <sha> --enable-auto-tool-choice --tool-call-parser gemma4 \
--limit-mm-per-prompt '{"image": 0, "audio": 0}'
# Decision (card recipe)
--revision <sha> --max-logprobs 64 --enable-prefix-caching --max-model-len 16384
# Classification (Gemma3TextForSequenceClassification) and Reranker (num_labels=1)
--runner pooling --convert classify        # endpoints /classify, /v1/score, /rerank
```

Any component can be replaced. The Red Hat products named here show one way to build this design.

### What you bring

<!-- generated:what-you-bring start -->

| Model change | Your expertise | How far to climb |
|---|---|---|
| Retrain the Classification head on your taxonomy; no other model changes | Your fault or alert taxonomy; a golden set your experts label; gate labels from your approvers | Configure first, and train only on a measured gap, as [PB-03 Adaptation](../../../platform/adaptation/README.md) sets out |

| Item | Network component | Mechanism | Owner | Matrix row |
|---|---|---|---|---|
| Root-cause taxonomy and SME-confirmed degradations | RAN | Classification labels | SME | [RAN](../../../platform/bring-your-own-data/README.md#domain-ran) |
| KPI reasoning skill over your computed KPI data | RAN | Skill or capability manifest | SME | [RAN](../../../platform/bring-your-own-data/README.md#domain-ran) |
| Parameter change ceilings and approver roles | RAN | Gate and action-layer policy | Risk owner | [RAN](../../../platform/bring-your-own-data/README.md#domain-ran) |

<!-- generated:what-you-bring end -->

### What you must add

| Gap | What you add | Source |
|---|---|---|
| KPI data | Your KPI series and counters, because the card leaves KPIs and 5G performance metrics out of training | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| Root-cause classes | The Classification head retrained on your taxonomy, because the shipped head covers eight synthetic TeleLogs drive-test classes | [OTel-LLM-8.3B-Classification model card](https://huggingface.co/farbodtavakkoli/OTel-LLM-8.3B-Classification) |
| Evaluation | A test set of your own past degradations with root causes your SMEs confirmed, because open reasoning models struggled on TeleLogs without domain adaptation | [TeleLogs paper](https://arxiv.org/abs/2507.21974) |
| Parameter changes | Every recommendation sent to an approver, because the card reports no check of the 31B against methods of procedure | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#operational-procedure-mop-validation-not-performed) |
| Language scope | Tests in every language your engineers read reasoning in, because the card's quality claims cover English text only | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |

## Governance

Each action request passes the [decision gate](../../../architecture/decision-gate.md), and the outcome never exceeds the policy ceiling for its class.
The outcome is the lower of the model label and the policy ceiling for the capability and risk class, so it never exceeds either. A STOP label forces STOP at every stage.
Every action class begins at the shadow stage, where the outcome is LOOK. A confirmed false ACT drops the use case and its action class back one stage, as [PB-06](../../../platform/safety-autonomy-gating/README.md#staged-autonomy) sets out.

| Action | Gate outcome (LOOK/NOTIFY/REVIEW/ACT/STOP) | Approval | AI Act class |
|---|---|---|---|
| Post a root-cause note on the degradation ticket, `notify` | NOTIFY, from the assist stage up | None | Recorded by your legal team in the classification record |
| Recommend a parameter change, `write_high` | REVIEW, from the recommend stage up | The `approver` role | Recorded by your legal team in the classification record |
| Any action the label marks STOP | STOP | None | Recorded by your legal team in the classification record |

| Parameter | What it controls | Who sets it | How to calibrate |
|---|---|---|---|
| Classification per-class recall floor | The lowest recall for each root-cause class in your taxonomy | Risk owner, with subject-matter expert (SME) review | [Evaluation and acceptance](../../../platform/evaluation-acceptance/README.md): use SME labels on a temporal holdout, so test cases come after training cases |
| Classification other-or-abstain recall floor | The lowest recall for root causes outside the taxonomy | Risk owner | Hold out root causes the model never saw and check they land in other or abstain |
| LLM groundedness floor | The lowest share of reasoning steps that the KPI data and configuration support | Risk owner, with SME review | Score SME-checked reasoning on past degradations with a calibrated judge |
| Decision false-ACT budget | The highest false-ACT rate accepted on parameter recommendations | Risk owner | [Evaluation and acceptance](../../../platform/evaluation-acceptance/README.md#false-act-method): use the false-ACT method on a gate set of past changes |
| Ceiling for high-risk writes | The highest outcome for parameter changes | Risk owner | Keep it at REVIEW until the risk owner signs off on canary evidence |
| Safety abstain-recall floor | The lowest share of insufficient-context items where the Safety slot abstains | Risk owner, with SME review | Remove the relevant counters from items and measure correct abstention |

This page gives no default values. Each owner sets the value with SME review and versions it with the policy that `policy_version` names.

## Sources

Each key claim links its source, as set out in [the Sources table](../../../framework/definitions.md#sources-table).

| # | Claim | Basis | Source |
|---|---|---|---|
| 1 | The 31B training leaves out KPIs and 5G performance metrics | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| 2 | The card reports no check of the 31B against methods of procedure, configuration changes included | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#operational-procedure-mop-validation-not-performed) |
| 3 | The 31B targets English-language use, and all its quality claims are text-only | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |
| 4 | The Classification model's head predicts eight root-cause classes from the synthetic TeleLogs drive-test dataset | model card | [OTel-LLM-8.3B-Classification model card](https://huggingface.co/farbodtavakkoli/OTel-LLM-8.3B-Classification) |
| 5 | Use the Decision model's label probabilities for confidence thresholds and routing; serve it on vLLM 0.26 or 0.30 | model card | [OTel-2.0-Decision-26B-A4B-4bit model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) |
| 6 | TeleLogs is a dataset of annotated 5G troubleshooting problems, and open reasoning LLMs struggled on it without domain adaptation | research | [TeleLogs paper](https://arxiv.org/abs/2507.21974) |
| 7 | TS 28.554 specifies 5G end-to-end key performance indicators | project documentation | [3GPP TS 28.554](https://www.3gpp.org/DynaReport/28554.htm) |

## Deploy and verify

_Stub: this catalog entry has no deploy steps yet._

## Limitations

- The entry never changes the network on its own; an approver accepts every parameter change through the action layer.
- It starts from a degradation your monitoring found; it doesn't detect degradations itself.
- The shipped Classification head knows synthetic drive-test classes only, so it needs your root-cause taxonomy first.
- The Decision label probabilities count as uncalibrated until you calibrate them on your own changes.
- The quality claims cover English only, so reasoning in another language needs its own evaluation.
