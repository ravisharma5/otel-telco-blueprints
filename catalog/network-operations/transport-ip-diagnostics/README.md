---
id: "UC-OPS-08"
type: "use-case"
title: "Transport and IP diagnostics"
doc_status: done
domain: "network-operations"
flagship: false
depth: "entry"
adaptation:
  rung: "retrieval-and-skills"
  expertise: ["golden-set", "gate-labels", "tool-contracts", "corpus"]
  bring:
    - {item: "IETF RFCs you run and vendor NOS guides", domains: ["transport-ip"], mechanism: "rag-corpus"}
    - {item: "BFD, LSP ping, TWAMP, and YANG-Push probe tools", domains: ["transport-ip"], mechanism: "tool-contract"}
    - {item: "Transport triage skill and capability manifests", domains: ["transport-ip"], mechanism: "skill-manifest"}
    - {item: "Fix ceilings and approver roles", domains: ["transport-ip"], mechanism: "gate-policy"}
sandbox:
  fit: "execution"
  why: "Runs LSP ping and TWAMP probes against live paths"
otel_slots: ["embedding", "reranker", "safety", "decision", "llm"]
autonomy_ceiling: "recommend-with-approval"
tmf_an_level_target: 2
placement_tier: ["regional", "core"]
one_liner: "Diagnoses transport and IP faults from read-only probe results and recommends fixes to a human approver. Never changes a router itself. Depends on IETF RFCs and vendor documents in retrieval and on read-only diagnostic tools."
platform_blueprints: ["PB-01", "PB-02", "PB-03", "PB-04", "PB-05", "PB-06", "PB-07", "PB-08", "PB-11"]
clarity_reviewed: "2026-11-16"
agent_school: [301]
card:
  goal: "incidents"
  summary: "Runs read-only probes on transport and IP paths, explains the fault with cited RFCs and vendor documents, and proposes a fix for approval."
  outcome: "Engineers locate path and session faults sooner, with each diagnosis tied to probe output."
  audience: "Transport and IP engineers, change approvers, and risk owners"
  measures: ["Mean time to locate a fault", "Diagnoses confirmed by an engineer"]
  risk: "A wrong fix could cut a path, so an approver signs off each one."
placement:
  far-edge: {runs: [], note: "Not used: diagnostics run from the regional site."}
  regional: {runs: ["embedding", "reranker", "safety", "decision"], note: "Retrieval, the Safety check, and the gate label run here."}
  core: {runs: ["llm-large"], note: "The large LLM writes each diagnosis and fix proposal."}
---

<!-- Writing rules: framework/style-guide.md. Name each component by its role and the Red Hat product used. Write no product support status. -->

# Transport and IP diagnostics

## At a glance

| Field | Value |
|---|---|
| One-liner | Diagnoses transport and IP faults from read-only probe results and recommends fixes to a human approver. Never changes a router itself. Depends on IETF RFCs and vendor documents in retrieval and on read-only diagnostic tools. |
| Problem | Path, session, and delay faults in the transport network take long to locate across many devices; the KPI is mean time to locate a fault |
| Audience | Transport and IP engineers, change approvers, and risk owners |
| OTel slots | `embedding` and `reranker`: retrieval of RFCs and vendor documents; `safety`: abstain on weak evidence; `decision`: the gate label; `llm`: writes the diagnosis |
| Autonomy ceiling | Recommend with approval |
| Placement tier | Regional and core |
| Agent-school courses | 301 in the [agent-school roadmap](https://github.com/open-experiments/agent-school/blob/main/docs/RoadMap.md) |

## Problem and value

Transport faults show up as flapping BFD sessions, broken MPLS paths, or rising delay and loss between sites.
Engineers run probes device by device and check RFCs and vendor guides to find where the path breaks.
This entry runs read-only probes as tools, explains the fault with cited sources, and proposes a fix to an approver.
The KPIs are mean time to locate a fault and the share of diagnoses an engineer confirms.
Any gain is a target, measured against a shadow-stage baseline.

## How it works

_Stub: this catalog entry has no worked example or diagram yet._

## What you need

- [ ] Models: the five slots, chosen from the family in [PB-01](../../../platform/intake-model-selection/README.md), each pinned by revision with its licence chain recorded
- [ ] Platform blueprints: evaluation ([PB-02](../../../platform/evaluation-acceptance/README.md)), serving and routing ([PB-04](../../../platform/serving-routing-placement/README.md)), integration ([PB-05](../../../platform/integration/README.md)), safety gating ([PB-06](../../../platform/safety-autonomy-gating/README.md)), and the action layer ([PB-07](../../../platform/action-layer/README.md))
- [ ] Components: one product for each role in the components table
- [ ] Diagnostic tools: probes for BFD state, LSP ping, TWAMP, and YANG-Push streams, read-only under the deny-unless-allowed rule in [PB-05](../../../platform/integration/README.md#per-tool-authorization)
- [ ] Corpora: the IETF RFCs you run and your vendor NOS guides, each with a usage-rights entry
- [ ] Approval: every fix goes through the action layer, and the approver accepts or rejects it there
- [ ] Decision engine: vLLM 0.26 or 0.30 on CUDA or ROCm, as the [Decision model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) states
- [ ] Placement: the regional site runs Embedding, Reranker, Safety, and Decision. The core runs the large LLM.

| Component role | Red Hat product used |
|---|---|
| Inference engine for every slot | Red Hat AI Inference (vLLM) |
| Serving platform | Red Hat OpenShift AI with KServe |
| Tool gateway for the diagnostic tools | MCP gateway in Red Hat Connectivity Link |
| Action orchestration: gate, approval, rollout, and audit | Automation Orchestrator for Red Hat Ansible Automation Platform |
| Vector store for RFCs and vendor documents | Your choice; this design names no product |

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
| No model change: retrieval, a skill per role, and a capability manifest per tool | A golden set your experts label; gate labels from your approvers; a contract for each tool; your domain corpus | Configure first, and train only on a measured gap, as [PB-03 Adaptation](../../../platform/adaptation/README.md) sets out |

| Item | Network component | Mechanism | Owner | Matrix row |
|---|---|---|---|---|
| IETF RFCs you run and vendor NOS guides | Transport and IP | RAG corpus | Operations engineer | [Transport and IP](../../../platform/bring-your-own-data/README.md#domain-transport-and-ip) |
| BFD, LSP ping, TWAMP, and YANG-Push probe tools | Transport and IP | MCP tool contract | Platform team | [Transport and IP](../../../platform/bring-your-own-data/README.md#domain-transport-and-ip) |
| Transport triage skill and capability manifests | Transport and IP | Skill or capability manifest | SME | [Transport and IP](../../../platform/bring-your-own-data/README.md#domain-transport-and-ip) |
| Fix ceilings and approver roles | Transport and IP | Gate and action-layer policy | Risk owner | [Transport and IP](../../../platform/bring-your-own-data/README.md#domain-transport-and-ip) |

<!-- generated:what-you-bring end -->

### Sandbox

<!-- generated:sandbox start -->

| Sandbox fit | Trigger on this page | Where to read |
|---|---|---|
| Sandbox the tools and code: run them in their own micro-VM | Runs LSP ping and TWAMP probes against live paths | [PB-08: when a use case needs a sandbox](../../../platform/security-identity-sandbox/README.md#when-a-use-case-needs-a-sandbox) |

<!-- generated:sandbox end -->

### What you must add

| Gap | What you add | Source |
|---|---|---|
| IETF RFCs | The RFCs your network runs, such as BFD, LSP ping, TWAMP, and YANG-Push, in retrieval, because the card's training has no IETF RFC corpus | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| Vendor documents | Your vendor command-line and NOS guides in retrieval, because the card's training leaves them out | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| Diagnostic tools | Read-only probe tools with checked schemas, because the card's tool-use training holds no telecom tool-calling examples | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#tool-use-and-instruction-following) |
| Procedure evaluation | A set of past faults your engineers diagnosed, scored before the shadow stage, because the card reports no check against troubleshooting procedures | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#operational-procedure-mop-validation-not-performed) |
| Gate labels | A gate set of past fixes labelled by your approvers, because the Decision label probabilities aren't calibrated for your workload | [OTel-2.0-Decision-26B-A4B-4bit model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) |
| Language scope | Tests in every language your engineers read diagnoses in, because the card's quality claims cover English text only | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |

## Governance

Each action request passes the [decision gate](../../../architecture/decision-gate.md), and the outcome never exceeds the policy ceiling for its class.
The outcome is the lower of the model label and the policy ceiling for the capability and risk class, so it never exceeds either. A STOP label forces STOP at every stage.
Every action class begins at the shadow stage, where the outcome is LOOK. A confirmed false ACT drops the use case and its action class back one stage, as [PB-06](../../../platform/safety-autonomy-gating/README.md#staged-autonomy) sets out.

| Action | Gate outcome (LOOK/NOTIFY/REVIEW/ACT/STOP) | Approval | AI Act class |
|---|---|---|---|
| Post a diagnosis on the incident, `notify` | NOTIFY, from the assist stage up | None | Recorded by your legal team in the classification record |
| Propose a fix such as an interface restart, `write_low` | REVIEW, from the recommend stage up | The `approver` role | Recorded by your legal team in the classification record |
| Any action the label marks STOP | STOP | None | Recorded by your legal team in the classification record |

| Parameter | What it controls | Who sets it | How to calibrate |
|---|---|---|---|
| Embedding and Reranker recall-at-k floor | The lowest share of questions with a correct passage in the top results | Platform team, with subject-matter expert (SME) review | [Evaluation and acceptance](../../../platform/evaluation-acceptance/README.md): label relevant RFC and vendor passages for past faults |
| LLM groundedness floor | The lowest share of diagnoses whose claims the probe output and cited passages support | Risk owner, with SME review | Score a golden set of past faults with SME-checked diagnoses and a calibrated judge |
| Safety abstain-recall floor | The lowest share of insufficient-context items where the Safety slot abstains | Risk owner, with SME review | Remove the probe output from items and measure correct abstention |
| Decision false-ACT budget | The highest false-ACT rate accepted on fix proposals | Risk owner | [Evaluation and acceptance](../../../platform/evaluation-acceptance/README.md#false-act-method): use the false-ACT method on a gate set of past fixes |
| Ceiling for notify requests | The highest outcome for diagnosis notes | Risk owner, with SME review | Review diagnosis notes for duplicates and noise |
| Ceiling for low-risk writes | The highest outcome for reversible fixes such as an interface restart | Risk owner | Raise it only after a canary window with no false ACT label |

This page gives no default values. Each owner sets the value with SME review and versions it with the policy that `policy_version` names.

## Sources

Each key claim links its source, as set out in [the Sources table](../../../framework/definitions.md#sources-table).

| # | Claim | Basis | Source |
|---|---|---|---|
| 1 | The 31B training has no dedicated IETF RFC corpus and leaves out vendor command-line and NOS documents | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| 2 | The tool-use training holds general examples only, and agentic use needs an external tool runtime with checked tool schemas | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#tool-use-and-instruction-following) |
| 3 | The card reports no check of the 31B against methods of procedure, troubleshooting sequences included | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#operational-procedure-mop-validation-not-performed) |
| 4 | The 31B targets English-language use, and all its quality claims are text-only | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |
| 5 | Use the Decision model's label probabilities for confidence thresholds and routing; serve it on vLLM 0.26 or 0.30 | model card | [OTel-2.0-Decision-26B-A4B-4bit model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) |
| 6 | BFD detects faults in the path between two forwarding engines with low latency, and LSP ping detects data-plane failures in MPLS paths | project documentation | [RFC 5880](https://www.rfc-editor.org/rfc/rfc5880), [RFC 8029](https://www.rfc-editor.org/rfc/rfc8029) |
| 7 | TWAMP adds two-way and round-trip measurement to OWAMP | project documentation | [RFC 5357](https://www.rfc-editor.org/rfc/rfc5357) |
| 8 | YANG-Push streams updates from a YANG datastore for remote monitoring of operational state | project documentation | [RFC 8641](https://www.rfc-editor.org/rfc/rfc8641) |

## Deploy and verify

_Stub: this catalog entry has no deploy steps yet._

## Limitations

- The entry never changes a router on its own; an approver accepts every fix through the action layer.
- Its diagnosis rests on the probe output; it doesn't replace the probes.
- The card reports no check against troubleshooting procedures, so test diagnoses on your own past faults first.
- The Decision label probabilities count as uncalibrated until you calibrate them on your own fixes.
- The quality claims cover English only, so diagnoses in another language need their own evaluation.
