---
title: "Ideas"
doc_status: done
clarity_reviewed: "2026-11-20"
---

# Ideas

These are exploration ideas for operators to try, test, and contribute back. They aren't recipes. Each page says why it's an idea and what would promote it to the front page.

Each idea keeps its full page. The earlier catalog, with every entry as it stood before this change, is kept at the [catalog-30-2026-11 tag](https://github.com/ravisharma5/otel-telco-blueprints/tree/catalog-30-2026-11).

## Ideas

<!-- generated:ideas start -->

| Idea | Why it's an idea | What would promote it |
|---|---|---|
| [UC-AGOPS-04 Site change-risk gate](site-change-risk-gate/README.md) | Rules cover most pre-change checks, and the 26B Decision model has no measured fit on cell-site CPU beside a vDU. | Measured CPU fit and latency on a DU server under vDU load; Evidence that the model adds value over rule-based pre-checks |
| [UC-KNOW-02 Standards and change-request summaries](spec-summarisation/README.md) | The grounded knowledge assistant already answers from versioned standards with citations, so summaries fit there rather than on a page of their own. | A clause-level citation check on versioned change requests; Evidence of an audience beyond standards delegates |
| [UC-OPS-10 Site log reduction](site-log-reduction/README.md) | Template mining such as Drain is the usual baseline for log reduction, and embedding clusters can hide the rare line that matters in an outage. | A measured comparison with template mining on your own site logs; Evidence that no rare fault line is hidden, on replayed incidents; Measured CPU and memory use on a DU server under vDU load |
| [UC-RES-01 KPI root-cause reasoning](kpi-rca-reasoning/README.md) | RAN and RF health checks already cover KPI degradations, and open reasoning models struggled on TeleLogs without domain adaptation. | Your own labelled KPI degradations; A measured gain over RAN and RF health checks |
| [UC-RES-02 5G mobility failure analysis](mobility-failure-analysis/README.md) | Signalling trace analysis covers the same traces, and the event rebuild tools are the real work. | Event rebuild tools and labelled failed procedures; Measured value beyond signalling trace analysis |
| [UC-SEC-02 Signalling attack classification](signalling-attack-classification/README.md) | The Classification head knows only TeleLogs root causes, no public labelled signalling-attack set exists to retrain it, and security alert triage already covers the flow. | A labelled signalling-attack set with usage rights; A measured Classification head on that set |
| [UC-SW-03 O-RAN RIC xApp assistant](oran-ric-xapp-assistant/README.md) | Most operators buy xApps from vendors rather than write them, so few teams need a code assistant for them. | Operators who build xApps in-house and want an assistant; A code-navigation evaluation beyond multiple-choice benchmark scores |

<!-- generated:ideas end -->

## Promote an idea

To move an idea back to the front page, open a pull request that addresses the checklist on its page. The pull request must pass lint and the clarity review.
