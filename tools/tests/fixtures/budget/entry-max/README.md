---
id: "UC-DEMO-03"
type: "use-case"
title: "Fictional widget fault triage (maximal entry fixture)"
doc_status: "review"
domain: "demo"
flagship: false
depth: "entry"
adaptation:
  rung: "head-retrain"
  expertise: ["taxonomy", "golden-set", "gate-labels", "corpus"]
  bring:
    - {item: "Fictional widget fault taxonomy", domains: ["oss-bss"], mechanism: "classification-labels"}
    - {item: "Fictional widget manuals", domains: ["oss-bss"], mechanism: "rag-corpus"}
    - {item: "Fictional widget action ceilings", domains: ["oss-bss"], mechanism: "gate-policy"}
sandbox:
  fit: "none"
  why: "Reads fictional widget records; the agent runs no code"
otel_slots: ["embedding", "reranker", "safety", "decision", "llm", "classification"]
autonomy_ceiling: "recommend-with-approval"
tmf_an_level_target: 2
placement_tier: ["regional", "core"]
one_liner: "Triages fictional widget faults and recommends fixes for approval. Depends on retrieval, the decision gate, and read-only widget tools."
platform_blueprints: ["PB-01", "PB-02", "PB-04", "PB-05", "PB-06", "PB-07"]
agent_school: [301, 401]
card:
  goal: "incidents"
  summary: "Labels the likely cause of each fictional widget fault and proposes a fix that an approver accepts or rejects."
  outcome: "Fictional engineers find the cause of a widget fault sooner and fix it with approval."
  audience: "Fictional operations engineers, approvers, and risk owners"
  measures: ["Mean time to identify", "Fixes approved unchanged"]
  risk: "A wrong cause label sends engineers down the wrong path until review."
placement:
  far-edge:
    runs: []
    note: "Not used: triage runs at the regional site."
  regional:
    runs: ["llm-small", "safety", "decision", "classification"]
    note: "Triage, cause labels, abstention, and the gate run here."
  core:
    runs: ["llm-large", "embedding", "reranker"]
    note: "Retrieval and the large LLM for long fault histories run here."
---

> Fictional maximal catalog entry that sets and guards the entry word budget. Not a real blueprint.

# Fictional widget fault triage

## At a glance

| Field | Value |
|---|---|
| One-liner | Triages fictional widget faults and recommends fixes for approval. Depends on retrieval, the decision gate, and read-only widget tools. |
| Problem | Widget fault storms bury the cause, and engineers sort alerts by hand; the KPI is mean time to identify |
| Audience | Fictional operations engineers, approvers, and risk owners |
| OTel slots | `classification`: labels the likely cause; `llm`: the triage agent; `safety`: abstains on thin evidence; `decision`: the gate label; `embedding` and `reranker`: retrieval |
| Autonomy ceiling | Recommend with approval |
| Placement tier | Regional for triage; core for retrieval and long fault histories |
| Agent-school courses | 301 and 401 in the [agent-school roadmap](https://github.com/open-experiments/agent-school/blob/main/docs/RoadMap.md) |

## Problem and value

A fictional power dip can raise dozens of widget alerts at one site.
Engineers sort them by hand to find the one cause, and the fix waits.
This entry labels the likely cause, writes a triage note, and proposes a fix for approval.
The KPIs are mean time to identify and the share of fixes approved unchanged.
Any time saving is a target, measured against a shadow-stage baseline.

## How it works

_Stub: this catalog entry has no worked example or diagram yet._

## What you need

- [ ] Models: the six slots, chosen from the family in [PB-01](../../../../../platform/intake-model-selection/README.md), each pinned by revision with its licence chain recorded
- [ ] Platform blueprints: the pages for [PB-02](../../../../../platform/evaluation-acceptance/README.md), [PB-04](../../../../../platform/serving-routing-placement/README.md), [PB-05](../../../../../platform/integration/README.md), [PB-06](../../../../../platform/safety-autonomy-gating/README.md), and [PB-07](../../../../../platform/action-layer/README.md)
- [ ] Components: one product for each role in the components table
- [ ] Integrations: read-only widget inventory and alert tools, denied unless allowed, as [PB-05](../../../../../platform/integration/README.md) sets out
- [ ] Tools and data: widget alert history and runbooks with usage rights
- [ ] Data and adaptation: retrieval and skills first; an adapter only when the acceptance suite shows a gap
- [ ] Retrieval: an index built with the Embedding slot, rebuilt whenever that checkpoint changes
- [ ] Gate: the Decision slot labels each action request, and the Safety slot abstains on thin evidence
- [ ] Regional site: one GPU that fits the small LLM, Safety, Decision, and Classification
- [ ] Core: a GPU pool for the large LLM, Embedding, and Reranker
- [ ] Decision engine: vLLM 0.26 or 0.30 on CUDA or ROCm, as the [Decision model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) states
- [ ] Placement: the regional site runs the small LLM, Safety, Decision, and Classification. The core runs the large LLM, Embedding, and Reranker.

| Component role | Red Hat product used |
|---|---|
| Inference engine for every slot | Red Hat AI Inference (vLLM) |
| Model registry that pins each revision | Model Registry in Red Hat OpenShift AI |
| Tool gateway for per-tool authorization | MCP gateway in Red Hat Connectivity Link |
| Evaluation runs for the acceptance suite | EvalHub in Red Hat OpenShift AI |
| Vector store for the retrieval index | Demo vector store (fictional) |

Key flags for each slot, copied from [PB-04](../../../../../platform/serving-routing-placement/README.md#key-flags-per-slot). Start the Safety slot with its own pinned revision and no tool-calling flags.

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
| Task data | Replayed widget faults with causes your engineers checked | [replay set](../../sources/replay.jsonl) |
| Evaluation | An acceptance suite and gate set for your own fault types | [eval spec](../../sources/eval-spec.md) |
| Cause labels | Your fault taxonomy, because the Classification head ships with other classes | [Classification card](https://huggingface.co/farbodtavakkoli/OTel-LLM-8.3B-Classification) |
| Integrations | Read-only tools for your widget inventory and alert systems | [acceptance spec](../../sources/acceptance-spec.md) |
| Language scope | Tests in every language your engineers write in, because the card targets English | [LLM card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |
| Gate labels | A gate set with your own action classes, because the card labels generic actions | [Decision model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) |

## Governance

Each action request passes the [decision gate](../../../../../architecture/decision-gate.md), and the outcome never exceeds the policy ceiling for its class.
The outcome is the lower of the model label and the policy ceiling for the capability and risk class, so it never exceeds either. A STOP label forces STOP at every stage.

| Action | Gate outcome (LOOK/NOTIFY/REVIEW/ACT/STOP) | Approval | AI Act class |
|---|---|---|---|
| Write a triage note to the fault record, `notify` | NOTIFY, from the assist stage up | None | Recorded by your legal team (fictional) |
| Propose a fix such as a widget restart, `write_low` | REVIEW, from the recommend stage up | The `approver` role | Recorded by your legal team (fictional) |
| Any action the label marks STOP | STOP | None | Recorded by your legal team (fictional) |

| Parameter | What it controls | Who sets it | How to calibrate |
|---|---|---|---|
| Classification per-class recall floor | The lowest recall for each cause class | Risk owner, with SME review | Use SME labels on a temporal holdout |
| Safety abstention threshold | When the Safety slot abstains | Risk owner | Replay unclear faults and count wrong labels |
| Decision false-ACT budget | The highest false-ACT rate accepted | Risk owner | Use the false-ACT method on the gate set |
| Ceiling for low-risk writes | The highest outcome for reversible fixes | Risk owner | Raise it only after a clean canary window |

This page gives no default values. Each owner sets the value with SME review and versions it with the policy that `policy_version` names.

| Activity | Responsible | Accountable | Consulted | Informed |
|---|---|---|---|---|
| Tune Safety slot abstention | Platform team | Risk owner | SME | Business owner |
| Approve a proposed fix | Approver | Risk owner | SME | Business owner |

## Sources

Each key claim links its source, as set out in [the Sources table](../../../../../framework/definitions.md#sources-table).

| # | Claim | Basis | Source |
|---|---|---|---|
| 1 | The LLM card targets English-language use | model card | [LLM card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |
| 2 | The Decision card names its engine versions and labels | model card | [Decision model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) |
| 3 | The Classification head ships with its own classes | model card | [Classification card](https://huggingface.co/farbodtavakkoli/OTel-LLM-8.3B-Classification) |
| 4 | Demo teams triage widget faults with a replay set | industry use case | [replay set](../../sources/replay.jsonl) |
| 5 | An acceptance suite gates each promotion | project documentation | [eval spec](../../sources/eval-spec.md) |
| 6 | Read-only tools pass an acceptance check before use | project documentation | [acceptance spec](../../sources/acceptance-spec.md) |

## Deploy and verify

_Stub: this catalog entry has no deploy steps yet._

## Limitations

- This entry never applies a fix on its own; every fix needs approval.
- The Classification head knows other classes until you train it on your taxonomy.
- The LLM card targets English, so test every other language first.
- A new Embedding checkpoint forces a full rebuild of the retrieval index.
- The Decision engine runs on the card's vLLM versions, not the current Red Hat AI Inference release.
- Fault storms across many sites need your own correlation step first.
