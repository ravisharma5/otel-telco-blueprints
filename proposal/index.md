---
title: "Proposal"
doc_status: done
clarity_reviewed: "2026-11-16"
---

# Proposal: running OTel models in production

<!-- generated:facts-stamp start -->

Facts checked as of 2026-11-16.

<!-- generated:facts-stamp end -->

Download the proposal as a PDF: <a href="otel-telco-blueprints-proposal.pdf">otel-telco-blueprints-proposal.pdf</a>

## At a glance

- **What it is:** blueprints for running the OTel model family in production for telecom use cases.
- **Who it's for:** GSMA members and telecom operators.
- **What's in it:** ten readiness questions, a reference architecture, eleven platform blueprints, and a catalog of use-case recipes.
- **Open source:** the blueprints use Red Hat products to show how the solution works, and you can replace any component.

## The problem

GSMA reports that general-purpose models still fall short on telecom tasks, and that operators often deploy models that can't reach the accuracy, safety, or efficiency they need ([GSMA press release, March 2, 2026](https://www.gsma.com/newsroom/press-release/gsma-launches-open-telco-ai-to-accelerate-development-of-telco%E2%80%91grade-ai/)).
A benchmark score shows what a model can do on a task. It doesn't show what it takes to run that model safely on a live network.

## Where this fits

GSMA's Open Telco AI programme provides open models, data, compute, and benchmarks that show what models can do on telecom tasks ([press release](https://www.gsma.com/newsroom/press-release/gsma-launches-open-telco-ai-to-accelerate-development-of-telco%E2%80%91grade-ai/)).
These blueprints cover what it takes to run those models in production: the platform, the integrations, the safety gates, the evidence, and the operating model.
GSMA publishes the programme's datasets and leaderboard on [Hugging Face](https://huggingface.co/GSMA).

## The ten readiness questions

A use case is ready for production when each question has a checkable answer.

<!-- generated:readiness-questions start -->

| # | Question | What ready means | Answered by |
|---|---|---|---|
| 1 | Intake: which checkpoints may you run, and where do they come from? | Every checkpoint in use is pinned to a revision hash, has a recorded licence chain, and is served from your own registry as a signed image | [PB-01](../platform/intake-model-selection/README.md) |
| 2 | Evaluation: how do you know a model is good enough for this use case? | Each slot has acceptance thresholds measured on your data and tool contracts, signed off by a named owner, and re-run on every model, prompt, tool, or adapter change | [PB-02](../platform/evaluation-acceptance/README.md) |
| 3 | Adaptation: how do you fit the model to your network? | You climb from retrieval to skills, LoRA, and OSFT only when an evaluation gap calls for it, and every adapter is bound to one base revision and re-evaluated after a base upgrade | [PB-03](../platform/adaptation/README.md), [PB-11](../platform/bring-your-own-data/README.md) |
| 4 | Serving and placement: where and how does each slot run? | Each slot has a sized deployment on a hardware class, a placement tier, a latency target, and a fallback for when it is down | [PB-04](../platform/serving-routing-placement/README.md) |
| 5 | Integration: how do agents reach your network and business systems? | Agents reach systems only through standards-based tools (TM Forum, CAMARA, 3GPP) behind one gateway. Tools are read-only by default and have versioned contracts and conformance tests | [PB-05](../platform/integration/README.md), [PB-11](../platform/bring-your-own-data/README.md) |
| 6 | Autonomy gating: what may the agent do without a human? | Each action class has a declared autonomy level, a gate outside the model decides each step, an approver handles REVIEW, and every change is verified and can roll back | [PB-06](../platform/safety-autonomy-gating/README.md), [PB-07](../platform/action-layer/README.md) |
| 7 | Security: how do you stop misuse of agents and tools? | Each agent has its own short-lived identity, the gateway authorizes every tool call, secrets never reach the model context, untrusted content is screened for prompt injection, and the stack runs air-gapped when required | [PB-08](../platform/security-identity-sandbox/README.md) |
| 8 | Quality operations: how do you notice when quality drops? | Every episode is traced end to end with OpenTelemetry, drift signals such as abstention rate, gate labels, and human overrides have thresholds and owners, and AI incidents follow your NOC and SOC process | [PB-09](../platform/quality-operations/README.md) |
| 9 | Compliance and sovereignty: can you show the use case meets the rules and keeps data where it must stay? | Each use case has an EU AI Act classification record, a GDPR, NIS2, and CAMARA consent mapping, and a data residency statement backed by in-country inference | [PB-10](../platform/compliance-operating-model/README.md) |
| 10 | Operating model: who owns the use case, and how does it grow? | The use case has a named accountable owner, a RACI, a staged rollout plan (shadow, assist, recommend, act), and a measured value case | [PB-10](../platform/compliance-operating-model/README.md) |

<!-- generated:readiness-questions end -->

## Reference architecture

These pages show how the six OTel model slots fit together and where each one runs.

<!-- generated:architecture start -->

| Page | Question it answers |
|---|---|
| [Architecture overview](../architecture/index.md) | How do the six OTel model slots map onto Red Hat products, and how do requests flow? |
| [Decision gate](../architecture/decision-gate.md) | How does an agent's proposed change become an executed, blocked, or human-approved action? |
| [Adaptation ladder](../architecture/adaptation-ladder.md) | How far should an operator customise an OTel model, and when should they go further? |
| [Placement tiers](../architecture/placement.md) | Which OTel slots run at the far edge, regional sites, and the core, and what latency can each tier support? |
| [Crosswalk to the agent blueprint table](../architecture/crosswalk.md) | How does this design line up with the 13-component agent blueprint table that agent-school uses? |

<!-- generated:architecture end -->

## Platform blueprints

Platform blueprints answer the readiness questions once, so every use case can reuse the answers.

<!-- generated:platform start -->

| ID | Platform blueprint | One-liner |
|---|---|---|
| PB-01 | [Intake and model selection](../platform/intake-model-selection/README.md) | Decides which OTel checkpoints you may run by following each licence chain to its base model, pins every checkpoint to a commit revision, and serves it as a signed image from your own registry. Depends on a model registry, an image signing service, and your legal team's review. |
| PB-02 | [Evaluation and acceptance](../platform/evaluation-acceptance/README.md) | Accepts a model, adapter, prompt, or tool change only after it passes a five-stage ladder on your own data, with process checks and a false-ACT budget for the gate. Depends on an evaluation runner, a promotion pipeline, and a model registry. |
| PB-03 | [Adaptation](../platform/adaptation/README.md) | Fits OTel models to your network by climbing from retrieval to skills and capability manifests, then to LoRA and OSFT, only when evaluation shows a measured gap. Depends on a knowledge service, a training stack, and a model registry that binds each adapter to its base revision. |
| PB-04 | [Serving, routing, and placement](../platform/serving-routing-placement/README.md) | Sizes, serves, routes, and places every OTel slot from the far edge to the core. Depends on a front door, the Decision slot for content routing, and a replica scheduler. |
| PB-05 | [Integration](../platform/integration/README.md) | Connects agents to network and business systems through standards-based tools. Each call is authorized per tool and audited. Depends on an MCP gateway and an authorization server. |
| PB-06 | [Safety and autonomy gating](../platform/safety-autonomy-gating/README.md) | Screens every input, tool response, and answer, grounds answers in evidence, and gates every change by autonomy stage. Depends on guardrails, the Safety and Decision slots, and an orchestrator that applies the policy ceiling. |
| PB-07 | [Action layer](../platform/action-layer/README.md) | Turns an agent's action request into a gated, approved, executed, verified, and audited change, with rollback on failure. Depends on an automation platform that holds the only write credentials. |
| PB-08 | [Security, identity, and sandbox](../platform/security-identity-sandbox/README.md) | Gives each agent its own short-lived identity, runs it in a sandbox with no shell and egress only to the two gateways, keeps secrets out of model context, screens tool responses for prompt injection, and runs air-gapped when required. Depends on a workload identity service, an agent sandbox, and a secret store. |
| PB-09 | [Quality operations and observability](../platform/quality-operations/README.md) | Traces every agent step with OpenTelemetry, watches six drift signals that each have an owner and a threshold, sends AI incidents through your NOC and SOC process, and feeds human overrides into the next golden set. Depends on a tracing collector, a trace store, and an agent trace store. |
| PB-10 | [Compliance, sovereignty, and operating model](../platform/compliance-operating-model/README.md) | Records an EU AI Act classification for each use case, maps the EU AI Act, NIS2, GDPR, CAMARA consent, and GSMA Responsible AI to the controls that produce evidence, keeps data in country, and names owners, rollout stages, and value measures. Depends on your legal team and on the evidence the other blueprints produce. |
| PB-11 | [Bring your own data and policies](../platform/bring-your-own-data/README.md) | Tells you, for each network domain and each part of the agent runtime harness, what data or policy to bring, in what format, where it goes, who owns it, and which gate checks it. Depends on the adaptation ladder, the tool gateway, and the evaluation gates. |

<!-- generated:platform end -->

## Use-case catalog

A full recipe adds a worked example and deploy steps. A catalog entry fits on one page.

<!-- generated:catalog start -->

### Standards and knowledge

| Use case | Title | Depth | Summary |
|---|---|---|---|
| [UC-KNOW-01](../catalog/standards-knowledge/grounded-knowledge-assistant/README.md) | Grounded knowledge assistant | Full recipe | Answers standards and runbook questions from your own documents with citations, or says it can't answer and shows what it searched. |
| [UC-KNOW-02](../catalog/standards-knowledge/spec-summarisation/README.md) | Standards and change-request summaries | Catalog entry | Summarises 3GPP specifications and change requests from documents you hold, citing each clause, or says what it could not find. |
| [UC-KNOW-03](../catalog/standards-knowledge/oss-bss-architecture-guidance/README.md) | OSS and BSS architecture guidance | Catalog entry | Answers OSS and BSS architecture questions from TM Forum material and your own designs, with citations, or says it can't answer. |

### Network software

| Use case | Title | Depth | Summary |
|---|---|---|---|
| [UC-SW-01](../catalog/network-software/ran-core-code-assistant/README.md) | RAN and core code assistant | Catalog entry | Answers questions about your RAN and core code, citing files and 3GPP clauses, or says what it searched without an answer. |
| [UC-SW-02](../catalog/network-software/network-automation-review/README.md) | Network automation review | Catalog entry | Reviews proposed network automation changes against schema checks, dry runs, and your standards, then recommends approval to an engineer. |
| [UC-SW-03](../catalog/network-software/oran-ric-xapp-assistant/README.md) | O-RAN RIC xApp assistant | Catalog entry | Answers xApp development questions from O-RAN specifications and your RIC code, with citations, or says what it searched. |

### Network operations

| Use case | Title | Depth | Summary |
|---|---|---|---|
| [UC-OPS-01](../catalog/network-operations/alarm-triage-adaptation/README.md) | Adaptation ladder on alarm and root-cause triage | Full recipe | Finds the likely cause in RAN and transport alarms and proposes fixes for approval. It fine-tunes the model only when evaluation shows a gap. |
| [UC-OPS-02](../catalog/network-operations/signalling-trace-analysis/README.md) | Signalling trace analysis | Catalog entry | Explains why a registration, session, or handover failed in a signalling trace. Each finding cites a decoded message and a 3GPP clause. |
| [UC-OPS-03](../catalog/network-operations/core-network-rca/README.md) | Core network root-cause analysis | Full recipe | Correlates 5G core logs, traces, counters, and alarms to rank likely causes, writes an RCA note, and proposes fixes for approval. |
| [UC-OPS-04](../catalog/network-operations/ran-rf-health-checks/README.md) | RAN and RF health checks | Catalog entry | Explains cell health findings from your performance counters and radio measurements, and proposes parameter changes for an engineer to approve. |
| [UC-OPS-05](../catalog/network-operations/ran-energy-saving/README.md) | RAN energy saving | Full recipe | Plans energy-saving windows for capacity booster cells hours ahead, simulates each first, and acts only on low-risk cells after earning it. |
| [UC-OPS-06](../catalog/network-operations/slice-sla-assurance/README.md) | Slice SLA assurance | Full recipe | Correlates slice KPIs and analytics with each slice's SLOs, warns the slice owner before a breach, and proposes slice changes for approval. |
| [UC-OPS-07](../catalog/network-operations/mop-validation/README.md) | MOP validation | Full recipe | Reviews each change's MOP against inventory, documents, and a dry run, then recommends approval or rejection to the change approver. |
| [UC-OPS-08](../catalog/network-operations/transport-ip-diagnostics/README.md) | Transport and IP diagnostics | Catalog entry | Runs read-only probes on transport and IP paths, explains the fault with cited RFCs and vendor documents, and proposes a fix for approval. |
| [UC-OPS-09](../catalog/network-operations/cross-domain-oss-correlation/README.md) | Cross-domain OSS correlation | Catalog entry | Links alarms from RAN, transport, and core into one incident through topology and inventory, and proposes the grouping for approval. |

### Agentic operations

| Use case | Title | Depth | Summary |
|---|---|---|---|
| [UC-AGOPS-01](../catalog/agentic-operations/closed-loop-incident-handling/README.md) | Governed closed-loop incident handling | Full recipe | An agent investigates router alarms with read-only tools and opens tickets. Every fix passes a gate, and low-risk fixes skip approval only after earning it. |
| [UC-AGOPS-02](../catalog/agentic-operations/router-core-read-only-ops/README.md) | Read-only router and 5G core operations | Catalog entry | An agent reads router state, network analytics, and subscription data through read-only tools, and answers with the output it read. |
| [UC-AGOPS-03](../catalog/agentic-operations/policy-following-ops-agents/README.md) | Policy-following operations agents | Catalog entry | Agents propose operations changes under written policies. Each policy names an action class and its ceiling, and an approver signs off every change. |

### Business assurance

| Use case | Title | Depth | Summary |
|---|---|---|---|
| [UC-BIZ-01](../catalog/business-assurance/churn-risk-explanation/README.md) | Churn risk explanation | Catalog entry | Explains why your own churn model scores a customer as at risk, and drafts a retention offer for a retention manager to approve. |
| [UC-BIZ-02](../catalog/business-assurance/revenue-assurance-triage/README.md) | Revenue assurance triage | Catalog entry | Explains each case your own fraud or revenue assurance model flags, and proposes a hold or an escalation for an analyst to approve. |
| [UC-CARE-01](../catalog/business-assurance/camara-care-diagnostics/README.md) | CAMARA customer-care diagnostics | Full recipe | Suggests answers to care agents on no-service calls, using device status read through CAMARA APIs with the customer's consent. |
| [UC-CARE-02](../catalog/business-assurance/broadband-digital-troubleshooting/README.md) | Broadband digital troubleshooting | Catalog entry | Reads home gateway and Wi-Fi diagnostics with the customer's consent, and suggests the next troubleshooting step to the care agent. |

### Security

| Use case | Title | Depth | Summary |
|---|---|---|---|
| [UC-SEC-01](../catalog/security/security-triage/README.md) | Security alert triage | Catalog entry | Labels and summarises alerts from your own security detectors, then proposes containment for an approver to accept or reject. |
| [UC-SEC-02](../catalog/security/signalling-attack-classification/README.md) | Signalling attack classification | Catalog entry | Labels suspect core signalling that your detectors flag and explains each label with the messages behind it. |

### Research

| Use case | Title | Depth | Summary |
|---|---|---|---|
| [UC-RES-01](../catalog/research/kpi-rca-reasoning/README.md) | KPI root-cause reasoning | Catalog entry | Takes a KPI degradation your monitoring already found, reasons to its likely root cause, and proposes a parameter change for approval. |
| [UC-RES-02](../catalog/research/mobility-failure-analysis/README.md) | 5G mobility failure analysis | Catalog entry | Explains failed 5G handovers and registrations step by step, citing the 3GPP procedure that each failed message belongs to. |

<!-- generated:catalog end -->

## Flagship recipes

<!-- generated:flagships start -->

| Recipe | Outcome | Measures |
|---|---|---|
| [Governed closed-loop incident handling](../catalog/agentic-operations/closed-loop-incident-handling/README.md) | Incidents reach a cause and a ticket sooner, with fewer duplicates, and every change leaves an audit record. | Mean time to identify; Incidents handled without rework; Duplicate tickets avoided |
| [CAMARA customer-care diagnostics](../catalog/business-assurance/camara-care-diagnostics/README.md) | Care agents see a device's roaming, reachability, and network type, so they resolve more calls on first contact. | Average handling time; First-contact resolution |
| [Grounded knowledge assistant](../catalog/standards-knowledge/grounded-knowledge-assistant/README.md) | Engineers get cited answers without searching 3GPP, IETF, TM Forum, and vendor documents by hand. | Time to a cited answer; Share of answers reviewers accept |
| [Adaptation ladder on alarm and root-cause triage](../catalog/network-operations/alarm-triage-adaptation/README.md) | Engineers find the one cause in an alarm storm sooner, with causes labelled in your own taxonomy. | Mean time to identify; Incidents triaged without rework |

<!-- generated:flagships end -->

Reference implementations are planned for these four recipes first.

## The explorer

The [use-case explorer](https://ravisharma5.github.io/otel-telco-blueprints/) shows every use case as a card.
Pick a goal, open a use case, and choose your hardware setup to see which models fit, where they run, and what you bring.

## Sources and evidence summary

Each use case links a source for every key claim. This table counts those sources and doesn't grade them.

<!-- vale Google.Colons = NO -->
<!-- generated:evidence-summary start -->

Counted from each page's Sources table on 2026-11-16. Each number is how many Sources rows on the page have that Basis.

| Use case | Depth | Model card | Research | Red Hat guidance | Industry use case | Project documentation | Named gates | What you bring |
|---|---|---|---|---|---|---|---|---|
| [UC-AGOPS-01](../catalog/agentic-operations/closed-loop-incident-handling/README.md) Governed closed-loop incident handling | Full recipe | 5 | 3 | 2 | 0 | 3 | Decision false-ACT budget; Decision minimum ACT probability; Decision REVIEW band; Decision calibration error ceiling; Minimum share of no-write scenarios; Non-inferiority margin; Shadow agreement floor; Canary window; Override rate ceiling; Ceiling for read requests; Ceiling for notify requests; Ceiling for low-risk writes; Ceiling for high-risk writes; Required approver role per action class; Label-mass floor | Retrain the Classification head. You bring: Your fault or alert taxonomy, A golden set your experts label, Gate labels from your approvers, A contract for each tool |
| [UC-AGOPS-02](../catalog/agentic-operations/router-core-read-only-ops/README.md) Read-only router and 5G core operations | Catalog entry | 4 | 0 | 0 | 0 | 3 | Decision routing threshold; Non-inferiority margin; LLM groundedness floor; Safety abstain-recall floor; Tool error rate threshold; Trace live retention period | No model change: retrieval and skills. You bring: A golden set your experts label, Gate labels from your approvers, A contract for each tool |
| [UC-AGOPS-03](../catalog/agentic-operations/policy-following-ops-agents/README.md) Policy-following operations agents | Catalog entry | 6 | 0 | 0 | 0 | 0 | Ceiling per risk class; Required approver role per action class; Decision false-ACT budget; Safety abstain-recall floor; Minimum share of no-write scenarios; Override rate ceiling | No model change: retrieval and skills. You bring: A golden set your experts label, Gate labels from your approvers, A contract for each tool |
| [UC-BIZ-01](../catalog/business-assurance/churn-risk-explanation/README.md) Churn risk explanation | Catalog entry | 5 | 0 | 0 | 0 | 3 | LLM groundedness floor; Safety abstain-recall floor; Decision false-ACT budget; Ceiling for high-risk writes; Required approver role per action class; Trace archive retention period | No model change: retrieval and skills. You bring: A golden set your experts label, Gate labels from your approvers, A contract for each tool |
| [UC-BIZ-02](../catalog/business-assurance/revenue-assurance-triage/README.md) Revenue assurance triage | Catalog entry | 6 | 0 | 0 | 0 | 1 | LLM groundedness floor; Decision false-ACT budget; Ceiling for low-risk writes; Ceiling for high-risk writes; Required approver role per action class; Trace archive retention period | No model change: retrieval and skills. You bring: A golden set your experts label, Gate labels from your approvers, A contract for each tool |
| [UC-CARE-01](../catalog/business-assurance/camara-care-diagnostics/README.md) CAMARA customer-care diagnostics | Full recipe | 2 | 1 | 1 | 0 | 9 | Safety abstain-recall floor; Safety false-abstention ceiling; LLM groundedness floor; Embedding and Reranker recall-at-k floor; Decision routing threshold; Ceiling for read requests; Ceiling for notify requests; Ceiling for low-risk writes; Required approver role per action class; Override rate ceiling; Trace archive retention period | No model change: retrieval and skills. You bring: A golden set your experts label, Gate labels from your approvers, A contract for each tool, Your domain corpus |
| [UC-CARE-02](../catalog/business-assurance/broadband-digital-troubleshooting/README.md) Broadband digital troubleshooting | Catalog entry | 6 | 0 | 0 | 0 | 2 | Embedding and Reranker recall-at-k floor; Safety abstain-recall floor; Decision false-ACT budget; Ceiling for low-risk writes; Required approver role per action class; Trace archive retention period | No model change: retrieval and skills. You bring: A golden set your experts label, Gate labels from your approvers, A contract for each tool, Your domain corpus |
| [UC-KNOW-01](../catalog/standards-knowledge/grounded-knowledge-assistant/README.md) Grounded knowledge assistant | Full recipe | 8 | 0 | 2 | 1 | 1 | LLM groundedness floor; LLM citation-correctness floor; Embedding and Reranker recall-at-k floor; Safety abstain-recall floor; Safety false-abstention ceiling; Non-inferiority margin; Decision routing threshold; Groundedness drift band; Abstention rate drift band | No model change: retrieval only. You bring: A golden set your experts label, Gate labels from your approvers, Your domain corpus |
| [UC-KNOW-02](../catalog/standards-knowledge/spec-summarisation/README.md) Standards and change-request summaries | Catalog entry | 6 | 0 | 0 | 0 | 3 | LLM groundedness floor; LLM citation-correctness floor; Safety abstain-recall floor; Non-inferiority margin; Decision routing threshold | No model change: retrieval only. You bring: A golden set your experts label, Gate labels from your approvers, Your domain corpus |
| [UC-KNOW-03](../catalog/standards-knowledge/oss-bss-architecture-guidance/README.md) OSS and BSS architecture guidance | Catalog entry | 5 | 0 | 0 | 0 | 2 | LLM groundedness floor; LLM citation-correctness floor; Embedding and Reranker recall-at-k floor; Safety abstain-recall floor; Safety false-abstention ceiling | No model change: retrieval only. You bring: A golden set your experts label, Your domain corpus |
| [UC-OPS-01](../catalog/network-operations/alarm-triage-adaptation/README.md) Adaptation ladder on alarm and root-cause triage | Full recipe | 2 | 1 | 2 | 0 | 4 | Minimum measured gap to train; Minimum share of non-ACT training cases; Non-inferiority margin; Classification per-class recall floor; Classification other-or-abstain recall floor; LLM groundedness floor; Decision false-ACT budget; Ceiling for notify requests; Ceiling for low-risk writes | Retrain the head; LoRA only if a gap remains. You bring: Your fault or alert taxonomy, A golden set your experts label, Gate labels from your approvers, A contract for each tool, Your domain corpus |
| [UC-OPS-02](../catalog/network-operations/signalling-trace-analysis/README.md) Signalling trace analysis | Catalog entry | 4 | 0 | 0 | 0 | 3 | Classification per-class recall floor; Classification other-or-abstain recall floor; LLM groundedness floor; Safety abstain-recall floor | Retrain the Classification head. You bring: Your fault or alert taxonomy, A golden set your experts label, A contract for each tool, Your domain corpus |
| [UC-OPS-03](../catalog/network-operations/core-network-rca/README.md) Core network root-cause analysis | Full recipe | 5 | 0 | 0 | 0 | 5 | Classification per-class recall floor; Classification other-or-abstain recall floor; LLM groundedness floor; Safety abstain-recall floor; Embedding and Reranker recall-at-k floor; Decision false-ACT budget; Ceiling for notify requests; Ceiling for low-risk writes; Ceiling for high-risk writes | Retrain the Classification head. You bring: Your fault or alert taxonomy, A golden set your experts label, Gate labels from your approvers, A contract for each tool, Your domain corpus |
| [UC-OPS-04](../catalog/network-operations/ran-rf-health-checks/README.md) RAN and RF health checks | Catalog entry | 5 | 1 | 0 | 0 | 1 | Classification per-class recall floor; Classification other-or-abstain recall floor; Decision false-ACT budget; Ceiling for notify requests; Ceiling for high-risk writes; Safety abstain-recall floor | Retrain the Classification head. You bring: Your fault or alert taxonomy, A golden set your experts label, Gate labels from your approvers, A contract for each tool |
| [UC-OPS-05](../catalog/network-operations/ran-energy-saving/README.md) RAN energy saving | Full recipe | 4 | 0 | 0 | 0 | 5 | Service KPI guard band; Minimum simulated energy saving; Shadow agreement floor; Canary window; Minimum ACT probability for the act stage; Override rate ceiling; Decision false-ACT budget; Ceiling for low-risk writes; Ceiling for high-risk writes; Required approver role per action class | No model change: retrieval and skills. You bring: A golden set your experts label, Gate labels from your approvers, A contract for each tool |
| [UC-OPS-06](../catalog/network-operations/slice-sla-assurance/README.md) Slice SLA assurance | Full recipe | 4 | 0 | 0 | 0 | 6 | SLO breach forecast horizon; LLM groundedness floor; Safety abstain-recall floor; Embedding and Reranker recall-at-k floor; Decision false-ACT budget; Ceiling for notify requests; Ceiling for high-risk writes | No model change: retrieval and skills. You bring: A golden set your experts label, Gate labels from your approvers, A contract for each tool, Your domain corpus |
| [UC-OPS-07](../catalog/network-operations/mop-validation/README.md) MOP validation | Full recipe | 4 | 1 | 0 | 0 | 6 | MOP defect recall floor; LLM groundedness floor; Non-inferiority margin; Safety abstain-recall floor; Embedding and Reranker recall-at-k floor; Decision false-ACT budget; Ceiling for notify requests; Ceiling for high-risk writes; Required approver role per action class | No model change: retrieval and skills. You bring: A golden set your experts label, Gate labels from your approvers, A contract for each tool, Your domain corpus |
| [UC-OPS-08](../catalog/network-operations/transport-ip-diagnostics/README.md) Transport and IP diagnostics | Catalog entry | 5 | 0 | 0 | 0 | 3 | Embedding and Reranker recall-at-k floor; LLM groundedness floor; Safety abstain-recall floor; Decision false-ACT budget; Ceiling for notify requests; Ceiling for low-risk writes | No model change: retrieval and skills. You bring: A golden set your experts label, Gate labels from your approvers, A contract for each tool, Your domain corpus |
| [UC-OPS-09](../catalog/network-operations/cross-domain-oss-correlation/README.md) Cross-domain OSS correlation | Catalog entry | 4 | 0 | 0 | 0 | 3 | Classification per-class recall floor; Classification other-or-abstain recall floor; Embedding and Reranker recall-at-k floor; Decision false-ACT budget; Ceiling for notify requests; Ceiling for low-risk writes | Retrain the Classification head. You bring: Your fault or alert taxonomy, A golden set your experts label, Gate labels from your approvers, A contract for each tool, Your domain corpus |
| [UC-RES-01](../catalog/research/kpi-rca-reasoning/README.md) KPI root-cause reasoning | Catalog entry | 5 | 1 | 0 | 0 | 1 | Classification per-class recall floor; Classification other-or-abstain recall floor; LLM groundedness floor; Decision false-ACT budget; Ceiling for high-risk writes; Safety abstain-recall floor | Retrain the Classification head. You bring: Your fault or alert taxonomy, A golden set your experts label, Gate labels from your approvers |
| [UC-RES-02](../catalog/research/mobility-failure-analysis/README.md) 5G mobility failure analysis | Catalog entry | 5 | 0 | 0 | 0 | 2 | LLM groundedness floor; LLM citation-correctness floor; Embedding and Reranker recall-at-k floor; Safety abstain-recall floor | No model change: retrieval and skills. You bring: A golden set your experts label, A contract for each tool, Your domain corpus |
| [UC-SEC-01](../catalog/security/security-triage/README.md) Security alert triage | Catalog entry | 5 | 0 | 0 | 0 | 3 | Classification per-class recall floor; Classification other-or-abstain recall floor; Safety abstain-recall floor; LLM groundedness floor; Decision false-ACT budget; Required approver role per action class | Retrain the Classification head. You bring: Your fault or alert taxonomy, A golden set your experts label, Gate labels from your approvers, A contract for each tool |
| [UC-SEC-02](../catalog/security/signalling-attack-classification/README.md) Signalling attack classification | Catalog entry | 4 | 0 | 0 | 0 | 2 | Classification per-class recall floor; Classification other-or-abstain recall floor; Safety abstain-recall floor; LLM groundedness floor | Retrain the Classification head. You bring: Your fault or alert taxonomy, A golden set your experts label |
| [UC-SW-01](../catalog/network-software/ran-core-code-assistant/README.md) RAN and core code assistant | Catalog entry | 4 | 1 | 0 | 0 | 3 | LLM groundedness floor; LLM citation-correctness floor; Embedding and Reranker recall-at-k floor; Safety abstain-recall floor; Safety false-abstention ceiling | No model change: retrieval only. You bring: A golden set your experts label, Your domain corpus |
| [UC-SW-02](../catalog/network-software/network-automation-review/README.md) Network automation review | Catalog entry | 5 | 0 | 0 | 0 | 4 | Decision false-ACT budget; Decision REVIEW band; Ceiling for notify requests; Ceiling for high-risk writes; Required approver role per action class; Safety abstain-recall floor | No model change: retrieval only. You bring: A golden set your experts label, Gate labels from your approvers, Your domain corpus |
| [UC-SW-03](../catalog/network-software/oran-ric-xapp-assistant/README.md) O-RAN RIC xApp assistant | Catalog entry | 4 | 1 | 0 | 0 | 3 | LLM groundedness floor; LLM citation-correctness floor; Embedding and Reranker recall-at-k floor; Safety abstain-recall floor | No model change: retrieval only. You bring: A golden set your experts label, Your domain corpus |

<!-- generated:evidence-summary end -->
<!-- vale Google.Colons = YES -->

## What's next and how to engage

- **Reference implementations:** deployable, evaluated builds of the four flagship recipes, once a cluster is available.
- **Your data and policies:** start with [Bring your own data and policies](../platform/bring-your-own-data/README.md). It lists what to bring for each network domain, who owns it, and which gate checks it.
- **Contribute:** propose a use case or a fix in the [repository](https://github.com/ravisharma5/otel-telco-blueprints).
- **Supported products:** the blueprints make no support claims. Engage Red Hat for supported products.
