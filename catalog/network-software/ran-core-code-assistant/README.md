---
id: "UC-SW-01"
type: "use-case"
title: "RAN and core code assistant"
doc_status: done
domain: "network-software"
flagship: false
depth: "entry"
adaptation:
  rung: "retrieval"
  expertise: ["golden-set", "corpus"]
  bring:
    - {item: "Your RAN and core repositories", domains: ["ran", "core-cnf"], mechanism: "rag-corpus"}
    - {item: "Specifications your code implements", domains: ["ran", "core-cnf"], mechanism: "rag-corpus"}
    - {item: "Internal design documents", domains: ["ran", "core-cnf"], mechanism: "rag-corpus"}
sandbox:
  fit: "none"
  why: "Reads code index passages; the agent runs no code itself"
otel_slots: ["embedding", "reranker", "safety", "llm"]
autonomy_ceiling: "inform"
placement_tier: ["regional", "core"]
one_liner: "Answers questions about your RAN and core code with citations to files and specifications, or abstains. Informs only and never changes code or the network. Depends on a code index you build and evaluate."
platform_blueprints: ["PB-01", "PB-02", "PB-03", "PB-04", "PB-05", "PB-06", "PB-08", "PB-11"]
clarity_reviewed: "2026-11-16"
agent_school: []
card:
  goal: "software"
  summary: "Answers questions about your RAN and core code, citing files and 3GPP clauses, or says what it searched without an answer."
  outcome: "Engineers find where a protocol procedure lives in the code without tracing it by hand."
  audience: "RAN and core software engineers and code reviewers"
  measures: ["Time to locate the code", "Share of answers engineers accept"]
  risk: "A wrong file pointer wastes review time, so every answer cites its files."
placement:
  far-edge: {runs: [], note: "Not used: code questions don't need to run at the cell site."}
  regional: {runs: ["embedding", "reranker", "safety"], note: "The code index, passage order, and the Safety check run here."}
  core: {runs: ["llm-large"], note: "The large LLM answers code questions from the retrieved files."}
---

<!-- Writing rules: framework/style-guide.md. Name each component by its role and the Red Hat product used. Write no product support status. -->

# RAN and core code assistant

## At a glance

| Field | Value |
|---|---|
| One-liner | Answers questions about your RAN and core code with citations to files and specifications, or abstains. Informs only and never changes code or the network. Depends on a code index you build and evaluate. |
| Problem | Engineers trace protocol procedures through large RAN and core codebases by hand; the KPI is time to locate the code |
| Audience | RAN and core software engineers and code reviewers |
| OTel slots | `embedding`: code and specification retrieval; `reranker`: passage order; `safety`: abstain on weak evidence; `llm`: answers with citations |
| Autonomy ceiling | Inform |
| Placement tier | Regional and core |
| Agent-school courses | None: no agent-school course covers this use case yet. See the [agent-school roadmap](https://github.com/open-experiments/agent-school/blob/main/docs/RoadMap.md) |

## Problem and value

RAN and core software implements long 3GPP protocol specifications, such as NGAP and F1AP, across large codebases.
Engineers trace a procedure from the specification to the code by hand before they change or review it.
This entry answers from your indexed code and specifications and cites each file and clause, or abstains and says what it searched.
The KPIs are time to locate the code and the share of answers engineers accept.
Any time saving is a target, measured against a shadow-stage baseline.

## How it works

_Stub: this catalog entry has no worked example or diagram yet._

## What you need

- [ ] Models: the four slots, chosen from the family in [PB-01](../../../platform/intake-model-selection/README.md), each pinned by revision with its licence chain recorded
- [ ] Platform blueprints: evaluation ([PB-02](../../../platform/evaluation-acceptance/README.md)), adaptation ([PB-03](../../../platform/adaptation/README.md)), serving and routing ([PB-04](../../../platform/serving-routing-placement/README.md)), integration ([PB-05](../../../platform/integration/README.md)), and safety gating ([PB-06](../../../platform/safety-autonomy-gating/README.md))
- [ ] Components: one product for each role in the components table
- [ ] Code index: your repositories and the specifications they implement, each with a filled usage-rights entry in the corpus register, as [PB-05](../../../platform/integration/README.md#knowledge-sources-and-usage-rights) requires
- [ ] Integrations: read-only access to your code hosts; the assistant writes nothing to a repository
- [ ] Adaptation: retrieval first, and an adapter only when your acceptance suite shows a gap, as [PB-03](../../../platform/adaptation/README.md) sets out
- [ ] Placement: the regional site runs Embedding, Reranker, and Safety. The core runs the large LLM.

| Component role | Red Hat product used |
|---|---|
| Code index and vector store | Your choice; this design names no product |
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
| Your RAN and core repositories | RAN; 5G core CNFs | RAG corpus | RAN: Operations engineer; 5G core CNFs: Platform team | [RAN](../../../platform/bring-your-own-data/README.md#domain-ran); [5G core CNFs](../../../platform/bring-your-own-data/README.md#domain-5g-core-cnfs) |
| Specifications your code implements | RAN; 5G core CNFs | RAG corpus | RAN: Operations engineer; 5G core CNFs: Platform team | [RAN](../../../platform/bring-your-own-data/README.md#domain-ran); [5G core CNFs](../../../platform/bring-your-own-data/README.md#domain-5g-core-cnfs) |
| Internal design documents | RAN; 5G core CNFs | RAG corpus | RAN: Operations engineer; 5G core CNFs: Platform team | [RAN](../../../platform/bring-your-own-data/README.md#domain-ran); [5G core CNFs](../../../platform/bring-your-own-data/README.md#domain-5g-core-cnfs) |

<!-- generated:what-you-bring end -->

### Sandbox

<!-- generated:sandbox start -->

| Sandbox fit | Trigger on this page | Where to read |
|---|---|---|
| Base sandbox only: the agent reads through the gateways, so its identity, the gateway screen, and the six sandbox controls are enough | Reads code index passages; the agent runs no code itself | [PB-08: when a use case needs a sandbox](../../../platform/security-identity-sandbox/README.md#when-a-use-case-needs-a-sandbox) |

<!-- generated:sandbox end -->

### What you must add

| Gap | What you add | Source |
|---|---|---|
| Code corpus | An index of your RAN and core repositories, rebuilt when the code changes, because the card names standards material as its training corpus and no source code | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#training-data) |
| Evaluation | Code questions from your own repositories with answers your engineers checked; public sets such as SRSRANBench test one open codebase with multiple-choice questions | [GSMA Open Telco benchmarks](https://huggingface.co/datasets/GSMA/ot-full) |
| Design artifacts | Your internal design documents in the index, because the card's training leaves out operator design and configuration artifacts | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| Integrations | Read-only connectors to your code hosts, tested before use, because the card's tool-use training holds no telecom tool examples | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#tool-use-and-instruction-following) |
| Language scope | Tests in every language your engineers write questions and code comments in, because the card's quality claims cover English text only | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |

## Governance

Every outcome is LOOK. The ceiling is inform, and nothing reaches the [decision gate](../../../architecture/decision-gate.md), because the flow changes no code and no network state.

| Action | Gate outcome (LOOK/NOTIFY/REVIEW/ACT/STOP) | Approval | AI Act class |
|---|---|---|---|
| Answer a code question with citations to files and clauses | LOOK | None: the engineer reads the answer and its sources | Recorded by your legal team in the classification record |
| Abstain and list what was searched | LOOK | None: the engineer sees what was searched | Recorded by your legal team in the classification record |

| Parameter | What it controls | Who sets it | How to calibrate |
|---|---|---|---|
| LLM groundedness floor | The lowest share of answers whose claims the cited files and clauses support | Risk owner, with subject-matter expert (SME) review | [Evaluation and acceptance](../../../platform/evaluation-acceptance/README.md): score a golden set of engineer-checked answers with a calibrated judge |
| LLM citation-correctness floor | The lowest share of citations that point to the file or clause that holds the claim | Risk owner, with SME review | Check citations against the retrieved passages on the same golden set |
| Embedding and Reranker recall-at-k floor | The lowest share of questions with a correct file or clause in the top results | Platform team, with SME review | Label relevant files for code questions; the reranker must beat retriever-only on the same set |
| Safety abstain-recall floor | The lowest share of insufficient-context items where the Safety slot abstains | Risk owner, with SME review | Remove the relevant files from items and measure correct abstention |
| Safety false-abstention ceiling | The highest share of sufficient-context items where the Safety slot abstains | Business owner | Measure abstention on items with full evidence, and weigh it against the human workload |

This page gives no default values. Each owner sets the value with SME review and versions it with the policy that `policy_version` names.

## Sources

Each key claim links its source, as set out in [the Sources table](../../../framework/definitions.md#sources-table).

| # | Claim | Basis | Source |
|---|---|---|---|
| 1 | The 31B training corpus is standards and industry material from 3GPP, ETSI, ITU, GSMA, CAMARA, O-RAN, and TM Forum | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#training-data) |
| 2 | The training leaves out operator design and configuration artifacts, and such applications need their own evaluation | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| 3 | The tool-use training holds general examples only, with no telecom tool-calling examples | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#tool-use-and-instruction-following) |
| 4 | The 31B targets English-language use, and all its quality claims are text-only | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |
| 5 | SRSRANBench asks multiple-choice questions on the srsRAN codebase, and ORANBench on O-RAN specifications | research | [GSMA Open Telco benchmarks](https://huggingface.co/datasets/GSMA/ot-full) |
| 6 | srsRAN Project is an open source 5G CU/DU, and OpenAirInterface publishes an open source RAN and core aligned with 3GPP and O-RAN | project documentation | [srsRAN Project documentation](https://docs.srsran.com/projects/project/en/latest/), [OpenAirInterface](https://openairinterface.org/) |
| 7 | Open5GS implements the 5G core and EPC in C, and free5GC is an open source 5G core | project documentation | [Open5GS documentation](https://open5gs.org/open5gs/docs/), [free5GC](https://free5gc.org/) |
| 8 | TS 38.413 specifies NGAP and TS 38.473 specifies F1AP | project documentation | [3GPP TS 38.413](https://www.3gpp.org/DynaReport/38413.htm), [3GPP TS 38.473](https://www.3gpp.org/DynaReport/38473.htm) |

## Deploy and verify

_Stub: this catalog entry has no deploy steps yet._

## Limitations

- The assistant never changes code or network state. It informs only, and every outcome is LOOK.
- It knows your code only through the index, so a stale index gives stale answers.
- Public benchmarks cover open codebases and specifications, not your repositories.
- It doesn't run, build, or test code; your pipelines keep doing that.
- The quality claims cover English only, so questions in another language need their own evaluation.
