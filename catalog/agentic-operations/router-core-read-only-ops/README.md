---
id: "UC-AGOPS-02"
type: "use-case"
title: "Read-only router and 5G core operations"
doc_status: done
domain: "agentic-operations"
flagship: false
depth: "entry"
adaptation:
  rung: "skills"
  expertise: ["golden-set", "gate-labels", "tool-contracts"]
  bring:
    - {item: "gNMI Get and Subscribe read tool contracts", domains: ["transport-ip"], mechanism: "tool-contract"}
    - {item: "NWDAF analytics and UDR subscription read tools", domains: ["core-cnf"], mechanism: "tool-contract"}
    - {item: "Read-only manifests for router and core tools", domains: ["transport-ip", "core-cnf"], mechanism: "skill-manifest"}
    - {item: "Read-only ceilings and the routing threshold", domains: ["transport-ip", "core-cnf"], mechanism: "gate-policy"}
otel_slots: ["llm", "decision", "safety"]
autonomy_ceiling: "inform"
placement_tier: ["regional", "core"]
one_liner: "Answers operations questions about routers and the 5G core by calling read-only tools and citing what each tool returned. Informs only and holds no write tools. Depends on read-only tool manifests and the deny-unless-allowed rule at the tool gateway."
platform_blueprints: ["PB-01", "PB-02", "PB-03", "PB-04", "PB-05", "PB-06", "PB-08", "PB-09", "PB-11"]
clarity_reviewed: "2026-11-16"
agent_school: [101, 401]
card:
  goal: "incidents"
  summary: "An agent reads router state, network analytics, and subscription data through read-only tools, and answers with the output it read."
  outcome: "Engineers get the state of a router or a core function in one answer, without logging in to each system."
  audience: "Router and 5G core operations engineers, platform teams, and data protection officers"
  measures: ["Time to answer a state question", "Answers confirmed by an engineer"]
  risk: "A wrong reading could mislead an engineer, so each answer cites the tool output."
placement:
  far-edge: {runs: [], note: "Not used: the agent and its tools run at regional and core sites."}
  regional: {runs: ["decision", "safety", "llm-small"], note: "The Decision routing label, the Safety check, and the small LLM run here."}
  core: {runs: ["llm-large"], note: "The large LLM handles the questions the Decision slot routes up."}
---

<!-- Writing rules: framework/style-guide.md. Name each component by its role and the Red Hat product used. Write no product support status. -->

# Read-only router and 5G core operations

## At a glance

| Field | Value |
|---|---|
| One-liner | Answers operations questions about routers and the 5G core by calling read-only tools and citing what each tool returned. Informs only and holds no write tools. Depends on read-only tool manifests and the deny-unless-allowed rule at the tool gateway. |
| Problem | Engineers log in to routers, analytics, and subscriber systems one by one to answer a simple state question; the KPI is time to answer |
| Audience | Router and 5G core operations engineers, platform teams, and data protection officers |
| OTel slots | `llm`: calls the read tools and writes the answer; `decision`: routes each question to the small or large LLM; `safety`: abstain when the tool output doesn't answer the question |
| Autonomy ceiling | Inform |
| Placement tier | Regional and core |
| Agent-school courses | 101 and 401 in the [agent-school roadmap](https://github.com/open-experiments/agent-school/blob/main/docs/RoadMap.md) |

## Problem and value

Engineers answer questions such as "is this BGP session up" or "what does analytics say about this slice" by logging in to each system.
This entry gives an agent read-only tools for router state, network analytics, and subscription data, and it answers with the output it read.
The agent holds no write tools, so it can't change a router or a core function.
The KPIs are time to answer a state question and the share of answers an engineer confirms.
Any gain is a target, measured against a shadow-stage baseline.

## How it works

_Stub: this catalog entry has no worked example or diagram yet._

## What you need

- [ ] Models: the three slots, chosen from the family in [PB-01](../../../platform/intake-model-selection/README.md), each pinned by revision with its licence chain recorded
- [ ] Platform blueprints: evaluation ([PB-02](../../../platform/evaluation-acceptance/README.md)), serving and routing ([PB-04](../../../platform/serving-routing-placement/README.md)), integration ([PB-05](../../../platform/integration/README.md)), safety gating ([PB-06](../../../platform/safety-autonomy-gating/README.md)), tool identity and sandbox ([PB-08](../../../platform/security-identity-sandbox/README.md)), and quality operations ([PB-09](../../../platform/quality-operations/README.md))
- [ ] Components: one product for each role in the components table
- [ ] Read tools: gNMI Get and Subscribe on routers, NWDAF analytics, and UDR subscription reads, each listed in a read-only tool manifest
- [ ] Tool access: the gateway applies the deny-unless-allowed rule in [PB-05](../../../platform/integration/README.md#per-tool-authorization), and no manifest lists gNMI Set or a UDR write
- [ ] Agent identity: a workload identity bound to the read roles only, as PB-08 sets out
- [ ] Subscriber data: subscription reads stay under your data protection officer's controls, and test sets use fictitious subscribers only
- [ ] Decision engine: vLLM 0.26 or 0.30 on CUDA or ROCm, as the [Decision model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) states
- [ ] Traces: every tool call and answer, as PB-09 sets out
- [ ] Placement: the regional site runs Decision, Safety, and the small LLM. The core runs the large LLM.

| Component role | Red Hat product used |
|---|---|
| Inference engine for every slot | Red Hat AI Inference (vLLM) |
| Serving platform | Red Hat OpenShift AI with KServe |
| Tool gateway for per-tool authorization | MCP gateway in Red Hat Connectivity Link |
| Input and tool-response guardrails | NeMo Guardrails in Red Hat OpenShift AI |

Key flags for each slot, copied from [PB-04](../../../platform/serving-routing-placement/README.md#key-flags-per-slot). Start the Safety slot with its own pinned revision and no tool-calling flags.

```text
# LLM 31B (pin the revision; text-only; tool calling)
--revision <sha> --enable-auto-tool-choice --tool-call-parser gemma4 \
--limit-mm-per-prompt '{"image": 0, "audio": 0}'
# Decision (card recipe)
--revision <sha> --max-logprobs 64 --enable-prefix-caching --max-model-len 16384
```

Any component can be replaced. The Red Hat products named here show one way to build this design.

### What you bring

<!-- generated:what-you-bring start -->

| Model change | Your expertise | How far to climb |
|---|---|---|
| No model change: a skill per role and a capability manifest per tool | A golden set your experts label; gate labels from your approvers; a contract for each tool | Configure first, and train only on a measured gap, as [PB-03 Adaptation](../../../platform/adaptation/README.md) sets out |

| Item | Network component | Mechanism | Owner | Matrix row |
|---|---|---|---|---|
| gNMI Get and Subscribe read tool contracts | Transport and IP | MCP tool contract | Platform team | [Transport and IP](../../../platform/bring-your-own-data/README.md#domain-transport-and-ip) |
| NWDAF analytics and UDR subscription read tools | 5G core CNFs | MCP tool contract | Platform team | [5G core CNFs](../../../platform/bring-your-own-data/README.md#domain-5g-core-cnfs) |
| Read-only manifests for router and core tools | Transport and IP; 5G core CNFs | Skill or capability manifest | SME | [Transport and IP](../../../platform/bring-your-own-data/README.md#domain-transport-and-ip); [5G core CNFs](../../../platform/bring-your-own-data/README.md#domain-5g-core-cnfs) |
| Read-only ceilings and the routing threshold | Transport and IP; 5G core CNFs | Gate and action-layer policy | Risk owner | [Transport and IP](../../../platform/bring-your-own-data/README.md#domain-transport-and-ip); [5G core CNFs](../../../platform/bring-your-own-data/README.md#domain-5g-core-cnfs) |

<!-- generated:what-you-bring end -->

### What you must add

| Gap | What you add | Source |
|---|---|---|
| Read tools | Read-only tool manifests with checked schemas for each router and core tool, because the card's tool-use training holds no telecom tool-calling examples | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#tool-use-and-instruction-following) |
| Core data | Tests on your own core analytics and subscription reads, because the card's training leaves out 5G core signalling data | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| Core interfaces | NWDAF and UDR clients in the tool runtime, set up for your core release | [3GPP TS 23.288](https://www.3gpp.org/DynaReport/23288.htm), [3GPP TS 29.504](https://www.3gpp.org/DynaReport/29504.htm), [3GPP TS 29.505](https://www.3gpp.org/DynaReport/29505.htm) |
| Router telemetry | gNMI Get and Subscribe access on your routers, with the Set call left out of every manifest | [gNMI specification](https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md) |
| Language scope | Tests in every language your engineers ask in, because the card's quality claims cover English text only | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |

## Governance

Every outcome is LOOK. The ceiling is inform, and nothing reaches the [decision gate](../../../architecture/decision-gate.md), because the agent holds read tools only.

| Action | Gate outcome (LOOK/NOTIFY/REVIEW/ACT/STOP) | Approval | AI Act class |
|---|---|---|---|
| Read router state, analytics, or subscription data through a read tool | LOOK | None: the gateway allows read roles only | Recorded by your legal team in the classification record |
| Answer a state question, citing the tool output | LOOK | None: the engineer reads the answer and its sources | Recorded by your legal team in the classification record |
| Abstain and list the tools called | LOOK | None: the engineer sees what was checked | Recorded by your legal team in the classification record |

| Parameter | What it controls | Who sets it | How to calibrate |
|---|---|---|---|
| Decision routing threshold | The label probability over which the large LLM answers instead of the small LLM | Model owner | Run the small and large LLM on the same golden set, and keep a band on the small LLM only while it stays within the non-inferiority margin |
| Non-inferiority margin | The largest drop against the incumbent that still counts as no worse | Risk owner | Run candidate and incumbent on identical items and set the margin from the run-to-run noise |
| LLM groundedness floor | The lowest share of answers whose claims the tool output supports | Risk owner, with subject-matter expert (SME) review | [Evaluation and acceptance](../../../platform/evaluation-acceptance/README.md): score a golden set of state questions with SME-checked answers |
| Safety abstain-recall floor | The lowest share of insufficient-context items where the Safety slot abstains | Risk owner, with SME review | Remove the tool output from items and measure correct abstention |
| Tool error rate threshold | The share of failed tool calls that raises an alert | Platform team | Read the tool error rate from the trace over a shadow window |
| Trace live retention period | How long traces that hold subscription reads stay in live storage | Data protection officer | Set it from your data protection rules for subscriber data |

This page gives no default values. Each owner sets the value with SME review and versions it with the policy that `policy_version` names.

## Sources

Each key claim links its source, as set out in [the Sources table](../../../framework/definitions.md#sources-table).

| # | Claim | Basis | Source |
|---|---|---|---|
| 1 | The tool-use training holds general examples only, with no telecom tool-calling or MCP examples, and agentic use needs an external tool runtime with checked tool schemas | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#tool-use-and-instruction-following) |
| 2 | The 31B training leaves out 5G core control-plane and inter-NF signalling data | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| 3 | The 31B targets English-language use, and all its quality claims are text-only | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |
| 4 | Use the Decision model's label probabilities for confidence thresholds and routing; serve it on vLLM 0.26 or 0.30 | model card | [OTel-2.0-Decision-26B-A4B-4bit model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) |
| 5 | TS 23.288 sets out the 5G System architecture for network data analytics services | project documentation | [3GPP TS 23.288](https://www.3gpp.org/DynaReport/23288.htm) |
| 6 | TS 29.504 specifies the Unified Data Repository services, and TS 29.505 their use for subscription data | project documentation | [3GPP TS 29.504](https://www.3gpp.org/DynaReport/29504.htm), [3GPP TS 29.505](https://www.3gpp.org/DynaReport/29505.htm) |
| 7 | gNMI is a gRPC protocol for reading and changing device configuration and for streaming telemetry | project documentation | [gNMI specification](https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md) |

## Deploy and verify

_Stub: this catalog entry has no deploy steps yet._

## Limitations

- The entry never changes a router or a core function; the agent holds read tools only.
- Its answers rest on the tool output, so a tool that returns stale data gives a stale answer.
- Subscription reads carry subscriber data, so your data protection officer sets who may read what.
- The card's tool-use training has no telecom examples, so test each tool on your own questions first.
- The quality claims cover English only, so answers in another language need their own evaluation.
