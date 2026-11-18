---
id: "UC-OPS-10"
type: "use-case"
title: "Site log reduction"
doc_status: done
domain: "network-operations"
flagship: false
depth: "entry"
adaptation:
  rung: "retrieval"
  expertise: ["golden-set", "corpus"]
  bring:
    - {item: "Sample of site log lines with known patterns", domains: ["ran", "vran-oran"], mechanism: "rag-corpus"}
    - {item: "Retention period and forwarding rules per log type", domains: ["ran", "vran-oran"], mechanism: "gate-policy"}
    - {item: "Known log patterns your engineers already track", domains: ["ran", "vran-oran"], mechanism: "rag-corpus"}
sandbox:
  fit: "none"
  why: "Groups log lines on site; the agent runs no code"
otel_slots: ["embedding"]
autonomy_ceiling: "inform"
placement_tier: ["far-edge"]
one_liner: "Groups repeated log lines on the cell-site server and forwards counts, samples, and new-pattern flags instead of every line. Informs only and never changes the network. Depends on the Embedding slot running on CPU at the site."
platform_blueprints: ["PB-01", "PB-02", "PB-03", "PB-04", "PB-05", "PB-08", "PB-10", "PB-11"]
clarity_reviewed: "2026-11-18"
agent_school: []
card:
  goal: "incidents"
  summary: "Groups repeated log lines at the cell site and forwards counts, samples, and new-pattern flags, so new patterns surface early."
  outcome: "Less log traffic leaves each site, and new patterns reach the NOC as early signals."
  audience: "Operations engineers, platform teams, and risk owners who run cell sites"
  measures: ["Log GB forwarded per site daily", "New patterns flagged early"]
  risk: "A grouping that hides a rare line can delay a fault."
placement:
  far-edge: {runs: ["embedding"], note: "Embedding groups repeated log lines on the cell-site server."}
  regional: {runs: [], note: "Receives counts, samples, and new-pattern flags; no model runs here."}
  core: {runs: [], note: "Not used: grouping happens at the site."}
---

<!-- Writing rules: framework/style-guide.md. Name each component by its role and the Red Hat product used. Write no product support status. -->

# Site log reduction

## At a glance

| Field | Value |
|---|---|
| One-liner | Groups repeated log lines on the cell-site server and forwards counts, samples, and new-pattern flags instead of every line. Informs only and never changes the network. Depends on the Embedding slot running on CPU at the site. |
| Problem | Every site ships every log line upstream, and new patterns hide in the repeats; the KPI is log GB forwarded per site per day |
| Audience | Operations engineers, platform teams, and risk owners who run cell sites |
| OTel slots | `embedding`: turns each log line into a vector so repeated lines group together |
| Autonomy ceiling | Inform |
| Placement tier | Far edge |
| Agent-school courses | None: no agent-school course covers this use case yet. See the [agent-school roadmap](https://github.com/open-experiments/agent-school/blob/main/docs/RoadMap.md) |

## Problem and value

Site link capacity, hub storage, and NOC log-store costs grow with every site, and a new pattern is buried among lines that repeat all day.
This entry groups repeated lines on the cell-site server and forwards a sample of each group with its count, and it flags lines that fit no known group.
The ROI measure is GB per day per site, times the number of sites, times cost per GB; you supply all three, the entry claims no saving, and you measure against a baseline with the [PB-10](../../../platform/compliance-operating-model/README.md#staged-rollout-and-roi) measures.

## How it works

_Stub: this catalog entry has no worked example or diagram yet._

## What you need

- [ ] Models: OTel-Embedding from 22M to 335M, or 600M, chosen in [PB-01](../../../platform/intake-model-selection/README.md) and pinned by revision with its licence chain recorded
- [ ] Platform blueprints: evaluation ([PB-02](../../../platform/evaluation-acceptance/README.md)), serving and placement ([PB-04](../../../platform/serving-routing-placement/README.md)), integration ([PB-05](../../../platform/integration/README.md)), and compliance ([PB-10](../../../platform/compliance-operating-model/README.md))
- [ ] Components: one product for each role in the components table
- [ ] Integrations: a read-only log export on the site server, and forwarding to the operator's NOC log store
- [ ] Tools and data: operational logs only; security logs keep their own retention and never pass through this flow
- [ ] Retention: raw logs stay on the site server for the retention period you set, and the flow never deletes a log before that period ends
- [ ] Embedding revision: a new embedding checkpoint changes every group, so record the revision with the group set
- [ ] Prerequisites: spare non-real-time cores on the cell-site single-node OpenShift server, as [Servers shared with a vDU](../../../architecture/placement.md#servers-shared-with-a-vdu) sets out

| Component role | Red Hat product used |
|---|---|
| Site server platform | Single-node OpenShift |
| Inference engine for the Embedding slot | Red Hat AI Inference (vLLM), CPU image `vllm-cpu-rhel9` |
| Log store at the NOC | Your choice; this design names no product |

Key flags for each slot, copied from [PB-04](../../../platform/serving-routing-placement/README.md#key-flags-per-slot).

```text
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
| Sample of site log lines with known patterns | RAN; vRAN and O-RAN | RAG corpus | RAN: Operations engineer; vRAN and O-RAN: Platform team | [RAN](../../../platform/bring-your-own-data/README.md#domain-ran); [vRAN and O-RAN](../../../platform/bring-your-own-data/README.md#domain-vran-and-o-ran) |
| Retention period and forwarding rules per log type | RAN; vRAN and O-RAN | Gate and action-layer policy | Risk owner | [RAN](../../../platform/bring-your-own-data/README.md#domain-ran); [vRAN and O-RAN](../../../platform/bring-your-own-data/README.md#domain-vran-and-o-ran) |
| Known log patterns your engineers already track | RAN; vRAN and O-RAN | RAG corpus | RAN: Operations engineer; vRAN and O-RAN: Platform team | [RAN](../../../platform/bring-your-own-data/README.md#domain-ran); [vRAN and O-RAN](../../../platform/bring-your-own-data/README.md#domain-vran-and-o-ran) |

<!-- generated:what-you-bring end -->

### Sandbox

<!-- generated:sandbox start -->

| Sandbox fit | Trigger on this page | Where to read |
|---|---|---|
| Base sandbox only: the agent reads through the gateways, so the six sandbox controls and the gateway screen are enough | Groups log lines on site; the agent runs no code | [PB-08: when a use case needs a sandbox](../../../platform/security-identity-sandbox/README.md#when-a-use-case-needs-a-sandbox) |

<!-- generated:sandbox end -->

### What you must add

| Gap | What you add | Source |
|---|---|---|
| Task data | A sample of your site log lines labelled with the pattern each belongs to, because the card trains the model to retrieve document passages, not to group log lines | [OTel-Embedding-335M model card](https://huggingface.co/farbodtavakkoli/OTel-Embedding-335M#intended-use) |
| Evaluation | A grouping recall check on a held-out sample, compared with a template-mining baseline such as Drain, so a rare line never hides in a group | [Drain log parsing paper](https://jiemingzhu.github.io/pub/pjhe_icws2017.pdf) |
| Language scope | Tests on log lines in every language your equipment writes, because the card's claims cover English text only | [OTel-Embedding-335M model card](https://huggingface.co/farbodtavakkoli/OTel-Embedding-335M#limitations-and-responsible-use) |

## Governance

Every outcome is LOOK. The ceiling is inform, and nothing reaches the [decision gate](../../../architecture/decision-gate.md), because the flow changes no network state.

| Action | Gate outcome (LOOK/NOTIFY/REVIEW/ACT/STOP) | Approval | AI Act class |
|---|---|---|---|
| Forward counts, samples, and new-pattern flags | LOOK | None: the NOC reads the forwarded summary | [Recorded by your legal team in the classification record](../../../platform/compliance-operating-model/README.md) |

| Parameter | What it controls | Who sets it | How to calibrate |
|---|---|---|---|
| Raw log retention period | How long raw logs stay on the site server before your normal log rotation may remove them | Risk owner | Match your log retention policy for each log type |
| New-pattern similarity threshold | The similarity under which a line counts as a new pattern instead of joining a group | Model owner | Run the grouping recall check on the held-out sample, and keep rare lines out of large groups |

This page gives no default values. Each owner sets the value with SME review and versions it with the policy that `policy_version` names.

## Sources

Each key claim links its source, as set out in [the Sources table](../../../framework/definitions.md#sources-table).

| # | Claim | Basis | Source |
|---|---|---|---|
| 1 | OTel-Embedding-335M is meant to retrieve chunks from telecom documents as the retrieval stage of a RAG pipeline | model card | [OTel-Embedding-335M model card](https://huggingface.co/farbodtavakkoli/OTel-Embedding-335M#intended-use) |
| 2 | The OTel embedding release is English-only and mainly text | model card | [OTel-Embedding-335M model card](https://huggingface.co/farbodtavakkoli/OTel-Embedding-335M#limitations-and-responsible-use) |
| 3 | vLLM serves embedding models in pooling mode, where the embed task returns one vector for each input | project documentation | [vLLM pooling models](https://docs.vllm.ai/en/latest/models/pooling_models/) |
| 4 | Red Hat AI Inference ships a CPU image, `vllm-cpu-rhel9` | Red Hat guidance | [Red Hat AI Inference release notes](https://docs.redhat.com/en/documentation/red_hat_ai_inference/3.5/html/release_notes/rhaii-350-ga-release-notes_release-notes) |
| 5 | Log parsing turns unstructured log messages into structured events, and Drain parses streaming logs online with a fixed-depth tree | research | [Drain log parsing paper](https://jiemingzhu.github.io/pub/pjhe_icws2017.pdf) |
| 6 | The RAN DU reference design pins platform pods to reserved cores, and unreserved cores stay allocatable for workloads | Red Hat guidance | [RAN DU reference design](https://docs.redhat.com/en/documentation/openshift_container_platform/4.20/html/scalability_and_performance/telco-ran-du-ref-design-specs) |

## Deploy and verify

_Stub: this catalog entry has no deploy steps yet._

## Limitations

- The entry never changes network state. It informs only, and every outcome is LOOK.
- It never deletes a log before the retention period ends; raw logs stay on the site server for that period.
- It doesn't cover security logs, which keep their own retention.
- Grouping quality depends on the embedding model and your threshold, so a rare line can join a large group until you tune it.
- The quality claims cover English only, so log lines in another language need their own evaluation.
- The AI Act class is your legal team's call, recorded in the classification record.
