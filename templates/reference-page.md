---
type: "reference"  # always reference
title: "<Reference page title in plain words>"
question: "<The one question this page answers>"
doc_status: "draft"  # draft | review | done; the site shows a banner for draft and review
platform_blueprints: ["PB-04"]  # PB ids named as plain text until those pages exist
otel_slots: ["llm"]  # llm | embedding | reranker | safety | decision | classification
clarity_reviewed: "2026-11-07"  # set after the humanizer pass; quoted ISO date
---

<!-- Writing rules: framework/style-guide.md. This page is a recipe: it says how to build the design, not how far it has been tested. Link every factual claim to its source. Write no validation-status words and no readiness levels. Name each component by its role and the Red Hat product used. Write no product support status. -->

# <Reference page title>

## At a glance

<!-- budget: 1 table, 5 rows ; purpose: the question, the short answer, who reads it, slots, and the platform blueprints that build on it -->

| Field | Value |
|---|---|
| Question answered | <The question in one line> |
| Answer | <The answer in one line> |
| Audience | <Architects, platform teams, or both> |
| OTel slots | <Slots this page covers> |
| Platform blueprints | <PB ids as plain text, for example PB-04> |

## The question

<!-- budget: 3 lines ; purpose: one sentence, and why an operator needs the answer -->

<The question in one sentence, and what goes wrong without an answer.>

## The principle

<!-- budget: 5 lines ; purpose: the rule this page sets, stated plainly, with a link to its source -->

<The rule in one or two sentences, with a link to the source behind it.>

## The design

<!-- budget: 4 tables, 8 steps, 1 diagram ; purpose: components by role, the flow, and page-specific parts under H3 headings -->

| Component role | Red Hat product used |
|---|---|
| <What the component does in this design> | <Red Hat product> |

Any component can be replaced. The Red Hat products named here show one way to build this design.

<!-- Put page-specific parts (tiers, layers, message formats) under their own H3 headings. Name each flow "Flow: <name>" so tests can find its diagram. -->

### Flow: <name>

```mermaid
flowchart LR
  A[<Caller>] --> B[<Component>]
  B --> C[<Result>]
```

1. <Step 1>
2. <Step 2>
3. <Step 3>

## Trade-offs and limits

<!-- budget: 1 table ; purpose: what this design costs and what to do about it -->

| Trade-off | What to do |
|---|---|
| <What the design costs or cannot do> | <How to handle it> |

## Used by

<!-- budget: 12 bullets ; purpose: platform blueprints as plain text; link only pages that exist -->

- <PB-04 as plain text, or a link once the page exists>
- <Another reference page link>
