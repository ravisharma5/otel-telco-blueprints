---
type: "reference"
title: "Decision gate"
question: "How does an agent's proposed change become an executed, blocked, or human-approved action?"
doc_status: done
clarity_reviewed: "2026-11-11"
platform_blueprints: ["PB-02", "PB-06", "PB-07"]
otel_slots: ["llm", "decision"]
---

# Decision gate

## At a glance

| Field | Value |
|---|---|
| Question answered | How does an agent's proposed change become an executed, blocked, or human-approved action? |
| Answer | The agent submits an action request, the OTel Decision model labels it, and the automation platform follows the label, then verifies and audits |
| Audience | Architects, platform engineers, and automation teams |
| OTel slots | LLM (the agent) and Decision (the gate) |
| Platform blueprints | PB-02, PB-06, PB-07 |

## The question

How does a step an agent proposes become an executed, blocked, or human-approved action?
Without one gate, every agent decides for itself when to change the network, and nobody can show why a change ran.

## The principle

The agent recommends and the orchestrator decides. The model never holds write credentials.
The gate call that counts runs inside the orchestrator. The agent's own label is advisory, so a prompt-injected agent cannot skip the gate.

## The design

| Component role | Red Hat product used |
|---|---|
| Agent: investigates and submits action requests | Agent harness with the OTel LLM slot on Red Hat AI Inference (vLLM) |
| Gate model: labels each request with label probabilities | OTel Decision slot on Red Hat AI Inference (vLLM), with log probabilities turned on |
| Action layer: applies policy, runs the job, verifies, and audits | Red Hat Ansible Automation Platform with Automation Orchestrator |
| Tool gateway: lets the agent submit requests for its risk class only | MCP gateway in Red Hat Connectivity Link |

Any component can be replaced. The Red Hat products named here show one way to build this design.

### Runtime pattern

1. The agent, an OTel LLM, has read tools, notify tools from the assist stage on, and one action-request tool. It can never execute changes.
2. The OTel Decision model labels each request as LOOK, NOTIFY, REVIEW, ACT, or STOP.
3. AAP, the automation layer, follows the label: it executes, routes REVIEW to a human, or blocks. It then verifies and audits.

Ansible Automation Platform (AAP) is the only part of this design that holds write credentials.

For example, an alarm reports link errors on a router. The agent investigates with read-only tools and proposes to restart interface eth1 on router r2. The Decision model labels the request, and AAP executes the restart, routes it to a human, or blocks it. AAP then checks that the interface is healthy and writes the audit record.

### Policy table

| Label | Who acts | What runs | What is logged |
|---|---|---|---|
| LOOK | The agent | Nothing; the request returns to the agent to keep reading | Request, label probabilities, and the reason |
| NOTIFY | AAP | A notification job, such as a ticket note or an operations-channel message; no state change | Request, label probabilities, and the notification sent |
| REVIEW | A human approver, then AAP | The approved job after sign-off, then verification | Request, label probabilities, approver role, decision, and job result |
| ACT | AAP | The approved job for an approved playbook, then verification and rollback on failure | Request, label probabilities, policy version, job result, and verification result |
| STOP | AAP | Nothing; the step ends and the agent reports what it found | Request, label probabilities, and the reason |

NOTIFY works two ways. From the assist stage up, an agent may hold direct notify tools, such as an operations-channel message or a ticket comment, through the MCP Gateway; the shadow stage gets no notify role. An action request that the gate labels NOTIFY becomes a notification job that AAP runs.

The outcome never exceeds the model label or the policy ceiling for the capability and risk class, and STOP is always allowed. The ceiling follows the [autonomy ceiling](../framework/definitions.md#autonomy-ceiling): inform allows LOOK, notify allows NOTIFY, recommend-with-approval allows REVIEW, and act-within-policy allows ACT.

### How AAP gets the label

| Path | How AAP gets the label | Use it when |
|---|---|---|
| Intended | An Automation Orchestrator workflow calls the Decision model over REST and branches on the label with a conditional node | You run Automation Orchestrator and want the gate, approval, and job in one workflow |
| Fallback | An Ansible job template calls the Decision model with the `uri` module before it executes, and stops unless the label allows the job | You run job templates only, or a playbook needs its own gate |

Both paths re-run the gate on the request. Neither trusts the agent's advisory label.

### Thresholds

| Parameter | What it controls | Who sets it | How to calibrate |
|---|---|---|---|
| Minimum ACT probability | The lowest ACT probability at which AAP may act alone | Risk owner, with subject-matter expert (SME) review | [PB-02 calibration method](../platform/evaluation-acceptance/README.md#false-act-method): fit on an operator gate set labelled by SMEs, and check calibration error |
| REVIEW band | The probability range that sends a request to a human instead of acting or blocking | Risk owner, with SME review | [PB-02 calibration method](../platform/evaluation-acceptance/README.md#false-act-method): set from the calibration curve and the human review load |
| False-ACT budget | How many wrong ACT labels the operator accepts on state-changing requests | Risk owner | [PB-02 calibration method](../platform/evaluation-acceptance/README.md#false-act-method): count false ACT labels on state-changing gate cases, with a set large enough to bound the rate |
| Ceiling per risk class | The highest outcome allowed for read, notify, low-risk write, and high-risk write | Risk owner, with SME review | [PB-02 calibration method](../platform/evaluation-acceptance/README.md#false-act-method): raise a ceiling only after a canary window with no false ACT labels |

This page gives no default values. You set each parameter with SME review and version the set as the policy that `policy_version` names.

### Message examples

An action request from the agent:

```json
{
  "kind": "action_request",
  "schema_version": "1",
  "request_id": "req-0001",
  "correlation_id": "inc-2041",
  "submitted_at": "2026-11-09T10:15:00Z",
  "agent_identity": "noc-triage-agent",
  "capability": "router.restart_interface",
  "risk_class": "write_low",
  "proposed_step": {
    "summary": "Restart interface eth1 on router r2",
    "parameters": {"device": "r2", "interface": "eth1"}
  },
  "evidence_bundle": {
    "observed": [
      "eth1 on r2 shows rising CRC errors since 09:58",
      "Neighbour r3 reports BFD flaps on the r2 link"
    ],
    "conclusion_strength": "correlated",
    "existing_ticket": null,
    "recent_change": null
  },
  "state_changing": true,
  "playbook_id": "pb-interface-restart",
  "advisory_label": "REVIEW"
}
```

The gate decision from AAP:

```json
{
  "kind": "gate_decision",
  "schema_version": "1",
  "decision_id": "dec-0001",
  "request_id": "req-0001",
  "correlation_id": "inc-2041",
  "decided_at": "2026-11-09T10:15:01Z",
  "model_label": "REVIEW",
  "label_probabilities": {"LOOK": 0.05, "NOTIFY": 0.1, "REVIEW": 0.7, "ACT": 0.13, "STOP": 0.02},
  "policy_ceiling": "REVIEW",
  "outcome": "REVIEW",
  "policy_version": "noc-gate-policy-3",
  "model_revision": "decision-slot@rev-a1b2c3",
  "required_approver": "approver",
  "reasons": ["Policy ceiling is REVIEW"]
}
```

Both messages follow the [decision gate schema](https://github.com/ravisharma5/otel-telco-blueprints/blob/main/schemas/decision-gate.schema.json). Consumers check that the label probabilities sum to 1.

## Trade-offs and limits

| Trade-off | What to do |
|---|---|
| Two gate calls, one advisory in the agent and one in the orchestrator, add latency | Keep both: the orchestrator call stops a prompt-injected agent from skipping the gate |
| The gate and tool governance answer different questions | Use the gate to decide whether a step should happen now, and the tool gateway to decide whether an identity may call a tool |
| Label probabilities may not match the operator's traffic | Calibrate on an operator gate set before any ACT ceiling, as the [model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) advises |
| A gate trained only on cases that end in a change learns to act | Weight the gate set toward LOOK, NOTIFY, REVIEW, and STOP cases |

## Used by

- [PB-02 Evaluation and acceptance](../platform/evaluation-acceptance/README.md): the calibration method behind every threshold
- [PB-06](../platform/safety-autonomy-gating/README.md), [PB-07](../platform/action-layer/README.md): gating and the action layer build on this contract
- [Architecture overview](index.md): the investigate-then-act flow this page details
- [Readiness questions](../framework/index.md): the autonomy question this page answers
