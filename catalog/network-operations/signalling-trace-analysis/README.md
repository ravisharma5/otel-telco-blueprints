---
id: "UC-OPS-02"
type: "use-case"
title: "Signalling trace analysis"
doc_status: done
domain: "network-operations"
flagship: false
depth: "entry"
otel_slots: ["embedding", "reranker", "safety", "classification", "llm"]
autonomy_ceiling: "inform"
placement_tier: ["regional", "core"]
one_liner: "Explains failed procedures in 5G and LTE signalling traces and cites the decoded messages and 3GPP clauses. Informs only. Depends on parser tools that decode each message, labelled traces from your network, and a retrained Classification head."
platform_blueprints: ["PB-01", "PB-02", "PB-03", "PB-04", "PB-05", "PB-06", "PB-09"]
clarity_reviewed: "2026-11-16"
agent_school: [201]
card:
  goal: "incidents"
  summary: "Explains why a registration, session, or handover failed in a signalling trace. Each finding cites a decoded message and a 3GPP clause."
  outcome: "Engineers find the failing step in a long trace sooner, with each finding tied to a message and a clause."
  audience: "Core and RAN operations engineers, trace analysts, and model owners"
  measures: ["Time to find the failing step", "Findings confirmed by an engineer"]
  risk: "A wrong finding could mislead an engineer, so each one cites its message."
placement:
  far-edge: {runs: [], note: "Not used: trace analysis doesn't need to run at the cell site."}
  regional: {runs: ["embedding", "reranker", "safety", "classification"], note: "Retrieval, the failure label, and the Safety check run here, close to the trace store."}
  core: {runs: ["llm-large"], note: "The large LLM writes each explanation."}
---

<!-- Writing rules: framework/style-guide.md. Name each component by its role and the Red Hat product used. Write no product support status. -->

# Signalling trace analysis

## At a glance

| Field | Value |
|---|---|
| One-liner | Explains failed procedures in 5G and LTE signalling traces and cites the decoded messages and 3GPP clauses. Informs only. Depends on parser tools that decode each message, labelled traces from your network, and a retrained Classification head. |
| Problem | Engineers read long signalling traces by hand to find the one step where a procedure failed; the KPI is time to find the failing step |
| Audience | Core and RAN operations engineers, trace analysts, and model owners |
| OTel slots | `embedding` and `reranker`: retrieval of procedure clauses and runbooks; `safety`: abstain on weak evidence; `classification`: labels the failure class; `llm`: writes the explanation |
| Autonomy ceiling | Inform |
| Placement tier | Regional and core |
| Agent-school courses | 201 in the [agent-school roadmap](https://github.com/open-experiments/agent-school/blob/main/docs/RoadMap.md) |

## Problem and value

Registration, session, and handover failures show up as long NAS, NGAP, and S1AP message sequences in subscriber and equipment traces.
Engineers decode them, match them against the 3GPP procedures, and find the failing step by hand.
This entry decodes each trace with parser tools, labels the failure class, and writes an explanation that cites the decoded messages and the procedure clause.
The KPIs are time to find the failing step and the share of findings an engineer confirms.
Any gain is a target, measured against a shadow-stage baseline.

## How it works

_Stub: this catalog entry has no worked example or diagram yet._

## What you need

- [ ] Models: the five slots, chosen from the family in [PB-01](../../../platform/intake-model-selection/README.md), each pinned by revision with its licence chain recorded
- [ ] Platform blueprints: evaluation ([PB-02](../../../platform/evaluation-acceptance/README.md)), adaptation ([PB-03](../../../platform/adaptation/README.md)), serving and routing ([PB-04](../../../platform/serving-routing-placement/README.md)), integration ([PB-05](../../../platform/integration/README.md)), safety gating ([PB-06](../../../platform/safety-autonomy-gating/README.md)), and quality operations ([PB-09](../../../platform/quality-operations/README.md))
- [ ] Components: one product for each role in the components table
- [ ] Parser tools: decoders for NAS, NGAP, and S1AP run as read-only tools under the deny-unless-allowed rule in [PB-05](../../../platform/integration/README.md#per-tool-authorization); the LLM never decodes raw messages
- [ ] Traces: trace collection set up in your network, and a set of past traces labelled by your engineers
- [ ] Classification head: retrained on your failure taxonomy, as [PB-03](../../../platform/adaptation/README.md) sets out
- [ ] Corpora: the 3GPP procedure specifications and your runbooks, each with a usage-rights entry
- [ ] Placement: the regional site runs Embedding, Reranker, Safety, and Classification. The core runs the large LLM.

| Component role | Red Hat product used |
|---|---|
| Inference engine for every slot | Red Hat AI Inference (vLLM) |
| Serving platform | Red Hat OpenShift AI with KServe |
| Tool gateway for the parser tools | MCP gateway in Red Hat Connectivity Link |
| Training for the Classification head | Training Hub in Red Hat OpenShift AI |
| Vector store for specifications and runbooks | Your choice; this design names no product |

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

### What you must add

| Gap | What you add | Source |
|---|---|---|
| Signalling data | Labelled traces from your network, because the card leaves 5G-core control-plane and inter-NF signalling out of training | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| Message decoding | Parser tools that decode each message, because the card's tool-use training holds no telecom tool-calling examples | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#tool-use-and-instruction-following) |
| Failure classes | The Classification head retrained on your failure taxonomy, because the shipped head covers eight synthetic drive-test classes | [OTel-LLM-8.3B-Classification model card](https://huggingface.co/farbodtavakkoli/OTel-LLM-8.3B-Classification) |
| Trace format | A trace export that your parser tools read, set up through your trace control | [3GPP TS 32.422](https://www.3gpp.org/DynaReport/32422.htm), [3GPP TS 32.423](https://www.3gpp.org/DynaReport/32423.htm) |
| Language scope | Tests in every language your engineers read findings in, because the card's quality claims cover English text only | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |

## Governance

Every outcome is LOOK. The ceiling is inform, and nothing reaches the [decision gate](../../../architecture/decision-gate.md), because the flow changes no network state.

| Action | Gate outcome (LOOK/NOTIFY/REVIEW/ACT/STOP) | Approval | AI Act class |
|---|---|---|---|
| Explain a failed procedure in a trace, with citations | LOOK | None: the engineer reads the finding and its sources | Recorded by your legal team in the classification record |
| Abstain and list what was decoded and searched | LOOK | None: the engineer sees what was checked | Recorded by your legal team in the classification record |

| Parameter | What it controls | Who sets it | How to calibrate |
|---|---|---|---|
| Classification per-class recall floor | The lowest recall for each failure class in your taxonomy | Risk owner, with subject-matter expert (SME) review | [Evaluation and acceptance](../../../platform/evaluation-acceptance/README.md): use SME labels on a temporal holdout, so test traces come after training traces |
| Classification other-or-abstain recall floor | The lowest recall for failures outside the taxonomy | Risk owner | Hold out failure types the model never saw and check they land in other or abstain |
| LLM groundedness floor | The lowest share of findings whose claims the decoded messages and cited clauses support | Risk owner, with SME review | Score a golden set of labelled traces with SME-checked findings and a calibrated judge |
| Safety abstain-recall floor | The lowest share of insufficient-context items where the Safety slot abstains | Risk owner, with SME review | Remove the failing messages from items and measure correct abstention |

This page gives no default values. Each owner sets the value with SME review and versions it with the policy that `policy_version` names.

## Sources

Each key claim links its source, as set out in [the Sources table](../../../framework/definitions.md#sources-table).

| # | Claim | Basis | Source |
|---|---|---|---|
| 1 | The 31B training leaves out 5G-core control-plane and inter-NF signalling data | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| 2 | The tool-use training holds general examples only, and agentic use needs an external tool runtime with checked tool schemas | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#tool-use-and-instruction-following) |
| 3 | The 31B targets English-language use, and all its quality claims are text-only | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |
| 4 | The Classification model's head predicts eight root-cause classes from the synthetic TeleLogs drive-test dataset | model card | [OTel-LLM-8.3B-Classification model card](https://huggingface.co/farbodtavakkoli/OTel-LLM-8.3B-Classification) |
| 5 | TS 23.502 specifies the procedures of the 5G System | project documentation | [3GPP TS 23.502](https://www.3gpp.org/DynaReport/23502.htm) |
| 6 | TS 24.501 specifies the 5GS NAS protocol, TS 38.413 specifies NGAP, and TS 36.413 specifies S1AP | project documentation | [3GPP TS 24.501](https://www.3gpp.org/DynaReport/24501.htm), [3GPP TS 38.413](https://www.3gpp.org/DynaReport/38413.htm), [3GPP TS 36.413](https://www.3gpp.org/DynaReport/36413.htm) |
| 7 | TS 32.422 covers trace control and configuration, and TS 32.423 defines trace data and its management | project documentation | [3GPP TS 32.422](https://www.3gpp.org/DynaReport/32422.htm), [3GPP TS 32.423](https://www.3gpp.org/DynaReport/32423.htm) |

## Deploy and verify

_Stub: this catalog entry has no deploy steps yet._

## Limitations

- The entry never changes network state. It informs only, and every outcome is LOOK.
- It explains only what the parser tools decode; a message they can't parse ends in an abstention.
- The shipped Classification head knows drive-test classes only, so it needs your failure taxonomy first.
- Traces can hold subscriber identities, so handle them under your data protection rules before indexing.
- The quality claims cover English only, so findings in another language need their own evaluation.
