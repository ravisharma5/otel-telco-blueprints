---
id: "UC-SEC-02"
type: "use-case"
title: "Signalling attack classification"
doc_status: done
domain: "security"
flagship: false
depth: "entry"
adaptation:
  rung: "head-retrain"
  expertise: ["taxonomy", "golden-set"]
  bring:
    - {item: "Attack taxonomy and labelled attack traffic", domains: ["core-cnf"], mechanism: "classification-labels"}
    - {item: "Decoded core signalling for training and tests", domains: ["core-cnf"], mechanism: "classification-labels"}
    - {item: "Labelling skill scoped to the interfaces you watch", domains: ["core-cnf"], mechanism: "skill-manifest"}
sandbox:
  fit: "none"
  why: "Reads records your detectors already flagged; the agent runs no code"
otel_slots: ["classification", "safety", "llm"]
autonomy_ceiling: "inform"
placement_tier: ["regional", "core"]
one_liner: "Labels suspect 5G core signalling that your detectors flag, such as unusual subscriber-data queries, and explains each label with the messages behind it. Informs only. Depends on labelled attack traffic from your network and a retrained Classification head."
platform_blueprints: ["PB-01", "PB-02", "PB-03", "PB-04", "PB-06", "PB-08", "PB-11"]
clarity_reviewed: "2026-11-17"
agent_school: []
card:
  goal: "secure"
  summary: "Labels suspect core signalling that your detectors flag and explains each label with the messages behind it."
  outcome: "Analysts sort flagged signalling sooner, with each label tied to the messages that raised it."
  audience: "Security operations analysts, core engineers, and risk owners"
  measures: ["Time to label a flagged sequence", "Labels confirmed by an analyst"]
  risk: "A wrong label could hide an attack, so analysts check each one."
placement:
  far-edge: {runs: [], note: "Not used: classification runs at regional and core sites."}
  regional: {runs: ["classification", "safety"], note: "The attack label and the Safety check run here, close to the signalling records."}
  core: {runs: ["llm-large"], note: "The large LLM writes each explanation."}
idea:
  why: "The Classification head knows only TeleLogs root causes, no public labelled signalling-attack set exists to retrain it, and security alert triage already covers the flow."
  promote:
    - "A labelled signalling-attack set with usage rights"
    - "A measured Classification head on that set"
  merged_into: "UC-SEC-01"
---

<!-- Writing rules: framework/style-guide.md. Name each component by its role and the Red Hat product used. Write no product support status. -->

# Signalling attack classification

<!-- generated:idea start -->

> **Exploration idea, not a recipe.** Try it, test it, and contribute back. [How to promote an idea](../index.md#promote-an-idea).

**Why it's an idea:** The Classification head knows only TeleLogs root causes, no public labelled signalling-attack set exists to retrain it, and security alert triage already covers the flow.

**What would promote it:**

- [ ] A labelled signalling-attack set with usage rights
- [ ] A measured Classification head on that set

Its scope now sits in [UC-SEC-01 Security alert triage](../../security/security-triage/README.md).

<!-- generated:idea end -->

## At a glance

| Field | Value |
|---|---|
| One-liner | Labels suspect 5G core signalling that your detectors flag, such as unusual subscriber-data queries, and explains each label with the messages behind it. Informs only. Depends on labelled attack traffic from your network and a retrained Classification head. |
| Problem | Detectors flag suspect signalling faster than analysts can sort it by attack type; the KPI is time to label a flagged sequence |
| Audience | Security operations analysts, core engineers, and risk owners |
| OTel slots | `classification`: labels the attack class; `safety`: abstain on weak evidence; `llm`: writes the explanation |
| Autonomy ceiling | Inform |
| Placement tier | Regional and core |
| Agent-school courses | None: no agent-school course covers this use case yet. See the [agent-school roadmap](https://github.com/open-experiments/agent-school/blob/main/docs/RoadMap.md) |

## Problem and value

Attacks on the 5G core can show up as unusual queries to subscriber data or repeated failed authentications.
Your detectors flag these sequences; analysts then sort them by attack type by hand.
This entry labels each flagged sequence with your attack taxonomy and explains the label with the messages behind it.
The KPIs are time to label a flagged sequence and the share of labels an analyst confirms.
Any gain is a target, measured against a shadow-stage baseline.

## How it works

_Stub: this catalog entry has no worked example or diagram yet._

## What you need

- [ ] Models: the three slots, chosen from the family in [PB-01](../../../platform/intake-model-selection/README.md), each pinned by revision with its licence chain recorded
- [ ] Platform blueprints: evaluation ([PB-02](../../../platform/evaluation-acceptance/README.md)), adaptation ([PB-03](../../../platform/adaptation/README.md)), serving and routing ([PB-04](../../../platform/serving-routing-placement/README.md)), safety gating ([PB-06](../../../platform/safety-autonomy-gating/README.md)), and identity and sandbox ([PB-08](../../../platform/security-identity-sandbox/README.md))
- [ ] Components: one product for each role in the components table
- [ ] Detectors: your own detectors flag every sequence, each checked on its own; the models don't detect attacks
- [ ] Attack data: labelled attack traffic from your network or your test lab, with fictitious subscribers only in shared test sets
- [ ] Classification head: retrained on your attack taxonomy, as [PB-03](../../../platform/adaptation/README.md) sets out
- [ ] Data access: a workload identity that reads the flagged records only, as PB-08 sets out
- [ ] Placement: the regional site runs Classification and Safety. The core runs the large LLM.

| Component role | Red Hat product used |
|---|---|
| Inference engine for every slot | Red Hat AI Inference (vLLM) |
| Serving platform | Red Hat OpenShift AI with KServe |
| Training for the Classification head | Training Hub in Red Hat OpenShift AI |
| Detectors and signalling record store | Your choice; this design names no product |

Key flags for each slot, copied from [PB-04](../../../platform/serving-routing-placement/README.md#key-flags-per-slot). Start the Safety slot with its own pinned revision and no tool-calling flags.

```text
# LLM 31B (pin the revision; text-only; tool calling)
--revision <sha> --enable-auto-tool-choice --tool-call-parser gemma4 \
--limit-mm-per-prompt '{"image": 0, "audio": 0}'
# Classification (Gemma3TextForSequenceClassification) and Reranker (num_labels=1)
--runner pooling --convert classify        # endpoints /classify, /v1/score, /rerank
```

Any component can be replaced. The Red Hat products named here show one way to build this design.

### What you bring

<!-- generated:what-you-bring start -->

| Model change | Your expertise | How far to climb |
|---|---|---|
| Retrain the Classification head on your taxonomy; no other model changes | Your fault or alert taxonomy; a golden set your experts label | Configure first, and train only on a measured gap, as [PB-03 Adaptation](../../../platform/adaptation/README.md) sets out |

| Item | Network component | Mechanism | Owner | Matrix row |
|---|---|---|---|---|
| Attack taxonomy and labelled attack traffic | 5G core CNFs | Classification labels | SME | [5G core CNFs](../../../platform/bring-your-own-data/README.md#domain-5g-core-cnfs) |
| Decoded core signalling for training and tests | 5G core CNFs | Classification labels | SME | [5G core CNFs](../../../platform/bring-your-own-data/README.md#domain-5g-core-cnfs) |
| Labelling skill scoped to the interfaces you watch | 5G core CNFs | Skill or capability manifest | SME | [5G core CNFs](../../../platform/bring-your-own-data/README.md#domain-5g-core-cnfs) |

<!-- generated:what-you-bring end -->

### Sandbox

<!-- generated:sandbox start -->

| Sandbox fit | Trigger on this page | Where to read |
|---|---|---|
| Base sandbox only: the agent reads through the gateways, so the six sandbox controls and the gateway screen are enough | Reads records your detectors already flagged; the agent runs no code | [PB-08: when a use case needs a sandbox](../../../platform/security-identity-sandbox/README.md#when-a-use-case-needs-a-sandbox) |

<!-- generated:sandbox end -->

### What you must add

| Gap | What you add | Source |
|---|---|---|
| Security data | Labelled attack traffic and a security evaluation before the shadow stage, because the card says the model was not trained or evaluated for defensive security operations | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#network-security-operations-not-validated) |
| Signalling data | Decoded core signalling from your network for training and tests, because the card's training leaves out 5G core signalling | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| Classification head | A head retrained on your attack taxonomy, because the shipped head covers eight synthetic drive-test classes | [OTel-LLM-8.3B-Classification model card](https://huggingface.co/farbodtavakkoli/OTel-LLM-8.3B-Classification) |
| Interface scope | The core interfaces you watch, such as the Nudm services, mapped to your attack taxonomy against the 5G security procedures | [3GPP TS 29.503](https://www.3gpp.org/DynaReport/29503.htm), [3GPP TS 33.501](https://www.3gpp.org/DynaReport/33501.htm) |
| Language scope | Tests in every language your analysts read explanations in, because the card's quality claims cover English text only | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |

## Governance

Every outcome is LOOK. The ceiling is inform, and nothing reaches the [decision gate](../../../architecture/decision-gate.md), because the flow changes no network state.

| Action | Gate outcome (LOOK/NOTIFY/REVIEW/ACT/STOP) | Approval | AI Act class |
|---|---|---|---|
| Label a flagged sequence and explain it, citing the messages | LOOK | None: the analyst reads the label and its evidence | Recorded by your legal team in the classification record |
| Abstain and list the messages read | LOOK | None: the analyst sees what was checked | Recorded by your legal team in the classification record |

| Parameter | What it controls | Who sets it | How to calibrate |
|---|---|---|---|
| Classification per-class recall floor | The lowest recall for each class in your attack taxonomy | Risk owner, with subject-matter expert (SME) review | [Evaluation and acceptance](../../../platform/evaluation-acceptance/README.md): use analyst labels on a temporal holdout, so test traffic comes after training traffic |
| Classification other-or-abstain recall floor | The lowest recall for sequences outside the taxonomy | Risk owner | Hold out attack types the model never saw and check they land in other or abstain |
| Safety abstain-recall floor | The lowest share of insufficient-context items where the Safety slot abstains | Risk owner, with SME review | Remove the flagged messages from items and measure correct abstention |
| LLM groundedness floor | The lowest share of explanations whose claims the flagged messages support | Risk owner, with SME review | Score a golden set of labelled sequences with analyst-checked explanations |

This page gives no default values. Each owner sets the value with SME review and versions it with the policy that `policy_version` names.

## Sources

Each key claim links its source, as set out in [the Sources table](../../../framework/definitions.md#sources-table).

| # | Claim | Basis | Source |
|---|---|---|---|
| 1 | The 31B was not trained or evaluated for defensive network-security operations such as traffic and anomaly analysis, and security use needs dedicated evaluation and human oversight | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#network-security-operations-not-validated) |
| 2 | The 31B training leaves out 5G core control-plane and inter-NF signalling data | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#telecommunications-data-not-included-in-training) |
| 3 | The 31B targets English-language use, and all its quality claims are text-only | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality) |
| 4 | The Classification model's head predicts eight root-cause classes from the synthetic TeleLogs drive-test dataset | model card | [OTel-LLM-8.3B-Classification model card](https://huggingface.co/farbodtavakkoli/OTel-LLM-8.3B-Classification) |
| 5 | TS 29.503 specifies the Unified Data Management services of the 5G System | project documentation | [3GPP TS 29.503](https://www.3gpp.org/DynaReport/29503.htm) |
| 6 | TS 33.501 specifies the security architecture and procedures for the 5G System | project documentation | [3GPP TS 33.501](https://www.3gpp.org/DynaReport/33501.htm) |

## Deploy and verify

_Stub: this catalog entry has no deploy steps yet._

## Limitations

- The entry never blocks or changes signalling; it informs only, and every outcome is LOOK.
- It labels what your detectors flag, so an attack no detector sees never reaches it.
- The card says the model was not trained or evaluated for security operations, so test it on your own traffic first.
- The shipped Classification head knows drive-test classes only, so it needs your attack taxonomy first.
- Signalling records hold subscriber identities, so handle them under your data protection rules.
- The quality claims cover English only, so explanations in another language need their own evaluation.
