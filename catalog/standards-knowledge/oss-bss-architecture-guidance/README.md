---
id: "UC-KNOW-03"
type: "use-case"
title: "OSS and BSS architecture guidance"
doc_status: done
domain: "standards-knowledge"
flagship: false
depth: "entry"
adaptation:
  rung: "retrieval"
  expertise: ["golden-set", "corpus"]
  bring:
    - {item: "TM Forum frameworks under your membership terms", domains: ["oss-bss"], mechanism: "rag-corpus"}
    - {item: "TM Forum Open API specifications", domains: ["oss-bss"], mechanism: "rag-corpus"}
    - {item: "Your architecture documents and integration designs", domains: ["oss-bss"], mechanism: "rag-corpus"}
otel_slots: ["embedding", "reranker", "safety", "llm"]
autonomy_ceiling: "inform"
placement_tier: ["regional", "core"]
one_liner: "Answers OSS and BSS architecture questions with citations to TM Forum material and your own designs, or abstains. Informs only and never changes the network. Depends on retrieval plus the Safety slot."
platform_blueprints: ["PB-01", "PB-02", "PB-03", "PB-04", "PB-05", "PB-06", "PB-09", "PB-11"]
clarity_reviewed: "2026-11-15"
agent_school: [402]
card:
  goal: "answer"
  summary: "Answers OSS and BSS architecture questions from TM Forum material and your own designs, with citations, or says it can't answer."
  outcome: "Architects map a change to TM Forum processes, data, and APIs without searching every framework by hand."
  audience: "OSS and BSS architects, solution designers, and integration engineers"
  measures: ["Time to a cited answer", "Share of answers architects accept"]
  risk: "A plausible but wrong mapping could steer a design, so every answer cites sources."
placement:
  far-edge: {runs: [], note: "Not used: design questions don't need to run at the cell site."}
  regional: {runs: ["embedding", "reranker", "safety", "llm-small"], note: "Retrieval, the Safety check, and the small LLM run here."}
  core: {runs: ["llm-large"], note: "The large LLM answers questions that span several frameworks."}
---

<!-- Writing rules: framework/style-guide.md. Name each component by its role and the Red Hat product used. Write no product support status. -->

# OSS and BSS architecture guidance

## At a glance

| Field | Value |
|---|---|
| One-liner | Answers OSS and BSS architecture questions with citations to TM Forum material and your own designs, or abstains. Informs only and never changes the network. Depends on retrieval plus the Safety slot. |
| Problem | Architects search TM Forum frameworks, Open API specifications, and internal designs by hand; the KPI is time to a cited answer |
| Audience | OSS and BSS architects, solution designers, and integration engineers |
| OTel slots | `embedding`: retrieval; `reranker`: passage order; `safety`: abstain on weak evidence; `llm`: answers with citations |
| Autonomy ceiling | Inform |
| Placement tier | Regional and core |
| Agent-school courses | 402 in the [agent-school roadmap](https://github.com/open-experiments/agent-school/blob/main/docs/RoadMap.md) |

## Problem and value

An OSS or BSS change touches TM Forum processes, data models, Open APIs, and your own integration designs.
Architects search each of them by hand, and a wrong mapping shows up late in delivery.
This entry answers from your indexed frameworks and designs, cites each passage, or abstains and says what it searched.
The KPIs are time to a cited answer and the share of answers architects accept.
Any time saving is a target, measured against a shadow-stage baseline.

## How it works

_Stub: this catalog entry has no worked example or diagram yet._

## What you need

- [ ] Models: the four slots, chosen from the family in [PB-01](../../../platform/intake-model-selection/README.md), each pinned by revision with its licence chain recorded
- [ ] Platform blueprints: evaluation ([PB-02](../../../platform/evaluation-acceptance/README.md)), serving and routing ([PB-04](../../../platform/serving-routing-placement/README.md)), integration ([PB-05](../../../platform/integration/README.md)), safety gating ([PB-06](../../../platform/safety-autonomy-gating/README.md)), and quality operations ([PB-09](../../../platform/quality-operations/README.md))
- [ ] Components: one product for each role in the components table
- [ ] Corpora: the TM Forum material, Open API specifications, and architecture documents you index each have a filled usage-rights entry in the corpus register before indexing, as [PB-05](../../../platform/integration/README.md#knowledge-sources-and-usage-rights) requires
- [ ] Embedding revision: a new embedding checkpoint forces a full re-index, so record the revision with the index
- [ ] Placement: the regional site runs Embedding, Reranker, Safety, and the small LLM. The core runs the large LLM for the question types you route there.

| Component role | Red Hat product used |
|---|---|
| Knowledge service and vector store | Your choice; this design names no product |
| Inference engine for every slot | Red Hat AI Inference (vLLM) |
| Serving platform | Red Hat OpenShift AI with KServe |
| Front door for identity and token limits | Models-as-a-Service in Red Hat OpenShift AI |
| Input and output guardrails | NeMo Guardrails in Red Hat OpenShift AI |

Key flags for each slot, copied from [PB-04](../../../platform/serving-routing-placement/README.md#key-flags-per-slot). The LLM block keeps its tool-calling flags as PB-04 sets them, though this flow makes no tool calls. Start the small LLM and the Safety slot with their own pinned revisions.

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
| No model change: retrieval over your corpus | A golden set your experts label; Your domain corpus | Configure first, and train only on a measured gap, as [PB-03 Adaptation](../../../platform/adaptation/README.md) sets out |

| Item | Network component | Mechanism | Owner | Matrix row |
|---|---|---|---|---|
| TM Forum frameworks under your membership terms | OSS and BSS | RAG corpus | Business owner | [OSS and BSS](../../../platform/bring-your-own-data/README.md#domain-oss-and-bss) |
| TM Forum Open API specifications | OSS and BSS | RAG corpus | Business owner | [OSS and BSS](../../../platform/bring-your-own-data/README.md#domain-oss-and-bss) |
| Your architecture documents and integration designs | OSS and BSS | RAG corpus | Business owner | [OSS and BSS](../../../platform/bring-your-own-data/README.md#domain-oss-and-bss) |

<!-- generated:what-you-bring end -->

### What you must add

| Gap | What you add | Source |
|---|---|---|
| Framework access | Your copies of TM Forum frameworks such as eTOM and SID, registered under your own membership terms; only the Open APIs are confirmed public here | [TM Forum Open APIs](https://github.com/tmforum-apis) |
| Architecture corpus | Your architecture documents, inventory models, and integration designs in retrieval, because the card's training leaves out operator design artifacts and OSS and BSS tooling | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| Evaluation | A golden set of architecture questions with answers your architects checked, because the card says TM Forum familiarity is not proof of running processes through OSS tooling | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| Language scope | Tests in every language your architects write in, because the card's quality claims cover English text only | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |

## Governance

Every outcome is LOOK. The ceiling is inform, and nothing reaches the [decision gate](../../../architecture/decision-gate.md), because the flow changes no network state.

| Action | Gate outcome (LOOK/NOTIFY/REVIEW/ACT/STOP) | Approval | AI Act class |
|---|---|---|---|
| Answer an architecture question with citations | LOOK | None: the architect reads the answer and its sources | Recorded by your legal team in the classification record |
| Abstain and list what was searched | LOOK | None: the architect sees what was searched | Recorded by your legal team in the classification record |

| Parameter | What it controls | Who sets it | How to calibrate |
|---|---|---|---|
| LLM groundedness floor | The lowest share of answers whose claims the cited passages support | Risk owner, with subject-matter expert (SME) review | [Evaluation and acceptance](../../../platform/evaluation-acceptance/README.md): score a golden set of architect-checked answers with a calibrated judge |
| LLM citation-correctness floor | The lowest share of citations that point to the passage that holds the claim | Risk owner, with SME review | Check citations against the retrieved passages on the same golden set |
| Embedding and Reranker recall-at-k floor | The lowest share of questions with a correct passage in the top results | Platform team, with SME review | Label relevant passages for architecture questions; the reranker must beat retriever-only on the same set |
| Safety abstain-recall floor | The lowest share of insufficient-context items where the Safety slot abstains | Risk owner, with SME review | Build items with the evidence removed and measure correct abstention |
| Safety false-abstention ceiling | The highest share of sufficient-context items where the Safety slot abstains | Business owner | Measure abstention on items with full evidence, and weigh it against the human workload |

This page gives no default values. Each owner sets the value with SME review and versions it with the policy that `policy_version` names.

## Sources

Each key claim links its source, as set out in [the Sources table](../../../framework/definitions.md#sources-table).

| # | Claim | Basis | Source |
|---|---|---|---|
| 1 | The 31B training corpus includes TM Forum business and operations frameworks | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#training-data) |
| 2 | The training leaves out operator design artifacts and OSS and BSS workflow tooling, and TM Forum familiarity doesn't imply the ability to work through those systems | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| 3 | The 31B targets English-language use, and all its quality claims are text-only | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |
| 4 | In a RAG pipeline the 31B is the generation stage only; purpose-built embedding and reranker models do retrieval | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#not-a-retrieval-or-reranking-model) |
| 5 | The Safety model is trained to refuse when retrieved context is insufficient | model card | [OTel-LLM-12B-Safety model card](https://huggingface.co/farbodtavakkoli/OTel-LLM-12B-Safety) |
| 6 | TM Forum publishes its Open API specifications on GitHub under the Apache 2.0 licence | project documentation | [TM Forum Open APIs](https://github.com/tmforum-apis) |
| 7 | The ODA Canvas reference implementation, the runtime for ODA components, is open source | project documentation | [ODA Canvas repository](https://github.com/tmforum-oda/oda-canvas) |

## Deploy and verify

_Stub: this catalog entry has no deploy steps yet._

## Limitations

- The entry never changes network state. It informs only, and every outcome is LOOK.
- It answers only from corpora in the register, so a framework you haven't indexed ends in an abstention.
- An answer is guidance for an architect, not a design decision; the architect checks the cited passages.
- It doesn't run processes in your OSS or BSS tools.
- The quality claims cover English only, so questions in another language need their own evaluation.
