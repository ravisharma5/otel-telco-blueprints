---
type: "reference"
title: "Crosswalk to the agent blueprint table"
question: "How does this design line up with the 13-component agent blueprint table that agent-school uses?"
doc_status: draft
clarity_reviewed: "2026-11-10"
platform_blueprints: ["PB-02", "PB-03", "PB-04", "PB-05", "PB-06", "PB-07", "PB-08", "PB-09"]
otel_slots: ["llm", "embedding", "reranker", "safety", "decision", "classification"]
---

# Crosswalk to the agent blueprint table

## At a glance

| Field | Value |
|---|---|
| Question answered | How does this design line up with the 13-component agent blueprint table that agent-school uses? |
| Answer | All 13 rows keep their numbers and names, each maps to a layer and product in this design, and seven extension rows add what telecom production needs |
| Audience | Architects, and teams that already follow the agent blueprint article or agent-school |
| OTel slots | All six: LLM, Embedding, Reranker, Safety, Decision, Classification |
| Platform blueprints | PB-02 to PB-09 |

## The question

How does this design line up with the 13-component agent blueprint table that agent-school uses?
Without a crosswalk, teams that know the table have to guess where each OTel slot and control fits.
This page is a draft pending review by the agent-school maintainers, who keep the table's numbering in the [agent-school project](https://github.com/open-experiments/agent-school).

## The principle

Compose, do not contradict. The 13 rows of Table 1 in the [Red Hat Developer blueprint article](https://developers.redhat.com/articles/2026/07/20/architect-open-blueprint-cloud-native-ai-agents) keep their numbers and names.
This design adds extension rows for what telecom production needs. It never renames or merges a row.

## The design

### Table 1 rows

The article's Table 1 has no row numbers. The numbers here follow agent-school's [roadmap](https://github.com/open-experiments/agent-school/blob/main/docs/RoadMap.md), and the component names match the [article](https://developers.redhat.com/articles/2026/07/20/architect-open-blueprint-cloud-native-ai-agents) exactly.

| # | Table 1 component | Layer in this design | Role and Red Hat product used |
|---|---|---|---|
| 1 | Agent blueprint / GitOps | Control | Declare and deploy every layer with OpenShift GitOps (Argo CD) and Helm, across sites with Red Hat Advanced Cluster Management |
| 2 | Agent orchestration | Agent runtime | Split work into diagnose, plan, execute, and validate agents that talk over A2A with agent cards, on Red Hat OpenShift |
| 3 | Sandbox runtime (supervisor) | Agent runtime | Limit files, egress, and system calls, and inject credentials, with the Red Hat build of Agent Sandbox on Red Hat OpenShift |
| 4 | Harness | Agent runtime | Own the loop, context, and tool calls with a LangGraph or custom harness and the OTel LLM slot |
| 5 | Agentic loop runtime (Agent-as-a-Service) | Agent runtime | Run the loop as a managed service with the Responses API in Red Hat OpenShift AI |
| 6 | Model | Model endpoint inferencing | Serve the six OTel slots by name, pinned to a revision, on Red Hat AI Inference (vLLM) |
| 7 | AI gateway (MaaS) | AI Gateway | Decide who may call which model and how many tokens with the Models-as-a-Service front door |
| 8 | Semantic routing | AI Gateway | Pick the slot and model size for each request with the OTel Decision model on Red Hat AI Inference (vLLM) |
| 9 | Inference routing | AI Gateway | Pick the replica by prefix cache and load with the Distributed Inference with llm-d scheduler |
| 10 | Model workers | Model endpoint inferencing | Generate tokens, log probabilities, and pooled outputs with Red Hat AI Inference (vLLM) on KServe, and with llm-d for generative slots in the core |
| 11 | Skills | Network capabilities | Offer read, notify, and action-request tools through standards-based MCP servers, with the Classification slot as a governed tool |
| 12 | Workload identity | Control | Give each agent its own short-lived identity with SPIFFE/SPIRE and Keycloak token exchange |
| 13 | Tool governance | MCP Gateway | Authorize every tool call by token claims and risk class with the MCP gateway in Red Hat Connectivity Link, Kuadrant policies, and Keycloak |

### Extension rows

| # | Extension | Layer in this design | Why it is added |
|---|---|---|---|
| E1 | Knowledge service with the Embedding and Reranker slots | Data and knowledge | Fills the knowledge half of the Skills row: what the operator owns goes into retrieval, and live state comes through tools |
| E2 | Inference guardrails and abstention with the Safety slot | Safety and governance | The article shows inference guardrails among its controls but gives them no row, and abstention needs its own slot |
| E3 | Decision gate with the Decision slot | Safety and governance | The gate decides whether a step should happen now, while tool governance decides whether an identity may call a tool |
| E4 | Action layer | Action | Only the action layer changes network state, so the agent recommends and the orchestrator decides |
| E5 | Evaluation and acceptance | Lifecycle plane | The article names pre-production testing, and production needs a promotion gate on measured results |
| E6 | Adaptation | Lifecycle plane | Each operator fits slots to its own network, and the adaptation ladder says when to climb |
| E7 | Placement and observability | Placement and lifecycle planes | Telecom sites run from far edge to core, and every step needs a trace and a cost |

Any component can be replaced. The Red Hat products named here show one way to build this design.

## Trade-offs and limits

| Trade-off | What to do |
|---|---|
| This page represents another project's table | Keep it as a draft until the agent-school maintainers review it, and never rename, renumber, or merge a row |
| Extension rows sit close to some Table 1 rows | Say which row each extension complements, such as the gate next to tool governance and knowledge next to skills |
| Semantic routing here uses the OTel Decision model instead of a dedicated router | Keep the row, and swap the component if a router fits your traffic better |
| Product picks change faster than the table | Keep row numbers and names fixed, and update only the product column |

## Used by

- [PB-04](../platform/serving-routing-placement/README.md), [PB-05](../platform/integration/README.md), [PB-06](../platform/safety-autonomy-gating/README.md), [PB-07](../platform/action-layer/README.md), [PB-08](../platform/security-identity-sandbox/README.md): serving, integration, gating, the action layer, and security map onto these rows
- [PB-02](../platform/evaluation-acceptance/README.md), [PB-03](../platform/adaptation/README.md), [PB-09](../platform/quality-operations/README.md): evaluation, adaptation, and observability fill the lifecycle extensions
- [Architecture overview](index.md): the layer table this crosswalk maps to
- [Decision gate](decision-gate.md): the gate extension in detail
- [Adaptation ladder](adaptation-ladder.md): the adaptation extension in detail
- [Placement tiers](placement.md): the placement extension in detail
