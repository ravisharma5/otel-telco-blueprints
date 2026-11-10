---
title: "Glossary"
doc_status: done
clarity_reviewed: "2026-11-10"
---

# Glossary

## At a glance

| Item | Answer |
|---|---|
| Purpose | One meaning per term across every blueprint |
| Naming rule | "OTel" is the model family; tracing is always "OpenTelemetry" in full |
| Sources terms | Defined in [Definitions](definitions.md); this page links there |
| Components | Named by role and the Red Hat product used; any component can be replaced ([Component naming](definitions.md#component-naming)) |

## The naming rule

"OTel" means the OTel model family: the GSMA/AT&T open telecom models (LLM, embedding, reranker, safety, decision, classification). Always write tracing, metrics, and logs instrumentation as "OpenTelemetry" in full. The Vale rule `Blueprints.OTelTracing` fails the lint when "OTel" means tracing.

| Write | Don't write |
|---|---|
| OpenTelemetry collector | `OTel collector` |
| OpenTelemetry traces | `OTel traces` |
| OpenTelemetry SDK | `OTel SDK` |
| OpenTelemetry spans | `OTel spans` |
| OpenTelemetry Protocol | `OTLP` (keep the acronym in code spans only) |

Correct uses of "OTel": OTel Decision model, OTel 2.5, OTel-2.0-LLM-31B-IT.

## Terms

| Term | Meaning | See |
|---|---|---|
| AAP (Ansible Automation Platform) | Red Hat automation platform that runs approved actions on network and IT systems | |
| AI grid tiers | Placement tiers for models: far-edge (cell site, hub), regional (MEC, regional edge), core (central DC) | |
| Autonomy ceiling | Highest gate outcome a blueprint allows without a human: inform, notify, recommend-with-approval, or act-within-policy | [Autonomy ceiling](definitions.md#autonomy-ceiling) |
| Basis | Where a key claim comes from: model card, research, Red Hat guidance, industry use case, or project documentation | [Claim basis](definitions.md#claim-basis) |
| Checkpoint | A published model revision, for example OTel-2.0-LLM-31B-IT at a pinned SHA. Contrast with OTel slot | OTel slot (this table) |
| EvalHub | OpenShift AI component that runs model evaluations and gates | |
| Gate outcome | Result of the decision gate: LOOK, NOTIFY, REVIEW, ACT, or STOP | [Autonomy ceiling](definitions.md#autonomy-ceiling) |
| llm-d | Distributed inference for vLLM on Kubernetes: replica scheduling, prefix-cache routing, flow control | |
| MaaS (Models-as-a-Service) | OpenShift AI gateway that gives each team API keys, token limits, and one endpoint per model | |
| MCP (Model Context Protocol) | Open protocol that agents use to call tools and read context | |
| MEC (multi-access edge computing) | Compute at the regional edge of the operator network | |
| MicroShift | Small-footprint Kubernetes in Red Hat Device Edge for far-edge devices | |
| OGX (formerly Llama Stack) | Agent and inference API layer in OpenShift AI | |
| One-liner | One line per blueprint: what the design does and its main dependency, plus the autonomy ceiling for use cases | [One-liner](definitions.md#one-liner) |
| OpenTelemetry | Open standard for traces, metrics, and logs; always written in full here | [The naming rule](#the-naming-rule) |
| OTel | The GSMA/AT&T open telecom model family; never tracing | [The naming rule](#the-naming-rule) |
| OTel slot | A role a model fills: `llm`, `embedding`, `reranker`, `safety`, `decision`, or `classification`. Blueprints name slots, not checkpoints | |
| Recipe | A blueprint or architecture built from telecom network expertise, industry use cases, research, and Red Hat recommendations | [Claim basis](definitions.md#claim-basis) |
| Replaceable component | A product the reference architecture uses to fill a role. Any component can be replaced; blueprints name the role and the Red Hat product, never a support status | [Component naming](definitions.md#component-naming) |
| RHAII (Red Hat AI Inference) | Red Hat's supported vLLM container images | |
| RHCL (Red Hat Connectivity Link) | Kuadrant-based gateway policy: auth, rate limits, multi-cluster routing | |
| RHOAI (Red Hat OpenShift AI) | Red Hat's AI platform on OpenShift: serving, registry, MaaS, EvalHub, Training Hub | |
| SDG Hub | Synthetic data generation toolkit for building training data from tools and documents | |
| SNO (single-node OpenShift) | A full OpenShift cluster on one node, used at regional sites | |
| Sources table | Per-blueprint table: one row per key claim, with its basis and a source link | [Sources table](definitions.md#sources-table) |
| Training Hub | Python library for LoRA, QLoRA, OSFT, and GRPO fine-tuning on OpenShift AI | |
| vLLM | Open source inference engine that serves every OTel slot | |
