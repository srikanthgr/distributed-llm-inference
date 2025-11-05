# vLLM Distributed Inference Project - Complete Overview

This project is a **complete parallel implementation** of the distributed ML patterns book project, adapted for LLM inference using vLLM instead of TensorFlow.

## 📁 Project Structure

```
vllm-project/
├── README.md                    # Main project documentation
├── QUICKSTART.md               # 5-minute getting started guide
├── ARCHITECTURE.md             # Detailed comparison with original
├── PROJECT_OVERVIEW.md         # This file
├── .gitignore                  # Git ignore rules
├── kind-gpu-config.yaml        # Kubernetes cluster config with GPU
│
├── basics/                     # Learning examples (start here!)
│   ├── hello-world.yaml            # Simple Kubernetes pod
│   ├── argo-hello-world.yaml       # Single-step Argo workflow
│   ├── argo-dag-diamond.yaml       # Multi-step DAG workflow
│   ├── argo-script-template.yaml   # Python script in workflow
│   ├── argo-resource-template.yaml # Resource management
│   └── vllm-pod.yaml              # Simple vLLM server pod
│
├── manifests/                  # Infrastructure installation
│   ├── kustomization.yaml          # Main kustomize config
│   ├── argo-workflows/
│   │   ├── kustomization.yaml      # Argo Workflows install
│   │   └── rbac-patch.yaml         # Permissions for workflows
│   └── kubeflow-training/
│       ├── kustomization.yaml      # Training Operator install
│       ├── deployment.yaml         # Operator deployment
│       ├── service.yaml            # Operator service
│       ├── cluster-role.yaml       # Cluster permissions
│       ├── cluster-role-binding.yaml
│       ├── service-account.yaml
│       └── crds/                   # Custom Resource Definitions
│           ├── kubeflow.org_tfjobs.yaml
│           ├── kubeflow.org_pytorchjobs.yaml
│           ├── kubeflow.org_mxjobs.yaml
│           └── kubeflow.org_xgboostjobs.yaml
│
└── code/                       # Main application code
    ├── README.md                   # Detailed usage guide
    ├── Dockerfile                  # Container image definition
    │
    ├── Python Scripts:
    ├── model-acquisition.py        # Download model from HuggingFace
    ├── model-optimization.py       # Create quantized versions
    ├── model-selection.py          # Evaluate and select best
    ├── inference-client.py         # Test inference endpoint
    ├── http-inference-request.py   # Simple HTTP test
    └── test-service.py            # Verify model files
    │
    ├── Kubernetes Resources:
    ├── model-pvc.yaml             # Persistent storage (20GB)
    ├── workflow.yaml              # Complete Argo pipeline
    ├── inference-service.yaml     # KServe deployment
    ├── autoscaled-inference-service.yaml  # With autoscaling
    ├── vllm-service.yaml          # Simple K8s deployment
    ├── model-selection.yaml       # Standalone selection pod
    └── test-pod.yaml              # Debug/test pod
```

## 🎯 What This Project Demonstrates

### Core Patterns (Same as Original)
1. ✅ **Workflow Orchestration** - Argo Workflows for complex pipelines
2. ✅ **Distributed Computing** - Parallel job execution
3. ✅ **Model Versioning** - Multiple model variants management
4. ✅ **Model Selection** - A/B testing and champion/challenger
5. ✅ **Autoscaling** - Dynamic scaling based on load
6. ✅ **Infrastructure as Code** - All resources in YAML
7. ✅ **Storage Patterns** - Shared PVC for model persistence

### Adaptations for LLM
1. 🆕 **Model Acquisition** - Download from HuggingFace Hub
2. 🆕 **Quantization** - FP16, AWQ, GPTQ optimization
3. 🆕 **Multi-metric Selection** - Quality + Latency + Throughput
4. 🆕 **vLLM Serving** - OpenAI-compatible API
5. 🆕 **GPU Support** - Resource configurations for GPUs
6. 🆕 **Large Model Handling** - 20GB+ storage, memory management

## 🚀 Complete Workflow

The pipeline orchestrates 4 main steps:

### 1. Model Acquisition (Sequential)
```python
# model-acquisition.py
snapshot_download(
    repo_id="facebook/opt-125m",
    local_dir="/models/base"
)
```
**Time**: 1-30 minutes (depending on model size)
**Output**: `/models/base/` with model files

### 2. Model Optimization (Parallel - 3 jobs)
```python
# model-optimization.py
optimize_fp16()   # FP16 precision
optimize_awq()    # AWQ quantization (4-bit)
optimize_gptq()   # GPTQ quantization (4-bit)
```
**Time**: 5-20 minutes each (parallel)
**Output**: 
- `/models/optimized/fp16/`
- `/models/optimized/awq/`
- `/models/optimized/gptq/`

### 3. Model Selection (Sequential)
```python
# model-selection.py
for model in [fp16, awq, gptq]:
    metrics = evaluate_model(model)
    score = calculate_combined_score(metrics)
best = select_highest_score()
copy_to_production(best)
```
**Metrics Evaluated**:
- Quality score (accuracy/perplexity)
- Average latency (ms)
- Throughput (tokens/sec)
- GPU memory usage (GB)

**Time**: 2-5 minutes
**Output**: `/models/production/` (best model)

### 4. Deploy Serving (Sequential)
```yaml
# Deploys KServe InferenceService
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
spec:
  predictor:
    containers:
    - name: vllm
      image: vllm/vllm-openai:latest
      args: [--model=/models/production]
```
**Time**: 1-2 minutes
**Output**: HTTP endpoint at `http://vllm-llm-service:8000`

## 📊 Side-by-Side Comparison

| Component | Original Project | vLLM Project |
|-----------|-----------------|--------------|
| **Data Prep** | `data-ingestion.py` (MNIST) | `model-acquisition.py` (HF) |
| **Training/Opt** | 3 TFJobs (6 workers) | 3 optimization jobs |
| **Selection** | Accuracy-based | Multi-metric scoring |
| **Serving** | TensorFlow Serving | vLLM OpenAI API |
| **Storage** | 1GB PVC | 20GB+ PVC |
| **API Format** | TF Serving format | OpenAI format |
| **Typical Latency** | 10-50ms | 100ms-10s |
| **Throughput** | 100+ RPS | 5-20 concurrent |

## 🛠️ Key Files Explained

### Python Scripts

| File | Lines | Purpose |
|------|-------|---------|
| `model-acquisition.py` | ~20 | Download model from HuggingFace Hub |
| `model-optimization.py` | ~100 | Apply FP16/AWQ/GPTQ quantization |
| `model-selection.py` | ~150 | Evaluate models and select winner |
| `inference-client.py` | ~80 | OpenAI-compatible test client |
| `http-inference-request.py` | ~30 | Simple HTTP REST test |
| `test-service.py` | ~60 | Verify model files and structure |

### YAML Configurations

| File | Purpose |
|------|---------|
| `model-pvc.yaml` | 20GB shared storage for models |
| `workflow.yaml` | Complete 4-step Argo pipeline |
| `inference-service.yaml` | Basic KServe deployment |
| `autoscaled-inference-service.yaml` | With HPA configuration |
| `vllm-service.yaml` | Simple K8s Deployment (no KServe) |
| `test-pod.yaml` | Debug pod with model access |

## 🎓 Learning Path

### Beginner (Day 1)
1. Read `README.md` - Understand the project
2. Follow `QUICKSTART.md` - Get hands-on quickly
3. Explore `basics/` - Learn Kubernetes & Argo basics
4. Run `basics/hello-world.yaml` → `argo-hello-world.yaml`

### Intermediate (Day 2-3)
1. Study `code/README.md` - Deep dive into components
2. Build and test individual scripts
3. Run the complete `workflow.yaml`
4. Experiment with different models

### Advanced (Day 4-5)
1. Read `ARCHITECTURE.md` - Understand design patterns
2. Customize model selection weights
3. Implement custom quantization
4. Add monitoring and observability

## 🔧 Customization Examples

### Change Model
```yaml
# In workflow.yaml
env:
- name: MODEL_NAME
  value: "meta-llama/Llama-2-7b-chat-hf"
```

### Adjust Selection Weights
```python
# In model-selection.py
weights = {
    "quality": 0.7,    # Prioritize quality
    "latency": 0.2,
    "throughput": 0.05,
    "memory": 0.05
}
```

### Enable GPU
```yaml
# In inference-service.yaml
resources:
  limits:
    nvidia.com/gpu: 2
```

### Tensor Parallelism
```yaml
# In inference-service.yaml
args:
- --tensor-parallel-size=2  # Split across 2 GPUs
```

## 📈 Resource Requirements

### Minimum (CPU-only, small models)
- **CPU**: 4 cores
- **Memory**: 8GB RAM
- **Storage**: 20GB
- **Cost**: ~$0.50/hour

### Recommended (GPU, 7B models)
- **CPU**: 8 cores
- **Memory**: 32GB RAM
- **GPU**: 1× T4 or A10
- **Storage**: 100GB
- **Cost**: ~$1.50/hour

### Production (GPU, 13B+ models)
- **CPU**: 16 cores
- **Memory**: 64GB RAM
- **GPU**: 2× A100
- **Storage**: 200GB
- **Cost**: ~$5-10/hour

## 🎯 Use Cases

This pattern is ideal for:

✅ **Serving pre-trained LLMs** in production  
✅ **Comparing different quantization strategies**  
✅ **A/B testing model versions**  
✅ **Cost optimization** (finding best perf/cost ratio)  
✅ **Learning MLOps patterns** for LLM systems  
✅ **Building CI/CD** for LLM deployments  

## 🚫 What This Project Does NOT Cover

❌ **LLM Training** from scratch (use PyTorch + DeepSpeed)  
❌ **Fine-tuning** workflows (covered by Kubeflow Training Operator)  
❌ **RAG systems** (retrieval-augmented generation)  
❌ **Multi-model serving** (model routing, ensembles)  
❌ **Production monitoring** (Prometheus, Grafana setup)  

These are beyond the scope but can be added as extensions.

## 🔗 Integration Points

This project integrates with:

- **HuggingFace Hub** - Model acquisition
- **Argo Workflows** - Pipeline orchestration
- **KServe** - Model serving
- **Knative** - Autoscaling
- **Kubernetes** - Infrastructure
- **vLLM** - Inference engine
- **OpenAI SDK** - Client libraries

## 📚 Next Steps

1. **Run the project** following `QUICKSTART.md`
2. **Read the book** "Distributed Machine Learning Patterns"
3. **Customize** for your specific LLM
4. **Extend** with monitoring, logging, etc.
5. **Deploy** to production cluster

## 🤝 Relationship to Original Project

This project is a **faithful adaptation** that:

✅ Maintains the **same directory structure**  
✅ Uses the **same infrastructure** (Argo, Kubeflow, KServe)  
✅ Follows the **same patterns** (orchestration, selection, serving)  
✅ Teaches the **same concepts** (distributed ML, MLOps)  

The **only difference** is the ML workload: Traditional ML → LLM Inference

**Key Insight**: The book's patterns are **framework-agnostic** and apply universally to distributed ML systems!

## 🎉 Summary

You now have a **complete, production-ready template** for deploying LLMs using the same proven patterns from the distributed ML patterns book. 

The project demonstrates that **architectural patterns transcend specific ML frameworks** - whether you're serving TensorFlow models or vLLM-powered LLMs, the principles remain the same.

Happy building! 🚀

