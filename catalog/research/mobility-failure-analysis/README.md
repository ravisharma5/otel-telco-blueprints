---
id: "UC-RES-02"
type: "use-case"
title: "5G mobility failure analysis"
doc_status: done
domain: "research"
flagship: false
depth: "entry"
adaptation:
  rung: "retrieval-and-skills"
  expertise: ["golden-set", "tool-contracts", "corpus"]
  bring:
    - {item: "Mobility procedure specifications with usage rights", domains: ["ran", "core-cnf"], mechanism: "rag-corpus"}
    - {item: "Event rebuild tools over radio and core traces", domains: ["ran", "core-cnf"], mechanism: "tool-contract"}
    - {item: "Mobility analysis skill and capability manifests", domains: ["ran"], mechanism: "skill-manifest"}
otel_slots: ["embedding", "reranker", "safety", "llm"]
autonomy_ceiling: "inform"
placement_tier: ["regional", "core"]
one_liner: "Explains a failed 5G handover or registration from rebuilt signalling and the 3GPP procedures, with citations. Informs only. Depends on your tools that rebuild each mobility event and your own failure cases."
platform_blueprints: ["PB-01", "PB-02", "PB-03", "PB-04", "PB-05", "PB-06", "PB-11"]
clarity_reviewed: "2026-11-16"
agent_school: []
card:
  goal: "incidents"
  summary: "Explains failed 5G handovers and registrations step by step, citing the 3GPP procedure that each failed message belongs to."
  outcome: "Engineers see where a mobility procedure broke, with the cited procedure step to check."
  audience: "Mobility and core signalling engineers"
  measures: ["Time to locate a failed step", "Explanations confirmed by engineers"]
  risk: "A wrong explanation sends engineers to the wrong node, so each one cites sources."
placement:
  far-edge: {runs: [], note: "Not used: signalling traces are collected at the regional site."}
  regional: {runs: ["embedding", "reranker", "safety"], note: "Retrieval over the procedures and the Safety check run here."}
  core: {runs: ["llm-large"], note: "The large LLM writes each step-by-step explanation."}
---

<!-- Writing rules: framework/style-guide.md. Name each component by its role and the Red Hat product used. Write no product support status. -->

# 5G mobility failure analysis

## At a glance

| Field | Value |
|---|---|
| One-liner | Explains a failed 5G handover or registration from rebuilt signalling and the 3GPP procedures, with citations. Informs only. Depends on your tools that rebuild each mobility event and your own failure cases. |
| Problem | A failed handover spans several interfaces and nodes, and engineers piece it together by hand; the KPI is time to locate the failed step |
| Audience | Mobility and core signalling engineers |
| OTel slots | `embedding` and `reranker`: find the procedure clauses; `safety`: abstain on weak evidence; `llm`: writes the explanation |
| Autonomy ceiling | Inform |
| Placement tier | Regional and core |
| Agent-school courses | None: no agent-school course covers this use case yet. See the [agent-school roadmap](https://github.com/open-experiments/agent-school/blob/main/docs/RoadMap.md) |

## Problem and value

A failed handover or registration leaves messages on several interfaces and nodes, and engineers rebuild the sequence by hand.
Your tools rebuild each mobility event from those sources, and this entry explains where it broke, citing the 3GPP procedure step for each failed message.
It informs only; engineers decide what to change.
The KPIs are time to locate the failed step and the share of explanations engineers confirm; any gain is a target, measured against a shadow-stage baseline.
This is a research item: the explanations need your own failure cases and evaluation first.

## How it works

_Stub: this catalog entry has no worked example or diagram yet._

## What you need

- [ ] Models: the four slots, chosen from the family in [PB-01](../../../platform/intake-model-selection/README.md), each pinned by revision with its licence chain recorded
- [ ] Platform blueprints: evaluation ([PB-02](../../../platform/evaluation-acceptance/README.md)), serving and routing ([PB-04](../../../platform/serving-routing-placement/README.md)), integration ([PB-05](../../../platform/integration/README.md)), and safety gating ([PB-06](../../../platform/safety-autonomy-gating/README.md))
- [ ] Components: one product for each role in the components table
- [ ] Event tools: your own tested tools rebuild each mobility event; the LLM explains their output and never reads raw traces
- [ ] Integrations: read-only tools through the MCP gateway, under the deny-unless-allowed rule in [PB-05](../../../platform/integration/README.md#per-tool-authorization)
- [ ] Corpora: each specification set has a filled usage-rights entry in the corpus register, as [PB-05](../../../platform/integration/README.md#knowledge-sources-and-usage-rights) requires
- [ ] Embedding revision: a new embedding checkpoint forces a full re-index, so record the revision with the index
- [ ] Placement: the regional site runs Embedding, Reranker, and Safety. The core runs the large LLM.

| Component role | Red Hat product used |
|---|---|
| Inference engine for every slot | Red Hat AI Inference (vLLM) |
| Serving platform | Red Hat OpenShift AI with KServe |
| Tool gateway for the event tools | MCP gateway in Red Hat Connectivity Link |
| Vector store for the specifications | Your choice; this design names no product |

Key flags for each slot, copied from [PB-04](../../../platform/serving-routing-placement/README.md#key-flags-per-slot). Start the Safety slot with its own pinned revision and no tool-calling flags.

```text
# LLM 31B (pin the revision; text-only; tool calling)
--revision <sha> --enable-auto-tool-choice --tool-call-parser gemma4 \
--limit-mm-per-prompt '{"image": 0, "audio": 0}'
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
| No model change: retrieval, a skill per role, and a capability manifest per tool | A golden set your experts label; a contract for each tool; your domain corpus | Configure first, and train only on a measured gap, as [PB-03 Adaptation](../../../platform/adaptation/README.md) sets out |

| Item | Network component | Mechanism | Owner | Matrix row |
|---|---|---|---|---|
| Mobility procedure specifications with usage rights | RAN; 5G core CNFs | RAG corpus | RAN: Operations engineer; 5G core CNFs: Platform team | [RAN](../../../platform/bring-your-own-data/README.md#domain-ran); [5G core CNFs](../../../platform/bring-your-own-data/README.md#domain-5g-core-cnfs) |
| Event rebuild tools over radio and core traces | RAN; 5G core CNFs | MCP tool contract | Platform team | [RAN](../../../platform/bring-your-own-data/README.md#domain-ran); [5G core CNFs](../../../platform/bring-your-own-data/README.md#domain-5g-core-cnfs) |
| Mobility analysis skill and capability manifests | RAN | Skill or capability manifest | SME | [RAN](../../../platform/bring-your-own-data/README.md#domain-ran) |

<!-- generated:what-you-bring end -->

### What you must add

| Gap | What you add | Source |
|---|---|---|
| Event rebuild | Tools that rebuild each mobility event from your radio, core, and interface traces, because the card leaves 5G core and inter-NF signalling out of training | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| Evaluation | A golden set of your own failure cases with causes your SMEs confirmed, because the card lists telecom QnA only where it was evaluated for the target task | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#intended-use) |
| Retrieval | The OTel Embedding and Reranker slots over your indexed specifications, because the 31B is the generation stage only | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#not-a-retrieval-or-reranking-model) |
| Language scope | Tests in every language your engineers read explanations in, because the card's quality claims cover English text only | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |

## Governance

Every outcome is LOOK. The ceiling is inform, and nothing reaches the [decision gate](../../../architecture/decision-gate.md), because the flow changes no network state.

| Action | Gate outcome (LOOK/NOTIFY/REVIEW/ACT/STOP) | Approval | AI Act class |
|---|---|---|---|
| Explain a mobility failure with cited procedure steps | LOOK | None: the engineer reads the explanation and its sources | Recorded by your legal team in the classification record |
| Abstain and list what was searched | LOOK | None: the engineer sees what was searched | Recorded by your legal team in the classification record |

| Parameter | What it controls | Who sets it | How to calibrate |
|---|---|---|---|
| LLM groundedness floor | The lowest share of explanation lines that the rebuilt event and cited clauses support | Risk owner, with subject-matter expert (SME) review | [Evaluation and acceptance](../../../platform/evaluation-acceptance/README.md): score SME-checked explanations of past failures with a calibrated judge |
| LLM citation-correctness floor | The lowest share of citations that point to the clause that holds the claim | Risk owner, with SME review | Check citations against the retrieved clauses on the same golden set |
| Embedding and Reranker recall-at-k floor | The lowest share of failures with the right procedure clause in the top results | Platform team, with SME review | Label the relevant clauses for past failures |
| Safety abstain-recall floor | The lowest share of insufficient-context items where the Safety slot abstains | Risk owner, with SME review | Remove the relevant messages from items and measure correct abstention |

This page gives no default values. Each owner sets the value with SME review and versions it with the policy that `policy_version` names.

## Sources

Each key claim links its source, as set out in [the Sources table](../../../framework/definitions.md#sources-table).

| # | Claim | Basis | Source |
|---|---|---|---|
| 1 | The 31B training leaves out 5G core control-plane and inter-NF signalling data | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| 2 | The 31B suits telecom QnA only where it was separately evaluated for the target task | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#intended-use) |
| 3 | In a RAG pipeline the 31B is the generation stage only; purpose-built embedding and reranker models do retrieval | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#not-a-retrieval-or-reranking-model) |
| 4 | The 31B targets English-language use, and all its quality claims are text-only | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |
| 5 | The Safety model is trained to refuse when retrieved context is insufficient | model card | [OTel-LLM-12B-Safety model card](https://huggingface.co/farbodtavakkoli/OTel-LLM-12B-Safety) |
| 6 | TS 23.502 specifies the procedures for the 5G System | project documentation | [3GPP TS 23.502](https://www.3gpp.org/DynaReport/23502.htm) |
| 7 | TS 38.413 specifies the NG-RAN protocol NGAP, and TS 38.423 specifies the NG-RAN protocol XnAP | project documentation | [3GPP TS 38.413](https://www.3gpp.org/DynaReport/38413.htm), [3GPP TS 38.423](https://www.3gpp.org/DynaReport/38423.htm) |

## Deploy and verify

_Stub: this catalog entry has no deploy steps yet._

## Limitations

- The entry never changes network state. It informs only, and every outcome is LOOK.
- It explains what your event tools rebuild; it doesn't replace them or read raw traces.
- It explains only from specifications in the corpus register, so a procedure nobody indexed ends in an abstention.
- The quality claims cover English only, so explanations in another language need their own evaluation.
