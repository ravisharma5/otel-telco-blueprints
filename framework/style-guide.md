---
title: "Style guide"
doc_status: done
clarity_reviewed: "2026-11-09"
---

# Style guide

## At a glance

| Field | Value |
|---|---|
| Purpose | One shape and one voice for every blueprint, so an operator finds the same answer in the same place |
| Rule 1 | The at-a-glance table comes first, before any prose |
| Rule 2 | Use tables instead of prose for comparisons, components, decisions, and risks |
| Rule 3 | Every claim carries an evidence level (E0-E4) or a link |
| Who it's for | Authors and reviewers of blueprints and reference pages |
| Where budgets live | [`tools/bplint/budgets.yaml`](https://github.com/ravisharma5/otel-telco-blueprints/blob/main/tools/bplint/budgets.yaml) |
| How to check | Run `make lint`, then follow the [review checklist](review-checklist.md) |

## Page skeletons

Every page opens with an at-a-glance table of at most 7 rows. Sections appear in the order below. Budgets are maximums.

### Platform blueprint

Page budget: 1800 prose words (about 4 pages at 450 words per page). Tables don't count toward prose words.

| # | Section | Budget |
|---|---|---|
| 0 | At a glance | 1 table, 7 rows: Honest one-liner, Question answered, Audience, OTel slots, Placement tier, Top 3 decisions, Agent-school courses |
| 1 | The operator question | 3 lines |
| 2 | Decisions you must make | 1 table (MADR style: decision, options, recommendation, because) |
| 3 | Reference design | 1 diagram, 8 steps, 8 bullets (config-artifact links) |
| 4 | Components | 1 table (component role, Red Hat product used), then the standard replaceable line |
| 5 | OTel slot guidance | 1 table |
| 6 | Validation and acceptance | 1 table (canonical validation table), 10 bullets (gates) |
| 7 | Operating model | 1 table |
| 8 | Risks and limitations | 1 table |
| 9 | Used by and next steps | 12 bullets (links only) |

### Use-case blueprint

Page budget: 1350 prose words for a flagship (about 3 pages), 450 prose words for a catalog entry (about 1 page).

| # | Section | Budget |
|---|---|---|
| 0 | At a glance | 1 table, 7 rows: Honest one-liner, Problem, Audience, OTel slots, Model readiness and evidence, Placement tier, Agent-school courses |
| 1 | Problem and value | 5 lines |
| 2 | How it works | 1 diagram, 8 steps |
| 3 | What you need | 12 bullets (checklist, including components), then the standard replaceable line |
| 4 | Governance | 1 table |
| 5 | Validation | 1 table (canonical validation table) |
| 6 | Deploy and verify | 5 lines, 5 bullets (related-work links) |
| 7 | Limitations | 6 bullets |

### Reference page

Reference pages define principles and recipes that blueprints build on. They carry no validation table, and every factual claim links to its source.

Page budget: 1350 prose words (about 3 pages). Tables and code, including Mermaid fences, don't count toward prose words.

| # | Section | Budget |
|---|---|---|
| 0 | At a glance | 1 table, 5 rows: Question answered, Answer, Audience, OTel slots, Platform blueprints |
| 1 | The question | 3 lines |
| 2 | The principle | 5 lines |
| 3 | The design | 4 tables, 8 steps, 1 diagram |
| 4 | Trade-offs and limits | 1 table |
| 5 | Used by | 12 bullets (links only) |

Put page-specific parts under *The design* as H3 headings. The linter checks only the order of H2 sections.

### What the skeletons fold in and leave out

Some topics don't get a section of their own; they fold into these skeletons. Config artifacts become links under *Reference design*. Integrations and data or adaptation needs go into *What you need*. Related work (agent-school, NVIDIA and Databricks blueprints, LFN projects) goes into *Used by and next steps* on platform pages and into the related-work bullets under *Deploy and verify* on use-case pages.

Platform section 6 is *Validation and acceptance*. It carries the canonical validation table and the acceptance gates.

Flagships and catalog entries share one use-case template. A catalog entry sets `flagship: false` and must fill At a glance, Governance, Validation, and Limitations. It may stub the other sections with a body that starts `_Stub:`. The linter picks budgets from the `flagship` flag.

There's no Sandbox, Tested, or Maintained tier. The readiness statement is the model readiness level (M) and the evidence level (E), both in the at-a-glance table.

## Budget units

Each section uses the unit that fits it. You tune the numbers in [`budgets.yaml`](https://github.com/ravisharma5/otel-telco-blueprints/blob/main/tools/bplint/budgets.yaml) without code changes.

| Unit | What counts |
|---|---|
| Rows | Body rows of a markdown table; header and separator rows don't count |
| Tables | Markdown tables in the section |
| Steps | Items of a numbered list |
| Bullets | Items of a bulleted list, including checklist items |
| Lines | Non-blank prose lines, excluding tables, lists, and headings |
| Diagrams | Embedded images (the exported SVG) |
| Page words | Prose words across the whole page, excluding tables, code, and front matter |

## Writing rules

1. Lead with the answer or decision. Put context after it, if you need it at all.
2. Use tables instead of prose for comparisons, components, decisions, and risks.
3. Keep one idea per paragraph and at most 3 sentences per paragraph.
4. Write in second person, active voice, and present tense: `You deploy`, not `It is deployed`.
5. Give every claim an evidence level or a link. Don't write `proven`, `validated`, `production-ready`, `seamless`, `robust`, or `cutting-edge`; write the E-level instead.
6. Use one qualifier or state the condition. Don't stack hedges.
7. Cut words that don't change what an operator does next.
8. Name things exactly: name each component by its role and the Red Hat product used, never by a support status, and use "OTel" for the model family only. See the [naming rule](glossary.md#the-naming-rule) and [component naming](definitions.md#component-naming).
9. Use numbers with units instead of adjectives: `< 200 ms`, `34 GB`.
10. Use sentence-case headings and descriptive link text, never `click here`.
11. Don't mix doc types. Explain in the blueprint and link to how-to steps.
12. State limitations plainly in their own section.

## Components, evidence, and links

| Topic | Rule |
|---|---|
| Components | Use the table `Component role \| Red Hat product used` and the standard line. Write no product support label; Vale fails on them (`Blueprints.InlineStatus`) |
| Evidence level | Every claim row carries an E-level as defined in [definitions.md](definitions.md) |
| E0 link | The vendor or upstream source |
| E1 link | The evaluation spec that defines the method |
| E2+ link | A file in this repo that resolves (log, `jsonl`, trace). Also give the release or revision that produced it |

## Diagrams

- Draw flow diagrams as inline code fences tagged `mermaid`. They render on the docs site and on GitHub.
- Author architecture diagrams with the archify skill. The architecture overview has one archify diagram.
- Commit three files in a `diagrams/` folder beside the doc: the archify source HTML, its `candidate.json`, and the exported SVG.
- Embed the SVG with a relative image link, for example `![Reference design](diagrams/reference-design.svg)`.
- archify has no command-line export. Export the SVG from the archify viewer.
- The linter fails with DG001 if a referenced diagram file is missing.

## Publishing

- Write plain GitHub markdown. Every push to `main` publishes the pages to the docs site.
- Commit generated files, such as indexes, as `.md`.
- Front matter is the data model. `schemas/*.schema.json` validates it, and later generators read it.
