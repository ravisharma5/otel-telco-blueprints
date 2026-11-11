---
title: "Definitions: sources, autonomy, and naming"
doc_status: done
clarity_reviewed: "2026-11-11"
---

# Definitions: sources, autonomy, and naming

## At a glance

| Item | Answer |
|---|---|
| What this defines | Claim basis, the Sources table, autonomy ceiling, component naming, one-liner |
| Who uses it | Blueprint authors, reviewers, and the linter (schemas reuse these exact values) |
| Rule to remember | Every key claim links its source |
| Component naming | Role in the design plus the Red Hat product used; any component can be replaced |
| Where terms live | [Glossary](glossary.md) |

## Claim basis

Blueprints are recipes. They draw on telecom network expertise, industry use cases, research, and Red Hat recommendations, so they state no validation status. Instead, each key claim names its basis and links its source.

| Basis | Use it for | Write it as | Source links to |
|---|---|---|---|
| model card | Numbers and behavior the model card reports, and the licence or usage terms a model's publisher sets for it | "The model card reports ..." | The model card URL, or the publisher's licence or terms page |
| research | Papers, benchmarks, and upstream issue reports | "Research shows ..." and name the paper or issue | The paper, benchmark, or issue URL |
| Red Hat guidance | Red Hat documentation, recommendations, and articles | "Red Hat recommends ..." | The doc or article URL |
| industry use case | Operator and GSMA material | "Operators use ..." | The source URL or a repo file |
| project documentation | Upstream open source project docs (vLLM, llm-d, KServe), and standards bodies' published specifications, whitepapers, and conformance programs (TM Forum, CAMARA, 3GPP, IETF RFCs), and laws and regulations that official bodies publish (EUR-Lex). Blog posts and news items aren't project documentation | Name the project or standard: "The vLLM docs state that" or "3GPP TS 23.288 defines" | The project doc, specification, or whitepaper URL |

## Sources table

Every blueprint has one Sources table with one row per key claim. Platform blueprints put it under *Sources and acceptance*; use-case blueprints put it under *Sources*.

The canonical columns, in order:

`# | Claim | Basis | Source`

| Column | Holds |
|---|---|
| # | Row number |
| Claim | The claim in one line |
| Basis | One of: model card, research, Red Hat guidance, industry use case, project documentation (any letter case) |
| Source | A link to an `http` or `https` URL, or to a file in this repo. Never the page itself |

The linter checks the header (VT002), the Basis value (VT007), and the Source link (VT004). A repo-file link must point to a file that exists inside the repo.

Worked example:

| # | Claim | Basis | Source |
|---|---|---|---|
| 1 | The 31B LLM needs about 62.6 GB for bf16 weights | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT) |
| 2 | The weights may change, so pin a revision before you deploy | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT) |

## Autonomy ceiling

The ceiling is the highest gate outcome a blueprint allows without a human.

| Value | Gate outcome allowed | What happens |
|---|---|---|
| inform | LOOK | Read-only answers and analysis |
| notify | NOTIFY | Alerts a human; takes no action |
| recommend-with-approval | REVIEW | Proposes an action; a human approves it |
| act-within-policy | ACT | Acts alone, only for low-risk classes the policy allows |

A TM Forum Autonomous Networks level is a target, never a claim.

## Component naming

Blueprints describe an open source solution. Each blueprint names every key component by its role in the design and the Red Hat product the reference architecture uses for that role. Platform blueprints use a `Component role | Red Hat product used` table; use-case blueprints list components under What you need.

Every blueprint carries this exact line:

Any component can be replaced. The Red Hat products named here show one way to build this design.

Blueprints make no product support claims, so labels like `GA`, `TP`, `DP`, `community`, or `partner-certified` never appear in prose. Vale enforces this with `Blueprints.InlineStatus`. For supported products and versions, operators engage Red Hat directly.

## One-liner

Every blueprint and catalog card has a one-line summary. It goes in the front matter `one_liner` field and in the at-a-glance `One-liner` row, and it says what the design does and what it mainly depends on. Use-case lines also state the autonomy ceiling in words. The line carries no readiness codes.

| Blueprint | Example |
|---|---|
| Platform | "Gives each team an OpenAI-compatible endpoint with per-team token limits. Depends on a gateway with token rate limiting." |
| Use case | "Recommends fixes with human approval. Needs a tool-calling LLM slot." |
