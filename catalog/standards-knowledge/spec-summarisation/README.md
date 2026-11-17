---
id: "UC-KNOW-02"
type: "use-case"
title: "Standards and change-request summaries"
doc_status: done
domain: "standards-knowledge"
flagship: false
depth: "entry"
adaptation:
  rung: "retrieval"
  expertise: ["golden-set", "gate-labels", "corpus"]
  bring:
    - {item: "Specification sets with release and version", domains: ["ran", "core-cnf", "transport-ip"], mechanism: "rag-corpus"}
    - {item: "Change-request archives", domains: ["ran", "core-cnf"], mechanism: "rag-corpus"}
    - {item: "Routing threshold and summary-only ceiling", domains: ["ran", "core-cnf", "transport-ip"], mechanism: "gate-policy"}
sandbox:
  fit: "none"
  why: "Reads retrieved specification clauses; the agent runs no code"
otel_slots: ["embedding", "reranker", "safety", "decision", "llm"]
autonomy_ceiling: "inform"
placement_tier: ["regional", "core"]
one_liner: "Summarises 3GPP specifications and change requests with a citation for each clause, or abstains. Informs only and never changes the network. Depends on retrieval plus the Safety and Decision slots."
platform_blueprints: ["PB-01", "PB-02", "PB-03", "PB-04", "PB-05", "PB-06", "PB-08", "PB-09", "PB-10", "PB-11"]
clarity_reviewed: "2026-11-17"
agent_school: [103, 402]
card:
  goal: "answer"
  summary: "Summarises 3GPP specifications and change requests from documents you hold, citing each clause, or says what it could not find."
  outcome: "Engineers see what a new release or change request changes without reading every clause by hand."
  audience: "Standards engineers, architects, and operations engineers who track releases"
  measures: ["Time to a reviewed summary", "Share of summaries reviewers accept"]
  risk: "A summary could drop a clause, so every line cites its source."
placement:
  far-edge: {runs: [], note: "Not used: summaries don't need to run at the cell site."}
  regional: {runs: ["embedding", "reranker", "safety", "decision", "llm-small"], note: "Retrieval, the Safety and Decision checks, and the small LLM run here."}
  core: {runs: ["llm-large"], note: "The large LLM writes the summaries the Decision slot routes up."}
---

<!-- Writing rules: framework/style-guide.md. Name each component by its role and the Red Hat product used. Write no product support status. -->

# Standards and change-request summaries

## At a glance

| Field | Value |
|---|---|
| One-liner | Summarises 3GPP specifications and change requests with a citation for each clause, or abstains. Informs only and never changes the network. Depends on retrieval plus the Safety and Decision slots. |
| Problem | Engineers read long specifications and change requests by hand to see what changed; the KPI is time to a reviewed summary |
| Audience | Standards engineers, architects, and operations engineers who track releases |
| OTel slots | `embedding`: retrieval; `reranker`: passage order; `safety`: abstain on weak evidence; `decision`: picks the LLM size; `llm`: writes the cited summary |
| Autonomy ceiling | Inform |
| Placement tier | Regional and core |
| Agent-school courses | 103 and 402 in the [agent-school roadmap](https://github.com/open-experiments/agent-school/blob/main/docs/RoadMap.md) |

## Problem and value

3GPP publishes new specification versions four times a year, each folding in the change requests the plenary approved.
Engineers read them by hand to find what affects their network.
This entry summarises a specification or change request from your indexed copies and cites each clause, or abstains and says what it searched.
The KPIs are time to a reviewed summary and the share of summaries reviewers accept.
Any time saving is a target, measured against a shadow-stage baseline.

## How it works

_Stub: this catalog entry has no worked example or diagram yet._

## What you need

- [ ] Models: the five slots, chosen from the family in [PB-01](../../../platform/intake-model-selection/README.md), each pinned by revision with its licence chain recorded
- [ ] Platform blueprints: evaluation ([PB-02](../../../platform/evaluation-acceptance/README.md)), serving and routing ([PB-04](../../../platform/serving-routing-placement/README.md)), integration ([PB-05](../../../platform/integration/README.md)), safety gating ([PB-06](../../../platform/safety-autonomy-gating/README.md)), quality operations ([PB-09](../../../platform/quality-operations/README.md)), and compliance ([PB-10](../../../platform/compliance-operating-model/README.md))
- [ ] Components: one product for each role in the components table
- [ ] Corpora: each specification set and change-request archive has a filled usage-rights entry in the corpus register before indexing, as [PB-05](../../../platform/integration/README.md#knowledge-sources-and-usage-rights) requires
- [ ] Versions: index each specification with its release and version, so every summary names the version it read
- [ ] Embedding revision: a new embedding checkpoint forces a full re-index, so record the revision with the index
- [ ] Decision engine: vLLM 0.26 or 0.30 on CUDA or ROCm, as the [Decision model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) states; call `/v1/chat/completions` with log probabilities
- [ ] Placement: the regional site runs Embedding, Reranker, Safety, Decision, and the small LLM. The core runs the large LLM.

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
| Specification sets with release and version | RAN; 5G core CNFs; Transport and IP | RAG corpus | RAN: Operations engineer; 5G core CNFs: Platform team; Transport and IP: Operations engineer | [RAN](../../../platform/bring-your-own-data/README.md#domain-ran); [5G core CNFs](../../../platform/bring-your-own-data/README.md#domain-5g-core-cnfs); [Transport and IP](../../../platform/bring-your-own-data/README.md#domain-transport-and-ip) |
| Change-request archives | RAN; 5G core CNFs | RAG corpus | RAN: Operations engineer; 5G core CNFs: Platform team | [RAN](../../../platform/bring-your-own-data/README.md#domain-ran); [5G core CNFs](../../../platform/bring-your-own-data/README.md#domain-5g-core-cnfs) |
| Routing threshold and summary-only ceiling | RAN; 5G core CNFs; Transport and IP | Gate and action-layer policy | Risk owner | [RAN](../../../platform/bring-your-own-data/README.md#domain-ran); [5G core CNFs](../../../platform/bring-your-own-data/README.md#domain-5g-core-cnfs); [Transport and IP](../../../platform/bring-your-own-data/README.md#domain-transport-and-ip) |

<!-- generated:what-you-bring end -->

### Sandbox

<!-- generated:sandbox start -->

| Sandbox fit | Trigger on this page | Where to read |
|---|---|---|
| Base sandbox only: the agent reads through the gateways, so the six sandbox controls and the gateway screen are enough | Reads retrieved specification clauses; the agent runs no code | [PB-08: when a use case needs a sandbox](../../../platform/security-identity-sandbox/README.md#when-a-use-case-needs-a-sandbox) |

<!-- generated:sandbox end -->

### What you must add

| Gap | What you add | Source |
|---|---|---|
| Corpus rights | A usage-rights entry for each specification and change-request set before you index it, because copyright in 3GPP specifications sits with the 3GPP Organizational Partners | [3GPP legal matters](https://www.3gpp.org/about-us/legal-matters) |
| Patent questions | A route to your legal team for any question about essential patents in a summarised clause; this entry draws no conclusion on patents | [3GPP legal matters](https://www.3gpp.org/about-us/legal-matters) |
| Evaluation | A golden set of specifications and change requests with summaries your SMEs wrote and checked, because the card lists summarisation as an intended use, not as a result on your documents | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#intended-use) |
| Version freshness | The release and version of each indexed specification, and a re-index when a new version appears, because the card says to check answers against the document version | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#general-reliability-and-deployment-limitations) |
| Language scope | Tests in every language your engineers read summaries in, because the card's quality claims cover English text only | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |

## Governance

Every outcome is LOOK. The ceiling is inform, and nothing reaches the [decision gate](../../../architecture/decision-gate.md), because the flow changes no network state.

| Action | Gate outcome (LOOK/NOTIFY/REVIEW/ACT/STOP) | Approval | AI Act class |
|---|---|---|---|
| Summarise a specification or change request with citations | LOOK | None: the engineer reads the summary and its sources | [Recorded by your legal team in the classification record](../../../platform/compliance-operating-model/README.md) |
| Abstain and list what was searched | LOOK | None: the engineer sees what was searched | [Recorded by your legal team in the classification record](../../../platform/compliance-operating-model/README.md) |

| Parameter | What it controls | Who sets it | How to calibrate |
|---|---|---|---|
| LLM groundedness floor | The lowest share of summary lines that the cited clauses support | Risk owner, with subject-matter expert (SME) review | [Evaluation and acceptance](../../../platform/evaluation-acceptance/README.md): score a golden set of SME-written summaries with a calibrated judge |
| LLM citation-correctness floor | The lowest share of citations that point to the clause that holds the claim | Risk owner, with SME review | Check citations against the retrieved clauses on the same golden set |
| Safety abstain-recall floor | The lowest share of insufficient-context items where the Safety slot abstains | Risk owner, with SME review | Remove the relevant clauses from items and measure correct abstention |
| Non-inferiority margin | The largest drop against the incumbent that still counts as no worse | Risk owner | Run candidate and incumbent on identical items and set the margin from the run-to-run noise |
| Decision routing threshold | The label probability over which the large LLM writes the summary instead of the small LLM | Model owner | Run the small and large LLM on the same golden set, and keep a band on the small LLM only while it stays within the non-inferiority margin |

This page gives no default values. Each owner sets the value with SME review and versions it with the policy that `policy_version` names.

## Sources

Each key claim links its source, as set out in [the Sources table](../../../framework/definitions.md#sources-table).

| # | Claim | Basis | Source |
|---|---|---|---|
| 1 | The 31B lists standards interpretation and summarisation for 3GPP, ETSI, GSMA, CAMARA, ITU, O-RAN, and TM Forum material among its intended uses | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#intended-use) |
| 2 | Telecom standards change over time, so check answers against the document version and release | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#general-reliability-and-deployment-limitations) |
| 3 | The 31B targets English-language use, and all its quality claims are text-only | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |
| 4 | In a RAG pipeline the 31B is the generation stage only; purpose-built embedding and reranker models do retrieval | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#not-a-retrieval-or-reranking-model) |
| 5 | Use the Decision model's label probabilities for confidence thresholds and routing; serve it on vLLM 0.26 or 0.30 | model card | [OTel-2.0-Decision-26B-A4B-4bit model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) |
| 6 | The Safety model is trained to refuse when retrieved context is insufficient | model card | [OTel-LLM-12B-Safety model card](https://huggingface.co/farbodtavakkoli/OTel-LLM-12B-Safety) |
| 7 | 3GPP makes specifications available free of charge four times a year, after the quarterly plenary meetings | project documentation | [3GPP specifications](https://www.3gpp.org/specifications-technologies) |
| 8 | Approved change requests are folded into a new version of the specification, and the change-request database records each status | project documentation | [3GPP change requests](https://www.3gpp.org/specifications-technologies/specifications-by-series/change-requests) |
| 9 | Copyright in 3GPP specifications vests jointly with the Organizational Partners, and members declare to them the intellectual property they believe essential | project documentation | [3GPP legal matters](https://www.3gpp.org/about-us/legal-matters) |

## Deploy and verify

_Stub: this catalog entry has no deploy steps yet._

## Limitations

- The entry never changes network state. It informs only, and every outcome is LOOK.
- It summarises only documents in the corpus register, so a change request nobody indexed ends in an abstention.
- A summary doesn't replace the specification; engineers check the cited clauses before they act on them.
- It draws no conclusion on patents or licensing; those questions go to your legal team.
- The Decision label probabilities count as uncalibrated until you calibrate them on your own documents.
- The quality claims cover English only, so summaries in another language need their own evaluation.
