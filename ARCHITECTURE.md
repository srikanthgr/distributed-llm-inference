# Architecture: Traditional ML vs LLM Inference

This document provides a detailed comparison between the original TensorFlow-based project and the vLLM-based LLM inference project.

## High-Level Architecture Comparison

### Original Project (TensorFlow)
```
┌─────────────────────────────────────────────────────────────┐
│                    ARGO WORKFLOW                             │
└─────────────────────────────────────────────────────────────┘
                              ↓
         ┌────────────────────────────────────┐
         │  Data Ingestion (MNIST Download)   │
         └────────────────────────────────────┘
                              ↓
         ┌────────────────────────────────────┐
         │  Distributed Training (3 TFJobs)   │
         │  ├─ CNN Model                      │
         │  ├─ CNN + Dropout                  │
         │  └─ CNN + Batch Norm               │
         │  Each TFJob: 2 Workers             │
         └────────────────────────────────────┘
                              ↓
         ┌────────────────────────────────────┐
         │  Model Selection (Accuracy-based)  │
         │  Evaluate on test set              │
         └────────────────────────────────────┘
                              ↓
         ┌────────────────────────────────────┐
         │  TensorFlow Serving (KServe)       │
         │  REST/gRPC API                     │
         └────────────────────────────────────┘
```

### vLLM Project (LLM Inference)
```
┌─────────────────────────────────────────────────────────────┐
│                    ARGO WORKFLOW                             │
└─────────────────────────────────────────────────────────────┘
                              ↓
         ┌────────────────────────────────────┐
         │  Model Acquisition (HF Download)   │
         └────────────────────────────────────┘
                              ↓
         ┌────────────────────────────────────┐
         │  Model Optimization (3 Jobs)       │
         │  ├─ FP16 Conversion                │
         │  ├─ AWQ Quantization (4-bit)       │
         │  └─ GPTQ Quantization (4-bit)      │
         │  All jobs run in parallel          │
         └────────────────────────────────────┘
                              ↓
         ┌────────────────────────────────────┐
         │  Model Selection (Multi-metric)    │
         │  Quality + Latency + Throughput    │
         └────────────────────────────────────┘
                              ↓
         ┌────────────────────────────────────┐
         │  vLLM Serving (KServe)             │
         │  OpenAI-compatible API             │
         └────────────────────────────────────┘
```

## Component-by-Component Comparison

### 1. Data/Model Preparation

| Aspect | Original | vLLM Version |
|--------|----------|--------------|
| **Purpose** | Download training data | Download pre-trained model |
| **Source** | TensorFlow Datasets | HuggingFace Hub |
| **Size** | ~50MB (Fashion MNIST) | 500MB - 100GB+ (LLMs) |
| **Caching** | Argo memoization (1h) | Argo memoization (24h) |
| **Script** | `data-ingestion.py` | `model-acquisition.py` |
| **Time** | ~10 seconds | 1-30 minutes |

### 2. Computation Phase

| Aspect | Original | vLLM Version |
|--------|----------|--------------|
| **Operation** | Training from scratch | Model optimization/quantization |
| **Parallelism** | Data parallelism | Independent optimization jobs |
| **Frameworks** | TensorFlow + MultiWorkerMirroredStrategy | Transformers + Quantization libs |
| **Compute** | 2 workers × 3 models = 6 pods | 3 optimization jobs |
| **Duration** | ~1 minute (demo) | 5-20 minutes |
| **Resource** | CPU-focused | CPU/GPU for quantization |
| **Operator** | Kubeflow TFJob | Standard Kubernetes Jobs |

### 3. Model Selection

| Aspect | Original | vLLM Version |
|--------|----------|--------------|
| **Metric** | Accuracy on test set | Multi-dimensional scoring |
| **Evaluated** | Quality only | Quality + Latency + Throughput + Memory |
| **Process** | Load model, evaluate, compare | Load model, benchmark, score |
| **Output** | Best accuracy model | Best combined-score model |
| **Weights** | N/A | Configurable (quality=0.5, latency=0.2, etc.) |

### 4. Model Serving

| Aspect | Original | vLLM Version |
|--------|----------|--------------|
| **Runtime** | TensorFlow Serving | vLLM |
| **API** | TF Serving REST/gRPC | OpenAI-compatible REST |
| **Request** | `{"instances": [...]}` | `{"messages": [...]}` |
| **Features** | Batch inference | Continuous batching, PagedAttention |
| **Optimization** | Basic TF optimizations | KV cache, quantization, tensor parallelism |
| **Autoscaling** | Knative (requests-based) | Knative (concurrency-based) |

## Storage Architecture

### Original Project
```
PVC: strategy-volume (1GB)
/trained_model/
├── saved_model_versions/
│   ├── 1/          # CNN (87% acc)
│   ├── 2/          # +Dropout (92% acc) ✓
│   ├── 3/          # +BatchNorm (89% acc)
│   └── 4/          # Best → copy of version 2
└── checkpoint/     # Training checkpoints
```

### vLLM Project
```
PVC: llm-model-storage (20GB+)
/models/
├── base/                     # Downloaded from HuggingFace
│   ├── config.json
│   ├── pytorch_model.bin
│   └── tokenizer.json
├── optimized/
│   ├── fp16/                # FP16 (85% quality, 100ms)
│   ├── awq/                 # AWQ (82% quality, 45ms) ✓
│   └── gptq/                # GPTQ (80% quality, 50ms)
├── production/              # Best → copy of AWQ
└── production_metrics.json  # Evaluation results
```

## Resource Requirements

### Original Project (Minimum)
```yaml
CPU: 500m per worker × 6 = 3 CPU cores
Memory: 1GB per worker × 6 = 6GB RAM
Storage: 1GB PVC
GPU: Not required
```

### vLLM Project (Minimum)
```yaml
CPU: 2 cores (optimization), 4 cores (serving)
Memory: 4GB (small models), 32GB+ (7B models)
Storage: 20GB PVC (OPT-125m), 100GB+ (Llama-2-7B)
GPU: Optional but highly recommended
  - 1× T4/A10 for 7B models
  - 2× A100 for 13B+ models
```

## Workflow Patterns

### Parallelization

**Original**: Sequential data ingestion → Parallel training → Sequential selection

```
Data Ingestion (10s)
        ↓
┌───────┴───────┐
│ TFJob 1       │  }
│ TFJob 2       │  } Parallel (60s)
│ TFJob 3       │  }
└───────┬───────┘
        ↓
Model Selection (10s)
        ↓
Deploy Serving (30s)

Total: ~110s
```

**vLLM**: Sequential acquisition → Parallel optimization → Sequential selection

```
Model Acquisition (60s)
        ↓
┌───────┴───────┐
│ FP16 Job      │  }
│ AWQ Job       │  } Parallel (300s)
│ GPTQ Job      │  }
└───────┬───────┘
        ↓
Model Selection (30s)
        ↓
Deploy Serving (60s)

Total: ~450s
```

### Fault Tolerance

Both projects use the same Argo Workflow patterns:

- **Retries**: Automatic retry on failure
- **Timeouts**: `activeDeadlineSeconds` per step
- **Pod garbage collection**: `podGC.strategy: OnPodSuccess`
- **Memoization**: Cache expensive operations

## API Comparison

### Original (TensorFlow Serving)

**Request**:
```json
POST /v1/models/flower-sample:predict
{
  "instances": [
    {"image_bytes": {"b64": "base64_encoded_image"}}
  ]
}
```

**Response**:
```json
{
  "predictions": [[0.1, 0.05, 0.8, ...]]
}
```

### vLLM (OpenAI-compatible)

**Request**:
```json
POST /v1/chat/completions
{
  "model": "llm-model",
  "messages": [
    {"role": "user", "content": "Hello"}
  ],
  "max_tokens": 100
}
```

**Response**:
```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "Hello! How can I help you?"
    }
  }],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 8,
    "total_tokens": 18
  }
}
```

## Autoscaling Behavior

### Configuration

Both use KServe/Knative autoscaling:

```yaml
scaleTarget: 10          # Target concurrent requests
scaleMetric: concurrency
minReplicas: 1
maxReplicas: 5
```

### Scaling Triggers

**Original (TF Serving)**:
- Image classification: Fast responses (10-50ms)
- Scales on request count
- Can handle 100+ RPS per pod

**vLLM**:
- Text generation: Slower responses (1-10s)
- Scales on concurrent connections
- Handles 5-20 concurrent requests per pod
- More sensitive to memory usage

## Cost Considerations

### Original Project (per hour)
```
Training: 6 CPU pods × $0.05/hr = $0.30
Serving: 1 CPU pod × $0.05/hr = $0.05
Storage: 1GB × $0.10/GB/month ≈ $0.0003/hr
Total: ~$0.35/hr
```

### vLLM Project (per hour)
```
Optimization: 3 CPU pods × $0.05/hr = $0.15 (one-time)
Serving (CPU): 1 pod × $0.20/hr = $0.20
Serving (GPU): 1 T4 × $0.35/hr = $0.35
Storage: 20GB × $0.10/GB/month ≈ $0.003/hr
Total: ~$0.55/hr (CPU) or ~$0.70/hr (GPU)
```

## When to Use Each Pattern

### Use Original Pattern (TensorFlow) When:
- ✅ Training custom models from scratch
- ✅ Small to medium sized models (<100MB)
- ✅ Image/tabular/structured data
- ✅ CPU-only infrastructure
- ✅ Fast inference required (<50ms)
- ✅ High throughput (100+ RPS)

### Use vLLM Pattern When:
- ✅ Serving pre-trained LLMs
- ✅ Large language models (1B+ parameters)
- ✅ Text generation tasks
- ✅ GPU infrastructure available
- ✅ OpenAI-compatible API needed
- ✅ Memory-efficient serving required

## Key Takeaways

1. **Same Infrastructure**: Both use Kubernetes, Argo, KServe
2. **Same Patterns**: Workflow orchestration, model selection, autoscaling
3. **Different Runtimes**: TF Serving vs vLLM
4. **Different Scale**: MB vs GB models, ms vs s latency
5. **Different Metrics**: Accuracy vs Quality+Latency+Throughput

The **architectural principles remain constant** - only the ML workload changes!

