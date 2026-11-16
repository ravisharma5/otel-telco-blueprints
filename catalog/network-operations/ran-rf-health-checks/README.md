---
id: "UC-OPS-04"
type: "use-case"
title: "RAN and RF health checks"
doc_status: draft
domain: "network-operations"
flagship: false
depth: "entry"
otel_slots: ["classification", "llm", "safety", "decision"]
autonomy_ceiling: "recommend-with-approval"
tmf_an_level_target: 2
placement_tier: ["regional", "core"]
one_liner: "Explains RAN and RF health findings that analytical tools compute, and recommends parameter changes to a human approver. Never changes a cell itself. Depends on your performance counters, your own analysis tools, and a retrained Classification head."
platform_blueprints: ["PB-01", "PB-02", "PB-03", "PB-04", "PB-05", "PB-06", "PB-07"]
agent_school: [101]
card:
  goal: "sla-energy"
  summary: "Explains cell health findings from your performance counters and radio measurements, and proposes parameter changes for an engineer to approve."
  outcome: "Engineers spot degrading cells sooner and get a cited reason with each proposed change."
  audience: "RAN optimisation engineers, change approvers, and risk owners"
  measures: ["Time to spot a degrading cell", "Proposals accepted by approvers"]
  risk: "A wrong parameter change could hurt coverage, so an approver signs off each one."
placement:
  far-edge: {runs: [], note: "Not used: health checks read counters collected at the regional site."}
  regional: {runs: ["classification", "safety", "decision", "llm-small"], note: "Fault labels, the Safety check, the gate label, and routine health notes run here."}
  core: {runs: ["llm-large"], note: "The large LLM writes each parameter-change proposal."}
---

<!-- Writing rules: framework/style-guide.md. Name each component by its role and the Red Hat product used. Write no product support status. -->

# RAN and RF health checks

## At a glance

| Field | Value |
|---|---|
| One-liner | Explains RAN and RF health findings that analytical tools compute, and recommends parameter changes to a human approver. Never changes a cell itself. Depends on your performance counters, your own analysis tools, and a retrained Classification head. |
| Problem | Engineers scan cell counters and radio measurements by hand, and degrading cells go unnoticed until customers complain; the KPI is time to spot a degrading cell |
| Audience | RAN optimisation engineers, change approvers, and risk owners |
| OTel slots | `classification`: labels the likely fault; `llm`: explains the finding and drafts proposals; `safety`: abstain on weak evidence; `decision`: the gate label |
| Autonomy ceiling | Recommend with approval |
| Placement tier | Regional and core |
| Agent-school courses | 101 in the [agent-school roadmap](https://github.com/open-experiments/agent-school/blob/main/docs/RoadMap.md) |

## Problem and value

Cell performance counters and radio measurements show coverage, interference, and load problems before customers notice them.
Engineers scan them by hand across thousands of cells, and slow degradation slips through.
This entry has your analysis tools compute the numbers, labels the likely fault, and explains each finding; any parameter change goes to an approver.
The KPIs are time to spot a degrading cell and the share of proposals approvers accept.
Any gain is a target, measured against a shadow-stage baseline.

## How it works

_Stub: this catalog entry has no worked example or diagram yet._

## What you need

- [ ] Models: the four slots, chosen from the family in [PB-01](../../../platform/intake-model-selection/README.md), each pinned by revision with its licence chain recorded
- [ ] Platform blueprints: evaluation ([PB-02](../../../platform/evaluation-acceptance/README.md)), adaptation ([PB-03](../../../platform/adaptation/README.md)), serving and routing ([PB-04](../../../platform/serving-routing-placement/README.md)), integration ([PB-05](../../../platform/integration/README.md)), safety gating ([PB-06](../../../platform/safety-autonomy-gating/README.md)), and the action layer ([PB-07](../../../platform/action-layer/README.md))
- [ ] Components: one product for each role in the components table
- [ ] Analysis tools: your own tested tools compute every KPI and radio statistic, and the LLM explains their output; it never computes the numbers itself
- [ ] Integrations: read-only access to performance counters and cell configuration under the deny-unless-allowed rule in [PB-05](../../../platform/integration/README.md#per-tool-authorization)
- [ ] Classification head: retrained on your fault taxonomy, as [PB-03](../../../platform/adaptation/README.md) sets out
- [ ] Approval: every parameter change goes through the action layer, and the approver accepts or rejects it there
- [ ] Decision engine: vLLM 0.26 or 0.30 on CUDA or ROCm, as the [Decision model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) states
- [ ] Placement: the regional site runs Classification, Safety, Decision, and the small LLM. The core runs the large LLM.

| Component role | Red Hat product used |
|---|---|
| Inference engine for every slot | Red Hat AI Inference (vLLM) |
| Serving platform | Red Hat OpenShift AI with KServe |
| Tool gateway for the analysis tools | MCP gateway in Red Hat Connectivity Link |
| Training for the Classification head | Training Hub in Red Hat OpenShift AI |
| Action orchestration: gate, approval, rollout, and audit | Automation Orchestrator for Red Hat Ansible Automation Platform |

Key flags for each slot, copied from [PB-04](../../../platform/serving-routing-placement/README.md#key-flags-per-slot). Start the small LLM and the Safety slot with their own pinned revisions and no tool-calling flags.

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

### What you must add

| Gap | What you add | Source |
|---|---|---|
| KPI and RF data | Your performance counters and radio measurements, because the card leaves KPIs and RF data out of training | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| Computed numbers | Your own tested analysis tools that compute each KPI from the counters, because the card asks for validation checks in high-impact use | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#intended-use) |
| Fault classes | The Classification head retrained on your fault taxonomy, because the shipped head covers eight synthetic drive-test classes | [OTel-LLM-8.3B-Classification model card](https://huggingface.co/farbodtavakkoli/OTel-LLM-8.3B-Classification) |
| Gate labels | A gate set of past parameter changes labelled by your approvers, because the Decision label probabilities aren't calibrated for your workload | [OTel-2.0-Decision-26B-A4B-4bit model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) |
| Language scope | Tests in every language your engineers read findings in, because the card's quality claims cover English text only | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |

## Governance

Each action request passes the [decision gate](../../../architecture/decision-gate.md), and the outcome never exceeds the policy ceiling for its class.
The outcome is the lower of the model label and the policy ceiling for the capability and risk class, so it never exceeds either. A STOP label forces STOP at every stage.
Every action class begins at the shadow stage, where the outcome is LOOK. A confirmed false ACT drops the use case and its action class back one stage, as [PB-06](../../../platform/safety-autonomy-gating/README.md#staged-autonomy) sets out.

| Action | Gate outcome (LOOK/NOTIFY/REVIEW/ACT/STOP) | Approval | AI Act class |
|---|---|---|---|
| Post a health note on the cell's ticket, `notify` | NOTIFY, from the assist stage up | None | Recorded by your legal team in the classification record |
| Propose a parameter change such as tilt or power, `write_high` | REVIEW, from the recommend stage up | The `approver` role | Recorded by your legal team in the classification record |
| Any action the label marks STOP | STOP | None | Recorded by your legal team in the classification record |

| Parameter | What it controls | Who sets it | How to calibrate |
|---|---|---|---|
| Classification per-class recall floor | The lowest recall for each fault class in your taxonomy | Risk owner, with subject-matter expert (SME) review | [Evaluation and acceptance](../../../platform/evaluation-acceptance/README.md): use SME labels on a temporal holdout, so test cases come after training cases |
| Classification other-or-abstain recall floor | The lowest recall for faults outside the taxonomy | Risk owner | Hold out fault types the model never saw and check they land in other or abstain |
| Decision false-ACT budget | The highest false-ACT rate accepted on parameter-change proposals | Risk owner | [Evaluation and acceptance](../../../platform/evaluation-acceptance/README.md#false-act-method): use the false-ACT method on a gate set of past changes |
| Ceiling for notify requests | The highest outcome for health notes | Risk owner, with SME review | Review health notes for duplicates and noise |
| Ceiling for high-risk writes | The highest outcome for parameter changes | Risk owner | Keep it at REVIEW until the risk owner signs off on canary evidence |
| Safety abstain-recall floor | The lowest share of insufficient-context items where the Safety slot abstains | Risk owner, with SME review | Remove the relevant counters from items and measure correct abstention |

This page gives no default values. Each owner sets the value with SME review and versions it with the policy that `policy_version` names.

## Sources

Each key claim links its source, as set out in [the Sources table](../../../framework/definitions.md#sources-table).

| # | Claim | Basis | Source |
|---|---|---|---|
| 1 | The 31B training leaves out KPIs, 5G performance metrics, and RF and spectral data | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| 2 | For high-impact operational use, deploy the 31B with retrieval, source attribution, validation checks, and human review | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#intended-use) |
| 3 | The 31B targets English-language use, and all its quality claims are text-only | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |
| 4 | The Classification model's head predicts eight root-cause classes from the synthetic TeleLogs drive-test dataset | model card | [OTel-LLM-8.3B-Classification model card](https://huggingface.co/farbodtavakkoli/OTel-LLM-8.3B-Classification) |
| 5 | Use the Decision model's label probabilities for confidence thresholds and routing; serve it on vLLM 0.26 or 0.30 | model card | [OTel-2.0-Decision-26B-A4B-4bit model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) |
| 6 | TeleLogs is a dataset of annotated 5G troubleshooting problems, and open reasoning LLMs struggled on it without domain adaptation | research | [TeleLogs paper](https://arxiv.org/abs/2507.21974) |
| 7 | TS 28.552 specifies 5G performance measurements, and TS 38.215 specifies NR physical layer measurements | project documentation | [3GPP TS 28.552](https://www.3gpp.org/DynaReport/28552.htm), [3GPP TS 38.215](https://www.3gpp.org/DynaReport/38215.htm) |

## Deploy and verify

_Stub: this catalog entry has no deploy steps yet._

## Limitations

- The entry never changes a cell on its own; an approver accepts every parameter change through the action layer.
- It explains what the analysis tools compute; it doesn't replace them.
- The shipped Classification head knows drive-test classes only, so it needs your fault taxonomy first.
- The Decision label probabilities count as uncalibrated until you calibrate them on your own changes.
- The quality claims cover English only, so findings in another language need their own evaluation.
