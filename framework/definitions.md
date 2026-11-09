---
title: "Definitions: claims, readiness, and evidence"
doc_status: done
clarity_reviewed: "2026-11-09"
---

# Definitions: claims, readiness, and evidence

## At a glance

| Item | Answer |
|---|---|
| What this defines | Claim terms, evidence levels (E0-E4), model readiness (M0-M3), autonomy ceiling, component naming |
| Who uses it | Blueprint authors, reviewers, and the linter (schemas reuse these exact values) |
| Rule to remember | Headline level = the minimum E-level across load-bearing claims |
| Component naming | Role in the design plus the Red Hat product used; any component can be replaced |
| Where terms live | [Glossary](glossary.md) |

## Claim terms and evidence levels

| Term | E-code | Meaning | Evidence required |
|---|---|---|---|
| described | E0 | Claimed by a vendor document or model card only | Link to the vendor source |
| designed | E1 | Method defined: eval spec written, not run | Link to the eval spec in the repo |
| deployed | E2 | Offline replay or unit evidence committed in the repo | Link to a log, `jsonl`, or trace file in the repo |
| exercised | E3 | Live run on a reference cluster with wire or trace capture | Link to the captured trace or log in the repo |
| evaluated | E3 (evaluated) | E3, plus a full eval set run against acceptance gates | Link to the eval report in the repo |
| operator-validated | E4 | Operator pilot on real data | Link to the anonymized pilot report |

You use the words in prose and the codes in tables and front matter; the two never diverge. You write `E3 (evaluated)` as qualifier text in the E-level cell, and its evidence must link an eval report in the repo.

## Model readiness (M0-M3)

| Level | Meaning | Examples |
|---|---|---|
| M3 | Ready on released checkpoints (1.x/2.0) for the stated role, read-only | Grounded standards Q&A, spec summarization, 5G RCA within the 8 trained classes |
| M2 | Needs a tool-calling LLM slot (OTel 2.5, unpublished; the 2.0 card lists no telecom tool-calling data) | Closed-loop incident, router and 5GC operations, CAMARA diagnostics |
| M1 | Needs task data, integration, or adaptation not in the family | Signalling traces, RAN code and ASN.1, security detection, French tickets |
| M0 | Research: under development, or no data exists | Mobility failure chains, broadband digital troubleshooting |

You set M once per blueprint, in front matter and the at-a-glance box, never per claim. Platform blueprints write `model_readiness: n/a`, because they describe platform capability, not a model task.

## Autonomy ceiling

The ceiling is the highest gate outcome a blueprint allows without a human.

| Value | Gate outcome allowed | What happens |
|---|---|---|
| inform | LOOK | Read-only answers and analysis |
| notify | NOTIFY | Alerts a human; takes no action |
| recommend-with-approval | REVIEW | Proposes an action; a human approves it |
| act-within-policy | ACT | Acts alone, only for low-risk classes the policy allows |

A TM Forum Autonomous Networks level is a target, never a claim.

## Headline level: the minimum rule

You mark each validation-table row as load-bearing or not. The headline E-level is the minimum across rows where `Load-bearing = yes`. The linter recomputes it and fails if your front matter disagrees. Load-bearing is exactly `yes` or `no`; any other value fails the linter (VT007), and the row still counts toward the minimum.

Worked example (fictional blueprint):

| # | Claim | Load-bearing | Vendor-reported | Our operator-task eval | E-level |
|---|---|---|---|---|---|
| 1 | Retrieves the governing clause | yes | | Replay set of 200 questions | E2 |
| 2 | Abstains when context lacks the answer | yes | Model card reports 0.9 | | E0 |
| 3 | Gate never returns ACT without an approved playbook | yes | | Eval spec written | E1 |
| 4 | Answers in under 2 s | no | | Live run | E3 |

Headline = min(E2, E0, E1) = E0 (described). Row 4 is not load-bearing, so it does not count. Row 2 stays E0 although the model card reports 0.9, because only the *Our operator-task eval* column can raise E.

## Evidence columns and links

| Column | Holds | Can raise E? |
|---|---|---|
| Vendor-reported | Model-card or vendor numbers | No |
| GSMA external | GSMA or other third-party results | No |
| Our operator-task eval | Results from this project's own eval on operator tasks | Yes, the only one |

| E-level | Evidence link must point to |
|---|---|
| E0 | The vendor source (`http` or `https` URL) |
| E1 | The eval spec (a file in the repo) |
| E2 or higher | A resolvable file in the repo (log, `jsonl`, trace) |

Where evidence lives: every repo-file evidence link (E1 to E4) must point to a file under an `evidence/` folder, either next to the blueprint or in a parent folder up to the repo root. The link can never point to the blueprint itself.

| Location | Example link from `platform/maas/README.md` |
|---|---|
| Next to the blueprint | `evidence/replay.jsonl` |
| Repo-level folder | `../../evidence/eval-report.md` |

E2+ rows must fill Release / revision with the checkpoint plus a pinned revision SHA, or a skill or adapter version, so a slot swap (2.0 to 2.5) leaves old rows visibly stale.

Canonical validation-table columns, in order:

`# | Claim | Slot / component | Load-bearing | Vendor-reported | GSMA external | Our operator-task eval | E-level | Evidence | Result | Date | Release / revision`

## Component naming

Blueprints describe an open source solution, and they make no product support claims. Each blueprint names every load-bearing component by its role in the design and the Red Hat product the reference architecture uses for that role. Platform blueprints use a `Component role | Red Hat product used` table; use-case blueprints list components under What you need.

Every blueprint carries this exact line:

Any component can be replaced. The Red Hat products named here show one way to build this design.

Blueprints make no product support claims, so labels such as `GA`, `TP`, `DP`, `community`, or `partner-certified` never appear in prose. Vale enforces this with `Blueprints.InlineStatus`. For supported products and versions, operators engage Red Hat directly.

## Honest one-liner

Every blueprint and catalog card carries one line in this format: `M-level / E-level / autonomy ceiling. Main blocker. What has been shown.`

Example: "M2 / E1 / recommend-with-approval. Needs a tool-calling slot. Method defined, not yet run."

The linter checks the M and E codes in this line against front matter and fails on a mismatch (AG002).
