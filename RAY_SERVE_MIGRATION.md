# Migration Guide: KServe → Ray Serve

**Complete guide to replace KServe with Ray Serve for vLLM serving**

---

## 📊 Quick Comparison

| Feature | KServe | Ray Serve |
|---------|--------|-----------|
| **Setup Complexity** | High (needs Knative/Istio) | Low (just Ray) |
| **Learning Curve** | Steep | Gentle |
| **Code Style** | YAML-based | Python-based |
| **Autoscaling** | Knative-based | Built-in Ray autoscaler |
| **Multi-model** | Via multiple InferenceServices | Native support |
| **Production Ready** | ✅ Very mature | ✅ Mature |
| **Vendor Lock-in** | None | None |

---

## 🎯 What Changes in Your Project

### Files That Stay The Same (No Changes) ✅
- ✅ All Python scripts (`model-acquisition.py`, `model-optimization.py`, `model-selection.py`)
- ✅ Workflow orchestration (`workflow.yaml` - mostly)
- ✅ Storage (`model-pvc.yaml`)
- ✅ Basic examples (`basics/`)
- ✅ Infrastructure manifests (`manifests/argo-workflows/`, `manifests/kubeflow-training/`)

### Files That Change 🔄
- 🔄 `inference-service.yaml` → `ray-serve-deployment.yaml`
- 🔄 `autoscaled-inference-service.yaml` → `ray-serve-autoscaled.yaml`
- 🔄 `workflow.yaml` (Step 4 only - deployment step)
- 🔄 `inference-client.py` (minor - endpoint URL only)

### Files You'll Add ➕
- ➕ `ray-vllm-server.py` - Ray Serve application code
- ➕ `ray-cluster.yaml` - Ray cluster setup
- ➕ `ray-service.yaml` - Kubernetes service for Ray

---

## 🚀 Step-by-Step Migration

### Step 1: Install Ray on Kubernetes

#### Option A: Using Ray Operator (Recommended)

```bash
# Install Ray Operator
kubectl create -k "github.com/ray-project/kuberay/ray-operator/config/default?ref=v0.6.0"

# Verify installation
kubectl get pods -n ray-system
```

#### Option B: Using Helm

```bash
# Add Ray Helm repo
helm repo add kuberay https://ray-project.github.io/kuberay-helm/
helm repo update

# Install Ray operator
helm install kuberay-operator kuberay/kuberay-operator --version 0.6.0

# Verify
kubectl get pods -l app.kubernetes.io/name=kuberay-operator
```

---

### Step 2: Create Ray Cluster Configuration

Create `code/ray-cluster.yaml`:

```yaml
apiVersion: ray.io/v1alpha1
kind: RayCluster
metadata:
  name: vllm-ray-cluster
  namespace: kubeflow
spec:
  # Ray head node
  rayVersion: '2.9.0'
  headGroupSpec:
    rayStartParams:
      dashboard-host: '0.0.0.0'
      num-cpus: '0'  # Don't schedule tasks on head
    template:
      spec:
        containers:
        - name: ray-head
          image: rayproject/ray:2.9.0-py310
          ports:
          - containerPort: 6379  # Redis
            name: redis
          - containerPort: 8265  # Dashboard
            name: dashboard
          - containerPort: 10001 # Client
            name: client
          - containerPort: 8000  # Serve
            name: serve
          resources:
            limits:
              cpu: "2"
              memory: "4Gi"
            requests:
              cpu: "1"
              memory: "2Gi"
          volumeMounts:
          - name: model-storage
            mountPath: /models
        volumes:
        - name: model-storage
          persistentVolumeClaim:
            claimName: llm-model-storage
  
  # Ray worker nodes (with GPUs)
  workerGroupSpecs:
  - replicas: 2
    minReplicas: 1
    maxReplicas: 5
    groupName: gpu-workers
    rayStartParams:
      num-cpus: "4"
      num-gpus: "1"
    template:
      spec:
        containers:
        - name: ray-worker
          image: rayproject/ray:2.9.0-py310-gpu
          resources:
            limits:
              nvidia.com/gpu: 1
              cpu: "4"
              memory: "16Gi"
            requests:
              cpu: "2"
              memory: "8Gi"
          volumeMounts:
          - name: model-storage
            mountPath: /models
        volumes:
        - name: model-storage
          persistentVolumeClaim:
            claimName: llm-model-storage
```

**Deploy Ray Cluster**:
```bash
kubectl create -f code/ray-cluster.yaml
kubectl get rayclusters -n kubeflow
kubectl get pods -l ray.io/cluster=vllm-ray-cluster
```

---

### Step 3: Create Ray Serve Application

Create `code/ray-vllm-server.py`:

```python
"""
Ray Serve application for vLLM inference
This replaces the KServe InferenceService
"""
from ray import serve
from vllm import LLM, SamplingParams
from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.engine.async_llm_engine import AsyncLLMEngine
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app for OpenAI-compatible API
app = FastAPI()

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    max_tokens: Optional[int] = 100
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = False

class CompletionRequest(BaseModel):
    model: str
    prompt: str
    max_tokens: Optional[int] = 100
    temperature: Optional[float] = 0.7

@serve.deployment(
    name="vllm-deployment",
    num_replicas=2,              # Start with 2 replicas
    ray_actor_options={
        "num_gpus": 1,            # Each replica gets 1 GPU
        "num_cpus": 2,
    },
    autoscaling_config={
        "min_replicas": 1,
        "max_replicas": 5,
        "target_num_ongoing_requests_per_replica": 5,
    },
)
@serve.ingress(app)
class VLLMDeployment:
    def __init__(self):
        """Initialize vLLM engine"""
        logger.info("Initializing vLLM engine...")
        
        # vLLM engine configuration
        engine_args = AsyncEngineArgs(
            model="/models/production",
            tensor_parallel_size=1,
            dtype="float16",
            max_model_len=2048,
            gpu_memory_utilization=0.9,
        )
        
        # Create async engine
        self.engine = AsyncLLMEngine.from_engine_args(engine_args)
        logger.info("vLLM engine initialized successfully!")
    
    @app.get("/")
    async def root(self):
        """Health check endpoint"""
        return {"status": "healthy", "service": "vllm-ray-serve"}
    
    @app.get("/v1/models")
    async def list_models(self):
        """List available models (OpenAI-compatible)"""
        return {
            "object": "list",
            "data": [
                {
                    "id": "llm-model",
                    "object": "model",
                    "created": 1234567890,
                    "owned_by": "organization"
                }
            ]
        }
    
    @app.post("/v1/completions")
    async def completions(self, request: CompletionRequest):
        """Text completion endpoint (OpenAI-compatible)"""
        logger.info(f"Received completion request: {request.prompt[:50]}...")
        
        # Generate using vLLM
        sampling_params = SamplingParams(
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        
        results = await self.engine.generate(
            request.prompt,
            sampling_params,
            request_id=f"completion-{id(request)}"
        )
        
        # Format response
        output_text = results.outputs[0].text if results.outputs else ""
        
        return {
            "id": f"cmpl-{id(request)}",
            "object": "text_completion",
            "created": 1234567890,
            "model": request.model,
            "choices": [
                {
                    "text": output_text,
                    "index": 0,
                    "logprobs": None,
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": len(request.prompt.split()),
                "completion_tokens": len(output_text.split()),
                "total_tokens": len(request.prompt.split()) + len(output_text.split())
            }
        }
    
    @app.post("/v1/chat/completions")
    async def chat_completions(self, request: ChatRequest):
        """Chat completion endpoint (OpenAI-compatible)"""
        logger.info(f"Received chat request with {len(request.messages)} messages")
        
        # Convert chat messages to prompt
        prompt = self._messages_to_prompt(request.messages)
        
        # Generate using vLLM
        sampling_params = SamplingParams(
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        
        results = await self.engine.generate(
            prompt,
            sampling_params,
            request_id=f"chat-{id(request)}"
        )
        
        # Format response
        output_text = results.outputs[0].text if results.outputs else ""
        
        return {
            "id": f"chatcmpl-{id(request)}",
            "object": "chat.completion",
            "created": 1234567890,
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": output_text
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(output_text.split()),
                "total_tokens": len(prompt.split()) + len(output_text.split())
            }
        }
    
    def _messages_to_prompt(self, messages: List[ChatMessage]) -> str:
        """Convert chat messages to a single prompt string"""
        prompt = ""
        for msg in messages:
            if msg.role == "system":
                prompt += f"System: {msg.content}\n"
            elif msg.role == "user":
                prompt += f"User: {msg.content}\n"
            elif msg.role == "assistant":
                prompt += f"Assistant: {msg.content}\n"
        prompt += "Assistant: "
        return prompt


# Deployment configuration
deployment = VLLMDeployment.bind()
```

---

### Step 4: Create Kubernetes Service for Ray Serve

Create `code/ray-service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: vllm-ray-service
  namespace: kubeflow
  labels:
    app: vllm-ray-serve
spec:
  type: ClusterIP
  ports:
  - name: serve
    port: 8000
    targetPort: 8000
    protocol: TCP
  selector:
    ray.io/cluster: vllm-ray-cluster
    ray.io/node-type: head
```

---

### Step 5: Deploy Ray Serve Application

Create `code/deploy-ray-serve.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ray-serve-config
  namespace: kubeflow
data:
  ray-vllm-server.py: |
    # Paste the entire ray-vllm-server.py content here
    # Or mount from a volume
---
apiVersion: batch/v1
kind: Job
metadata:
  name: ray-serve-deployer
  namespace: kubeflow
spec:
  template:
    spec:
      restartPolicy: OnFailure
      containers:
      - name: deployer
        image: rayproject/ray:2.9.0-py310
        command: ["/bin/bash", "-c"]
        args:
        - |
          # Install dependencies
          pip install vllm fastapi pydantic
          
          # Deploy to Ray cluster
          ray start --address="vllm-ray-cluster-head-svc:6379" --block &
          sleep 5
          
          # Deploy serve application
          serve deploy /config/ray-vllm-server.py
          
          # Keep running
          sleep infinity
        volumeMounts:
        - name: config
          mountPath: /config
        - name: model-storage
          mountPath: /models
      volumes:
      - name: config
        configMap:
          name: ray-serve-config
      - name: model-storage
        persistentVolumeClaim:
          claimName: llm-model-storage
```

**Or deploy directly via kubectl exec**:

```bash
# Copy Python file to Ray head
kubectl cp code/ray-vllm-server.py \
  kubeflow/vllm-ray-cluster-head-xxxxx:/tmp/

# Deploy to Ray Serve
kubectl exec -n kubeflow vllm-ray-cluster-head-xxxxx -- \
  serve deploy /tmp/ray-vllm-server.py
```

---

### Step 6: Update Workflow (Step 4 Only)

Modify `code/workflow.yaml` - only the deployment step changes:

```yaml
# Original Step 4 (KServe) - REMOVE THIS
# - name: deploy-inference-service
#   serviceAccountName: argo
#   resource:
#     action: create
#     manifest: |
#       apiVersion: serving.kserve.io/v1beta1
#       kind: InferenceService
#       ...

# New Step 4 (Ray Serve) - ADD THIS
- name: deploy-ray-serve
  serviceAccountName: argo
  script:
    image: rayproject/ray:2.9.0-py310
    command: [python]
    source: |
      import subprocess
      import time
      
      print("Installing dependencies...")
      subprocess.run(["pip", "install", "vllm", "fastapi", "pydantic"])
      
      print("Connecting to Ray cluster...")
      subprocess.run([
          "ray", "start", 
          "--address=vllm-ray-cluster-head-svc:6379"
      ])
      
      time.sleep(5)
      
      print("Deploying Ray Serve application...")
      subprocess.run(["serve", "deploy", "/ray-vllm-server.py"])
      
      print("Deployment successful!")
    volumeMounts:
    - name: model-storage
      mountPath: /models
    - name: serve-config
      mountPath: /
```

---

### Step 7: Update Client Code

Modify `code/inference-client.py` - minimal changes:

```python
# OLD (KServe)
# base_url = "http://vllm-llm-service:8000/v1"

# NEW (Ray Serve)
base_url = "http://vllm-ray-service:8000/v1"

# Everything else stays the same!
client = OpenAI(base_url=base_url, api_key="dummy")
response = client.chat.completions.create(...)
```

---

## 📁 Complete File Structure After Migration

```
code/
├── Existing files (no change):
│   ├── model-acquisition.py          ✅ No change
│   ├── model-optimization.py         ✅ No change
│   ├── model-selection.py            ✅ No change
│   ├── model-pvc.yaml                ✅ No change
│   └── Dockerfile                    ✅ No change
│
├── New Ray Serve files:
│   ├── ray-cluster.yaml              ➕ NEW
│   ├── ray-vllm-server.py            ➕ NEW
│   ├── ray-service.yaml              ➕ NEW
│   └── deploy-ray-serve.yaml         ➕ NEW
│
├── Modified files:
│   ├── workflow.yaml                 🔄 Step 4 changed
│   ├── inference-client.py           🔄 URL changed
│   └── http-inference-request.py     🔄 URL changed
│
└── Deprecated (can delete):
    ├── inference-service.yaml        ❌ Not needed
    └── autoscaled-inference-service.yaml ❌ Not needed
```

---

## 🚀 Complete Deployment Commands

### Full Migration Process

```bash
# 1. Install Ray Operator
kubectl create -k "github.com/ray-project/kuberay/ray-operator/config/default?ref=v0.6.0"

# 2. Create Ray Cluster
kubectl create -f code/ray-cluster.yaml

# 3. Wait for Ray cluster to be ready
kubectl wait --for=condition=Ready raycluster/vllm-ray-cluster -n kubeflow --timeout=300s

# 4. Create Ray Service
kubectl create -f code/ray-service.yaml

# 5. Build Docker image with Ray Serve app
cat > code/Dockerfile.ray << 'EOF'
FROM rayproject/ray:2.9.0-py310-gpu

RUN pip install vllm fastapi pydantic

COPY ray-vllm-server.py /app/
WORKDIR /app

CMD ["serve", "run", "ray-vllm-server:deployment"]
EOF

docker build -f code/Dockerfile.ray -t vllm-ray-serve:v0.1 code/
k3d image import vllm-ray-serve:v0.1 --cluster vllm-cluster

# 6. Deploy Ray Serve application
RAY_HEAD=$(kubectl get pods -n kubeflow -l ray.io/node-type=head -o jsonpath='{.items[0].metadata.name}')

kubectl cp code/ray-vllm-server.py kubeflow/$RAY_HEAD:/tmp/

kubectl exec -n kubeflow $RAY_HEAD -- \
  bash -c "pip install vllm fastapi pydantic && serve deploy /tmp/ray-vllm-server.py"

# 7. Port forward and test
kubectl port-forward -n kubeflow svc/vllm-ray-service 8000:8000 &

# 8. Test with client
python code/inference-client.py --base_url http://localhost:8000/v1
```

---

## 🔄 Side-by-Side Comparison

### KServe Approach (YAML-heavy)

```yaml
# inference-service.yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: vllm-service
spec:
  predictor:
    minReplicas: 1
    maxReplicas: 5
    containers:
    - name: vllm
      image: vllm/vllm-openai:latest
      args: [--model=/models/production]
```

**Pros**: Declarative, GitOps-friendly
**Cons**: Less flexible, needs Knative/Istio

---

### Ray Serve Approach (Python-based)

```python
# ray-vllm-server.py
@serve.deployment(
    num_replicas=2,
    autoscaling_config={
        "min_replicas": 1,
        "max_replicas": 5,
    }
)
class VLLMDeployment:
    def __init__(self):
        self.engine = AsyncLLMEngine(...)
    
    async def __call__(self, request):
        return await self.engine.generate(...)
```

**Pros**: Python-native, more flexible, easier to customize
**Cons**: Less declarative, requires Python knowledge

---

## ⚡ Advanced Ray Serve Features

### 1. Multi-Model Serving

```python
# Serve multiple models from one deployment
@serve.deployment
class MultiModelDeployment:
    def __init__(self):
        self.models = {
            "llama-7b": load_model("/models/llama-7b"),
            "llama-13b": load_model("/models/llama-13b"),
        }
    
    async def __call__(self, request):
        model_name = request.model
        return await self.models[model_name].generate(...)

# Deploy
serve.run(MultiModelDeployment.bind())
```

### 2. Custom Autoscaling Logic

```python
@serve.deployment(
    autoscaling_config={
        "min_replicas": 1,
        "max_replicas": 10,
        "target_num_ongoing_requests_per_replica": 3,
        "upscale_delay_s": 10,      # Fast scale up
        "downscale_delay_s": 600,   # Slow scale down
    }
)
class SmartScalingDeployment:
    # Your model code
    pass
```

### 3. Request Batching

```python
@serve.deployment
class BatchedDeployment:
    def __init__(self):
        self.model = load_model()
    
    @serve.batch(max_batch_size=8, batch_wait_timeout_s=0.1)
    async def handle_batch(self, requests):
        # Process batch together
        prompts = [r.prompt for r in requests]
        return await self.model.generate(prompts)
```

### 4. Monitoring & Metrics

```python
from ray.serve.metrics import Counter, Histogram

@serve.deployment
class MonitoredDeployment:
    def __init__(self):
        self.request_counter = Counter(
            "num_requests",
            description="Number of requests"
        )
        self.latency_histogram = Histogram(
            "request_latency",
            description="Request latency",
            boundaries=[0.1, 0.5, 1.0, 2.0]
        )
    
    async def __call__(self, request):
        self.request_counter.inc()
        
        start = time.time()
        response = await self.model.generate(...)
        duration = time.time() - start
        
        self.latency_histogram.observe(duration)
        return response
```

---

## 📊 Performance Comparison

| Metric | KServe | Ray Serve |
|--------|--------|-----------|
| **Cold Start** | ~30-60s | ~20-40s |
| **Request Latency** | Similar | Similar |
| **Throughput** | High | High |
| **GPU Utilization** | 85-90% | 85-90% |
| **Memory Overhead** | ~500MB | ~300MB |
| **Autoscale Speed** | Medium (Knative) | Fast (Native) |

**Verdict**: Performance is comparable. Ray Serve is slightly lighter.

---

## 🎯 Pros & Cons Summary

### Advantages of Ray Serve Over KServe

✅ **Simpler Setup**
- No Knative, no Istio
- Just Ray operator

✅ **Python-Native**
- Define everything in Python
- More flexible logic
- Easier debugging

✅ **Better Multi-Model Support**
- Native multi-model serving
- Dynamic model loading
- Easy model routing

✅ **Integrated Ecosystem**
- Works seamlessly with Ray Data
- Ray Tune for hyperparameter tuning
- Ray Train for distributed training

✅ **Lighter Weight**
- Less infrastructure overhead
- Faster cold starts

### Disadvantages of Ray Serve vs KServe

❌ **Less Declarative**
- Python code vs YAML
- Harder to version control serving logic

❌ **Fewer Integrations**
- Less mature ecosystem
- Fewer out-of-box connectors

❌ **Less K8s-Native**
- KServe feels more "Kubernetes-native"
- Ray feels like "running on Kubernetes"

❌ **GitOps**
- KServe better for GitOps workflows
- Ray Serve requires code deployment

---

## 🔄 Rollback Plan (If Needed)

If you need to switch back to KServe:

```bash
# 1. Delete Ray Serve deployment
kubectl delete raycluster vllm-ray-cluster -n kubeflow

# 2. Restore KServe deployment
kubectl create -f code/inference-service.yaml

# 3. Update client URL back
# base_url = "http://vllm-llm-service:8000/v1"
```

---

## 🎓 Learning Resources

**Ray Serve Documentation**:
- [Official Docs](https://docs.ray.io/en/latest/serve/)
- [Ray Serve Examples](https://github.com/ray-project/ray/tree/master/python/ray/serve/examples)
- [LLM Serving with Ray](https://docs.ray.io/en/latest/serve/tutorials/vllm-example.html)

**Video Tutorials**:
- [Ray Summit Talks](https://www.youtube.com/c/AnotheraySummit)
- [Ray Serve Intro](https://www.youtube.com/watch?v=CPR7pYaJMg)

---

## ✅ Final Recommendation

### When to Use Ray Serve:
- ✅ Python-first team
- ✅ Complex serving logic needed
- ✅ Want simpler infrastructure
- ✅ Multi-model serving
- ✅ Using Ray for other tasks (data, training)

### When to Keep KServe:
- ✅ Prefer declarative YAML
- ✅ GitOps-heavy workflow
- ✅ Multi-framework serving (TF, PyTorch, etc.)
- ✅ Need enterprise features
- ✅ Team comfortable with Knative

---

## 🚀 Quick Start Commands

```bash
# Complete migration in one go:

# 1. Install Ray
kubectl create -k "github.com/ray-project/kuberay/ray-operator/config/default?ref=v0.6.0"

# 2. Deploy everything
kubectl create -f code/ray-cluster.yaml
kubectl create -f code/ray-service.yaml

# 3. Deploy serve app
RAY_HEAD=$(kubectl get pods -n kubeflow -l ray.io/node-type=head -o name)
kubectl cp code/ray-vllm-server.py $RAY_HEAD:/tmp/
kubectl exec $RAY_HEAD -- serve deploy /tmp/ray-vllm-server.py

# 4. Test
kubectl port-forward svc/vllm-ray-service 8000:8000
python code/inference-client.py
```

**That's it! You're now running vLLM with Ray Serve!** 🎉

---

**Both KServe and Ray Serve are excellent choices. Pick based on your team's preferences and use case!** 🚀

