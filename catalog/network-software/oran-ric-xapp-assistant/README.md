---
id: "UC-SW-03"
type: "use-case"
title: "O-RAN RIC xApp assistant"
doc_status: done
domain: "network-software"
flagship: false
depth: "entry"
adaptation:
  rung: "retrieval"
  expertise: ["golden-set", "corpus"]
  bring:
    - {item: "O-RAN E2AP and E2SM specifications", domains: ["vran-oran"], mechanism: "rag-corpus"}
    - {item: "Your xApp code and RIC framework", domains: ["vran-oran"], mechanism: "rag-corpus"}
    - {item: "Read-only ceiling: no writes to code or the RIC", domains: ["vran-oran"], mechanism: "gate-policy"}
sandbox:
  fit: "none"
  why: "Reads specification and code index passages; the agent runs no code"
otel_slots: ["embedding", "reranker", "safety", "llm"]
autonomy_ceiling: "inform"
placement_tier: ["regional", "core"]
one_liner: "Answers xApp development questions with citations to O-RAN specifications and your RIC code, or abstains. Informs only and never changes code or the network. Depends on a specification and code index you build and evaluate."
platform_blueprints: ["PB-01", "PB-02", "PB-03", "PB-04", "PB-05", "PB-06", "PB-08", "PB-11"]
clarity_reviewed: "2026-11-17"
agent_school: []
card:
  goal: "software"
  summary: "Answers xApp development questions from O-RAN specifications and your RIC code, with citations, or says what it searched."
  outcome: "xApp developers find the E2AP message or framework call they need without searching specifications by hand."
  audience: "xApp developers and RAN software engineers working on a near-real-time RIC"
  measures: ["Time to a cited answer", "Share of answers developers accept"]
  risk: "A wrong E2AP detail could break an xApp, so answers cite the specification."
placement:
  far-edge: {runs: [], note: "Not used: development questions don't need to run at the cell site."}
  regional: {runs: ["embedding", "reranker", "safety"], note: "The specification and code index, passage order, and the Safety check run here."}
  core: {runs: ["llm-large"], note: "The large LLM answers from the retrieved passages and files."}
---

<!-- Writing rules: framework/style-guide.md. Name each component by its role and the Red Hat product used. Write no product support status. -->

# O-RAN RIC xApp assistant

## At a glance

| Field | Value |
|---|---|
| One-liner | Answers xApp development questions with citations to O-RAN specifications and your RIC code, or abstains. Informs only and never changes code or the network. Depends on a specification and code index you build and evaluate. |
| Problem | xApp developers search the O-RAN E2AP and E2SM specifications and RIC framework code by hand; the KPI is time to a cited answer |
| Audience | xApp developers and RAN software engineers working on a near-real-time RIC |
| OTel slots | `embedding`: specification and code retrieval; `reranker`: passage order; `safety`: abstain on weak evidence; `llm`: answers with citations |
| Autonomy ceiling | Inform |
| Placement tier | Regional and core |
| Agent-school courses | None: no agent-school course covers this use case yet. See the [agent-school roadmap](https://github.com/open-experiments/agent-school/blob/main/docs/RoadMap.md) |

## Problem and value

An xApp talks to the RAN through E2AP messages and E2SM service models on a near-real-time RIC, so developers work from the O-RAN specifications and a RIC framework at once.
They search both by hand for the right message, service model, or framework call.
This entry answers from your indexed specifications and code and cites each passage and file, or abstains and says what it searched.
The KPIs are time to a cited answer and the share of answers developers accept.
Any time saving is a target, measured against a shadow-stage baseline.

## How it works

_Stub: this catalog entry has no worked example or diagram yet._

## What you need

- [ ] Models: the four slots, chosen from the family in [PB-01](../../../platform/intake-model-selection/README.md), each pinned by revision with its licence chain recorded
- [ ] Platform blueprints: evaluation ([PB-02](../../../platform/evaluation-acceptance/README.md)), serving and routing ([PB-04](../../../platform/serving-routing-placement/README.md)), integration ([PB-05](../../../platform/integration/README.md)), and safety gating ([PB-06](../../../platform/safety-autonomy-gating/README.md))
- [ ] Components: one product for each role in the components table
- [ ] Index: the O-RAN specifications you use, your xApp code, and the RIC framework you build on, each with a filled usage-rights entry in the corpus register, as [PB-05](../../../platform/integration/README.md#knowledge-sources-and-usage-rights) requires
- [ ] Integrations: read-only access to your code hosts; the assistant writes nothing to a repository or a RIC
- [ ] Placement: the regional site runs Embedding, Reranker, and Safety. The core runs the large LLM.

| Component role | Red Hat product used |
|---|---|
| Specification and code index | Your choice; this design names no product |
| Inference engine for every slot | Red Hat AI Inference (vLLM) |
| Serving platform | Red Hat OpenShift AI with KServe |
| Front door for identity and token limits | Models-as-a-Service in Red Hat OpenShift AI |

Key flags for each slot, copied from [PB-04](../../../platform/serving-routing-placement/README.md#key-flags-per-slot). The LLM block keeps its tool-calling flags as PB-04 sets them, though this flow makes no tool calls. Start the Safety slot with its own pinned revision.

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
| No model change: retrieval over your corpus | A golden set your experts label; your domain corpus | Configure first, and train only on a measured gap, as [PB-03 Adaptation](../../../platform/adaptation/README.md) sets out |

| Item | Network component | Mechanism | Owner | Matrix row |
|---|---|---|---|---|
| O-RAN E2AP and E2SM specifications | vRAN and O-RAN | RAG corpus | Platform team | [vRAN and O-RAN](../../../platform/bring-your-own-data/README.md#domain-vran-and-o-ran) |
| Your xApp code and RIC framework | vRAN and O-RAN | RAG corpus | Platform team | [vRAN and O-RAN](../../../platform/bring-your-own-data/README.md#domain-vran-and-o-ran) |
| Read-only ceiling: no writes to code or the RIC | vRAN and O-RAN | Gate and action-layer policy | Risk owner | [vRAN and O-RAN](../../../platform/bring-your-own-data/README.md#domain-vran-and-o-ran) |

<!-- generated:what-you-bring end -->

### Sandbox

<!-- generated:sandbox start -->

| Sandbox fit | Trigger on this page | Where to read |
|---|---|---|
| Base sandbox only: the agent reads through the gateways, so the six sandbox controls and the gateway screen are enough | Reads specification and code index passages; the agent runs no code | [PB-08: when a use case needs a sandbox](../../../platform/security-identity-sandbox/README.md#when-a-use-case-needs-a-sandbox) |

<!-- generated:sandbox end -->

### What you must add

| Gap | What you add | Source |
|---|---|---|
| Specification corpus | Your copies of the O-RAN E2AP and E2SM specifications in the index, downloaded from the O-RAN portal and registered with their usage terms | [O-RAN specifications](https://www.o-ran.org/specifications) |
| Code corpus | An index of your xApp code and RIC framework, rebuilt when the code changes, because the card names standards material as its training corpus and no source code | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#training-data) |
| Evaluation | xApp tasks from your own code with answers your developers checked; ORANBench tests specification knowledge with multiple-choice questions, not xApp code | [GSMA Open Telco benchmarks](https://huggingface.co/datasets/GSMA/ot-full) |
| Language scope | Tests in every language your developers write questions in, because the card's quality claims cover English text only | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |

## Governance

Every outcome is LOOK. The ceiling is inform, and nothing reaches the [decision gate](../../../architecture/decision-gate.md), because the flow changes no code and no network state.

| Action | Gate outcome (LOOK/NOTIFY/REVIEW/ACT/STOP) | Approval | AI Act class |
|---|---|---|---|
| Answer an xApp question with citations to passages and files | LOOK | None: the developer reads the answer and its sources | Recorded by your legal team in the classification record |
| Abstain and list what was searched | LOOK | None: the developer sees what was searched | Recorded by your legal team in the classification record |

| Parameter | What it controls | Who sets it | How to calibrate |
|---|---|---|---|
| LLM groundedness floor | The lowest share of answers whose claims the cited passages and files support | Risk owner, with subject-matter expert (SME) review | [Evaluation and acceptance](../../../platform/evaluation-acceptance/README.md): score a golden set of developer-checked answers with a calibrated judge |
| LLM citation-correctness floor | The lowest share of citations that point to the passage or file that holds the claim | Risk owner, with SME review | Check citations against the retrieved passages on the same golden set |
| Embedding and Reranker recall-at-k floor | The lowest share of questions with a correct passage or file in the top results | Platform team, with SME review | Label relevant passages for xApp questions; the reranker must beat retriever-only on the same set |
| Safety abstain-recall floor | The lowest share of insufficient-context items where the Safety slot abstains | Risk owner, with SME review | Remove the relevant passages from items and measure correct abstention |

This page gives no default values. Each owner sets the value with SME review and versions it with the policy that `policy_version` names.

## Sources

Each key claim links its source, as set out in [the Sources table](../../../framework/definitions.md#sources-table).

| # | Claim | Basis | Source |
|---|---|---|---|
| 1 | The 31B training corpus is standards and industry material, including O-RAN specifications | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#training-data) |
| 2 | The 31B lists product development and engineering support among its intended uses | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#intended-use) |
| 3 | The 31B targets English-language use, and all its quality claims are text-only | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |
| 4 | In a RAG pipeline the 31B is the generation stage only; purpose-built embedding and reranker models do retrieval | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#not-a-retrieval-or-reranking-model) |
| 5 | ORANBench asks multiple-choice questions on O-RAN specifications | research | [GSMA Open Telco benchmarks](https://huggingface.co/datasets/GSMA/ot-full) |
| 6 | O-RAN specifications are available to the public through the O-RAN download portal | project documentation | [O-RAN specifications](https://www.o-ran.org/specifications) |
| 7 | The O-RAN Software Community near-real-time RIC supports xApps and terminates the RAN interface, with xApp frameworks for Python, Go, C++, and Rust | project documentation | [O-RAN SC near-real-time RIC](https://lf-o-ran-sc.atlassian.net/wiki/spaces/RICP) |
| 8 | FlexRIC is an open source RAN intelligent controller with a RAN-side agent, under the Apache 2.0 licence | project documentation | [FlexRIC repository](https://gitlab.eurecom.fr/mosaic5g/flexric) |

## Deploy and verify

_Stub: this catalog entry has no deploy steps yet._

## Limitations

- The assistant never changes code, a RIC, or network state. It informs only, and every outcome is LOOK.
- It knows your code only through the index, so a stale index gives stale answers.
- ORANBench covers specification knowledge, not your xApps.
- It doesn't build, test, or deploy xApps; your pipelines keep doing that.
- The quality claims cover English only, so questions in another language need their own evaluation.
