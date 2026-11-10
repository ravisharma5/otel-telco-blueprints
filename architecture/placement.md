---
type: "reference"
title: "Placement tiers"
question: "Which OTel slots run at the far edge, regional sites, and the core, and what latency can each tier support?"
doc_status: "draft"
platform_blueprints: ["PB-04", "PB-08", "PB-10"]
otel_slots: ["llm", "embedding", "reranker", "safety", "decision", "classification"]
---

# Placement tiers

## At a glance

| Field | Value |
|---|---|
| Question answered | Which OTel slots run at the far edge, regional sites, and the core, and what latency can each tier support? |
| Answer | The far edge runs one small model per box, regional sites run a closed loop with several slots, and the core runs the large LLM, adaptation, and evaluation |
| Audience | Architects and platform engineers |
| OTel slots | All six: LLM, Embedding, Reranker, Safety, Decision, Classification |
| Platform blueprints | PB-04, PB-08, PB-10 |

## The question

Which OTel slots run at the far edge, at regional sites, and in the core, and what latency can each tier support?
Without a placement rule, a slow model ends up inside a fast loop, or network data leaves the region it must stay in.

## The principle

Place a slot as close to the network as its latency needs, and no closer.
Keep adaptation, evaluation, and the model lifecycle in the core, and send only evaluated, pinned models out to the sites.
Each use case answers the serving and placement question in the [readiness questions](../framework/index.md) with a tier for every slot.

## The design

### Tiers

| Tier | Platform (role and Red Hat product) | OTel slots placed here | Latency range | Place a slot here when |
|---|---|---|---|---|
| Far edge | Single-model inference box on RHEL with Podman running Red Hat AI Inference, or on Red Hat Device Edge (MicroShift) with KServe | One model per box, either Decision as the gate, Classification, or a small LLM; small Embedding models on CPU | milliseconds per decision | A decision must happen next to a network element at a cell site or hub |
| Regional | Closed-loop site on single-node OpenShift with Red Hat OpenShift AI | Decision, Safety, Classification, a small LLM, Embedding, Reranker, and the large LLM in a quantized build; a local retrieval index | sub-second closed loop | Network data must stay in the region, and the loop must close on site |
| Core | Shared model and lifecycle platform on multi-node Red Hat OpenShift with Red Hat OpenShift AI | The large LLM at full precision under Distributed Inference with llm-d, Decision replicas, and shared Safety, Classification, Embedding, and Reranker services; plus the Models-as-a-Service front door, Training Hub, SDG Hub, EvalHub, Model Registry, and the fleet hub (Red Hat Advanced Cluster Management) | seconds (interactive) to minutes-hours (batch) | Many teams share the work, it needs the largest model, or it changes models through adaptation and evaluation |

Any component can be replaced. The Red Hat products named here show one way to build this design.

Models and adapters reach edge sites through OpenShift GitOps and Red Hat Advanced Cluster Management: the core builds, evaluates, and versions each model, and the fleet hub copies it to each site before rollout.

## Trade-offs and limits

| Trade-off | What to do |
|---|---|
| Generative answers take seconds | Put the Decision or Classification slot in closed loops, and use the large LLM to explain results and support human review |
| MicroShift runs one AI model per deployment ([MicroShift docs](https://docs.redhat.com/en/documentation/red_hat_build_of_microshift/4.22/html/using_ai_models/microshift-rh-openshift-ai)) | Plan one model per far-edge box, and use single-node OpenShift when a site needs several slots |
| llm-d schedules within one cluster, so it does not choose the tier | Choose far edge, regional, or core in the caller, or with multi-cluster DNS policy |
| A quantized large LLM can answer worse than the full-precision build | Evaluate the quantized build on your own telecom tasks before you place it at a regional site |
| Edge sites can have thin or no links to the core | Copy models and adapters to each site ahead of rollout, and serve them from a local registry mirror |

## Used by

- PB-04: serving and placement build on these tiers
- PB-08, PB-10: air-gapped operation and in-country inference use the regional and far-edge tiers
- [Architecture overview](index.md): the placement layer this page details
- [Decision gate](decision-gate.md): the gate model that runs closest to the network
- [Adaptation ladder](adaptation-ladder.md): the adaptation work that stays in the core
- [Readiness questions](../framework/index.md): the serving and placement question this page answers
