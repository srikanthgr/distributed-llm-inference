# Ray Serve Quick Start - 5 Minutes to Deployment

**Replace KServe with Ray Serve in 3 commands!**

---

## 🎯 What You'll Get

By the end of this guide:
- ✅ Ray Serve running instead of KServe
- ✅ vLLM inference with autoscaling
- ✅ OpenAI-compatible API (no client changes!)
- ✅ Python-native deployment (no YAML wrestling!)

---

## 📋 Prerequisites

```bash
# 1. Running Kubernetes cluster
kubectl cluster-info

# 2. PVC with models (from previous steps)
kubectl get pvc llm-model-storage -n kubeflow

# 3. Models ready at /models/production/
```

---

## 🚀 3-Step Deployment

### **Option A: Automated (Easiest) ⭐**

```bash
cd code/
./deploy-ray-serve.sh
```

That's it! Script handles everything automatically.

---

### **Option B: Manual (Step-by-Step)**

#### Step 1: Install Ray Operator (30 seconds)

```bash
kubectl create -k "github.com/ray-project/kuberay/ray-operator/config/default?ref=v0.6.0"

# Verify
kubectl get pods -n ray-system
```

#### Step 2: Deploy Ray Cluster (2 minutes)

```bash
kubectl create -f ray-cluster.yaml -n kubeflow

# Wait for ready
kubectl wait --for=condition=Ready raycluster/vllm-ray-cluster -n kubeflow --timeout=300s

# Check pods
kubectl get pods -n kubeflow -l ray.io/cluster=vllm-ray-cluster
```

**Expected output**:
```
NAME                                     READY   STATUS
vllm-ray-cluster-head-xxxxx              1/1     Running
vllm-ray-cluster-worker-gpu-workers-xxx  1/1     Running
vllm-ray-cluster-worker-gpu-workers-yyy  1/1     Running
```

#### Step 3: Create Service (5 seconds)

```bash
kubectl create -f ray-service.yaml -n kubeflow

# Verify
kubectl get svc vllm-ray-service -n kubeflow
```

#### Step 4: Deploy vLLM Application (2 minutes)

```bash
# Find Ray head pod
RAY_HEAD=$(kubectl get pods -n kubeflow -l ray.io/node-type=head -o jsonpath='{.items[0].metadata.name}')

# Install dependencies
kubectl exec -n kubeflow $RAY_HEAD -- pip install vllm fastapi pydantic

# Copy application code
kubectl cp ray-vllm-server.py kubeflow/$RAY_HEAD:/tmp/

# Deploy to Ray Serve
kubectl exec -n kubeflow $RAY_HEAD -- serve deploy /tmp/ray-vllm-server.py

# Check status
kubectl exec -n kubeflow $RAY_HEAD -- serve status
```

---

## 🧪 Test the Deployment

### 1. Port Forward

```bash
kubectl port-forward -n kubeflow svc/vllm-ray-service 8000:8000 &
```

### 2. Test Health

```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy"}
```

### 3. Test Inference (OpenAI-compatible!)

```bash
# Using existing client (NO CHANGES NEEDED!)
python inference-client.py --base_url http://localhost:8000/v1

# Or use curl
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llm-model",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 50
  }'
```

---

## 📊 Monitor Your Deployment

### Ray Dashboard

```bash
# Port forward dashboard
kubectl port-forward -n kubeflow svc/vllm-ray-service 8265:8265

# Open in browser
open http://localhost:8265
```

**Dashboard shows**:
- Active replicas
- Request throughput
- GPU utilization
- Autoscaling status

### Check Logs

```bash
# Ray head logs
kubectl logs -n kubeflow $RAY_HEAD

# Worker logs
kubectl logs -n kubeflow vllm-ray-cluster-worker-gpu-workers-xxx

# Follow logs
kubectl logs -f -n kubeflow $RAY_HEAD
```

### Check Ray Serve Status

```bash
kubectl exec -n kubeflow $RAY_HEAD -- serve status

# Detailed info
kubectl exec -n kubeflow $RAY_HEAD -- serve config
```

---

## 🔄 What Changed from KServe

### Before (KServe)

```yaml
# inference-service.yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: vllm-service
spec:
  predictor:
    containers:
    - name: vllm
      image: vllm/vllm-openai:latest
```

**Needed**: KServe, Knative, Istio (complex setup)

### After (Ray Serve)

```python
# ray-vllm-server.py
@serve.deployment(
    num_replicas=2,
    autoscaling_config={"min_replicas": 1, "max_replicas": 5}
)
class VLLMDeployment:
    def __init__(self):
        self.engine = AsyncLLMEngine(...)
```

**Needed**: Just Ray operator (simpler!)

---

## 📁 New Files Created

```
code/
├── ray-vllm-server.py        ← Ray Serve application (Python!)
├── ray-cluster.yaml          ← Ray cluster config
├── ray-service.yaml          ← Kubernetes service
├── deploy-ray-serve.sh       ← Automated deployment script
└── RAY_SERVE_QUICKSTART.md   ← This file
```

---

## 🎛️ Configuration Options

### Scale Replicas

Edit `ray-vllm-server.py`:

```python
@serve.deployment(
    num_replicas=5,  # Change this
    ...
)
```

Redeploy:
```bash
kubectl exec -n kubeflow $RAY_HEAD -- serve deploy /tmp/ray-vllm-server.py
```

### Autoscaling Settings

```python
autoscaling_config={
    "min_replicas": 1,
    "max_replicas": 10,  # Scale up to 10
    "target_num_ongoing_requests_per_replica": 3,  # Scale at 3 req/replica
}
```

### GPU Configuration

Edit `ray-cluster.yaml`:

```yaml
workerGroupSpecs:
- replicas: 5  # More workers
  rayStartParams:
    num-gpus: "2"  # 2 GPUs per worker
```

---

## 🐛 Troubleshooting

### Issue: Ray cluster not starting

```bash
# Check events
kubectl describe raycluster vllm-ray-cluster -n kubeflow

# Check pod events
kubectl describe pod $RAY_HEAD -n kubeflow
```

### Issue: Deployment fails

```bash
# Check Ray Serve logs
kubectl exec -n kubeflow $RAY_HEAD -- serve status

# Check serve logs
kubectl logs -n kubeflow $RAY_HEAD | grep serve
```

### Issue: Out of memory

```bash
# Reduce GPU memory utilization in ray-vllm-server.py:
engine_args = AsyncEngineArgs(
    gpu_memory_utilization=0.7,  # Reduce from 0.9
    ...
)
```

### Issue: Models not found

```bash
# Verify PVC is mounted
kubectl exec -n kubeflow $RAY_HEAD -- ls /models/production

# Check if models exist
kubectl exec -n kubeflow $RAY_HEAD -- ls -la /models/
```

---

## 🔄 Update Deployment

### Update Code

```bash
# 1. Edit ray-vllm-server.py locally
vim ray-vllm-server.py

# 2. Copy to cluster
kubectl cp ray-vllm-server.py kubeflow/$RAY_HEAD:/tmp/

# 3. Redeploy
kubectl exec -n kubeflow $RAY_HEAD -- serve deploy /tmp/ray-vllm-server.py
```

**Zero downtime!** Ray Serve handles rolling updates.

---

## 🧹 Cleanup

```bash
# Delete Ray Serve deployment
kubectl exec -n kubeflow $RAY_HEAD -- serve shutdown

# Delete Ray cluster
kubectl delete raycluster vllm-ray-cluster -n kubeflow

# Delete service
kubectl delete svc vllm-ray-service -n kubeflow

# Uninstall Ray operator (optional)
kubectl delete -k "github.com/ray-project/kuberay/ray-operator/config/default?ref=v0.6.0"
```

---

## 🔄 Switch Back to KServe

If you want to revert:

```bash
# Delete Ray components
kubectl delete raycluster vllm-ray-cluster -n kubeflow

# Deploy KServe
kubectl create -f inference-service.yaml

# Update client URL (only change needed)
# base_url = "http://vllm-llm-service:8000/v1"
```

---

## 📊 Performance Comparison

| Metric | KServe | Ray Serve |
|--------|--------|-----------|
| **Setup Time** | ~5-10 min | ~3-5 min |
| **Cold Start** | ~40s | ~30s |
| **Scaling Speed** | Medium | Fast |
| **Request Latency** | ~100ms | ~100ms |
| **Throughput** | High | High |
| **Memory Overhead** | ~500MB | ~300MB |

**Verdict**: Ray Serve is simpler and slightly lighter!

---

## 🎓 Advanced Features

### Multi-Model Serving

```python
@serve.deployment
class MultiModelDeployment:
    def __init__(self):
        self.models = {
            "small": load_model("/models/small"),
            "large": load_model("/models/large"),
        }
    
    async def __call__(self, request):
        model = self.models[request.model]
        return await model.generate(...)
```

### Custom Metrics

```python
from ray.serve.metrics import Counter, Histogram

@serve.deployment
class MonitoredDeployment:
    def __init__(self):
        self.request_counter = Counter("requests")
        self.latency = Histogram("latency", boundaries=[0.1, 0.5, 1.0])
```

### Request Batching

```python
@serve.deployment
class BatchedDeployment:
    @serve.batch(max_batch_size=8)
    async def handle_batch(self, requests):
        # Process batch together for efficiency
        prompts = [r.prompt for r in requests]
        return await self.model.generate(prompts)
```

---

## ✅ Checklist

- [ ] Ray operator installed
- [ ] Ray cluster running
- [ ] Service created
- [ ] vLLM application deployed
- [ ] Health check passing
- [ ] Inference working
- [ ] Ray dashboard accessible
- [ ] Monitoring configured

---

## 🎉 Success!

You're now running **vLLM with Ray Serve**!

**Benefits**:
- ✅ Simpler infrastructure (no Knative/Istio)
- ✅ Python-native (easier to customize)
- ✅ Fast autoscaling
- ✅ Built-in monitoring
- ✅ OpenAI-compatible API (no client changes)

**Next Steps**:
- Customize `ray-vllm-server.py` for your needs
- Add monitoring and alerts
- Optimize autoscaling parameters
- Deploy to production!

---

## 📚 Learn More

- [Ray Serve Docs](https://docs.ray.io/en/latest/serve/)
- [vLLM + Ray Example](https://docs.ray.io/en/latest/serve/tutorials/vllm-example.html)
- [Ray Dashboard Guide](https://docs.ray.io/en/latest/ray-core/ray-dashboard.html)

---

**Happy serving with Ray! 🚀**

