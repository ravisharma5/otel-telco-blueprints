---
title: "Recipes"
doc_status: done
clarity_reviewed: "2026-11-15"
---

# Recipes

Pick a recipe by domain, or by a platform blueprint it uses. Each recipe maps an operator use case to OTel model slots and the platform blueprints it depends on.

A full recipe adds a worked example and deploy steps. A catalog entry fits on one page and lists what you must add before production. *Also covers* names the applications a recipe already handles, so they get no page of their own.

The Use cases page shows the same use cases as cards.

<!-- generated:catalog-by-domain start -->

## Standards and knowledge

| Recipe | Topic | Depth | Also covers |
|---|---|---|---|
| [UC-KNOW-01](standards-knowledge/grounded-knowledge-assistant/README.md) | Grounded knowledge assistant | Full recipe | Telecom standards Q&A over documents you hold rights to; Grounded RAG assistants |
| [UC-KNOW-02](standards-knowledge/spec-summarisation/README.md) | Standards and change-request summaries | Catalog entry |  |
| [UC-KNOW-03](standards-knowledge/oss-bss-architecture-guidance/README.md) | OSS and BSS architecture guidance | Catalog entry |  |

## Network software

| Recipe | Topic | Depth | Also covers |
|---|---|---|---|
| [UC-SW-01](network-software/ran-core-code-assistant/README.md) | RAN and core code assistant | Catalog entry |  |
| [UC-SW-02](network-software/network-automation-review/README.md) | Network automation review | Catalog entry |  |
| [UC-SW-03](network-software/oran-ric-xapp-assistant/README.md) | O-RAN RIC xApp assistant | Catalog entry |  |

## Network operations

| Recipe | Topic | Depth | Also covers |
|---|---|---|---|
| [UC-OPS-01](network-operations/alarm-triage-adaptation/README.md) | Adaptation ladder on alarm and root-cause triage | Full recipe | NOC ticket triage |
| [UC-OPS-02](network-operations/signalling-trace-analysis/README.md) | Signalling trace analysis | Catalog entry |  |
| [UC-OPS-03](network-operations/core-network-rca/README.md) | Core network root-cause analysis | Full recipe |  |
| [UC-OPS-04](network-operations/ran-rf-health-checks/README.md) | RAN and RF health checks | Catalog entry |  |
| [UC-OPS-05](network-operations/ran-energy-saving/README.md) | RAN energy saving | Full recipe |  |
| [UC-OPS-06](network-operations/slice-sla-assurance/README.md) | Slice SLA assurance | Full recipe |  |
| [UC-OPS-08](network-operations/transport-ip-diagnostics/README.md) | Transport and IP diagnostics | Catalog entry |  |
| [UC-OPS-09](network-operations/cross-domain-oss-correlation/README.md) | Cross-domain OSS correlation | Catalog entry |  |

## Agentic operations

| Recipe | Topic | Depth | Also covers |
|---|---|---|---|
| [UC-AGOPS-01](agentic-operations/closed-loop-incident-handling/README.md) | Governed closed-loop incident handling | Full recipe | Closed-loop incident handling |
| [UC-AGOPS-02](agentic-operations/router-core-read-only-ops/README.md) | Read-only router and 5G core operations | Catalog entry |  |
| [UC-AGOPS-03](agentic-operations/policy-following-ops-agents/README.md) | Policy-following operations agents | Catalog entry |  |

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
| [UC-SEC-01](security/security-triage/README.md) | Security alert triage | Catalog entry |  |
| [UC-SEC-02](security/signalling-attack-classification/README.md) | Signalling attack classification | Catalog entry |  |

## Research

| Recipe | Topic | Depth | Also covers |
|---|---|---|---|
| [UC-RES-01](research/kpi-rca-reasoning/README.md) | KPI root-cause reasoning | Catalog entry |  |
| [UC-RES-02](research/mobility-failure-analysis/README.md) | 5G mobility failure analysis | Catalog entry |  |

<!-- generated:catalog-by-domain end -->

## By platform blueprint

Find the recipes that use each platform blueprint.

<!-- generated:catalog-by-platform start -->

### PB-01 Intake and model selection

These recipes use [the Intake and model selection page](../platform/intake-model-selection/README.md):

- [UC-AGOPS-01 Governed closed-loop incident handling](agentic-operations/closed-loop-incident-handling/README.md)
- [UC-AGOPS-02 Read-only router and 5G core operations](agentic-operations/router-core-read-only-ops/README.md)
- [UC-AGOPS-03 Policy-following operations agents](agentic-operations/policy-following-ops-agents/README.md)
- [UC-BIZ-01 Churn risk explanation](business-assurance/churn-risk-explanation/README.md)
- [UC-BIZ-02 Revenue assurance triage](business-assurance/revenue-assurance-triage/README.md)
- [UC-CARE-01 CAMARA customer-care diagnostics](business-assurance/camara-care-diagnostics/README.md)
- [UC-CARE-02 Broadband digital troubleshooting](business-assurance/broadband-digital-troubleshooting/README.md)
- [UC-KNOW-01 Grounded knowledge assistant](standards-knowledge/grounded-knowledge-assistant/README.md)
- [UC-KNOW-02 Standards and change-request summaries](standards-knowledge/spec-summarisation/README.md)
- [UC-KNOW-03 OSS and BSS architecture guidance](standards-knowledge/oss-bss-architecture-guidance/README.md)
- [UC-OPS-01 Adaptation ladder on alarm and root-cause triage](network-operations/alarm-triage-adaptation/README.md)
- [UC-OPS-02 Signalling trace analysis](network-operations/signalling-trace-analysis/README.md)
- [UC-OPS-03 Core network root-cause analysis](network-operations/core-network-rca/README.md)
- [UC-OPS-04 RAN and RF health checks](network-operations/ran-rf-health-checks/README.md)
- [UC-OPS-05 RAN energy saving](network-operations/ran-energy-saving/README.md)
- [UC-OPS-06 Slice SLA assurance](network-operations/slice-sla-assurance/README.md)
- [UC-OPS-08 Transport and IP diagnostics](network-operations/transport-ip-diagnostics/README.md)
- [UC-OPS-09 Cross-domain OSS correlation](network-operations/cross-domain-oss-correlation/README.md)
- [UC-RES-01 KPI root-cause reasoning](research/kpi-rca-reasoning/README.md)
- [UC-RES-02 5G mobility failure analysis](research/mobility-failure-analysis/README.md)
- [UC-SEC-01 Security alert triage](security/security-triage/README.md)
- [UC-SEC-02 Signalling attack classification](security/signalling-attack-classification/README.md)
- [UC-SW-01 RAN and core code assistant](network-software/ran-core-code-assistant/README.md)
- [UC-SW-02 Network automation review](network-software/network-automation-review/README.md)
- [UC-SW-03 O-RAN RIC xApp assistant](network-software/oran-ric-xapp-assistant/README.md)

### PB-02 Evaluation and acceptance

These recipes use [the Evaluation and acceptance page](../platform/evaluation-acceptance/README.md):

- [UC-AGOPS-01 Governed closed-loop incident handling](agentic-operations/closed-loop-incident-handling/README.md)
- [UC-AGOPS-02 Read-only router and 5G core operations](agentic-operations/router-core-read-only-ops/README.md)
- [UC-AGOPS-03 Policy-following operations agents](agentic-operations/policy-following-ops-agents/README.md)
- [UC-BIZ-01 Churn risk explanation](business-assurance/churn-risk-explanation/README.md)
- [UC-BIZ-02 Revenue assurance triage](business-assurance/revenue-assurance-triage/README.md)
- [UC-CARE-01 CAMARA customer-care diagnostics](business-assurance/camara-care-diagnostics/README.md)
- [UC-CARE-02 Broadband digital troubleshooting](business-assurance/broadband-digital-troubleshooting/README.md)
- [UC-KNOW-01 Grounded knowledge assistant](standards-knowledge/grounded-knowledge-assistant/README.md)
- [UC-KNOW-02 Standards and change-request summaries](standards-knowledge/spec-summarisation/README.md)
- [UC-KNOW-03 OSS and BSS architecture guidance](standards-knowledge/oss-bss-architecture-guidance/README.md)
- [UC-OPS-01 Adaptation ladder on alarm and root-cause triage](network-operations/alarm-triage-adaptation/README.md)
- [UC-OPS-02 Signalling trace analysis](network-operations/signalling-trace-analysis/README.md)
- [UC-OPS-03 Core network root-cause analysis](network-operations/core-network-rca/README.md)
- [UC-OPS-04 RAN and RF health checks](network-operations/ran-rf-health-checks/README.md)
- [UC-OPS-05 RAN energy saving](network-operations/ran-energy-saving/README.md)
- [UC-OPS-06 Slice SLA assurance](network-operations/slice-sla-assurance/README.md)
- [UC-OPS-08 Transport and IP diagnostics](network-operations/transport-ip-diagnostics/README.md)
- [UC-OPS-09 Cross-domain OSS correlation](network-operations/cross-domain-oss-correlation/README.md)
- [UC-RES-01 KPI root-cause reasoning](research/kpi-rca-reasoning/README.md)
- [UC-RES-02 5G mobility failure analysis](research/mobility-failure-analysis/README.md)
- [UC-SEC-01 Security alert triage](security/security-triage/README.md)
- [UC-SEC-02 Signalling attack classification](security/signalling-attack-classification/README.md)
- [UC-SW-01 RAN and core code assistant](network-software/ran-core-code-assistant/README.md)
- [UC-SW-02 Network automation review](network-software/network-automation-review/README.md)
- [UC-SW-03 O-RAN RIC xApp assistant](network-software/oran-ric-xapp-assistant/README.md)

### PB-03 Adaptation

These recipes use [the Adaptation page](../platform/adaptation/README.md):

- [UC-OPS-01 Adaptation ladder on alarm and root-cause triage](network-operations/alarm-triage-adaptation/README.md)
- [UC-OPS-02 Signalling trace analysis](network-operations/signalling-trace-analysis/README.md)
- [UC-OPS-03 Core network root-cause analysis](network-operations/core-network-rca/README.md)
- [UC-OPS-04 RAN and RF health checks](network-operations/ran-rf-health-checks/README.md)
- [UC-OPS-09 Cross-domain OSS correlation](network-operations/cross-domain-oss-correlation/README.md)
- [UC-RES-01 KPI root-cause reasoning](research/kpi-rca-reasoning/README.md)
- [UC-SEC-01 Security alert triage](security/security-triage/README.md)
- [UC-SEC-02 Signalling attack classification](security/signalling-attack-classification/README.md)
- [UC-SW-01 RAN and core code assistant](network-software/ran-core-code-assistant/README.md)

### PB-04 Serving, routing, and placement

These recipes use [the Serving, routing, and placement page](../platform/serving-routing-placement/README.md):

- [UC-AGOPS-01 Governed closed-loop incident handling](agentic-operations/closed-loop-incident-handling/README.md)
- [UC-AGOPS-02 Read-only router and 5G core operations](agentic-operations/router-core-read-only-ops/README.md)
- [UC-AGOPS-03 Policy-following operations agents](agentic-operations/policy-following-ops-agents/README.md)
- [UC-BIZ-01 Churn risk explanation](business-assurance/churn-risk-explanation/README.md)
- [UC-BIZ-02 Revenue assurance triage](business-assurance/revenue-assurance-triage/README.md)
- [UC-CARE-01 CAMARA customer-care diagnostics](business-assurance/camara-care-diagnostics/README.md)
- [UC-CARE-02 Broadband digital troubleshooting](business-assurance/broadband-digital-troubleshooting/README.md)
- [UC-KNOW-01 Grounded knowledge assistant](standards-knowledge/grounded-knowledge-assistant/README.md)
- [UC-KNOW-02 Standards and change-request summaries](standards-knowledge/spec-summarisation/README.md)
- [UC-KNOW-03 OSS and BSS architecture guidance](standards-knowledge/oss-bss-architecture-guidance/README.md)
- [UC-OPS-01 Adaptation ladder on alarm and root-cause triage](network-operations/alarm-triage-adaptation/README.md)
- [UC-OPS-02 Signalling trace analysis](network-operations/signalling-trace-analysis/README.md)
- [UC-OPS-03 Core network root-cause analysis](network-operations/core-network-rca/README.md)
- [UC-OPS-04 RAN and RF health checks](network-operations/ran-rf-health-checks/README.md)
- [UC-OPS-05 RAN energy saving](network-operations/ran-energy-saving/README.md)
- [UC-OPS-06 Slice SLA assurance](network-operations/slice-sla-assurance/README.md)
- [UC-OPS-08 Transport and IP diagnostics](network-operations/transport-ip-diagnostics/README.md)
- [UC-OPS-09 Cross-domain OSS correlation](network-operations/cross-domain-oss-correlation/README.md)
- [UC-RES-01 KPI root-cause reasoning](research/kpi-rca-reasoning/README.md)
- [UC-RES-02 5G mobility failure analysis](research/mobility-failure-analysis/README.md)
- [UC-SEC-01 Security alert triage](security/security-triage/README.md)
- [UC-SEC-02 Signalling attack classification](security/signalling-attack-classification/README.md)
- [UC-SW-01 RAN and core code assistant](network-software/ran-core-code-assistant/README.md)
- [UC-SW-02 Network automation review](network-software/network-automation-review/README.md)
- [UC-SW-03 O-RAN RIC xApp assistant](network-software/oran-ric-xapp-assistant/README.md)

### PB-05 Integration

These recipes use [the Integration page](../platform/integration/README.md):

- [UC-AGOPS-01 Governed closed-loop incident handling](agentic-operations/closed-loop-incident-handling/README.md)
- [UC-AGOPS-02 Read-only router and 5G core operations](agentic-operations/router-core-read-only-ops/README.md)
- [UC-AGOPS-03 Policy-following operations agents](agentic-operations/policy-following-ops-agents/README.md)
- [UC-BIZ-01 Churn risk explanation](business-assurance/churn-risk-explanation/README.md)
- [UC-BIZ-02 Revenue assurance triage](business-assurance/revenue-assurance-triage/README.md)
- [UC-CARE-01 CAMARA customer-care diagnostics](business-assurance/camara-care-diagnostics/README.md)
- [UC-CARE-02 Broadband digital troubleshooting](business-assurance/broadband-digital-troubleshooting/README.md)
- [UC-KNOW-01 Grounded knowledge assistant](standards-knowledge/grounded-knowledge-assistant/README.md)
- [UC-KNOW-02 Standards and change-request summaries](standards-knowledge/spec-summarisation/README.md)
- [UC-KNOW-03 OSS and BSS architecture guidance](standards-knowledge/oss-bss-architecture-guidance/README.md)
- [UC-OPS-01 Adaptation ladder on alarm and root-cause triage](network-operations/alarm-triage-adaptation/README.md)
- [UC-OPS-02 Signalling trace analysis](network-operations/signalling-trace-analysis/README.md)
- [UC-OPS-03 Core network root-cause analysis](network-operations/core-network-rca/README.md)
- [UC-OPS-04 RAN and RF health checks](network-operations/ran-rf-health-checks/README.md)
- [UC-OPS-05 RAN energy saving](network-operations/ran-energy-saving/README.md)
- [UC-OPS-06 Slice SLA assurance](network-operations/slice-sla-assurance/README.md)
- [UC-OPS-08 Transport and IP diagnostics](network-operations/transport-ip-diagnostics/README.md)
- [UC-OPS-09 Cross-domain OSS correlation](network-operations/cross-domain-oss-correlation/README.md)
- [UC-RES-02 5G mobility failure analysis](research/mobility-failure-analysis/README.md)
- [UC-SEC-01 Security alert triage](security/security-triage/README.md)
- [UC-SW-01 RAN and core code assistant](network-software/ran-core-code-assistant/README.md)
- [UC-SW-02 Network automation review](network-software/network-automation-review/README.md)
- [UC-SW-03 O-RAN RIC xApp assistant](network-software/oran-ric-xapp-assistant/README.md)

### PB-06 Safety and autonomy gating

These recipes use [the Safety and autonomy gating page](../platform/safety-autonomy-gating/README.md):

- [UC-AGOPS-01 Governed closed-loop incident handling](agentic-operations/closed-loop-incident-handling/README.md)
- [UC-AGOPS-02 Read-only router and 5G core operations](agentic-operations/router-core-read-only-ops/README.md)
- [UC-AGOPS-03 Policy-following operations agents](agentic-operations/policy-following-ops-agents/README.md)
- [UC-BIZ-01 Churn risk explanation](business-assurance/churn-risk-explanation/README.md)
- [UC-BIZ-02 Revenue assurance triage](business-assurance/revenue-assurance-triage/README.md)
- [UC-CARE-01 CAMARA customer-care diagnostics](business-assurance/camara-care-diagnostics/README.md)
- [UC-CARE-02 Broadband digital troubleshooting](business-assurance/broadband-digital-troubleshooting/README.md)
- [UC-KNOW-01 Grounded knowledge assistant](standards-knowledge/grounded-knowledge-assistant/README.md)
- [UC-KNOW-02 Standards and change-request summaries](standards-knowledge/spec-summarisation/README.md)
- [UC-KNOW-03 OSS and BSS architecture guidance](standards-knowledge/oss-bss-architecture-guidance/README.md)
- [UC-OPS-01 Adaptation ladder on alarm and root-cause triage](network-operations/alarm-triage-adaptation/README.md)
- [UC-OPS-02 Signalling trace analysis](network-operations/signalling-trace-analysis/README.md)
- [UC-OPS-03 Core network root-cause analysis](network-operations/core-network-rca/README.md)
- [UC-OPS-04 RAN and RF health checks](network-operations/ran-rf-health-checks/README.md)
- [UC-OPS-05 RAN energy saving](network-operations/ran-energy-saving/README.md)
- [UC-OPS-06 Slice SLA assurance](network-operations/slice-sla-assurance/README.md)
- [UC-OPS-08 Transport and IP diagnostics](network-operations/transport-ip-diagnostics/README.md)
- [UC-OPS-09 Cross-domain OSS correlation](network-operations/cross-domain-oss-correlation/README.md)
- [UC-RES-01 KPI root-cause reasoning](research/kpi-rca-reasoning/README.md)
- [UC-RES-02 5G mobility failure analysis](research/mobility-failure-analysis/README.md)
- [UC-SEC-01 Security alert triage](security/security-triage/README.md)
- [UC-SEC-02 Signalling attack classification](security/signalling-attack-classification/README.md)
- [UC-SW-01 RAN and core code assistant](network-software/ran-core-code-assistant/README.md)
- [UC-SW-02 Network automation review](network-software/network-automation-review/README.md)
- [UC-SW-03 O-RAN RIC xApp assistant](network-software/oran-ric-xapp-assistant/README.md)

### PB-07 Action layer

These recipes use [the Action layer page](../platform/action-layer/README.md):

- [UC-AGOPS-01 Governed closed-loop incident handling](agentic-operations/closed-loop-incident-handling/README.md)
- [UC-AGOPS-03 Policy-following operations agents](agentic-operations/policy-following-ops-agents/README.md)
- [UC-BIZ-02 Revenue assurance triage](business-assurance/revenue-assurance-triage/README.md)
- [UC-CARE-01 CAMARA customer-care diagnostics](business-assurance/camara-care-diagnostics/README.md)
- [UC-OPS-01 Adaptation ladder on alarm and root-cause triage](network-operations/alarm-triage-adaptation/README.md)
- [UC-OPS-03 Core network root-cause analysis](network-operations/core-network-rca/README.md)
- [UC-OPS-04 RAN and RF health checks](network-operations/ran-rf-health-checks/README.md)
- [UC-OPS-05 RAN energy saving](network-operations/ran-energy-saving/README.md)
- [UC-OPS-06 Slice SLA assurance](network-operations/slice-sla-assurance/README.md)
- [UC-OPS-08 Transport and IP diagnostics](network-operations/transport-ip-diagnostics/README.md)
- [UC-OPS-09 Cross-domain OSS correlation](network-operations/cross-domain-oss-correlation/README.md)
- [UC-RES-01 KPI root-cause reasoning](research/kpi-rca-reasoning/README.md)
- [UC-SW-02 Network automation review](network-software/network-automation-review/README.md)

### PB-08 Security, identity, and sandbox

These recipes use [the Security, identity, and sandbox page](../platform/security-identity-sandbox/README.md):

- [UC-AGOPS-01 Governed closed-loop incident handling](agentic-operations/closed-loop-incident-handling/README.md)
- [UC-AGOPS-02 Read-only router and 5G core operations](agentic-operations/router-core-read-only-ops/README.md)
- [UC-AGOPS-03 Policy-following operations agents](agentic-operations/policy-following-ops-agents/README.md)
- [UC-CARE-01 CAMARA customer-care diagnostics](business-assurance/camara-care-diagnostics/README.md)
- [UC-OPS-03 Core network root-cause analysis](network-operations/core-network-rca/README.md)
- [UC-OPS-05 RAN energy saving](network-operations/ran-energy-saving/README.md)
- [UC-OPS-06 Slice SLA assurance](network-operations/slice-sla-assurance/README.md)
- [UC-SEC-01 Security alert triage](security/security-triage/README.md)
- [UC-SEC-02 Signalling attack classification](security/signalling-attack-classification/README.md)
- [UC-SW-02 Network automation review](network-software/network-automation-review/README.md)

### PB-09 Quality operations and observability

These recipes use [the Quality operations and observability page](../platform/quality-operations/README.md):

- [UC-AGOPS-01 Governed closed-loop incident handling](agentic-operations/closed-loop-incident-handling/README.md)
- [UC-AGOPS-02 Read-only router and 5G core operations](agentic-operations/router-core-read-only-ops/README.md)
- [UC-AGOPS-03 Policy-following operations agents](agentic-operations/policy-following-ops-agents/README.md)
- [UC-CARE-01 CAMARA customer-care diagnostics](business-assurance/camara-care-diagnostics/README.md)
- [UC-KNOW-01 Grounded knowledge assistant](standards-knowledge/grounded-knowledge-assistant/README.md)
- [UC-KNOW-02 Standards and change-request summaries](standards-knowledge/spec-summarisation/README.md)
- [UC-KNOW-03 OSS and BSS architecture guidance](standards-knowledge/oss-bss-architecture-guidance/README.md)
- [UC-OPS-02 Signalling trace analysis](network-operations/signalling-trace-analysis/README.md)
- [UC-OPS-03 Core network root-cause analysis](network-operations/core-network-rca/README.md)
- [UC-OPS-05 RAN energy saving](network-operations/ran-energy-saving/README.md)
- [UC-OPS-06 Slice SLA assurance](network-operations/slice-sla-assurance/README.md)
- [UC-OPS-09 Cross-domain OSS correlation](network-operations/cross-domain-oss-correlation/README.md)
- [UC-SEC-01 Security alert triage](security/security-triage/README.md)

### PB-10 Compliance, sovereignty, and operating model

These recipes use [the Compliance, sovereignty, and operating model page](../platform/compliance-operating-model/README.md):

- [UC-AGOPS-01 Governed closed-loop incident handling](agentic-operations/closed-loop-incident-handling/README.md)
- [UC-BIZ-01 Churn risk explanation](business-assurance/churn-risk-explanation/README.md)
- [UC-BIZ-02 Revenue assurance triage](business-assurance/revenue-assurance-triage/README.md)
- [UC-CARE-01 CAMARA customer-care diagnostics](business-assurance/camara-care-diagnostics/README.md)
- [UC-CARE-02 Broadband digital troubleshooting](business-assurance/broadband-digital-troubleshooting/README.md)
- [UC-KNOW-01 Grounded knowledge assistant](standards-knowledge/grounded-knowledge-assistant/README.md)
- [UC-KNOW-02 Standards and change-request summaries](standards-knowledge/spec-summarisation/README.md)
- [UC-OPS-01 Adaptation ladder on alarm and root-cause triage](network-operations/alarm-triage-adaptation/README.md)
- [UC-OPS-03 Core network root-cause analysis](network-operations/core-network-rca/README.md)
- [UC-OPS-05 RAN energy saving](network-operations/ran-energy-saving/README.md)
- [UC-OPS-06 Slice SLA assurance](network-operations/slice-sla-assurance/README.md)

<!-- generated:catalog-by-platform end -->
