---
id: "PB-04"
type: "platform"
title: "Serving, routing, and placement"
readiness_question: "Serving and placement: where and how does each slot run?"
doc_status: done
layers: ["model-endpoint-inferencing", "ai-gateway", "placement"]
table1_rows: [6, 7, 8, 9, 10]
extension_rows: ["E7"]
otel_slots: ["llm", "embedding", "reranker", "safety", "decision", "classification"]
placement_tier: ["far-edge", "regional", "core"]
one_liner: "Sizes, serves, routes, and places every OTel slot from the far edge to the core. Depends on a front door, the Decision slot for content routing, and a replica scheduler."
top_decisions:
  - "Pick a hardware class and precision for each slot"
  - "Keep the front door, content routing, and replica scheduling separate"
  - "Pick a serving option for each tier"
agent_school: [104, 203]
clarity_reviewed: "2026-11-10"
---

<!-- Writing rules: framework/style-guide.md. Name each component by its role and the Red Hat product used. Write no product support status. -->

# Serving, routing, and placement

## At a glance

| Field | Value |
|---|---|
| One-liner | Sizes, serves, routes, and places every OTel slot from the far edge to the core. Depends on a front door, the Decision slot for content routing, and a replica scheduler. |
| Question answered | Serving and placement: where and how does each slot run? |
| Audience | Platform engineers and architects |
| OTel slots | All six slots, LLM, Embedding, Reranker, Safety, Decision, and Classification |
| Placement tier | Far edge, regional, and core |
| Top 3 decisions | Pick a hardware class and precision for each slot; keep the front door, content routing, and replica scheduling separate; pick a serving option for each tier |
| Agent-school courses | 104 and 203 in the [agent-school roadmap](https://github.com/open-experiments/agent-school/blob/main/docs/RoadMap.md) |

## The operator question

Where and how does each OTel slot run: on what hardware, at what precision, on which tier, and behind which routing?
Until you answer it, slots get sized by guesswork, and the gateway, the app, and the scheduler each make routing choices that belong to another layer.

## Decisions you must make

| Decision | Options | Recommendation | Because |
|---|---|---|---|
| Pick a hardware class and precision for each slot | Full precision (bf16); FP8; W4A16 | bf16 for the large LLM at the core; FP8 for the large LLM at a regional site; W4A16 for the Decision slot | The 31B needs about 62.6 GB in bf16 ([model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT)), and the Decision model ships only as W4A16 ([model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit)) |
| Keep the front door, content routing, and replica scheduling separate | One component does all three; three layers | Three layers: the front door decides access and tokens, the app calling the Decision slot picks the slot, and the replica scheduler picks the pod | The front door has no content-aware routing, and the replica scheduler works inside one model's pool ([OpenShift AI release notes](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/release_notes/new-features-and-enhancements_relnotes)) |
| Pick a serving option for each tier | Replica scheduler; one KServe service per slot; one model per box | Replica scheduler for generative slots at the core; one KServe service per slot at a regional site; one model per box at the far edge | Each tier has different limits; see [Edge options and limits](#edge-options-and-limits) |
| Set priority between interactive and batch traffic | One queue; priority bands | Priority bands, with interactive triage ahead of batch evaluation and data generation | Batch jobs on the same pool must never starve NOC traffic ([OpenShift AI release notes](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/release_notes/new-features-and-enhancements_relnotes)) |
| Add a semantic router in front of the replica scheduler | Decision slot only; semantic router as well | Decision slot only; try a semantic router in a pilot, as agent-school 203 does | A semantic router's classifiers need telecom tuning, and the Decision slot already returns label probabilities you can threshold |

## Reference design

```mermaid
flowchart LR
    caller["Caller chooses the tier"] --> edge["Far-edge box: one model"]
    caller --> gateway["AI Gateway front door: access and token limits"]
    gateway --> routing["Decision slot content routing: picks the slot"]
    routing --> regional["Regional slots: Classification, Safety, small LLM, Embedding, Reranker"]
    routing --> scheduler["Replica scheduler: picks the pod"]
    scheduler --> core["Core pool: large LLM replicas"]
```

1. The caller picks the tier: a far-edge box, the regional site, or the core. None of the routing layers below makes this choice.
2. The front door checks the caller's API key against a subscription, applies that team's token limit, and routes on the `model` field in the request body.
3. The app asks the Decision slot about the request and reads its label probabilities. It compares them with your thresholds and picks the slot: a small LLM, the large LLM, the abstain path, or STOP.
4. For a generative slot at the core, the replica scheduler picks the pod by prefix-cache hits, KV cache use, and queue depth, and serves interactive traffic before batch.
5. The chosen slot answers. The app records the slot, the model revision, and the Decision probabilities with the request.

### Three routing layers

| Layer | Decides | Signals | Product used |
|---|---|---|---|
| Front door | Who may call which model name, and how many tokens | API key mapped to a subscription, OIDC groups, the `model` field in the body, per-model token limits | Models-as-a-Service in Red Hat OpenShift AI (needs PostgreSQL) |
| Content routing | Which slot handles the request: small LLM, large LLM, abstain path, or STOP | Decision label probabilities against your thresholds; an explicit caller override | Your app or agent runtime calling the OTel Decision slot |
| Replica scheduling | Which pod of the chosen model's pool serves it | Prefix-cache hits, KV cache use, queue depth; priority bands set in an `InferenceObjective`; a weighted canary for a new revision | Distributed Inference with llm-d in Red Hat OpenShift AI, for generative slots at the core |

None of these layers picks the tier. llm-d schedules within one cluster, so the caller, or multi-cluster DNS policy, picks far edge, regional, or core, as the [placement tiers](../../architecture/placement.md) page sets out.

### Sizing by hardware class

The figures cover weights only. The KV cache comes on top, so leave headroom for your context length and concurrency.

| Slot | Precision | Weights | Hardware class |
|---|---|---|---|
| LLM 31B | bf16 | about 62.6 GB | Single large GPU with about 141 GB or more, or a Multi-GPU core node with two GPUs of about 80 GB in tensor parallel |
| LLM 31B, operator-made build | FP8 W8A8 | about 33 GB | Single large GPU (about 80 GB or more); Small edge GPU at the 48 GB end, with less room for KV cache |
| Decision 26B-A4B | W4A16 | about 17 GB | Small edge GPU (about 24 to 48 GB), tight at 24 GB; Single large GPU for high concurrency |
| Safety 12B | bf16 | about 24 GB | Small edge GPU at the 48 GB end, or Single large GPU |
| Classification 8.3B | bf16 or FP8 | about 17 GB in bf16, about 8.5 GB in FP8 | Small edge GPU (about 24 to 48 GB) |
| Embedding and Reranker, 0.6B to 8B | bf16 | about 1.2 to 16 GB | Small edge GPU, or a slice of a Single large GPU |
| Small Embedding models up to 335M | bf16 or fp32 | under 1.5 GB | CPU |

Safety and Classification figures assume about 2 bytes per parameter in bf16. The 31B FP8 figure comes from the FP8 build of its base model.

### Edge options and limits

| Option | Tier | Limits | Source |
|---|---|---|---|
| RHEL with Podman running Red Hat AI Inference | Far edge | One container per model; no Kubernetes API, front door, or replica scheduler on the box | [Red Hat AI Inference release notes](https://docs.redhat.com/en/documentation/red_hat_ai_inference/3.5/html/release_notes/rhaii-350-ga-release-notes_release-notes) |
| Red Hat Device Edge (MicroShift) with KServe | Far edge | Runs only one AI model per deployment; `x86_64` only; ModelCar images only; raw deployment | [MicroShift AI models](https://docs.redhat.com/en/documentation/red_hat_build_of_microshift/4.22/html/using_ai_models/microshift-rh-openshift-ai) |
| Single-node OpenShift with Red Hat OpenShift AI | Regional | The node needs at least 32 CPU cores and 128 GiB of RAM; run one KServe service per slot | [OpenShift AI install](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/installing_and_uninstalling_openshift_ai_self-managed/installing-and-deploying-openshift-ai_install) |
| Distributed Inference with llm-d | Core | Multi-node OpenShift 4.20 or later; an `amd64` node for the tokenizer; schedules within one cluster | [llm-d components](https://access.redhat.com/articles/7136620) |

### Hardware prerequisites

These failures are silent: the endpoint answers, but the output or the build is wrong.

| Hardware or build | Prerequisite | Source |
|---|---|---|
| AMD MI350-class GPUs (gfx950) serving the 31B | Set `VLLM_ROCM_USE_AITER=0`, or the model can return malformed text while still answering HTTP 200. `VLLM_ROCM_USE_AITER_MOE=0` is no substitute | [31B model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT) |
| NVIDIA Blackwell (compute capability 10.0 and newer) | No INT8 W8A8 kernels; use FP8 or NVFP4 instead | [vLLM INT8 W8A8](https://docs.vllm.ai/en/latest/features/quantization/llm_compressor/int8_w8a8/) |
| NVIDIA Ampere | No FP8 W8A8; use W8A16 or W4A16 instead | [vLLM quantization](https://docs.vllm.ai/en/stable/features/quantization/) |
| Decision slot (Gemma 4 MoE) on ROCm with the Red Hat AI Inference build of vLLM 0.24 | Add `--moe-backend triton` | [Red Hat AI Inference release notes](https://docs.redhat.com/en/documentation/red_hat_ai_inference/3.5/html/release_notes/rhaii-350-ga-release-notes_release-notes) |
| Gemma 4 with image input on H100 or H200 with the Red Hat AI Inference build of vLLM 0.24 | Add `--attention-backend TRITON_ATTN`; text-only serving avoids the issue | [Red Hat AI Inference release notes](https://docs.redhat.com/en/documentation/red_hat_ai_inference/3.5/html/release_notes/rhaii-350-ga-release-notes_release-notes) |
| Decision slot engine | vLLM 0.26 or later on CUDA, or 0.30 or later on ROCm | [Decision model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) |
| Decision MoE kernels | Results are not bit-deterministic; expect small run-to-run variation on low-margin cases and keep thresholds clear of it | [Decision model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) |
| Any 31B deployment | Ask the model to identify itself after deploy; it should answer as OTel 2.0, because HTTP 200 alone does not show the deployment is correct | [31B model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT) |

### Key flags per slot

```text
# LLM 31B (pin the revision; text-only; tool calling)
--revision <sha> --enable-auto-tool-choice --tool-call-parser gemma4 \
--limit-mm-per-prompt '{"image": 0, "audio": 0}'
# Decision (card recipe)
--revision <sha> --max-logprobs 64 --enable-prefix-caching --max-model-len 16384
# Classification (Gemma3TextForSequenceClassification) and Reranker (num_labels=1)
--runner pooling --convert classify        # endpoints /classify, /v1/score, /rerank
# Embedding
--runner pooling --convert embed           # endpoint /v1/embeddings
# Static LoRA only (never runtime hot-load)
--enable-lora --lora-modules <name>=<path> --max-loras <n> --max-lora-rank <r>
```

Load adapters only at start, pinned by digest. Never enable runtime adapter loading: block `VLLM_ALLOW_RUNTIME_LORA_UPDATING` by policy, as the [LoRA backdoor article](https://developers.redhat.com/articles/2026/09/02/lora-backdoor-threat-how-openshift-ai-mitigates-risk) recommends.

### Worked example: alarm and root-cause triage

Rising CRC errors and BFD flaps on router r2 open incident `inc-2041`, and `noc-triage-agent` starts triage at the regional site. That site runs single-node OpenShift with one large GPU and serves Classification for the root-cause label, Decision for the gate and content routing, Safety, a small LLM, and Embedding and Reranker for local retrieval.

When the shift lead asks for a written explanation, the Decision slot routes the request to the 31B at the core, behind the replica scheduler. The front door gives the NOC triage team its own subscription and token limit, and the triage priority band ranks ahead of batch evaluation on the same pool. The [decision gate](../../architecture/decision-gate.md) page covers the gate itself.

- Config artifact: serving runtime config for each slot with its key flags and pinned revision
- Config artifact: front-door subscription and token limit for each team, such as the NOC triage team
- Config artifact: priority objective that ranks interactive triage ahead of batch evaluation
- Config artifact: pinned revision record in the model registry for every checkpoint and quantized build

## Components

| Component role | Red Hat product used |
|---|---|
| Front door for API keys, subscriptions, token limits, and body-based model routing | Models-as-a-Service in Red Hat OpenShift AI |
| Inference engine for every slot | Red Hat AI Inference (vLLM) |
| Replica scheduling and priority bands for generative slots at the core | Distributed Inference with llm-d in Red Hat OpenShift AI |
| Per-slot serving at regional sites and for pooling slots | KServe in Red Hat OpenShift AI |
| Regional closed-loop platform | Single-node OpenShift with Red Hat OpenShift AI |
| Far-edge runtime | RHEL with Podman, or Red Hat Device Edge |
| Quantized builds (FP8, W4A16, NVFP4) | Red Hat AI Model Optimization Toolkit |
| Model storage and revision records | Model registry in Red Hat OpenShift AI with ModelCar images |

Any component can be replaced. The Red Hat products named here show one way to build this design.

## OTel slot guidance

| Slot | Candidate checkpoints | Notes |
|---|---|---|
| `llm` | OTel-2.0-LLM-31B-IT for explanations, and a 1B to 14B OTel LLM as the small LLM, pinned by revision | Serve the 31B text-only with the `gemma4` tool parser. Use an FP8 build at regional sites after it passes your acceptance suite |
| `decision` | OTel-2.0-Decision-26B-A4B-4bit, pinned by revision | The card targets vLLM 0.26 (CUDA) or 0.30 (ROCm). The current Red Hat AI Inference release ships vLLM 0.24, so run the Decision slot under KServe on an engine at 0.26 or later, such as a Red Hat AI Inference fast release. Call `/v1/chat/completions` with log probabilities; the card's `/v1/systemone` endpoint needs a nightly build |
| `classification` | OTel-LLM-8.3B-Classification, pinned by revision | Serve with the pooling runner and `--convert classify` |
| `safety` | OTel-LLM-12B-Safety or OTel-LLM-8.3B-Safety, pinned by revision | Generative; size at about 2 bytes per parameter in bf16 |
| `embedding` | OTel-Embedding models from 22M to 8B, pinned by revision | Models up to 335M run on CPU. Changing the model forces a full re-index of every vector store built with it |
| `reranker` | OTel-Reranker-0.6B or OTel-Reranker-4B, pinned by revision | These are Qwen3 LLM fine-tunes with a one-label head, not Qwen3-Reranker. Compare their vLLM `/rerank` scores against `sentence-transformers` scores on held-out pairs before use |

## Sources and acceptance

Each key claim links its source, as set out in [the Sources table](../../framework/definitions.md#sources-table).

| # | Claim | Basis | Source |
|---|---|---|---|
| 1 | The 31B needs about 62.6 GB for bf16 weights; pin a revision because weights may change | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT) |
| 2 | On MI350-class GPUs the 31B needs `VLLM_ROCM_USE_AITER=0`, and HTTP 200 alone does not show a correct deployment | model card | [OTel-2.0-LLM-31B-IT model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT) |
| 3 | The Decision model ships as W4A16 at about 17 GB, targets vLLM 0.26 (CUDA) or 0.30 (ROCm), and its label probabilities serve as routing thresholds | model card | [OTel-2.0-Decision-26B-A4B-4bit model card](https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit) |
| 4 | An FP8 build of the base Gemma 4 31B is about 33 GB | model card | [gemma-4-31B-it-FP8-dynamic model card](https://huggingface.co/RedHatAI/gemma-4-31B-it-FP8-dynamic) |
| 5 | The OTel rerankers are Qwen3 LLM fine-tunes with a one-label head | model card | [OTel-Reranker-4B model card](https://huggingface.co/farbodtavakkoli/OTel-Reranker-4B) |
| 6 | Gemma 4 uses the `gemma4` tool parser, and image and audio inputs can be turned off | project documentation | [vLLM Gemma 4 recipe](https://docs.vllm.ai/projects/recipes/en/latest/Google/Gemma4.html) |
| 7 | Pooling models serve embeddings, classification, and scores through `--runner pooling` and `--convert` | project documentation | [vLLM pooling models](https://docs.vllm.ai/en/latest/models/pooling_models/) |
| 8 | INT8 W8A8 has no kernels on compute capability 10.0 and newer, and FP8 W8A8 needs Ada, Hopper, or AMD | project documentation | [vLLM quantization](https://docs.vllm.ai/en/stable/features/quantization/) |
| 9 | The front door routes on the request body and enforces per-subscription token limits; llm-d adds priority bands and weighted canary rollout | Red Hat guidance | [OpenShift AI release notes](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/release_notes/new-features-and-enhancements_relnotes) |
| 10 | The current Red Hat AI Inference release ships vLLM 0.24, offers fast releases between its stable releases, and needs the MoE and attention flags in the hardware prerequisites | Red Hat guidance | [Red Hat AI Inference release notes](https://docs.redhat.com/en/documentation/red_hat_ai_inference/3.5/html/release_notes/rhaii-350-ga-release-notes_release-notes) |
| 11 | llm-d needs OpenShift 4.20 or later and an `amd64` node for the tokenizer | Red Hat guidance | [llm-d components](https://access.redhat.com/articles/7136620) |
| 12 | MicroShift runs one AI model per deployment, on `x86_64` only, from ModelCar images | Red Hat guidance | [MicroShift AI models](https://docs.redhat.com/en/documentation/red_hat_build_of_microshift/4.22/html/using_ai_models/microshift-rh-openshift-ai) |
| 13 | OpenShift AI on single-node OpenShift needs at least 32 CPU cores and 128 GiB of RAM | Red Hat guidance | [OpenShift AI install](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/installing_and_uninstalling_openshift_ai_self-managed/installing-and-deploying-openshift-ai_install) |
| 14 | Block runtime adapter loading and pin adapters by digest | Red Hat guidance | [LoRA backdoor article](https://developers.redhat.com/articles/2026/09/02/lora-backdoor-threat-how-openshift-ai-mitigates-risk) |

- Gate: after every deploy, ask each generative slot to identify itself, and fail the rollout if the answer is wrong or empty.
- Gate: on MI350-class GPUs, confirm the pod sets `VLLM_ROCM_USE_AITER=0` and that a fixed prompt returns well-formed text before traffic arrives.
- Gate: every quantized build passes your operator acceptance suite (PB-02) before you place it at a regional site.
- Gate: reranker scores from the serving engine match `sentence-transformers` scores on your held-out pairs before the reranker serves retrieval.
- Gate: the deployed revision of every slot matches the revision record in the model registry.

## Operating model

| Activity | Responsible | Accountable | Consulted | Informed |
|---|---|---|---|---|
| Size and place each slot | Platform engineer | Model owner | NOC lead | Operator risk owner |
| Set front-door subscriptions and token limits | Platform engineer | NOC lead | Model owner | Operator risk owner |
| Set Decision routing thresholds | Model owner | NOC lead | Platform engineer | Operator risk owner |
| Roll out a new model revision | Platform engineer | Model owner | NOC lead | Operator risk owner |
| Roll back a slot | Platform engineer | NOC lead | Model owner | Operator risk owner |

## Risks and limitations

| Risk | Likelihood | Mitigation |
|---|---|---|
| A slot returns malformed output while answering HTTP 200 | Medium | Apply the hardware prerequisites, and run the self-identification and fixed-prompt gates after every deploy |
| KV cache runs out under load, and requests queue or fail | Medium | Size with KV headroom, cap context length per slot, and give triage a higher priority band than batch work |
| A quantized build answers worse than full precision | Medium | Gate every quantized build on your acceptance suite before regional placement; keep the bf16 build at the core as the fallback |
| One component takes on access, content routing, and replica scheduling | Medium | Keep the three layers in separate components with separate owners, as in the routing layers table |
| A far-edge box runs one model, so a second slot has nowhere to go | High | Plan one model per far-edge box, and use single-node OpenShift where a site needs several slots |

## Used by and next steps

- [Architecture overview](../../architecture/index.md): the model endpoint, AI Gateway, and placement layers this page details
- [Placement tiers](../../architecture/placement.md): the tier rules this page sizes and serves
- [Decision gate](../../architecture/decision-gate.md): the gate the Decision slot serves
- [PB-05 Integration](../integration/README.md): integration reaches the slots served here through the same front door
- [PB-06 Safety and autonomy gating](../safety-autonomy-gating/README.md): uses the Safety and Decision slots placed here
- [PB-07 Action layer](../action-layer/README.md): the action layer runs behind the gate at the regional site and the core
- PB-02: evaluation and acceptance gates every quantized build before placement
- Agent-school: 104 serves a NOC assistant behind the front door, and 203 covers routing, in the [agent-school roadmap](https://github.com/open-experiments/agent-school/blob/main/docs/RoadMap.md)
