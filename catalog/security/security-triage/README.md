---
id: "UC-SEC-01"
type: "use-case"
title: "Security alert triage"
doc_status: done
domain: "security"
flagship: false
depth: "entry"
adaptation:
  rung: "head-retrain"
  expertise: ["taxonomy", "golden-set", "gate-labels", "tool-contracts"]
otel_slots: ["classification", "safety", "decision", "llm"]
autonomy_ceiling: "recommend-with-approval"
tmf_an_level_target: 2
placement_tier: ["regional", "core"]
one_liner: "Triages alerts from your security detectors, labels each one with your alert taxonomy, and proposes containment to a human approver. Never detects threats or contains them itself. Depends on independently checked detectors, labelled alerts from your network, and a retrained Classification head."
platform_blueprints: ["PB-01", "PB-02", "PB-03", "PB-04", "PB-05", "PB-06", "PB-08", "PB-09"]
clarity_reviewed: "2026-11-16"
agent_school: []
card:
  goal: "secure"
  summary: "Labels and summarises alerts from your own security detectors, then proposes containment for an approver to accept or reject."
  outcome: "Analysts reach the alerts that matter sooner, with each triage note tied to detector evidence."
  audience: "Security operations analysts, approvers, and risk owners"
  measures: ["Time to triage an alert", "Triage labels confirmed by an analyst"]
  risk: "A wrong label could hide an attack, so analysts review every proposal."
placement:
  far-edge: {runs: [], note: "Not used: triage runs at regional and core sites."}
  regional: {runs: ["classification", "safety", "decision"], note: "The alert label, the Safety check, and the gate label run here."}
  core: {runs: ["llm-large"], note: "The large LLM writes each triage note and containment proposal."}
---

<!-- Writing rules: framework/style-guide.md. Name each component by its role and the Red Hat product used. Write no product support status. -->

# Security alert triage

## At a glance

| Field | Value |
|---|---|
| One-liner | Triages alerts from your security detectors, labels each one with your alert taxonomy, and proposes containment to a human approver. Never detects threats or contains them itself. Depends on independently checked detectors, labelled alerts from your network, and a retrained Classification head. |
| Problem | Security analysts face more detector alerts than they can read, so real attacks wait in the queue; the KPI is time to triage an alert |
| Audience | Security operations analysts, approvers, and risk owners |
| OTel slots | `classification`: labels the alert class; `safety`: abstain on weak evidence; `decision`: the gate label; `llm`: writes the triage note |
| Autonomy ceiling | Recommend with approval |
| Placement tier | Regional and core |
| Agent-school courses | None: no agent-school course covers this use case yet. See the [agent-school roadmap](https://github.com/open-experiments/agent-school/blob/main/docs/RoadMap.md) |

## Problem and value

Detectors raise more alerts on failed authentications, unusual registrations, and suspect radio reports than analysts can read.
This entry reads each alert and its evidence, labels it with your alert taxonomy, and writes a triage note that cites the detector output.
Containment proposals go to an approver; the entry never acts on them itself.
The KPIs are time to triage an alert and the share of labels an analyst confirms.
Any gain is a target, measured against a shadow-stage baseline.

## How it works

_Stub: this catalog entry has no worked example or diagram yet._

## What you need

- [ ] Models: the four slots, chosen from the family in [PB-01](../../../platform/intake-model-selection/README.md), each pinned by revision with its licence chain recorded
- [ ] Platform blueprints: evaluation ([PB-02](../../../platform/evaluation-acceptance/README.md)), adaptation ([PB-03](../../../platform/adaptation/README.md)), serving and routing ([PB-04](../../../platform/serving-routing-placement/README.md)), integration ([PB-05](../../../platform/integration/README.md)), safety gating ([PB-06](../../../platform/safety-autonomy-gating/README.md)), identity and sandbox ([PB-08](../../../platform/security-identity-sandbox/README.md)), and quality operations ([PB-09](../../../platform/quality-operations/README.md))
- [ ] Components: one product for each role in the components table
- [ ] Detectors: your own detectors raise every alert, each checked on its own before this entry reads it; the models don't detect threats
- [ ] Alert tools: read-only tools for alerts and their evidence under the deny-unless-allowed rule in [PB-05](../../../platform/integration/README.md#per-tool-authorization)
- [ ] Classification head: retrained on your alert taxonomy, as [PB-03](../../../platform/adaptation/README.md) sets out
- [ ] Test data: labelled alerts from your network for training, and fictitious subscribers only in shared test sets
- [ ] Agent identity: a workload identity bound to the read roles and the action request, as PB-08 sets out
- [ ] Decision engine: vLLM 0.26 or 0.30 on CUDA or ROCm, as the [Decision model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) states
- [ ] Traces: tool calls, labels, gate decisions, and approvals, as PB-09 sets out
- [ ] Placement: the regional site runs Classification, Safety, and Decision. The core runs the large LLM.

| Component role | Red Hat product used |
|---|---|
| Inference engine for every slot | Red Hat AI Inference (vLLM) |
| Serving platform | Red Hat OpenShift AI with KServe |
| Tool gateway for the alert tools | MCP gateway in Red Hat Connectivity Link |
| Training for the Classification head | Training Hub in Red Hat OpenShift AI |
| Detectors and alert store | Your choice; this design names no product |

Key flags for each slot, copied from [PB-04](../../../platform/serving-routing-placement/README.md#key-flags-per-slot). Start the Safety slot with its own pinned revision and no tool-calling flags.

```text
# LLM 31B (pin the revision; text-only; tool calling)
--revision <sha> --enable-auto-tool-choice --tool-call-parser gemma4 \
--limit-mm-per-prompt '{"image": 0, "audio": 0}'
# Decision (card recipe)
--revision <sha> --max-logprobs 64 --enable-prefix-caching --max-model-len 16384
# Classification (Gemma3TextForSequenceClassification) and Reranker (num_labels=1)
--runner pooling --convert classify        # endpoints /classify, /v1/score, /rerank
```

Any component can be replaced. The Red Hat products named here show one way to build this design.

### What you must add

| Gap | What you add | Source |
|---|---|---|
| Security data | Labelled alerts from your own security operations, and a security evaluation before the shadow stage, because the card says the model was not trained or evaluated for defensive security operations | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#network-security-operations-not-validated) |
| Detectors | Detectors you check on their own, because the card asks for dedicated evaluation and human oversight in security use | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#network-security-operations-not-validated) |
| Authentication events | RADIUS logs and 5G authentication records as tool reads, because the card's training leaves out RADIUS events and 5G core signalling | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training), [RFC 2865](https://www.rfc-editor.org/rfc/rfc2865), [3GPP TS 33.501](https://www.3gpp.org/DynaReport/33501.htm) |
| Classification head | A head retrained on your alert taxonomy, because the shipped head covers eight synthetic drive-test classes | [OTel-LLM-8.3B-Classification model card](https://huggingface.co/farbodtavakkoli/OTel-LLM-8.3B-Classification) |
| False base stations | Any false base station reports come from your own RAN detection, which you set up and check | [3GPP TR 33.809](https://www.3gpp.org/DynaReport/33809.htm) |
| Language scope | Tests in every language your analysts read triage notes in, because the card's quality claims cover English text only | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |

## Governance

Each action request passes the [decision gate](../../../architecture/decision-gate.md), and the outcome never exceeds the policy ceiling for its class.
The outcome is the lower of the model label and the policy ceiling for the capability and risk class, so it never exceeds either. A STOP label forces STOP at every stage.
Every action class begins at the shadow stage, where the outcome is LOOK. A confirmed false ACT drops the use case and its action class back one stage, as [PB-06](../../../platform/safety-autonomy-gating/README.md#staged-autonomy) sets out.

| Action | Gate outcome (LOOK/NOTIFY/REVIEW/ACT/STOP) | Approval | AI Act class |
|---|---|---|---|
| Post a triage note on the security case, `notify` | NOTIFY, from the assist stage up | None | Recorded by your legal team in the classification record |
| Propose blocking one source address, `write_low` | REVIEW, from the recommend stage up | The `approver` role | Recorded by your legal team in the classification record |
| Propose suspending a subscription or isolating a network function, `write_high` | REVIEW, from the recommend stage up | The `approver` role | Recorded by your legal team in the classification record |
| Any action the label marks STOP | STOP | None | Recorded by your legal team in the classification record |

| Parameter | What it controls | Who sets it | How to calibrate |
|---|---|---|---|
| Classification per-class recall floor | The lowest recall for each class in your alert taxonomy | Risk owner, with subject-matter expert (SME) review | [Evaluation and acceptance](../../../platform/evaluation-acceptance/README.md): use analyst labels on a temporal holdout, so test alerts come after training alerts |
| Classification other-or-abstain recall floor | The lowest recall for alerts outside the taxonomy | Risk owner | Hold out alert types the model never saw and check they land in other or abstain |
| Safety abstain-recall floor | The lowest share of insufficient-context items where the Safety slot abstains | Risk owner, with SME review | Remove the detector evidence from items and measure correct abstention |
| LLM groundedness floor | The lowest share of triage notes whose claims the detector output supports | Risk owner, with SME review | Score a golden set of past alerts with analyst-checked notes |
| Decision false-ACT budget | The highest false-ACT rate accepted on containment proposals | Risk owner | [Evaluation and acceptance](../../../platform/evaluation-acceptance/README.md#false-act-method): use the false-ACT method on a gate set of past containment decisions |
| Required approver role per action class | Which role approves REVIEW for each action class | Risk owner | Check approval times and overrides per class in the trace |

This page gives no default values. Each owner sets the value with SME review and versions it with the policy that `policy_version` names.

## Sources

Each key claim links its source, as set out in [the Sources table](../../../framework/definitions.md#sources-table).

| # | Claim | Basis | Source |
|---|---|---|---|
| 1 | The 31B was not trained or evaluated for defensive network-security operations such as traffic and anomaly analysis or DDoS detection, and security use needs dedicated evaluation and human oversight | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#network-security-operations-not-validated) |
| 2 | The 31B training leaves out RADIUS authentication events and 5G core control-plane signalling | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| 3 | The 31B targets English-language use, and all its quality claims are text-only | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |
| 4 | The Classification model's head predicts eight root-cause classes from the synthetic TeleLogs drive-test dataset | model card | [OTel-LLM-8.3B-Classification model card](https://huggingface.co/farbodtavakkoli/OTel-LLM-8.3B-Classification) |
| 5 | Use the Decision model's label probabilities for confidence thresholds and routing; serve it on vLLM 0.26 or 0.30 | model card | [OTel-2.0-Decision-26B-A4B-4bit model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) |
| 6 | TS 33.501 specifies the security architecture and procedures for the 5G System | project documentation | [3GPP TS 33.501](https://www.3gpp.org/DynaReport/33501.htm) |
| 7 | RADIUS carries authentication, authorization, and configuration information between a network access server and a shared authentication server | project documentation | [RFC 2865](https://www.rfc-editor.org/rfc/rfc2865) |
| 8 | TR 33.809 is the 3GPP study on 5G security enhancements against false base stations | project documentation | [3GPP TR 33.809](https://www.3gpp.org/DynaReport/33809.htm) |

## Deploy and verify

_Stub: this catalog entry has no deploy steps yet._

## Limitations

- The entry never acts on a threat on its own; an approver accepts every containment proposal.
- It triages only what your detectors raise; an attack they miss never reaches it.
- The card says the model was not trained or evaluated for security operations, so test it on your own alerts first.
- The shipped Classification head knows drive-test classes only, so it needs your alert taxonomy first.
- Alerts can hold subscriber identities; handle them under your data protection rules.
- The quality claims cover English only, so triage notes in another language need their own evaluation.
