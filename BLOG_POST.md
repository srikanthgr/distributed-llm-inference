# Distributed LLM Inference Pipelines: A Production-Grade Architecture on Kubernetes

> How to build an end-to-end pipeline that acquires, optimizes, selects, and serves Large Language Models at scale using Kubernetes, Argo Workflows, vLLM, and KServe.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Why Distributed LLM Inference?](#2-why-distributed-llm-inference)
3. [Architecture Overview](#3-architecture-overview)
4. [Architecture Diagram](#4-architecture-diagram)
5. [Pipeline Stages Deep Dive](#5-pipeline-stages-deep-dive)
   - 5.1 [Stage 1: Model Acquisition](#51-stage-1-model-acquisition)
   - 5.2 [Stage 2: Model Optimization (Parallel)](#52-stage-2-model-optimization-parallel)
   - 5.3 [Stage 3: Model Selection](#53-stage-3-model-selection)
   - 5.4 [Stage 4: Inference Service Deployment](#54-stage-4-inference-service-deployment)
6. [Key Components of the Architecture](#6-key-components-of-the-architecture)
   - 6.1 [Workflow Orchestration — Argo Workflows](#61-workflow-orchestration--argo-workflows)
   - 6.2 [Inference Engine — vLLM](#62-inference-engine--vllm)
   - 6.3 [Model Serving — KServe](#63-model-serving--kserve)
   - 6.4 [Autoscaling — Knative](#64-autoscaling--knative)
   - 6.5 [Storage — Kubernetes PersistentVolumeClaim](#65-storage--kubernetes-persistentvolumeclaim)
   - 6.6 [Alternative: Ray Serve](#66-alternative-ray-serve)
7. [Storage Architecture](#7-storage-architecture)
8. [Communication & API Design](#8-communication--api-design)
9. [Autoscaling & Performance Tuning](#9-autoscaling--performance-tuning)
10. [Cloud Portability & Multi-Cloud Deployment](#10-cloud-portability--multi-cloud-deployment)
11. [Production Considerations](#11-production-considerations)
12. [Conclusion](#12-conclusion)

---

## 1. Introduction

Serving Large Language Models in production is fundamentally different from serving traditional ML models. LLMs are massive (billions of parameters), memory-hungry (often requiring multiple GPUs), and latency-sensitive (users expect real-time responses). A single monolithic deployment quickly becomes a bottleneck.

This blog post walks through the architecture of a **distributed LLM inference pipeline** — a system that automates the entire lifecycle from downloading a pre-trained model off HuggingFace, through quantization and optimization, to deploying an autoscaled, OpenAI-compatible inference API on Kubernetes.

The architecture builds on battle-tested cloud-native tools: **Argo Workflows** for orchestration, **vLLM** for high-throughput inference, **KServe** for model serving, and **Knative** for autoscaling — all running on Kubernetes.

---

## 2. Why Distributed LLM Inference?

Traditional ML model serving (e.g., a scikit-learn model behind a Flask API) doesn't translate to LLMs for several reasons:

| Challenge | Traditional ML | LLM Inference |
|-----------|---------------|---------------|
| **Model Size** | MBs to low GBs | 1GB to 100s of GBs |
| **Memory** | CPU RAM is sufficient | GPU VRAM required (16–80 GB per GPU) |
| **Latency** | Sub-millisecond | 50ms–5s per token |
| **Throughput** | 1000s of req/s trivially | 10–100 req/s per GPU |
| **Optimization** | One format fits most | Quantization is critical (FP16, AWQ, GPTQ) |
| **Selection Criteria** | Accuracy only | Quality + Latency + Throughput + Memory |

A distributed pipeline addresses these by:

- **Parallelizing optimization** — multiple quantization strategies run simultaneously
- **Automating selection** — the best variant is chosen using multi-dimensional scoring
- **Scaling horizontally** — Knative spins up/down inference pods based on demand
- **Decoupling concerns** — each stage (acquire, optimize, select, serve) is an independent, containerized step

---

## 3. Architecture Overview

The system follows a **four-stage pipeline** pattern, orchestrated as a Directed Acyclic Graph (DAG) by Argo Workflows:

```
┌────────────────┐
│  HuggingFace   │  (External Model Registry)
│  Model Hub     │
└───────┬────────┘
        │ Download
        ▼
┌────────────────┐
│ STAGE 1        │
│ Model          │  → /models/base/
│ Acquisition    │
└───────┬────────┘
        │
        ├──────────────────┬──────────────────┐
        ▼                  ▼                  ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ STAGE 2a     │   │ STAGE 2b     │   │ STAGE 2c     │
│ FP16         │   │ AWQ          │   │ GPTQ         │
│ Conversion   │   │ Quantization │   │ Quantization │
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       │                  │                  │
       │    /models/optimized/{fp16,awq,gptq}/
       └──────────────────┼──────────────────┘
                          │
                          ▼
                  ┌────────────────┐
                  │ STAGE 3        │
                  │ Model          │  → /models/production/
                  │ Selection      │  → /models/production_metrics.json
                  └───────┬────────┘
                          │
                          ▼
                  ┌────────────────┐
                  │ STAGE 4        │
                  │ KServe         │  → OpenAI-compatible API
                  │ Deployment     │     :8000/v1/chat/completions
                  └────────────────┘
```

All stages share a single **20 GB PersistentVolumeClaim** (`ReadWriteMany`) that acts as a shared filesystem, eliminating the need for artifact transfer between pods.

---

## 4. Architecture Diagram

Below is the full system architecture showing how every component interacts within the Kubernetes cluster:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           KUBERNETES CLUSTER                                    │
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                     ARGO WORKFLOW CONTROLLER                              │  │
│  │                                                                           │  │
│  │   ┌─────────────┐    ┌──────────────────────────────┐    ┌────────────┐  │  │
│  │   │   Step 1     │    │         Step 2               │    │  Step 3    │  │  │
│  │   │             │    │  ┌────────┐ ┌────┐ ┌────────┐│    │            │  │  │
│  │   │  Acquire    │───▶│  │ FP16   │ │AWQ │ │ GPTQ   ││───▶│  Select   │  │  │
│  │   │  Model      │    │  │ Pod    │ │Pod │ │ Pod    ││    │  Best     │  │  │
│  │   │             │    │  └────────┘ └────┘ └────────┘│    │  Model    │  │  │
│  │   └─────────────┘    └──────────────────────────────┘    └─────┬──────┘  │  │
│  │                                                                │         │  │
│  └────────────────────────────────────────────────────────────────┼─────────┘  │
│                                                                   │            │
│                              kubectl apply                        │            │
│                                                                   ▼            │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                     KSERVE / KNATIVE LAYER                                │  │
│  │                                                                           │  │
│  │   ┌──────────────────────────────────────────────────────────────────┐    │  │
│  │   │              InferenceService: llm-inference                     │    │  │
│  │   │                                                                  │    │  │
│  │   │   ┌──────────┐   ┌──────────┐   ┌──────────┐                   │    │  │
│  │   │   │  vLLM    │   │  vLLM    │   │  vLLM    │   ◄── Autoscaled │    │  │
│  │   │   │ Replica  │   │ Replica  │   │ Replica  │       1–3 pods   │    │  │
│  │   │   │    1     │   │    2     │   │    3     │                   │    │  │
│  │   │   └──────────┘   └──────────┘   └──────────┘                   │    │  │
│  │   │        │              │              │                          │    │  │
│  │   │        └──────────────┼──────────────┘                          │    │  │
│  │   │                       │                                         │    │  │
│  │   │              :8000/v1/chat/completions                          │    │  │
│  │   └──────────────────────────────────────────────────────────────────┘    │  │
│  │                                                                           │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                     SHARED STORAGE LAYER                                  │  │
│  │                                                                           │  │
│  │   PersistentVolumeClaim: llm-model-storage (20 GB, ReadWriteMany)        │  │
│  │   ┌──────────┐  ┌──────────────────────────────┐  ┌──────────────────┐   │  │
│  │   │ /models/ │  │ /models/optimized/           │  │ /models/         │   │  │
│  │   │ base/    │  │   ├── fp16/                  │  │ production/      │   │  │
│  │   │          │  │   ├── awq/                   │  │ (best model)     │   │  │
│  │   │          │  │   └── gptq/                  │  │                  │   │  │
│  │   └──────────┘  └──────────────────────────────┘  └──────────────────┘   │  │
│  │                                                                           │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

                                     │
                                     │  Port-forward / Ingress / LoadBalancer
                                     ▼

                    ┌──────────────────────────────┐
                    │         CLIENTS               │
                    │                                │
                    │  ┌────────────────────────┐   │
                    │  │  OpenAI Python SDK     │   │
                    │  │  inference-client.py   │   │
                    │  └────────────────────────┘   │
                    │  ┌────────────────────────┐   │
                    │  │  HTTP / curl / REST    │   │
                    │  │  Any OpenAI-compat     │   │
                    │  │  client                │   │
                    │  └────────────────────────┘   │
                    └──────────────────────────────┘
```

---

## 5. Pipeline Stages Deep Dive

### 5.1 Stage 1: Model Acquisition

**Purpose:** Download a pre-trained LLM from HuggingFace Hub into shared storage.

**How it works:**
- Uses `huggingface_hub.snapshot_download()` to fetch all model artifacts (weights, tokenizer, config)
- Stores the full model to `/models/base/`
- Supports any HuggingFace model ID (default: `facebook/opt-125m` for testing)
- For gated models (e.g., Llama 2), a HuggingFace API token is passed via Kubernetes secrets

**Argo Memoization:** This step is cached for 24 hours. If the same model was downloaded recently, the cached version is reused — saving bandwidth and time for iterative development.

```python
from huggingface_hub import snapshot_download

model_name = os.environ.get("MODEL_NAME", "facebook/opt-125m")
snapshot_download(
    repo_id=model_name,
    local_dir="/models/base",
    local_dir_use_symlinks=False
)
```

**Key design decision:** The model is downloaded into a shared `ReadWriteMany` PVC, not an ephemeral container filesystem. This allows all subsequent pods (optimization, selection, serving) to access the same files without re-downloading.

---

### 5.2 Stage 2: Model Optimization (Parallel)

**Purpose:** Create multiple quantized variants of the base model to explore the quality-performance tradeoff.

Three optimization jobs run **in parallel** as separate Kubernetes pods:

| Variant | Technique | Precision | Typical Size Reduction | Inference Speed |
|---------|-----------|-----------|----------------------|-----------------|
| **FP16** | Float16 conversion | 16-bit | ~50% of FP32 | Baseline |
| **AWQ** | Activation-Aware Weight Quantization | 4-bit | ~75% of FP32 | 2–3x faster |
| **GPTQ** | Post-Training Quantization | 4-bit | ~75% of FP32 | 1.5–2x faster |

Each optimization pod:
1. Reads the base model from `/models/base/`
2. Applies its quantization technique
3. Writes the optimized model to `/models/optimized/{fp16|awq|gptq}/`

**Why parallel?** Each quantization technique is independent. Running them simultaneously (instead of sequentially) cuts this stage's wall-clock time by ~3x. Argo Workflows handles this natively:

```yaml
- - name: optimize-fp16           # Double dash = parallel group
    template: optimize-model
    arguments:
      parameters:
        - name: optimization-type
          value: "fp16"
  - name: optimize-awq
    template: optimize-model
    arguments:
      parameters:
        - name: optimization-type
          value: "awq"
  - name: optimize-gptq
    template: optimize-model
    arguments:
      parameters:
        - name: optimization-type
          value: "gptq"
```

---

### 5.3 Stage 3: Model Selection

**Purpose:** Evaluate all optimized variants and automatically promote the best one to production.

Unlike traditional ML where model selection is based on a single metric (accuracy), LLM inference requires **multi-dimensional evaluation**:

| Metric | Weight | What it Measures |
|--------|--------|-----------------|
| **Quality Score** | 50% | Response coherence and correctness (0.0–1.0) |
| **Latency** | 20% | Time to first token (lower is better) |
| **Throughput** | 20% | Tokens generated per second (higher is better) |
| **GPU Memory** | 10% | VRAM consumption (lower is better) |

The selection algorithm:
1. Evaluates each variant against all four metrics
2. Normalizes scores to 0–1 range
3. Computes a weighted combined score
4. Selects the variant with the highest combined score
5. Copies the winner to `/models/production/`
6. Writes a metrics report to `/models/production_metrics.json`

**Typical result:** AWQ wins in most scenarios because it offers the best balance of quality preservation (~0.82) with significantly reduced latency (45ms) and memory usage (4 GB).

```json
{
  "selected_model": "awq",
  "combined_score": 0.847,
  "metrics": {
    "quality_score": 0.82,
    "latency_ms": 45,
    "throughput_tokens_per_sec": 450,
    "gpu_memory_gb": 4
  }
}
```

---

### 5.4 Stage 4: Inference Service Deployment

**Purpose:** Deploy the winning model as a production-ready, autoscaled inference API.

This stage uses `kubectl` to create a **KServe InferenceService** resource that:
- Launches vLLM containers serving the production model
- Exposes an OpenAI-compatible REST API
- Configures autoscaling (1–3 replicas based on concurrency)
- Sets resource limits (4 CPU, 8 GB RAM per pod)
- Mounts the model storage as read-only

The deployed API is fully OpenAI-compatible — any client that works with the OpenAI API can point to this endpoint with zero code changes:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://llm-service:8000/v1",
    api_key="not-needed"       # vLLM doesn't require auth by default
)

response = client.chat.completions.create(
    model="llm-model",
    messages=[{"role": "user", "content": "Explain distributed inference"}],
    max_tokens=200
)
```

---

## 6. Key Components of the Architecture

### 6.1 Workflow Orchestration — Argo Workflows

[Argo Workflows](https://argoproj.github.io/workflows/) is a CNCF-graduated project that runs containerized workflows on Kubernetes.

**Why Argo?**
- **Kubernetes-native:** Workflows are Custom Resources; each step is a Pod
- **DAG support:** Define complex step dependencies (sequential + parallel)
- **Memoization:** Cache expensive steps (e.g., model downloads) across runs
- **Retry policies:** Automatic retries on transient failures
- **UI Dashboard:** Visual workflow monitoring and debugging

In this architecture, Argo serves as the "conductor" — it ensures Stage 1 completes before Stage 2 begins, that all three Stage 2 jobs finish before Stage 3 starts, and that Stage 3 produces a result before Stage 4 deploys.

---

### 6.2 Inference Engine — vLLM

[vLLM](https://vllm.ai/) is the fastest open-source LLM inference engine, powering services at companies like Anyscale, Databricks, and Cloudflare.

**Key innovations:**
- **PagedAttention:** Manages KV-cache memory like virtual memory pages, reducing waste by up to 90%
- **Continuous Batching:** Dynamically batches incoming requests instead of waiting for a fixed batch to fill
- **Quantization Support:** Native AWQ, GPTQ, and FP8 support
- **OpenAI Compatibility:** Drop-in replacement API — no client-side changes needed

**Configuration in this architecture:**
```yaml
args:
  - "--model=/models/production"
  - "--max-model-len=2048"       # Context window
  - "--tensor-parallel-size=1"   # GPUs per replica
  - "--max-num-batched-tokens=4096"
  - "--max-num-seqs=32"          # Max concurrent sequences
```

---

### 6.3 Model Serving — KServe

[KServe](https://kserve.github.io/) is the standard model inference platform on Kubernetes, providing:

- **InferenceService CRD:** Declarative model deployment (one YAML = one model service)
- **Canary Deployments:** Gradually roll out new model versions
- **Request Routing:** Traffic splitting between model versions
- **Transformer Support:** Pre/post-processing sidecars
- **Multi-Framework:** Supports vLLM, TensorFlow Serving, Triton, and more

KServe sits on top of Knative, which provides the serverless runtime and autoscaling.

---

### 6.4 Autoscaling — Knative

Knative provides the autoscaling layer that makes inference cost-efficient:

```yaml
annotations:
  autoscaling.knative.dev/target: "10"        # Scale at 10 concurrent requests
  autoscaling.knative.dev/metric: "concurrency"
  autoscaling.knative.dev/minScale: "1"       # Always keep 1 pod warm
  autoscaling.knative.dev/maxScale: "3"       # Cap at 3 pods
```

**Scaling behavior:**
- **0 → 1 pod:** Cold start (~60–120s for LLM loading)
- **1 → N pods:** ~10–30s (model already cached in PVC)
- **N → 1 pod:** Scale-down after idle period (default: 5 min)

---

### 6.5 Storage — Kubernetes PersistentVolumeClaim

All pipeline stages communicate through a shared PVC:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: llm-model-storage
spec:
  accessModes:
    - ReadWriteMany          # Critical: multiple pods read/write simultaneously
  resources:
    requests:
      storage: 20Gi
```

**Why PVC over object storage (S3/GCS)?**
- Lower latency for model loading (no download step at serve time)
- Simpler configuration (no IAM roles, bucket policies)
- Works identically across clouds and on-premise

**Trade-off:** For models >20 GB or multi-cluster deployments, object storage with a model cache layer is recommended.

---

### 6.6 Alternative: Ray Serve

The architecture also supports **Ray Serve** as an alternative to KServe for teams that prefer Python-first orchestration:

```
┌──────────────────────────────────────────────┐
│              RAY CLUSTER                      │
│                                               │
│   ┌───────────┐   ┌───────────────────────┐  │
│   │ Head Node │   │  GPU Worker Pool      │  │
│   │ (GCS,     │   │  ┌───────┐ ┌───────┐  │  │
│   │  Redis,   │   │  │vLLM   │ │vLLM   │  │  │
│   │  Dashboard│   │  │Worker │ │Worker │  │  │
│   │  :8265)   │   │  │1 GPU  │ │1 GPU  │  │  │
│   └───────────┘   │  └───────┘ └───────┘  │  │
│                    └───────────────────────┘  │
│                                               │
│   FastAPI (:8000/v1/chat/completions)        │
└──────────────────────────────────────────────┘
```

Ray Serve provides:
- **Python-native deployment:** Define serving logic in Python, not YAML
- **Built-in autoscaling:** 1–5 replicas with `autoscaling_config`
- **GPU awareness:** Fractional GPU allocation (`num_gpus=1.0`)
- **Async engine:** vLLM's `AsyncLLMEngine` for non-blocking inference

---

## 7. Storage Architecture

The filesystem layout on the shared PVC acts as the contract between pipeline stages:

```
/models/  (PersistentVolumeClaim: 20 GB)
│
├── base/                          # Stage 1 output
│   ├── config.json                # Model architecture config
│   ├── tokenizer.json             # Tokenizer vocabulary
│   ├── tokenizer_config.json      # Tokenizer settings
│   ├── special_tokens_map.json    # Special token definitions
│   └── pytorch_model.bin          # Model weights (largest file)
│
├── optimized/                     # Stage 2 output
│   ├── fp16/
│   │   ├── config.json
│   │   └── pytorch_model.bin      # FP16 weights (~50% of original)
│   ├── awq/
│   │   ├── config.json
│   │   ├── quantization_config.json
│   │   └── model.safetensors      # AWQ 4-bit weights (~25% of original)
│   └── gptq/
│       ├── config.json
│       ├── quantization_config.json
│       └── model.safetensors      # GPTQ 4-bit weights (~25% of original)
│
├── production/                    # Stage 3 output → Stage 4 input
│   ├── config.json
│   ├── quantization_config.json
│   └── model.safetensors          # Best model (typically AWQ)
│
└── production_metrics.json        # Selection metrics and reasoning
```

---

## 8. Communication & API Design

### Internal Communication (Within Cluster)

Stages communicate exclusively through the **shared filesystem** — there are no RPCs, message queues, or APIs between pipeline steps. This keeps the architecture simple and debuggable.

```
Stage 1 ──writes──▶ /models/base/
Stage 2 ──reads───▶ /models/base/    ──writes──▶ /models/optimized/
Stage 3 ──reads───▶ /models/optimized/ ──writes──▶ /models/production/
Stage 4 ──reads───▶ /models/production/ (mounted read-only)
```

### External API (Client-Facing)

The inference service exposes an **OpenAI-compatible REST API**:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/chat/completions` | POST | Chat-style inference (messages array) |
| `/v1/completions` | POST | Text completion (raw prompt) |
| `/v1/models` | GET | List available models |
| `/health` | GET | Health check |

**Request example:**
```json
POST /v1/chat/completions
{
  "model": "llm-model",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is distributed inference?"}
  ],
  "max_tokens": 150,
  "temperature": 0.7,
  "stream": false
}
```

**Response:**
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "model": "llm-model",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Distributed inference is the practice of spreading model inference across multiple machines..."
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 28,
    "completion_tokens": 42,
    "total_tokens": 70
  }
}
```

The OpenAI-compatibility means **any existing OpenAI SDK client** works out of the box — just change the `base_url`.

---

## 9. Autoscaling & Performance Tuning

### Horizontal Pod Autoscaling

The inference service scales based on **request concurrency**, not CPU utilization — a much better signal for LLM workloads:

```
Incoming Requests: 5   → 1 pod  (5 concurrent / 10 target = 0.5 ratio)
Incoming Requests: 15  → 2 pods (15 / 10 = 1.5, rounds up)
Incoming Requests: 30  → 3 pods (30 / 10 = 3.0, hits max)
Incoming Requests: 3   → 1 pod  (scale down after cooldown)
```

### vLLM Performance Knobs

| Parameter | Default | Effect |
|-----------|---------|--------|
| `max-model-len` | 2048 | Maximum context window (more = more VRAM) |
| `max-num-batched-tokens` | 4096 | Tokens processed per batch (higher = better throughput) |
| `max-num-seqs` | 32 | Maximum concurrent sequences |
| `tensor-parallel-size` | 1 | Number of GPUs per replica (for models too large for 1 GPU) |

### Resource Allocation Per Pod

```yaml
resources:
  requests:
    cpu: "2"
    memory: "4Gi"
  limits:
    cpu: "4"
    memory: "8Gi"
    # nvidia.com/gpu: "1"    # Uncomment for GPU nodes
```

---

## 10. Cloud Portability & Multi-Cloud Deployment

The entire architecture is Kubernetes-native, meaning it runs on **any conformant Kubernetes cluster** with minimal configuration changes:

| Cloud | Managed K8s | Storage Class | GPU Nodes |
|-------|-------------|---------------|-----------|
| **AWS** | EKS | `gp3` | `p3.2xlarge` (V100) / `g5.xlarge` (A10G) |
| **GCP** | GKE | `standard` | `n1-standard-8` + NVIDIA T4/A100 |
| **Azure** | AKS | `managed-premium` | `Standard_NC6s_v3` (V100) |
| **On-Prem** | kubeadm / k3s | `local-path` | Any NVIDIA GPU with drivers |

**What changes per cloud:**
1. Storage class name in the PVC
2. GPU node selector / tolerations
3. Container registry URL in workflow templates
4. Load balancer annotations for external access

**What stays the same (everything else):**
- All Python application code
- Argo workflow definition
- KServe InferenceService spec
- vLLM configuration
- Autoscaling policies

---

## 11. Production Considerations

### What's Production-Ready

- **Error handling and retries** — Argo retries failed steps automatically
- **Health checks** — Liveness and readiness probes on inference pods
- **Resource limits** — CPU and memory boundaries prevent noisy-neighbor problems
- **RBAC** — Service accounts with least-privilege permissions
- **Autoscaling** — Demand-based scaling prevents over-provisioning
- **Immutable deployments** — Model path is fixed at deploy time

### What to Add for Production

| Concern | Recommendation |
|---------|---------------|
| **Observability** | Prometheus + Grafana for metrics; request latency, queue depth, GPU utilization |
| **Logging** | Structured logging with correlation IDs; aggregate with ELK or Loki |
| **Authentication** | API key validation or OAuth2 proxy in front of the inference service |
| **TLS** | cert-manager + Ingress controller for HTTPS termination |
| **Model Registry** | MLflow or Weights & Biases for model versioning beyond the filesystem |
| **Cost Optimization** | Spot/preemptible GPU instances for non-critical workloads |
| **Disaster Recovery** | Velero backups for PVCs; model artifacts mirrored to object storage |
| **CI/CD** | GitOps with ArgoCD — workflow definitions in Git, auto-deployed on merge |

---

## 12. Conclusion

Distributed LLM inference is not just about running a model behind an API — it's about building a **pipeline** that automates the entire lifecycle:

1. **Acquire** the model from a registry
2. **Optimize** it with multiple quantization strategies in parallel
3. **Select** the best variant using multi-dimensional scoring
4. **Serve** it with autoscaling and OpenAI compatibility

The architecture described in this post uses best-in-class, CNCF-backed tools that are production-proven at scale:

- **Argo Workflows** for orchestration (CNCF graduated)
- **vLLM** for inference (PagedAttention, continuous batching)
- **KServe** for model serving (declarative, autoscaled)
- **Kubernetes** for everything else (portable, ubiquitous)

The result is a system that's **cloud-portable** (runs on AWS, GCP, Azure, or bare metal), **cost-efficient** (scales to zero when idle), and **operationally simple** (one `argo submit` command to go from model ID to production API).

Whether you're serving a 125M parameter model for experimentation or a 70B parameter model for production, this architecture scales with you — just change the model name, adjust the GPU count, and submit the workflow.

---

*Built with Kubernetes, Argo Workflows, vLLM, and KServe. The complete source code and deployment manifests are available in the project repository.*
