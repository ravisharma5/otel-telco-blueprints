---
id: "UC-OPS-09"
type: "use-case"
title: "Cross-domain OSS correlation"
doc_status: done
domain: "network-operations"
flagship: false
depth: "entry"
adaptation:
  rung: "head-retrain"
  expertise: ["taxonomy", "golden-set", "gate-labels", "tool-contracts", "corpus"]
  bring:
    - {item: "Cause taxonomy and labelled past incidents", domains: ["oss-bss"], mechanism: "classification-labels"}
    - {item: "Past incidents and tickets from your OSS tools", domains: ["oss-bss"], mechanism: "rag-corpus"}
    - {item: "Alarm, inventory, and performance read tools", domains: ["oss-bss"], mechanism: "tool-contract"}
    - {item: "Correlation skill and capability manifests", domains: ["oss-bss"], mechanism: "skill-manifest"}
    - {item: "Grouping ceilings and approver roles", domains: ["oss-bss"], mechanism: "gate-policy"}
otel_slots: ["classification", "embedding", "reranker", "safety", "decision", "llm"]
autonomy_ceiling: "recommend-with-approval"
tmf_an_level_target: 2
placement_tier: ["regional", "core"]
one_liner: "Correlates RAN, transport, and core alarms into one incident using topology and inventory, and recommends the grouping to a human approver. Never changes an OSS record itself. Depends on your alarm, inventory, and performance APIs and a retrained Classification head."
platform_blueprints: ["PB-01", "PB-02", "PB-03", "PB-04", "PB-05", "PB-06", "PB-07", "PB-09", "PB-11"]
clarity_reviewed: "2026-11-16"
agent_school: [301, 402]
card:
  goal: "incidents"
  summary: "Links alarms from RAN, transport, and core into one incident through topology and inventory, and proposes the grouping for approval."
  outcome: "Engineers see one incident per fault instead of a storm of alarms from each domain."
  audience: "Operations engineers, OSS owners, change approvers, and risk owners"
  measures: ["Alarms per incident", "Groupings accepted by approvers"]
  risk: "A wrong grouping could hide a second fault, so an approver signs off each one."
placement:
  far-edge: {runs: [], note: "Not used: correlation reads the OSS at the regional site."}
  regional: {runs: ["classification", "embedding", "reranker", "safety", "decision"], note: "Cause labels, retrieval, the Safety check, and the gate label run here."}
  core: {runs: ["llm-large"], note: "The large LLM writes each correlated incident summary."}
---

<!-- Writing rules: framework/style-guide.md. Name each component by its role and the Red Hat product used. Write no product support status. -->

# Cross-domain OSS correlation

## At a glance

| Field | Value |
|---|---|
| One-liner | Correlates RAN, transport, and core alarms into one incident using topology and inventory, and recommends the grouping to a human approver. Never changes an OSS record itself. Depends on your alarm, inventory, and performance APIs and a retrained Classification head. |
| Problem | One fault raises alarms in several domain tools, and each team chases its own share; the KPI is alarms per incident |
| Audience | Operations engineers, OSS owners, change approvers, and risk owners |
| OTel slots | `classification`: labels the likely cause; `embedding` and `reranker`: retrieval of runbooks and past incidents; `safety`: abstain on weak evidence; `decision`: the gate label; `llm`: writes the incident summary |
| Autonomy ceiling | Recommend with approval |
| Placement tier | Regional and core |
| Agent-school courses | 301 and 402 in the [agent-school roadmap](https://github.com/open-experiments/agent-school/blob/main/docs/RoadMap.md) |

## Problem and value

A fibre cut or a power event raises alarms in RAN, transport, and core tools at once.
Each domain team opens its own ticket, and nobody sees the shared cause until the teams compare notes.
This entry reads alarms, inventory, and performance data through read-only APIs, links them by topology, and proposes one incident to an approver.
The KPIs are alarms per incident and the share of groupings approvers accept.
Any gain is a target, measured against a shadow-stage baseline.

## How it works

_Stub: this catalog entry has no worked example or diagram yet._

## What you need

- [ ] Models: the six slots, chosen from the family in [PB-01](../../../platform/intake-model-selection/README.md), each pinned by revision with its licence chain recorded
- [ ] Platform blueprints: evaluation ([PB-02](../../../platform/evaluation-acceptance/README.md)), adaptation ([PB-03](../../../platform/adaptation/README.md)), serving and routing ([PB-04](../../../platform/serving-routing-placement/README.md)), integration ([PB-05](../../../platform/integration/README.md)), safety gating ([PB-06](../../../platform/safety-autonomy-gating/README.md)), the action layer ([PB-07](../../../platform/action-layer/README.md)), and quality operations ([PB-09](../../../platform/quality-operations/README.md))
- [ ] Components: one product for each role in the components table
- [ ] Integrations: alarm, inventory, and performance APIs as read-only tools under the deny-unless-allowed rule in [PB-05](../../../platform/integration/README.md#per-tool-authorization)
- [ ] Topology: a current map of which RAN, transport, and core resources depend on each other
- [ ] Classification head: retrained on your cause taxonomy, as [PB-03](../../../platform/adaptation/README.md) sets out
- [ ] Approval: every grouping goes through the action layer, and the approver accepts or rejects it there
- [ ] Decision engine: vLLM 0.26 or 0.30 on CUDA or ROCm, as the [Decision model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) states
- [ ] Placement: the regional site runs Classification, Embedding, Reranker, Safety, and Decision. The core runs the large LLM.

| Component role | Red Hat product used |
|---|---|
| Inference engine for every slot | Red Hat AI Inference (vLLM) |
| Serving platform | Red Hat OpenShift AI with KServe |
| Tool gateway for the OSS APIs | MCP gateway in Red Hat Connectivity Link |
| Training for the Classification head | Training Hub in Red Hat OpenShift AI |
| Action orchestration: gate, approval, rollout, and audit | Automation Orchestrator for Red Hat Ansible Automation Platform |
| Vector store for runbooks and past incidents | Your choice; this design names no product |

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
| Retrain the Classification head on your taxonomy; no other model changes | Your fault or alert taxonomy; A golden set your experts label; Gate labels from your approvers; A contract for each tool; Your domain corpus | Configure first, and train only on a measured gap, as [PB-03 Adaptation](../../../platform/adaptation/README.md) sets out |

| Item | Network component | Mechanism | Owner | Matrix row |
|---|---|---|---|---|
| Cause taxonomy and labelled past incidents | OSS and BSS | Classification labels | SME | [OSS and BSS](../../../platform/bring-your-own-data/README.md#domain-oss-and-bss) |
| Past incidents and tickets from your OSS tools | OSS and BSS | RAG corpus | Business owner | [OSS and BSS](../../../platform/bring-your-own-data/README.md#domain-oss-and-bss) |
| Alarm, inventory, and performance read tools | OSS and BSS | MCP tool contract | Platform team | [OSS and BSS](../../../platform/bring-your-own-data/README.md#domain-oss-and-bss) |
| Correlation skill and capability manifests | OSS and BSS | Skill or capability manifest | SME | [OSS and BSS](../../../platform/bring-your-own-data/README.md#domain-oss-and-bss) |
| Grouping ceilings and approver roles | OSS and BSS | Gate and action-layer policy | Risk owner | [OSS and BSS](../../../platform/bring-your-own-data/README.md#domain-oss-and-bss) |

<!-- generated:what-you-bring end -->

### What you must add

| Gap | What you add | Source |
|---|---|---|
| Alarm feed | Read access to your fault management system, for example through the TM Forum alarm API | [TMF642 Alarm Management](https://github.com/tmforum-apis/TMF642_AlarmManagement) |
| Topology and inventory | Read access to your resource inventory, for example through the TM Forum inventory API, kept current with the network | [TMF639 Resource Inventory](https://github.com/tmforum-apis/TMF639_ResourceInventory) |
| OSS workflow data | Past incidents and tickets from your OSS tools, because the card leaves fault consoles, ticketing, and change systems out of training | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| Cause classes | The Classification head retrained on your cause taxonomy, because the shipped head covers eight synthetic drive-test classes | [OTel-LLM-8.3B-Classification model card](https://huggingface.co/farbodtavakkoli/OTel-LLM-8.3B-Classification) |
| Gate labels | A gate set of past groupings labelled by your approvers, because the Decision label probabilities aren't calibrated for your workload | [OTel-2.0-Decision-26B-A4B-4bit model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) |
| Language scope | Tests in every language your engineers write tickets in, because the card's quality claims cover English text only | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |

## Governance

Each action request passes the [decision gate](../../../architecture/decision-gate.md), and the outcome never exceeds the policy ceiling for its class.
The outcome is the lower of the model label and the policy ceiling for the capability and risk class, so it never exceeds either. A STOP label forces STOP at every stage.
Every action class begins at the shadow stage, where the outcome is LOOK. A confirmed false ACT drops the use case and its action class back one stage, as [PB-06](../../../platform/safety-autonomy-gating/README.md#staged-autonomy) sets out.

| Action | Gate outcome (LOOK/NOTIFY/REVIEW/ACT/STOP) | Approval | AI Act class |
|---|---|---|---|
| Post a correlation note on each linked ticket, `notify` | NOTIFY, from the assist stage up | None | Recorded by your legal team in the classification record |
| Propose grouping the alarms under one incident, `write_low` | REVIEW, from the recommend stage up | The `approver` role | Recorded by your legal team in the classification record |
| Any action the label marks STOP | STOP | None | Recorded by your legal team in the classification record |

| Parameter | What it controls | Who sets it | How to calibrate |
|---|---|---|---|
| Classification per-class recall floor | The lowest recall for each cause class in your taxonomy | Risk owner, with subject-matter expert (SME) review | [Evaluation and acceptance](../../../platform/evaluation-acceptance/README.md): use SME labels on a temporal holdout, so test incidents come after training incidents |
| Classification other-or-abstain recall floor | The lowest recall for incidents outside the taxonomy | Risk owner | Hold out incident types the model never saw and check they land in other or abstain |
| Embedding and Reranker recall-at-k floor | The lowest share of questions with a correct passage in the top results | Platform team, with SME review | Label relevant runbook and incident passages for past incidents |
| Decision false-ACT budget | The highest false-ACT rate accepted on grouping proposals | Risk owner | [Evaluation and acceptance](../../../platform/evaluation-acceptance/README.md#false-act-method): use the false-ACT method on a gate set of past groupings |
| Ceiling for notify requests | The highest outcome for correlation notes | Risk owner, with SME review | Review correlation notes for duplicates and noise |
| Ceiling for low-risk writes | The highest outcome for alarm groupings | Risk owner | Raise it only after a canary window with no false ACT label |

This page gives no default values. Each owner sets the value with SME review and versions it with the policy that `policy_version` names.

## Sources

Each key claim links its source, as set out in [the Sources table](../../../framework/definitions.md#sources-table).

| # | Claim | Basis | Source |
|---|---|---|---|
| 1 | The 31B training leaves out OSS and incident tooling, such as fault consoles, ticketing, and change approval, and TM Forum familiarity is not experience running those systems | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| 2 | The 31B targets English-language use, and all its quality claims are text-only | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |
| 3 | The Classification model's head predicts eight root-cause classes from the synthetic TeleLogs drive-test dataset | model card | [OTel-LLM-8.3B-Classification model card](https://huggingface.co/farbodtavakkoli/OTel-LLM-8.3B-Classification) |
| 4 | Use the Decision model's label probabilities for confidence thresholds and routing; serve it on vLLM 0.26 or 0.30 | model card | [OTel-2.0-Decision-26B-A4B-4bit model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) |
| 5 | The TM Forum alarm API lists, acknowledges, clears, comments on, and groups alarms; the repository mirrors the official version under Apache 2.0 | project documentation | [TMF642 Alarm Management](https://github.com/tmforum-apis/TMF642_AlarmManagement) |
| 6 | The TM Forum resource inventory API exposes physical and logical resources | project documentation | [TMF639 Resource Inventory](https://github.com/tmforum-apis/TMF639_ResourceInventory) |
| 7 | The TM Forum performance API defines measurement collection jobs and performance indicator specifications | project documentation | [TMF628 Performance](https://github.com/tmforum-apis/TMF628_Performance) |

## Deploy and verify

_Stub: this catalog entry has no deploy steps yet._

## Limitations

- The entry never changes an OSS record on its own; an approver accepts every grouping through the action layer.
- Correlation is only as good as your topology and inventory, so a stale map gives wrong groupings.
- The shipped Classification head knows drive-test classes only, so it needs your cause taxonomy first.
- The Decision label probabilities count as uncalibrated until you calibrate them on your own incidents.
- The quality claims cover English only, so tickets in another language need their own evaluation.
