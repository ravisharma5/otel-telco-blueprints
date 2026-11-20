---
title: "Recipes"
doc_status: done
clarity_reviewed: "2026-11-15"
---

# Recipes

Pick a recipe by domain, or by a platform blueprint it uses. Each recipe maps an operator use case to OTel model slots and the platform blueprints it depends on.

A full recipe adds a worked example and deploy steps. A catalog entry fits on one page and lists what you must add before production. *Also covers* names the applications a recipe already handles.

Use cases that aren't recipes yet are listed as [exploration ideas](ideas/index.md).

The Use cases page shows the same use cases as cards.

## When not to use OTel

Some problems are numeric or high-volume, so a classic method should come first. OTel then adds a gate, a check, or a readable explanation around that method's output.

| Problem | Start with | Where OTel fits | In this catalog |
|---|---|---|---|
| Numeric optimisation, such as energy-saving windows or RF parameters | Your SON, planner, or vendor energy feature | Gate each proposal, check it against its simulation, and report | [UC-OPS-05](network-operations/ran-energy-saving/README.md) works this way: your planner proposes the windows |
| Log volume reduction | Template mining, for example [Drain](https://jiemingzhu.github.io/pub/pjhe_icws2017.pdf), and log-pipeline rules | Summarise reduced logs centrally if you need a readable digest | [UC-OPS-10](ideas/site-log-reduction/README.md) moved to the ideas area for this reason |
| Threshold and anomaly detection on KPIs | Thresholds and classic anomaly detection | Explain and triage a degradation your monitoring already found | [UC-OPS-04](network-operations/ran-rf-health-checks/README.md) |
| Time-series forecasting | Your forecasting tool, called as a read tool | Read forecasts; never compute them | [UC-OPS-06](network-operations/slice-sla-assurance/README.md) |

<!-- generated:catalog-by-domain start -->

## Standards and knowledge

| Recipe | Topic | Depth | Also covers |
|---|---|---|---|
| [UC-KNOW-01](standards-knowledge/grounded-knowledge-assistant/README.md) | Grounded knowledge assistant | Full recipe | Telecom standards Q&A over documents you hold rights to; Grounded RAG assistants; Standards and change-request summaries |
| [UC-KNOW-03](standards-knowledge/oss-bss-architecture-guidance/README.md) | OSS and BSS architecture guidance | Catalog entry |  |

## Network software

| Recipe | Topic | Depth | Also covers |
|---|---|---|---|
| [UC-SW-01](network-software/ran-core-code-assistant/README.md) | RAN and core code assistant | Catalog entry |  |
| [UC-SW-02](network-software/network-automation-review/README.md) | Network automation review | Catalog entry |  |

## Network operations

| Recipe | Topic | Depth | Also covers |
|---|---|---|---|
| [UC-OPS-01](network-operations/alarm-triage-adaptation/README.md) | Adaptation ladder on alarm and root-cause triage | Full recipe | NOC ticket triage |
| [UC-OPS-02](network-operations/signalling-trace-analysis/README.md) | Signalling trace analysis | Catalog entry | 5G mobility failure analysis |
| [UC-OPS-03](network-operations/core-network-rca/README.md) | Core network root-cause analysis | Full recipe |  |
| [UC-OPS-04](network-operations/ran-rf-health-checks/README.md) | RAN and RF health checks | Catalog entry | KPI root-cause reasoning |
| [UC-OPS-05](network-operations/ran-energy-saving/README.md) | RAN energy saving | Full recipe |  |
| [UC-OPS-06](network-operations/slice-sla-assurance/README.md) | Slice SLA assurance | Full recipe |  |
| [UC-OPS-07](network-operations/mop-validation/README.md) | MOP validation | Full recipe |  |
| [UC-OPS-08](network-operations/transport-ip-diagnostics/README.md) | Transport and IP diagnostics | Catalog entry |  |
| [UC-OPS-09](network-operations/cross-domain-oss-correlation/README.md) | Cross-domain OSS correlation | Catalog entry |  |

## Agentic operations

| Recipe | Topic | Depth | Also covers |
|---|---|---|---|
| [UC-AGOPS-01](agentic-operations/closed-loop-incident-handling/README.md) | Governed closed-loop incident handling | Full recipe | Closed-loop incident handling |
| [UC-AGOPS-02](agentic-operations/router-core-read-only-ops/README.md) | Read-only router and 5G core operations | Catalog entry |  |
| [UC-AGOPS-05](agentic-operations/cnf-upgrade-checks/README.md) | CNF upgrade pre- and post-checks | Full recipe |  |

## Business assurance

| Recipe | Topic | Depth | Also covers |
|---|---|---|---|
| [UC-BIZ-01](business-assurance/churn-risk-explanation/README.md) | Churn risk explanation | Catalog entry |  |
| [UC-BIZ-02](business-assurance/revenue-assurance-triage/README.md) | Revenue assurance triage | Catalog entry |  |
| [UC-CARE-01](business-assurance/camara-care-diagnostics/README.md) | CAMARA customer-care diagnostics | Full recipe | Customer care diagnostics |
| [UC-CARE-02](business-assurance/broadband-digital-troubleshooting/README.md) | Broadband digital troubleshooting | Catalog entry |  |

## Security

| Recipe | Topic | Depth | Also covers |
|---|---|---|---|
| [UC-SEC-01](security/security-triage/README.md) | Security alert triage | Catalog entry | Signalling attack classification |
| [UC-SEC-03](security/software-onboarding-cve-review/README.md) | Software onboarding and CVE review | Catalog entry |  |

<!-- generated:catalog-by-domain end -->

## By platform blueprint

Find the recipes that use each platform blueprint.

<!-- generated:catalog-by-platform start -->

### PB-01 Intake and model selection

These recipes use [the Intake and model selection page](../platform/intake-model-selection/README.md):

- [UC-AGOPS-01 Governed closed-loop incident handling](agentic-operations/closed-loop-incident-handling/README.md)
- [UC-AGOPS-02 Read-only router and 5G core operations](agentic-operations/router-core-read-only-ops/README.md)
- [UC-AGOPS-05 CNF upgrade pre- and post-checks](agentic-operations/cnf-upgrade-checks/README.md)
- [UC-BIZ-01 Churn risk explanation](business-assurance/churn-risk-explanation/README.md)
- [UC-BIZ-02 Revenue assurance triage](business-assurance/revenue-assurance-triage/README.md)
- [UC-CARE-01 CAMARA customer-care diagnostics](business-assurance/camara-care-diagnostics/README.md)
- [UC-CARE-02 Broadband digital troubleshooting](business-assurance/broadband-digital-troubleshooting/README.md)
- [UC-KNOW-01 Grounded knowledge assistant](standards-knowledge/grounded-knowledge-assistant/README.md)
- [UC-KNOW-03 OSS and BSS architecture guidance](standards-knowledge/oss-bss-architecture-guidance/README.md)
- [UC-OPS-01 Adaptation ladder on alarm and root-cause triage](network-operations/alarm-triage-adaptation/README.md)
- [UC-OPS-02 Signalling trace analysis](network-operations/signalling-trace-analysis/README.md)
- [UC-OPS-03 Core network root-cause analysis](network-operations/core-network-rca/README.md)
- [UC-OPS-04 RAN and RF health checks](network-operations/ran-rf-health-checks/README.md)
- [UC-OPS-05 RAN energy saving](network-operations/ran-energy-saving/README.md)
- [UC-OPS-06 Slice SLA assurance](network-operations/slice-sla-assurance/README.md)
- [UC-OPS-07 MOP validation](network-operations/mop-validation/README.md)
- [UC-OPS-08 Transport and IP diagnostics](network-operations/transport-ip-diagnostics/README.md)
- [UC-OPS-09 Cross-domain OSS correlation](network-operations/cross-domain-oss-correlation/README.md)
- [UC-SEC-01 Security alert triage](security/security-triage/README.md)
- [UC-SEC-03 Software onboarding and CVE review](security/software-onboarding-cve-review/README.md)
- [UC-SW-01 RAN and core code assistant](network-software/ran-core-code-assistant/README.md)
- [UC-SW-02 Network automation review](network-software/network-automation-review/README.md)

### PB-02 Evaluation and acceptance

These recipes use [the Evaluation and acceptance page](../platform/evaluation-acceptance/README.md):

- [UC-AGOPS-01 Governed closed-loop incident handling](agentic-operations/closed-loop-incident-handling/README.md)
- [UC-AGOPS-02 Read-only router and 5G core operations](agentic-operations/router-core-read-only-ops/README.md)
- [UC-AGOPS-05 CNF upgrade pre- and post-checks](agentic-operations/cnf-upgrade-checks/README.md)
- [UC-BIZ-01 Churn risk explanation](business-assurance/churn-risk-explanation/README.md)
- [UC-BIZ-02 Revenue assurance triage](business-assurance/revenue-assurance-triage/README.md)
- [UC-CARE-01 CAMARA customer-care diagnostics](business-assurance/camara-care-diagnostics/README.md)
- [UC-CARE-02 Broadband digital troubleshooting](business-assurance/broadband-digital-troubleshooting/README.md)
- [UC-KNOW-01 Grounded knowledge assistant](standards-knowledge/grounded-knowledge-assistant/README.md)
- [UC-KNOW-03 OSS and BSS architecture guidance](standards-knowledge/oss-bss-architecture-guidance/README.md)
- [UC-OPS-01 Adaptation ladder on alarm and root-cause triage](network-operations/alarm-triage-adaptation/README.md)
- [UC-OPS-02 Signalling trace analysis](network-operations/signalling-trace-analysis/README.md)
- [UC-OPS-03 Core network root-cause analysis](network-operations/core-network-rca/README.md)
- [UC-OPS-04 RAN and RF health checks](network-operations/ran-rf-health-checks/README.md)
- [UC-OPS-05 RAN energy saving](network-operations/ran-energy-saving/README.md)
- [UC-OPS-06 Slice SLA assurance](network-operations/slice-sla-assurance/README.md)
- [UC-OPS-07 MOP validation](network-operations/mop-validation/README.md)
- [UC-OPS-08 Transport and IP diagnostics](network-operations/transport-ip-diagnostics/README.md)
- [UC-OPS-09 Cross-domain OSS correlation](network-operations/cross-domain-oss-correlation/README.md)
- [UC-SEC-01 Security alert triage](security/security-triage/README.md)
- [UC-SEC-03 Software onboarding and CVE review](security/software-onboarding-cve-review/README.md)
- [UC-SW-01 RAN and core code assistant](network-software/ran-core-code-assistant/README.md)
- [UC-SW-02 Network automation review](network-software/network-automation-review/README.md)

### PB-03 Adaptation

These recipes use [the Adaptation page](../platform/adaptation/README.md):

- [UC-AGOPS-01 Governed closed-loop incident handling](agentic-operations/closed-loop-incident-handling/README.md)
- [UC-AGOPS-02 Read-only router and 5G core operations](agentic-operations/router-core-read-only-ops/README.md)
- [UC-AGOPS-05 CNF upgrade pre- and post-checks](agentic-operations/cnf-upgrade-checks/README.md)
- [UC-BIZ-01 Churn risk explanation](business-assurance/churn-risk-explanation/README.md)
- [UC-BIZ-02 Revenue assurance triage](business-assurance/revenue-assurance-triage/README.md)
- [UC-CARE-01 CAMARA customer-care diagnostics](business-assurance/camara-care-diagnostics/README.md)
- [UC-CARE-02 Broadband digital troubleshooting](business-assurance/broadband-digital-troubleshooting/README.md)
- [UC-KNOW-01 Grounded knowledge assistant](standards-knowledge/grounded-knowledge-assistant/README.md)
- [UC-KNOW-03 OSS and BSS architecture guidance](standards-knowledge/oss-bss-architecture-guidance/README.md)
- [UC-OPS-01 Adaptation ladder on alarm and root-cause triage](network-operations/alarm-triage-adaptation/README.md)
- [UC-OPS-02 Signalling trace analysis](network-operations/signalling-trace-analysis/README.md)
- [UC-OPS-03 Core network root-cause analysis](network-operations/core-network-rca/README.md)
- [UC-OPS-04 RAN and RF health checks](network-operations/ran-rf-health-checks/README.md)
- [UC-OPS-05 RAN energy saving](network-operations/ran-energy-saving/README.md)
- [UC-OPS-06 Slice SLA assurance](network-operations/slice-sla-assurance/README.md)
- [UC-OPS-07 MOP validation](network-operations/mop-validation/README.md)
- [UC-OPS-08 Transport and IP diagnostics](network-operations/transport-ip-diagnostics/README.md)
- [UC-OPS-09 Cross-domain OSS correlation](network-operations/cross-domain-oss-correlation/README.md)
- [UC-SEC-01 Security alert triage](security/security-triage/README.md)
- [UC-SEC-03 Software onboarding and CVE review](security/software-onboarding-cve-review/README.md)
- [UC-SW-01 RAN and core code assistant](network-software/ran-core-code-assistant/README.md)
- [UC-SW-02 Network automation review](network-software/network-automation-review/README.md)

### PB-04 Serving, routing, and placement

These recipes use [the Serving, routing, and placement page](../platform/serving-routing-placement/README.md):

- [UC-AGOPS-01 Governed closed-loop incident handling](agentic-operations/closed-loop-incident-handling/README.md)
- [UC-AGOPS-02 Read-only router and 5G core operations](agentic-operations/router-core-read-only-ops/README.md)
- [UC-AGOPS-05 CNF upgrade pre- and post-checks](agentic-operations/cnf-upgrade-checks/README.md)
- [UC-BIZ-01 Churn risk explanation](business-assurance/churn-risk-explanation/README.md)
- [UC-BIZ-02 Revenue assurance triage](business-assurance/revenue-assurance-triage/README.md)
- [UC-CARE-01 CAMARA customer-care diagnostics](business-assurance/camara-care-diagnostics/README.md)
- [UC-CARE-02 Broadband digital troubleshooting](business-assurance/broadband-digital-troubleshooting/README.md)
- [UC-KNOW-01 Grounded knowledge assistant](standards-knowledge/grounded-knowledge-assistant/README.md)
- [UC-KNOW-03 OSS and BSS architecture guidance](standards-knowledge/oss-bss-architecture-guidance/README.md)
- [UC-OPS-01 Adaptation ladder on alarm and root-cause triage](network-operations/alarm-triage-adaptation/README.md)
- [UC-OPS-02 Signalling trace analysis](network-operations/signalling-trace-analysis/README.md)
- [UC-OPS-03 Core network root-cause analysis](network-operations/core-network-rca/README.md)
- [UC-OPS-04 RAN and RF health checks](network-operations/ran-rf-health-checks/README.md)
- [UC-OPS-05 RAN energy saving](network-operations/ran-energy-saving/README.md)
- [UC-OPS-06 Slice SLA assurance](network-operations/slice-sla-assurance/README.md)
- [UC-OPS-07 MOP validation](network-operations/mop-validation/README.md)
- [UC-OPS-08 Transport and IP diagnostics](network-operations/transport-ip-diagnostics/README.md)
- [UC-OPS-09 Cross-domain OSS correlation](network-operations/cross-domain-oss-correlation/README.md)
- [UC-SEC-01 Security alert triage](security/security-triage/README.md)
- [UC-SEC-03 Software onboarding and CVE review](security/software-onboarding-cve-review/README.md)
- [UC-SW-01 RAN and core code assistant](network-software/ran-core-code-assistant/README.md)
- [UC-SW-02 Network automation review](network-software/network-automation-review/README.md)

### PB-05 Integration

These recipes use [the Integration page](../platform/integration/README.md):

- [UC-AGOPS-01 Governed closed-loop incident handling](agentic-operations/closed-loop-incident-handling/README.md)
- [UC-AGOPS-02 Read-only router and 5G core operations](agentic-operations/router-core-read-only-ops/README.md)
- [UC-AGOPS-05 CNF upgrade pre- and post-checks](agentic-operations/cnf-upgrade-checks/README.md)
- [UC-BIZ-01 Churn risk explanation](business-assurance/churn-risk-explanation/README.md)
- [UC-BIZ-02 Revenue assurance triage](business-assurance/revenue-assurance-triage/README.md)
- [UC-CARE-01 CAMARA customer-care diagnostics](business-assurance/camara-care-diagnostics/README.md)
- [UC-CARE-02 Broadband digital troubleshooting](business-assurance/broadband-digital-troubleshooting/README.md)
- [UC-KNOW-01 Grounded knowledge assistant](standards-knowledge/grounded-knowledge-assistant/README.md)
- [UC-KNOW-03 OSS and BSS architecture guidance](standards-knowledge/oss-bss-architecture-guidance/README.md)
- [UC-OPS-01 Adaptation ladder on alarm and root-cause triage](network-operations/alarm-triage-adaptation/README.md)
- [UC-OPS-02 Signalling trace analysis](network-operations/signalling-trace-analysis/README.md)
- [UC-OPS-03 Core network root-cause analysis](network-operations/core-network-rca/README.md)
- [UC-OPS-04 RAN and RF health checks](network-operations/ran-rf-health-checks/README.md)
- [UC-OPS-05 RAN energy saving](network-operations/ran-energy-saving/README.md)
- [UC-OPS-06 Slice SLA assurance](network-operations/slice-sla-assurance/README.md)
- [UC-OPS-07 MOP validation](network-operations/mop-validation/README.md)
- [UC-OPS-08 Transport and IP diagnostics](network-operations/transport-ip-diagnostics/README.md)
- [UC-OPS-09 Cross-domain OSS correlation](network-operations/cross-domain-oss-correlation/README.md)
- [UC-SEC-01 Security alert triage](security/security-triage/README.md)
- [UC-SEC-03 Software onboarding and CVE review](security/software-onboarding-cve-review/README.md)
- [UC-SW-01 RAN and core code assistant](network-software/ran-core-code-assistant/README.md)
- [UC-SW-02 Network automation review](network-software/network-automation-review/README.md)

### PB-06 Safety and autonomy gating

These recipes use [the Safety and autonomy gating page](../platform/safety-autonomy-gating/README.md):

- [UC-AGOPS-01 Governed closed-loop incident handling](agentic-operations/closed-loop-incident-handling/README.md)
- [UC-AGOPS-02 Read-only router and 5G core operations](agentic-operations/router-core-read-only-ops/README.md)
- [UC-AGOPS-05 CNF upgrade pre- and post-checks](agentic-operations/cnf-upgrade-checks/README.md)
- [UC-BIZ-01 Churn risk explanation](business-assurance/churn-risk-explanation/README.md)
- [UC-BIZ-02 Revenue assurance triage](business-assurance/revenue-assurance-triage/README.md)
- [UC-CARE-01 CAMARA customer-care diagnostics](business-assurance/camara-care-diagnostics/README.md)
- [UC-CARE-02 Broadband digital troubleshooting](business-assurance/broadband-digital-troubleshooting/README.md)
- [UC-KNOW-01 Grounded knowledge assistant](standards-knowledge/grounded-knowledge-assistant/README.md)
- [UC-KNOW-03 OSS and BSS architecture guidance](standards-knowledge/oss-bss-architecture-guidance/README.md)
- [UC-OPS-01 Adaptation ladder on alarm and root-cause triage](network-operations/alarm-triage-adaptation/README.md)
- [UC-OPS-02 Signalling trace analysis](network-operations/signalling-trace-analysis/README.md)
- [UC-OPS-03 Core network root-cause analysis](network-operations/core-network-rca/README.md)
- [UC-OPS-04 RAN and RF health checks](network-operations/ran-rf-health-checks/README.md)
- [UC-OPS-05 RAN energy saving](network-operations/ran-energy-saving/README.md)
- [UC-OPS-06 Slice SLA assurance](network-operations/slice-sla-assurance/README.md)
- [UC-OPS-07 MOP validation](network-operations/mop-validation/README.md)
- [UC-OPS-08 Transport and IP diagnostics](network-operations/transport-ip-diagnostics/README.md)
- [UC-OPS-09 Cross-domain OSS correlation](network-operations/cross-domain-oss-correlation/README.md)
- [UC-SEC-01 Security alert triage](security/security-triage/README.md)
- [UC-SEC-03 Software onboarding and CVE review](security/software-onboarding-cve-review/README.md)
- [UC-SW-01 RAN and core code assistant](network-software/ran-core-code-assistant/README.md)
- [UC-SW-02 Network automation review](network-software/network-automation-review/README.md)

### PB-07 Action layer

These recipes use [the Action layer page](../platform/action-layer/README.md):

- [UC-AGOPS-01 Governed closed-loop incident handling](agentic-operations/closed-loop-incident-handling/README.md)
- [UC-AGOPS-05 CNF upgrade pre- and post-checks](agentic-operations/cnf-upgrade-checks/README.md)
- [UC-BIZ-02 Revenue assurance triage](business-assurance/revenue-assurance-triage/README.md)
- [UC-CARE-01 CAMARA customer-care diagnostics](business-assurance/camara-care-diagnostics/README.md)
- [UC-OPS-01 Adaptation ladder on alarm and root-cause triage](network-operations/alarm-triage-adaptation/README.md)
- [UC-OPS-03 Core network root-cause analysis](network-operations/core-network-rca/README.md)
- [UC-OPS-04 RAN and RF health checks](network-operations/ran-rf-health-checks/README.md)
- [UC-OPS-05 RAN energy saving](network-operations/ran-energy-saving/README.md)
- [UC-OPS-06 Slice SLA assurance](network-operations/slice-sla-assurance/README.md)
- [UC-OPS-07 MOP validation](network-operations/mop-validation/README.md)
- [UC-OPS-08 Transport and IP diagnostics](network-operations/transport-ip-diagnostics/README.md)
- [UC-OPS-09 Cross-domain OSS correlation](network-operations/cross-domain-oss-correlation/README.md)
- [UC-SW-02 Network automation review](network-software/network-automation-review/README.md)

### PB-08 Security, identity, and sandbox

These recipes use [the Security, identity, and sandbox page](../platform/security-identity-sandbox/README.md):

- [UC-AGOPS-01 Governed closed-loop incident handling](agentic-operations/closed-loop-incident-handling/README.md)
- [UC-AGOPS-02 Read-only router and 5G core operations](agentic-operations/router-core-read-only-ops/README.md)
- [UC-AGOPS-05 CNF upgrade pre- and post-checks](agentic-operations/cnf-upgrade-checks/README.md)
- [UC-BIZ-01 Churn risk explanation](business-assurance/churn-risk-explanation/README.md)
- [UC-BIZ-02 Revenue assurance triage](business-assurance/revenue-assurance-triage/README.md)
- [UC-CARE-01 CAMARA customer-care diagnostics](business-assurance/camara-care-diagnostics/README.md)
- [UC-CARE-02 Broadband digital troubleshooting](business-assurance/broadband-digital-troubleshooting/README.md)
- [UC-KNOW-01 Grounded knowledge assistant](standards-knowledge/grounded-knowledge-assistant/README.md)
- [UC-KNOW-03 OSS and BSS architecture guidance](standards-knowledge/oss-bss-architecture-guidance/README.md)
- [UC-OPS-01 Adaptation ladder on alarm and root-cause triage](network-operations/alarm-triage-adaptation/README.md)
- [UC-OPS-02 Signalling trace analysis](network-operations/signalling-trace-analysis/README.md)
- [UC-OPS-03 Core network root-cause analysis](network-operations/core-network-rca/README.md)
- [UC-OPS-04 RAN and RF health checks](network-operations/ran-rf-health-checks/README.md)
- [UC-OPS-05 RAN energy saving](network-operations/ran-energy-saving/README.md)
- [UC-OPS-06 Slice SLA assurance](network-operations/slice-sla-assurance/README.md)
- [UC-OPS-07 MOP validation](network-operations/mop-validation/README.md)
- [UC-OPS-08 Transport and IP diagnostics](network-operations/transport-ip-diagnostics/README.md)
- [UC-OPS-09 Cross-domain OSS correlation](network-operations/cross-domain-oss-correlation/README.md)
- [UC-SEC-01 Security alert triage](security/security-triage/README.md)
- [UC-SEC-03 Software onboarding and CVE review](security/software-onboarding-cve-review/README.md)
- [UC-SW-01 RAN and core code assistant](network-software/ran-core-code-assistant/README.md)
- [UC-SW-02 Network automation review](network-software/network-automation-review/README.md)

### PB-09 Quality operations and observability

These recipes use [the Quality operations and observability page](../platform/quality-operations/README.md):

- [UC-AGOPS-01 Governed closed-loop incident handling](agentic-operations/closed-loop-incident-handling/README.md)
- [UC-AGOPS-02 Read-only router and 5G core operations](agentic-operations/router-core-read-only-ops/README.md)
- [UC-AGOPS-05 CNF upgrade pre- and post-checks](agentic-operations/cnf-upgrade-checks/README.md)
- [UC-CARE-01 CAMARA customer-care diagnostics](business-assurance/camara-care-diagnostics/README.md)
- [UC-KNOW-01 Grounded knowledge assistant](standards-knowledge/grounded-knowledge-assistant/README.md)
- [UC-KNOW-03 OSS and BSS architecture guidance](standards-knowledge/oss-bss-architecture-guidance/README.md)
- [UC-OPS-02 Signalling trace analysis](network-operations/signalling-trace-analysis/README.md)
- [UC-OPS-03 Core network root-cause analysis](network-operations/core-network-rca/README.md)
- [UC-OPS-05 RAN energy saving](network-operations/ran-energy-saving/README.md)
- [UC-OPS-06 Slice SLA assurance](network-operations/slice-sla-assurance/README.md)
- [UC-OPS-07 MOP validation](network-operations/mop-validation/README.md)
- [UC-OPS-09 Cross-domain OSS correlation](network-operations/cross-domain-oss-correlation/README.md)
- [UC-SEC-01 Security alert triage](security/security-triage/README.md)

### PB-10 Compliance, sovereignty, and operating model

These recipes use [the Compliance, sovereignty, and operating model page](../platform/compliance-operating-model/README.md):

- [UC-AGOPS-01 Governed closed-loop incident handling](agentic-operations/closed-loop-incident-handling/README.md)
- [UC-AGOPS-05 CNF upgrade pre- and post-checks](agentic-operations/cnf-upgrade-checks/README.md)
- [UC-BIZ-01 Churn risk explanation](business-assurance/churn-risk-explanation/README.md)
- [UC-BIZ-02 Revenue assurance triage](business-assurance/revenue-assurance-triage/README.md)
- [UC-CARE-01 CAMARA customer-care diagnostics](business-assurance/camara-care-diagnostics/README.md)
- [UC-CARE-02 Broadband digital troubleshooting](business-assurance/broadband-digital-troubleshooting/README.md)
- [UC-KNOW-01 Grounded knowledge assistant](standards-knowledge/grounded-knowledge-assistant/README.md)
- [UC-OPS-01 Adaptation ladder on alarm and root-cause triage](network-operations/alarm-triage-adaptation/README.md)
- [UC-OPS-03 Core network root-cause analysis](network-operations/core-network-rca/README.md)
- [UC-OPS-05 RAN energy saving](network-operations/ran-energy-saving/README.md)
- [UC-OPS-06 Slice SLA assurance](network-operations/slice-sla-assurance/README.md)
- [UC-OPS-07 MOP validation](network-operations/mop-validation/README.md)
- [UC-SEC-03 Software onboarding and CVE review](security/software-onboarding-cve-review/README.md)

### PB-11 Bring your own data and policies

These recipes use [the Bring your own data and policies page](../platform/bring-your-own-data/README.md):

- [UC-AGOPS-01 Governed closed-loop incident handling](agentic-operations/closed-loop-incident-handling/README.md)
- [UC-AGOPS-02 Read-only router and 5G core operations](agentic-operations/router-core-read-only-ops/README.md)
- [UC-AGOPS-05 CNF upgrade pre- and post-checks](agentic-operations/cnf-upgrade-checks/README.md)
- [UC-BIZ-01 Churn risk explanation](business-assurance/churn-risk-explanation/README.md)
- [UC-BIZ-02 Revenue assurance triage](business-assurance/revenue-assurance-triage/README.md)
- [UC-CARE-01 CAMARA customer-care diagnostics](business-assurance/camara-care-diagnostics/README.md)
- [UC-CARE-02 Broadband digital troubleshooting](business-assurance/broadband-digital-troubleshooting/README.md)
- [UC-KNOW-01 Grounded knowledge assistant](standards-knowledge/grounded-knowledge-assistant/README.md)
- [UC-KNOW-03 OSS and BSS architecture guidance](standards-knowledge/oss-bss-architecture-guidance/README.md)
- [UC-OPS-01 Adaptation ladder on alarm and root-cause triage](network-operations/alarm-triage-adaptation/README.md)
- [UC-OPS-02 Signalling trace analysis](network-operations/signalling-trace-analysis/README.md)
- [UC-OPS-03 Core network root-cause analysis](network-operations/core-network-rca/README.md)
- [UC-OPS-04 RAN and RF health checks](network-operations/ran-rf-health-checks/README.md)
- [UC-OPS-05 RAN energy saving](network-operations/ran-energy-saving/README.md)
- [UC-OPS-06 Slice SLA assurance](network-operations/slice-sla-assurance/README.md)
- [UC-OPS-07 MOP validation](network-operations/mop-validation/README.md)
- [UC-OPS-08 Transport and IP diagnostics](network-operations/transport-ip-diagnostics/README.md)
- [UC-OPS-09 Cross-domain OSS correlation](network-operations/cross-domain-oss-correlation/README.md)
- [UC-SEC-01 Security alert triage](security/security-triage/README.md)
- [UC-SEC-03 Software onboarding and CVE review](security/software-onboarding-cve-review/README.md)
- [UC-SW-01 RAN and core code assistant](network-software/ran-core-code-assistant/README.md)
- [UC-SW-02 Network automation review](network-software/network-automation-review/README.md)

<!-- generated:catalog-by-platform end -->
