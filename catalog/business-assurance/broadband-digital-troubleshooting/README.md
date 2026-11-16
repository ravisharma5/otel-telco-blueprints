---
id: "UC-CARE-02"
type: "use-case"
title: "Broadband digital troubleshooting"
doc_status: done
domain: "business-assurance"
flagship: false
depth: "entry"
adaptation:
  rung: "skills"
  expertise: ["golden-set", "gate-labels", "tool-contracts", "corpus"]
  bring:
    - {item: "Care articles with usage-rights entries", domains: ["customer-care"], mechanism: "rag-corpus"}
    - {item: "Read-only gateway and Wi-Fi diagnostic tools", domains: ["customer-care"], mechanism: "tool-contract"}
    - {item: "Care diagnostics skill and tool manifests", domains: ["customer-care"], mechanism: "skill-manifest"}
    - {item: "Consent check and remote-fix ceilings", domains: ["customer-care"], mechanism: "gate-policy"}
otel_slots: ["embedding", "reranker", "safety", "decision", "llm"]
autonomy_ceiling: "recommend-with-approval"
tmf_an_level_target: 2
placement_tier: ["regional", "core"]
one_liner: "Helps a care agent troubleshoot a home broadband fault from gateway diagnostics and care articles, and proposes remote fixes for approval. Never talks to the customer. Depends on your device management platform and the customer's consent."
platform_blueprints: ["PB-01", "PB-02", "PB-03", "PB-04", "PB-05", "PB-06", "PB-10", "PB-11"]
clarity_reviewed: "2026-11-16"
agent_school: []
card:
  goal: "customers"
  summary: "Reads home gateway and Wi-Fi diagnostics with the customer's consent, and suggests the next troubleshooting step to the care agent."
  outcome: "Care agents resolve more broadband faults on the first call, with a cited reason for each step."
  audience: "Care agents, care operations, the data protection officer, and risk owners"
  measures: ["Average handling time", "First-contact resolution"]
  risk: "It reads device data tied to a customer, so consent is checked first."
placement:
  far-edge: {runs: [], note: "Not used: diagnostics arrive through the device management platform."}
  regional: {runs: ["embedding", "reranker", "safety", "decision", "llm-small"], note: "Retrieval, the Safety check, the gate label, and routine suggestions run here."}
  core: {runs: ["llm-large"], note: "The large LLM drafts suggestions for complex faults."}
---

<!-- Writing rules: framework/style-guide.md. Name each component by its role and the Red Hat product used. Write no product support status. -->

# Broadband digital troubleshooting

## At a glance

| Field | Value |
|---|---|
| One-liner | Helps a care agent troubleshoot a home broadband fault from gateway diagnostics and care articles, and proposes remote fixes for approval. Never talks to the customer. Depends on your device management platform and the customer's consent. |
| Problem | Slow or dropped home broadband has many causes, and care agents rarely have time to read gateway diagnostics; the KPI is first-contact resolution |
| Audience | Care agents, care operations, the data protection officer, and risk owners |
| OTel slots | `embedding` and `reranker`: find care articles; `safety`: abstain on weak evidence; `decision`: the gate label; `llm`: drafts each suggestion |
| Autonomy ceiling | Recommend with approval |
| Placement tier | Regional and core |
| Agent-school courses | None: no agent-school course covers this use case yet. See the [agent-school roadmap](https://github.com/open-experiments/agent-school/blob/main/docs/RoadMap.md) |

## Problem and value

Wi-Fi interference, a failing gateway, and a line fault all reach the care desk as the same complaint about slow internet.
Your device management platform can read gateway and Wi-Fi diagnostics, but care agents rarely have time to read them during a call.
This entry reads them with the customer's consent and finds the matching care article. It suggests the next step to the care agent, who stays the one talking to the customer.
The KPIs are average handling time and first-contact resolution.
Any gain is a target, measured against a shadow-stage baseline.

## How it works

_Stub: this catalog entry has no worked example or diagram yet._

## What you need

- [ ] Models: the five slots, chosen from the family in [PB-01](../../../platform/intake-model-selection/README.md), each pinned by revision with its licence chain recorded
- [ ] Platform blueprints: evaluation ([PB-02](../../../platform/evaluation-acceptance/README.md)), serving and routing ([PB-04](../../../platform/serving-routing-placement/README.md)), integration ([PB-05](../../../platform/integration/README.md)), safety gating ([PB-06](../../../platform/safety-autonomy-gating/README.md)), and compliance ([PB-10](../../../platform/compliance-operating-model/README.md))
- [ ] Components: one product for each role in the components table
- [ ] Consent: the customer's consent, or another lawful basis your data protection officer records, before any diagnostic read; map the processing to the [PB-10 privacy map](../../../platform/compliance-operating-model/README.md#privacy-map-for-gdpr-and-eprivacy)
- [ ] Integrations: read-only diagnostic tools through the MCP gateway, under the deny-unless-allowed rule in [PB-05](../../../platform/integration/README.md#per-tool-authorization)
- [ ] Corpora: each care article set has a filled usage-rights entry in the corpus register, as [PB-05](../../../platform/integration/README.md#knowledge-sources-and-usage-rights) requires
- [ ] Embedding revision: a new embedding checkpoint forces a full re-index, so record the revision with the index
- [ ] Decision engine: vLLM 0.26 or 0.30 on CUDA or ROCm, as the [Decision model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) states
- [ ] Placement: the regional site runs Embedding, Reranker, Safety, Decision, and the small LLM. The core runs the large LLM.

| Component role | Red Hat product used |
|---|---|
| Inference engine for every slot | Red Hat AI Inference (vLLM) |
| Serving platform | Red Hat OpenShift AI with KServe |
| Tool gateway for the diagnostic tools | MCP gateway in Red Hat Connectivity Link |
| Device management for home gateways | Your choice; this design names no product |
| Vector store for care articles | Your choice; this design names no product |

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

### What you bring

<!-- generated:what-you-bring start -->

| Model change | Your expertise | How far to climb |
|---|---|---|
| No model change: retrieval, a skill per role, and a capability manifest per tool | A golden set your experts label; gate labels from your approvers; a contract for each tool; your domain corpus | Configure first, and train only on a measured gap, as [PB-03 Adaptation](../../../platform/adaptation/README.md) sets out |

| Item | Network component | Mechanism | Owner | Matrix row |
|---|---|---|---|---|
| Care articles with usage-rights entries | Customer and care | RAG corpus | Business owner, with data protection officer review | [Customer and care](../../../platform/bring-your-own-data/README.md#domain-customer-and-care) |
| Read-only gateway and Wi-Fi diagnostic tools | Customer and care | MCP tool contract | Platform team | [Customer and care](../../../platform/bring-your-own-data/README.md#domain-customer-and-care) |
| Care diagnostics skill and tool manifests | Customer and care | Skill or capability manifest | SME | [Customer and care](../../../platform/bring-your-own-data/README.md#domain-customer-and-care) |
| Consent check and remote-fix ceilings | Customer and care | Gate and action-layer policy | Risk owner | [Customer and care](../../../platform/bring-your-own-data/README.md#domain-customer-and-care) |

<!-- generated:what-you-bring end -->

### What you must add

| Gap | What you add | Source |
|---|---|---|
| Device data | Gateway and Wi-Fi diagnostics from your device management platform, because the card leaves operator customer and equipment records out of training | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| Device tools | Read-only diagnostic tools with checked schemas over your TR-369 controller or current platform, because the card asks for an external tool runtime | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#tool-use-and-instruction-following) |
| Consent | The customer's consent, or another lawful basis your data protection officer records, before each read, because TR-369 expects device data to reach only parties the user enabled | [TR-369 specification](https://usp.technology/specification/index.html) |
| Care-agent scope | A care agent between every suggestion and the customer, with no customer-facing stage, because the card asks for human review in high-impact use | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#intended-use) |
| Evaluation | A golden set of your own resolved broadband cases, labelled by care SMEs, because the card's tool-use training holds no telecom examples | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#tool-use-and-instruction-following) |
| Language scope | Tests in every language your care agents work in, because the card's quality claims cover English text only | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |

## Governance

Each action request passes the [decision gate](../../../architecture/decision-gate.md), and the outcome never exceeds the policy ceiling for its class.
The outcome is the lower of the model label and the policy ceiling for the capability and risk class, so it never exceeds either. A STOP label forces STOP at every stage.
Every action class begins at the shadow stage, where the outcome is LOOK. A confirmed false ACT drops the use case and its action class back one stage, as [PB-06](../../../platform/safety-autonomy-gating/README.md#staged-autonomy) sets out.

| Action | Gate outcome (LOOK/NOTIFY/REVIEW/ACT/STOP) | Approval | AI Act class |
|---|---|---|---|
| Suggest the next step to the care agent | LOOK, with no action request | None; the care agent decides | [Recorded by your legal team in the classification record](../../../platform/compliance-operating-model/README.md) |
| Add a diagnostic summary to the customer case, `notify` | NOTIFY, from the assist stage up | None | [Recorded by your legal team in the classification record](../../../platform/compliance-operating-model/README.md) |
| Propose a remote fix such as a gateway restart or a Wi-Fi channel change, `write_low` | REVIEW, from the recommend stage up | The `approver` role | [Recorded by your legal team in the classification record](../../../platform/compliance-operating-model/README.md) |
| Any request the label marks STOP | STOP | None | [Recorded by your legal team in the classification record](../../../platform/compliance-operating-model/README.md) |

| Parameter | What it controls | Who sets it | How to calibrate |
|---|---|---|---|
| Embedding and Reranker recall-at-k floor | The lowest share of cases with a correct care article in the top results | Platform team, with subject-matter expert (SME) review | [Evaluation and acceptance](../../../platform/evaluation-acceptance/README.md): label relevant articles for past cases |
| Safety abstain-recall floor | The lowest share of insufficient-context items where the Safety slot abstains | Risk owner, with SME review | Remove the relevant diagnostics from items and measure correct abstention |
| Decision false-ACT budget | The highest false-ACT rate accepted on remote fixes | Risk owner | [Evaluation and acceptance](../../../platform/evaluation-acceptance/README.md#false-act-method): use the false-ACT method on a gate set of past fixes |
| Ceiling for low-risk writes | The highest outcome for remote fixes | Risk owner | Raise it only after a canary window with no false ACT label |
| Required approver role per action class | Which role approves REVIEW for each action class | Risk owner | Check approval times and overrides per class in the trace |
| Trace archive retention period | How long archived prompts and tool payloads are kept before deletion | Data protection officer | Set from the retention period the applicable law and your audit needs require |

This page gives no default values. Each owner sets the value with SME review and versions it with the policy that `policy_version` names.

## Sources

Each key claim links its source, as set out in [the Sources table](../../../framework/definitions.md#sources-table).

| # | Claim | Basis | Source |
|---|---|---|---|
| 1 | The 31B training leaves out operator customer and equipment configuration records and OSS/BSS tooling | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| 2 | The tool-use training holds general examples only, and agentic use needs an external tool runtime with checked tool schemas and human review | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#tool-use-and-instruction-following) |
| 3 | For high-impact operational use, deploy the 31B with retrieval, source attribution, validation checks, and human review | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#intended-use) |
| 4 | The 31B targets English-language use, and all its quality claims are text-only | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |
| 5 | Use the Decision model's label probabilities for confidence thresholds and routing; serve it on vLLM 0.26 or 0.30 | model card | [OTel-2.0-Decision-26B-A4B-4bit model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) |
| 6 | The Safety model is trained to refuse when retrieved context is insufficient | model card | [OTel-LLM-12B-Safety model card](https://huggingface.co/farbodtavakkoli/OTel-LLM-12B-Safety) |
| 7 | TR-369 is a protocol to manage, monitor, and troubleshoot connected devices and home network links, including for customer support | project documentation | [TR-369 User Services Platform](https://usp.technology/) |
| 8 | TR-369 access control and authorization aim to let only parties the user enabled use device data | project documentation | [TR-369 specification](https://usp.technology/specification/index.html) |

## Deploy and verify

_Stub: this catalog entry has no deploy steps yet._

## Limitations

- It never serves customers directly; it assists the care agent, who talks to the customer and approves every remote fix.
- It reads diagnostics only after consent or another recorded lawful basis, and it draws no legal conclusion on which one holds.
- It suggests from care articles in the corpus register, so a fault no article covers ends in an abstention.
- The Decision label probabilities count as uncalibrated until you calibrate them on your own cases.
- The quality claims cover English only, so suggestions in another language need their own evaluation.
