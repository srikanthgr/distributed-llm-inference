# Complete Files Reference - vLLM Project

**Quick lookup guide for every file in the project**

---

## 📑 All Files at a Glance

### 📖 Documentation (6 files)

| File | Purpose | Start Here? |
|------|---------|-------------|
| `README.md` | Main project overview | ✅ Yes - Read 2nd |
| `QUICKSTART.md` | 5-minute setup guide | ✅ Yes - Read 1st |
| `KUBERNETES_BASICS.md` | Beginner's K8s guide | ✅ Yes - Read 3rd |
| `ARCHITECTURE.md` | Design patterns comparison | Read after basics |
| `PROJECT_OVERVIEW.md` | Complete reference | Read last |
| `FILES_REFERENCE.md` | This file! | Reference anytime |

### 🎓 Basic Examples - `basics/` (6 files)

**Learning order**: Run them in this sequence!

| File | What It Teaches | Run Time | Difficulty |
|------|----------------|----------|------------|
| `hello-world.yaml` | Pods | 5 sec | ⭐ Easiest |
| `argo-hello-world.yaml` | Workflows | 10 sec | ⭐ |
| `argo-dag-diamond.yaml` | Parallel execution | 20 sec | ⭐⭐ |
| `argo-script-template.yaml` | Python in workflows | 30 sec | ⭐⭐ |
| `argo-resource-template.yaml` | Creating resources | 10 sec | ⭐⭐ |
| `vllm-pod.yaml` | vLLM server | 2 min | ⭐⭐⭐ |

### ⚙️ Infrastructure - `manifests/` (12+ files)

**Purpose**: Install Kubernetes operators (Argo, Kubeflow)

| File/Directory | What It Installs |
|---------------|------------------|
| `kustomization.yaml` | Main installer config |
| `argo-workflows/kustomization.yaml` | Argo Workflows (v3.4.0) |
| `argo-workflows/rbac-patch.yaml` | Argo permissions |
| `kubeflow-training/` | Kubeflow Training Operator |
| `kubeflow-training/crds/*.yaml` | TFJob, PyTorchJob definitions |
| `kubeflow-training/deployment.yaml` | Operator deployment |
| `kubeflow-training/service.yaml` | Operator service |
| `kubeflow-training/cluster-role*.yaml` | Permissions |

**When to use**: Run once during cluster setup
```bash
kubectl kustomize manifests | kubectl apply -f -
```

### 💻 Main Application - `code/` (17 files)

---

#### Python Scripts (6 files)

| File | Lines | What It Does | Runs When |
|------|-------|--------------|-----------|
| `model-acquisition.py` | ~20 | Downloads model from HuggingFace | Workflow Step 1 |
| `model-optimization.py` | ~100 | Creates FP16/AWQ/GPTQ versions | Workflow Step 2 |
| `model-selection.py` | ~160 | Evaluates & selects best model | Workflow Step 3 |
| `inference-client.py` | ~105 | Tests inference endpoint | Manual testing |
| `http-inference-request.py` | ~30 | Simple HTTP test | Manual testing |
| `test-service.py` | ~70 | Verifies model files | Manual debugging |

**Usage**:
```bash
# Scripts are copied into Docker image
# Run automatically by workflow, or manually:
kubectl exec <pod> -- python /model-acquisition.py
python inference-client.py  # From your laptop
```

---

#### Docker Configuration (1 file)

| File | Purpose | When to Build |
|------|---------|---------------|
| `Dockerfile` | Builds `vllm-utils:v0.1` image | Before running workflow |

**Contains**:
- Python 3.10
- Dependencies: `huggingface-hub`, `openai`, `requests`
- All 6 Python scripts

**Build & load**:
```bash
docker build -f Dockerfile -t vllm-utils:v0.1 .
k3d image import vllm-utils:v0.1 --cluster vllm-cluster
```

---

#### Storage Configuration (1 file)

| File | Creates | Size | Access Mode |
|------|---------|------|-------------|
| `model-pvc.yaml` | PersistentVolumeClaim | 20GB | ReadWriteMany |

**Creates**: `llm-model-storage` PVC

**Storage structure**:
```
/models/
├── base/                  # Downloaded model
├── optimized/
│   ├── fp16/             # Optimized versions
│   ├── awq/
│   └── gptq/
├── production/           # Selected best model
└── production_metrics.json
```

**Create it**:
```bash
kubectl create -f model-pvc.yaml
```

---

#### Main Workflow (1 file)

| File | Creates | Steps | Runtime |
|------|---------|-------|---------|
| `workflow.yaml` | Argo Workflow | 4 (7 pods total) | ~10-30 min |

**What it orchestrates**:
```
Step 1: Download model          (1 pod,  sequential)
Step 2: Optimize models         (3 pods, parallel)
Step 3: Select best             (1 pod,  sequential)
Step 4: Deploy serving          (Creates InferenceService)
```

**Components**:
- `llm-pipeline` template: Main entry point
- `model-acquisition-step`: Download from HuggingFace
- `optimize-fp16/awq/gptq`: Parallel optimization
- `model-selection-step`: Evaluation
- `deploy-inference-service`: KServe deployment

**Run it**:
```bash
kubectl create -f workflow.yaml
kubectl get workflows -w  # Watch progress
```

---

#### Serving Configurations (3 files)

| File | Type | Autoscaling | Best For |
|------|------|-------------|----------|
| `inference-service.yaml` | KServe | Basic (1-3 pods) | Production (simple) |
| `autoscaled-inference-service.yaml` | KServe | Advanced (1-5 pods) | Production (complex) |
| `vllm-service.yaml` | K8s Deployment | Manual | Development/Learning |

**`inference-service.yaml`**:
```yaml
minReplicas: 1
maxReplicas: 3
# Scales based on default metrics
```

**`autoscaled-inference-service.yaml`**:
```yaml
minReplicas: 1
maxReplicas: 5
scaleTarget: 10       # Target 10 concurrent requests
scaleMetric: concurrency
# Fine-tuned autoscaling
```

**`vllm-service.yaml`**:
```yaml
replicas: 1           # Fixed, no autoscaling
# Standard Kubernetes Deployment + Service
# Good for learning K8s basics
```

**When to use**:
- **Learning?** → Use `vllm-service.yaml`
- **Production?** → Use `inference-service.yaml` or `autoscaled-inference-service.yaml`
- **High traffic?** → Use `autoscaled-inference-service.yaml`

---

#### Testing/Debugging (2 files)

| File | Type | Purpose |
|------|------|---------|
| `test-pod.yaml` | Pod | Interactive debugging |
| `model-selection.yaml` | Pod | Standalone model selection |

**`test-pod.yaml`**:
```yaml
command: ['sleep', 'infinity']  # Stays running
volumeMounts: [model-storage]    # Access models
```

**Usage**:
```bash
kubectl create -f test-pod.yaml
kubectl exec -it llm-test-pod -- bash
# Now you're inside, can run:
ls /models/
python /test-service.py
```

**`model-selection.yaml`**:
Run model selection independently (not in workflow):
```bash
kubectl create -f model-selection.yaml
kubectl logs model-selection
```

---

#### Additional Files (2 files)

| File | Purpose |
|------|---------|
| `kind-gpu-config.yaml` | Kind cluster with GPU support |
| `.gitignore` | Files to exclude from git |

---

## 🎯 File Usage by Scenario

### Scenario 1: First Time Setup

```bash
# 1. Create cluster
k3d cluster create vllm-cluster

# 2. Install infrastructure
kubectl create ns kubeflow
kubectl config set-context --current --namespace=kubeflow
kubectl kustomize manifests | kubectl apply -f -

# 3. Build image
cd code/
docker build -f Dockerfile -t vllm-utils:v0.1 .
k3d image import vllm-utils:v0.1 --cluster vllm-cluster
```

**Files used**:
- `manifests/kustomization.yaml`
- `manifests/argo-workflows/*`
- `manifests/kubeflow-training/*`
- `code/Dockerfile`

---

### Scenario 2: Run Complete Pipeline

```bash
# 1. Create storage
kubectl create -f code/model-pvc.yaml

# 2. Run workflow
kubectl create -f code/workflow.yaml

# 3. Monitor
kubectl get workflows -w
kubectl get pods -w

# 4. Test (after completion)
kubectl port-forward svc/vllm-llm-service 8000:8000 &
python code/inference-client.py
```

**Files used**:
- `code/model-pvc.yaml`
- `code/workflow.yaml` (orchestrates these scripts:)
  - `code/model-acquisition.py`
  - `code/model-optimization.py`
  - `code/model-selection.py`
- `code/inference-client.py`

---

### Scenario 3: Learning Kubernetes

```bash
# Run examples in order
kubectl create -f basics/hello-world.yaml
kubectl logs hello-llm

kubectl create -f basics/argo-hello-world.yaml
kubectl get workflows

kubectl create -f basics/argo-dag-diamond.yaml
kubectl get workflows

kubectl create -f basics/vllm-pod.yaml
kubectl port-forward vllm-test 8000:8000
curl http://localhost:8000/v1/models
```

**Files used** (in order):
1. `basics/hello-world.yaml`
2. `basics/argo-hello-world.yaml`
3. `basics/argo-dag-diamond.yaml`
4. `basics/argo-script-template.yaml`
5. `basics/argo-resource-template.yaml`
6. `basics/vllm-pod.yaml`

---

### Scenario 4: Debugging

```bash
# Create test pod
kubectl create -f code/test-pod.yaml

# Enter pod
kubectl exec -it llm-test-pod -- bash

# Inside pod:
ls -la /models/
python /test-service.py
python /model-selection.py
```

**Files used**:
- `code/test-pod.yaml`
- `code/test-service.py`
- `code/model-selection.py`

---

### Scenario 5: Production Deployment

```bash
# Option A: Basic autoscaling
kubectl create -f code/inference-service.yaml

# Option B: Advanced autoscaling
kubectl create -f code/autoscaled-inference-service.yaml

# Test
kubectl port-forward svc/vllm-llm-service 8000:8000 &
python code/http-inference-request.py
```

**Files used**:
- `code/inference-service.yaml` OR
- `code/autoscaled-inference-service.yaml`
- `code/http-inference-request.py`

---

## 📊 File Dependencies

### Workflow Dependencies
```
workflow.yaml
├─ Requires: model-pvc.yaml (must exist first)
├─ Uses: vllm-utils:v0.1 image (from Dockerfile)
├─ Runs: model-acquisition.py
├─ Runs: model-optimization.py (3x in parallel)
├─ Runs: model-selection.py
└─ Creates: InferenceService (from workflow step 4)
```

### InferenceService Dependencies
```
inference-service.yaml
├─ Requires: model-pvc.yaml (models must exist)
├─ Uses: vllm/vllm-openai:latest image (public)
└─ Mounts: /models/production/ (created by workflow)
```

### Testing Dependencies
```
inference-client.py
├─ Requires: InferenceService running
├─ Requires: Port forwarding active
└─ Uses: OpenAI Python library

http-inference-request.py
├─ Requires: InferenceService running
├─ Requires: Port forwarding active
└─ Uses: requests library
```

---

## 🗂️ Files by Purpose

### Infrastructure Setup (Run Once)
- `manifests/kustomization.yaml`
- `manifests/argo-workflows/kustomization.yaml`
- `manifests/argo-workflows/rbac-patch.yaml`
- `manifests/kubeflow-training/*`

### Storage (Create Once)
- `code/model-pvc.yaml`

### Build Artifacts (Build Once, Use Many Times)
- `code/Dockerfile` → Builds `vllm-utils:v0.1`

### Pipeline Execution (Run When Needed)
- `code/workflow.yaml` (orchestrates everything)
  - Internally runs: `model-acquisition.py`, `model-optimization.py`, `model-selection.py`

### Model Serving (Deploy Once, Runs Continuously)
- `code/inference-service.yaml` OR
- `code/autoscaled-inference-service.yaml` OR
- `code/vllm-service.yaml`

### Testing/Debugging (Use Anytime)
- `code/inference-client.py`
- `code/http-inference-request.py`
- `code/test-pod.yaml`
- `code/test-service.py`
- `code/model-selection.yaml`

### Learning (Practice Anytime)
- `basics/*.yaml` (all 6 files)

### Documentation (Read Anytime)
- All `*.md` files in root directory

---

## 🚀 Typical Usage Flow

```
Day 1: Setup
1. Read QUICKSTART.md
2. Read KUBERNETES_BASICS.md
3. Run manifests/ (install infrastructure)
4. Build Dockerfile
5. Practice with basics/*.yaml

Day 2: Run Pipeline
1. Create model-pvc.yaml
2. Run workflow.yaml
3. Monitor progress
4. Wait for completion (~20 min)

Day 3: Test Serving
1. Check InferenceService status
2. Port-forward to service
3. Run inference-client.py
4. Run http-inference-request.py

Day 4: Explore & Debug
1. Use test-pod.yaml to explore
2. Run test-service.py
3. Modify and rerun components
4. Read ARCHITECTURE.md
```

---

## 📝 File Size & Complexity

| Category | File Count | Total Lines | Complexity |
|----------|-----------|-------------|------------|
| Documentation | 6 | ~2,500 | Low (reading) |
| Python Scripts | 6 | ~450 | Medium |
| Basic Examples | 6 | ~200 | Low |
| Main Configs | 6 | ~500 | Medium-High |
| Infrastructure | 12+ | ~7,000+ | High (but copy-paste) |
| **Total** | **36+** | **~10,650** | Mixed |

**Don't be intimidated!**
- Infrastructure files: Copy-paste, rarely modify
- Most files: < 100 lines
- Focus on: `code/*.yaml` and `code/*.py` (23 files)

---

## 🎯 Quick Reference Table

| I Want To... | Use This File |
|-------------|---------------|
| Learn Kubernetes basics | `basics/hello-world.yaml` |
| Understand workflows | `basics/argo-hello-world.yaml` |
| See parallel execution | `basics/argo-dag-diamond.yaml` |
| Download a model | `code/model-acquisition.py` |
| Optimize a model | `code/model-optimization.py` |
| Evaluate models | `code/model-selection.py` |
| Run complete pipeline | `code/workflow.yaml` |
| Deploy for production | `code/inference-service.yaml` |
| Test the API | `code/inference-client.py` |
| Debug models | `code/test-pod.yaml` |
| Simple deployment | `code/vllm-service.yaml` |

---

## ✅ Checklist: Files You MUST Know

**Absolute essentials** (understand these first):

- [ ] `QUICKSTART.md` - How to get started
- [ ] `KUBERNETES_BASICS.md` - Core concepts
- [ ] `code/model-pvc.yaml` - Storage setup
- [ ] `code/workflow.yaml` - Main pipeline
- [ ] `code/inference-service.yaml` - Serving setup

**Important for operations**:

- [ ] `code/model-acquisition.py` - Step 1
- [ ] `code/model-optimization.py` - Step 2
- [ ] `code/model-selection.py` - Step 3
- [ ] `code/inference-client.py` - Testing

**Nice to know**:

- [ ] `basics/*.yaml` - Learning examples
- [ ] `ARCHITECTURE.md` - Deep dive
- [ ] `code/test-pod.yaml` - Debugging

---

## 🎓 Learning Resources

**For each file category:**

1. **Basics**: Start here, run each example
2. **Manifests**: Read once, apply once, forget about it
3. **Python Scripts**: Read to understand logic
4. **YAML Configs**: Read and modify for your needs
5. **Documentation**: Reference when stuck

**Reading order**:
1. `QUICKSTART.md` (5 min)
2. `KUBERNETES_BASICS.md` (30 min)
3. `README.md` (10 min)
4. Run `basics/` examples (30 min)
5. Study `code/workflow.yaml` (20 min)
6. Deep dive: `ARCHITECTURE.md` (30 min)

---

**You now have a complete reference for every file!** 🎉

Use this document as a quick lookup when you're wondering "what does this file do?" or "which file should I use for X?"

Happy exploring! 🚀

