# vLLM Distributed Inference - Complete Pipeline

This directory contains the complete implementation of a distributed LLM inference pipeline using vLLM, following the same patterns as the traditional ML project.

## 📋 Overview

The pipeline consists of 4 main steps:

1. **Model Acquisition**: Download LLM from HuggingFace Hub
2. **Model Optimization**: Create quantized versions (FP16, AWQ, GPTQ) in parallel
3. **Model Selection**: Evaluate all versions and select the best
4. **Model Serving**: Deploy winner with vLLM + KServe with autoscaling

## 🚀 Quick Start

### Prerequisites

```bash
# Ensure you're in the kubeflow namespace
kubectl config set-context --current --namespace=kubeflow

# Verify infrastructure is installed
kubectl get deployments  # Should see argo and training-operator
```

### Step 1: Build Docker Image

```bash
cd code/
docker build -f Dockerfile -t vllm-utils:v0.1 .

# Load into your cluster
# For k3d:
k3d image import vllm-utils:v0.1 --cluster vllm-cluster

# For kind:
kind load docker-image vllm-utils:v0.1 --name vllm-cluster
```

### Step 2: Create Persistent Storage

```bash
kubectl create -f model-pvc.yaml
```

This creates a 20GB PVC named `llm-model-storage` for storing models.

**Storage Structure**:
```
/models/
├── base/                  # Downloaded base model
├── optimized/
│   ├── fp16/             # FP16 version
│   ├── awq/              # AWQ quantized (4-bit)
│   └── gptq/             # GPTQ quantized (4-bit)
├── production/           # Selected best model
└── production_metrics.json  # Evaluation metrics
```

### Step 3: Run Complete Pipeline

```bash
kubectl create -f workflow.yaml
```

**Monitor Progress**:
```bash
# View workflow status
kubectl get workflows

# Get detailed status
kubectl get workflow vllm-llm-pipeline-xxxxx

# View logs
kubectl logs -f <pod-name>

# Watch all pods
kubectl get pods -w
```

**Expected Timeline**:
```
t=0s:   Model acquisition starts (downloading from HuggingFace)
t=60s:  Model downloaded, optimization starts (3 parallel jobs)
t=120s: All optimizations complete, selection starts
t=150s: Best model selected and copied to /models/production
t=150s: Inference service deployment starts
t=180s: vLLM service ready and serving
```

### Step 4: Test the Deployed Service

#### Option A: Port Forward and Test Locally

```bash
# Port forward the service
kubectl port-forward svc/vllm-llm-service 8000:8000

# In another terminal, test with Python client
python inference-client.py \
  --base_url http://localhost:8000/v1 \
  --model llm-model \
  --prompt "Explain distributed machine learning"

# Or use simple HTTP request
python http-inference-request.py
```

#### Option B: Test from Inside Cluster

```bash
# Create test pod
kubectl create -f test-pod.yaml

# Execute test
kubectl exec -it llm-test-pod -- python /test-service.py

# Test inference from pod
kubectl exec -it llm-test-pod -- python /inference-client.py \
  --base_url http://vllm-llm-service.kubeflow.svc.cluster.local:8000/v1 \
  --model llm-model \
  --prompt "What is Kubernetes?"
```

## 📝 Component Details

### Python Scripts

| Script | Purpose | Equivalent in Original Project |
|--------|---------|-------------------------------|
| `model-acquisition.py` | Download model from HuggingFace | `data-ingestion.py` |
| `model-optimization.py` | Create quantized versions | `multi-worker-distributed-training.py` |
| `model-selection.py` | Evaluate and select best model | `model-selection.py` |
| `inference-client.py` | Test inference endpoint | `inference-client.py` |
| `http-inference-request.py` | Simple HTTP test | `http-inference-request.py` |
| `test-service.py` | Verify model files | `predict-service.py` |

### Kubernetes Resources

| Resource | Purpose |
|----------|---------|
| `model-pvc.yaml` | Persistent volume for models |
| `workflow.yaml` | Complete Argo workflow |
| `inference-service.yaml` | Basic KServe deployment |
| `autoscaled-inference-service.yaml` | With autoscaling |
| `test-pod.yaml` | Debug/test pod |

## 🔧 Customization

### Change Model

Edit `workflow.yaml`:
```yaml
env:
- name: MODEL_NAME
  value: "meta-llama/Llama-2-7b-chat-hf"  # Your model
```

**Popular models**:
- `facebook/opt-125m` (small, for testing)
- `facebook/opt-1.3b` (medium)
- `meta-llama/Llama-2-7b-chat-hf` (requires auth)
- `mistralai/Mistral-7B-v0.1`
- `tiiuae/falcon-7b`

### Adjust Resources

For larger models, increase resources in `inference-service.yaml`:
```yaml
resources:
  limits:
    nvidia.com/gpu: 2  # Add GPUs
    memory: 32Gi       # More memory
```

### Tensor Parallelism

For multi-GPU inference, adjust vLLM args:
```yaml
args:
- --tensor-parallel-size=2  # Split across 2 GPUs
```

### Model Selection Weights

Edit `model-selection.py` to prioritize different metrics:
```python
weights = {
    "quality": 0.5,      # Increase for better quality
    "latency": 0.3,      # Increase for lower latency
    "throughput": 0.1,
    "memory": 0.1        # Increase for memory efficiency
}
```

## 🐛 Debugging

### Check Model Files

```bash
kubectl exec -it llm-test-pod -- ls -lh /models/base
kubectl exec -it llm-test-pod -- python /test-service.py
```

### View Workflow Status

```bash
# Get workflow
kubectl get workflow vllm-llm-pipeline-xxxxx -o yaml

# Check specific step
kubectl logs vllm-llm-pipeline-xxxxx-model-acquisition-xxxxx
```

### Test vLLM Service

```bash
# Check service status
kubectl get inferenceservice vllm-llm-service

# View logs
kubectl logs -l serving.kserve.io/inferenceservice=vllm-llm-service

# Describe for events
kubectl describe inferenceservice vllm-llm-service
```

### Common Issues

**Issue**: Model download timeout
```bash
# Increase timeout in workflow.yaml
activeDeadlineSeconds: 3600  # 1 hour
```

**Issue**: Out of memory
```bash
# Reduce max-model-len in vLLM args
- --max-model-len=1024  # Smaller context window
```

**Issue**: GPU not detected
```bash
# Check GPU availability
kubectl describe nodes | grep -i gpu

# Ensure GPU operator is installed
kubectl get pods -n gpu-operator-resources
```

## 📊 Monitoring

### Prometheus Metrics

vLLM exposes metrics at `/metrics`:
```bash
kubectl port-forward svc/vllm-llm-service 8000:8000
curl http://localhost:8000/metrics
```

**Key metrics**:
- `vllm:num_requests_running` - Active requests
- `vllm:num_requests_waiting` - Queue depth
- `vllm:gpu_cache_usage_perc` - KV cache usage
- `vllm:time_to_first_token_seconds` - Latency

### Load Testing

```bash
# Install hey (HTTP load testing)
# macOS:
brew install hey

# Linux:
wget https://hey-release.s3.us-east-2.amazonaws.com/hey_linux_amd64
chmod +x hey_linux_amd64

# Run load test
kubectl port-forward svc/vllm-llm-service 8000:8000

hey -n 100 -c 10 \
  -m POST \
  -H "Content-Type: application/json" \
  -d '{"model":"llm-model","messages":[{"role":"user","content":"Hello"}],"max_tokens":50}' \
  http://localhost:8000/v1/chat/completions
```

## 🧹 Cleanup

```bash
# Delete workflow
kubectl delete workflow --all

# Delete inference service
kubectl delete inferenceservice vllm-llm-service

# Delete test pod
kubectl delete pod llm-test-pod

# Delete PVC (WARNING: deletes all models)
kubectl delete pvc llm-model-storage

# Clean up images
docker rmi vllm-utils:v0.1
```

## 🎯 Production Considerations

### 1. Model Registry
Use a proper model registry instead of PVC:
```yaml
storageUri: "s3://my-bucket/models/llama-2-7b"
# or
storageUri: "gs://my-bucket/models/llama-2-7b"
```

### 2. GPU Nodes
Label GPU nodes and use node selectors:
```yaml
nodeSelector:
  nvidia.com/gpu: "true"
  gpu-type: "a100"
```

### 3. Authentication
Add HuggingFace token for gated models:
```yaml
env:
- name: HF_TOKEN
  valueFrom:
    secretKeyRef:
      name: hf-secret
      key: token
```

### 4. Monitoring
Install Prometheus + Grafana:
```bash
# Add Prometheus Operator
kubectl apply -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/main/bundle.yaml

# Create ServiceMonitor for vLLM
kubectl apply -f monitoring/vllm-service-monitor.yaml
```

### 5. Cost Optimization
- Use spot/preemptible instances
- Scale to zero when idle
- Use smaller quantized models
- Optimize batch sizes

## 📚 Additional Resources

- [vLLM Documentation](https://docs.vllm.ai/)
- [KServe Documentation](https://kserve.github.io/website/)
- [Argo Workflows](https://argoproj.github.io/argo-workflows/)
- [HuggingFace Models](https://huggingface.co/models)

## 🤝 Comparison with Original Project

| Original (TensorFlow) | vLLM Version |
|----------------------|--------------|
| Data ingestion | Model acquisition |
| Distributed training (3 models) | Model optimization (3 versions) |
| Model selection on accuracy | Model selection on quality+perf |
| TensorFlow Serving | vLLM OpenAI-compatible API |
| TFJob for training | Jobs for optimization |
| Same workflow orchestration | Same workflow orchestration |
| Same autoscaling patterns | Same autoscaling patterns |

**Key Insight**: The architectural patterns remain the same - only the ML runtime changes!

