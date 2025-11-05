# Kubernetes Basics for the vLLM Project

**A Beginner's Guide to Understanding Every Component**

This guide explains all Kubernetes concepts used in the vLLM project, from the ground up. No prior Kubernetes knowledge required!

---

## 📚 Table of Contents

1. [What is Kubernetes?](#what-is-kubernetes)
2. [Core Concepts](#core-concepts)
3. [Components Used in This Project](#components-used-in-this-project)
4. [File-by-File Explanation](#file-by-file-explanation)
5. [How Everything Connects](#how-everything-connects)
6. [Common Operations](#common-operations)

---

## What is Kubernetes?

**Simple Analogy**: Kubernetes is like a **smart apartment building manager** for your applications.

```
Your Application = Tenants (containers)
Kubernetes = Building Manager
  - Finds apartments (schedules containers)
  - Handles maintenance (restarts failed containers)
  - Manages utilities (networking, storage)
  - Scales up/down (adds/removes apartments)
  - Handles mail delivery (routing traffic)
```

**Technical Definition**: Kubernetes (K8s) is a platform for automating deployment, scaling, and management of containerized applications.

---

## Core Concepts

### 1. **Pod** 🏠
**What**: The smallest deployable unit. A pod is like a single apartment.

**Purpose**: Runs one or more containers that work together.

**Real Example**:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-app
spec:
  containers:
  - name: app
    image: nginx:latest
```

**Think of it as**: A single running instance of your application.

---

### 2. **Deployment** 🏢
**What**: Manages multiple identical pods. Like managing multiple apartments of the same type.

**Purpose**: Ensures you always have the desired number of pods running.

**Example**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 3  # Always keep 3 pods running
  template:
    spec:
      containers:
      - name: app
        image: nginx:latest
```

**Think of it as**: A manager that keeps 3 identical apartments ready.

**What it does**:
- If a pod crashes → Starts a new one automatically
- Want more pods? → Change `replicas: 5`
- Update version? → Gradually replaces old pods with new ones

---

### 3. **Service** 🚪
**What**: A stable address to access your pods. Like a building's street address.

**Purpose**: Provides a fixed endpoint even as pods come and go.

**Example**:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-app-service
spec:
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
```

**Think of it as**: The building's address stays the same even if tenants move in/out.

**Why needed**: Pods get random IP addresses that change. Services give you one stable address.

---

### 4. **PersistentVolumeClaim (PVC)** 💾
**What**: Request for storage. Like requesting a storage unit in the building.

**Purpose**: Store data that persists even if pods are deleted.

**Example**:
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: my-storage
spec:
  accessModes: [ "ReadWriteOnce" ]
  resources:
    requests:
      storage: 10Gi
```

**Think of it as**: A storage locker that exists independently of your apartment.

**Why needed**: Containers are ephemeral (temporary). PVCs keep data safe.

---

### 5. **Namespace** 🏘️
**What**: A virtual cluster within a cluster. Like different neighborhoods in a city.

**Purpose**: Organize and isolate resources.

**Example**:
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: production
```

**Think of it as**: Different buildings for different purposes (residential, commercial, etc.)

**In this project**: We use the `kubeflow` namespace for all ML components.

---

### 6. **ConfigMap** 📋
**What**: Store configuration data. Like a bulletin board with announcements.

**Purpose**: Separate configuration from application code.

**Example**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  database_url: "postgres://localhost:5432"
  log_level: "info"
```

**Think of it as**: A shared notice board that all apartments can read.

---

### 7. **Secret** 🔐
**What**: Store sensitive data (passwords, tokens). Like a secure lockbox.

**Purpose**: Keep sensitive information secure.

**Example**:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: api-keys
type: Opaque
data:
  token: YWJjMTIz  # base64 encoded
```

**Think of it as**: A secure mailbox only you can open.

---

## Components Used in This Project

### Standard Kubernetes Resources

| Component | Count | Purpose |
|-----------|-------|---------|
| **Pod** | Multiple | Run individual containers |
| **Deployment** | 1 | Manage vLLM server pods |
| **Service** | 1 | Expose vLLM endpoint |
| **PVC** | 1 | Store ML models (20GB) |
| **Namespace** | 1 | Isolate ML components (`kubeflow`) |

### Extended Kubernetes (Custom Resources)

| Component | What It Is | Purpose |
|-----------|-----------|---------|
| **Workflow** | Argo Workflows | Orchestrate multi-step pipelines |
| **InferenceService** | KServe | Manage ML model serving |
| **TFJob/PyTorchJob** | Kubeflow | Distributed ML training |

**Custom Resources**: Extensions to Kubernetes that add new types of objects.

**Analogy**: Like adding "gym", "pool", "theater" to your apartment building beyond just "apartments".

---

## File-by-File Explanation

### 📁 `basics/` - Learning Examples

Start here! These are simple examples to learn Kubernetes concepts.

#### `hello-world.yaml` - Simplest Pod
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: hello-llm
spec:
  containers:
  - name: hello
    image: alpine:3.7
    command: [echo]
    args: ["Hello from LLM Project!"]
```

**What it does**: Runs a single container that prints "Hello from LLM Project!" and exits.

**Kubernetes concepts**:
- `Pod`: Basic unit of deployment
- `containers`: List of containers in the pod
- `image`: Docker image to run
- `command`: What to execute

**Try it**:
```bash
kubectl create -f basics/hello-world.yaml
kubectl logs hello-llm
kubectl delete pod hello-llm
```

---

#### `argo-hello-world.yaml` - Simple Workflow
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: hello-vllm-
spec:
  entrypoint: hello
  serviceAccountName: argo
  templates:
  - name: hello
    container:
      image: alpine:3.7
      command: [echo]
      args: ["Hello from vLLM Workflow!"]
```

**What it does**: Runs the same hello example but using Argo Workflows.

**New concepts**:
- `Workflow`: Argo's way of defining job pipelines
- `generateName`: Creates unique names (hello-vllm-abc123)
- `entrypoint`: Which template to run first
- `serviceAccountName`: Permissions to use
- `templates`: Reusable job definitions

**Why use workflows**: For multi-step processes (download → process → deploy).

**Try it**:
```bash
kubectl create -f basics/argo-hello-world.yaml
kubectl get workflows
kubectl logs <workflow-pod-name>
```

---

#### `argo-dag-diamond.yaml` - Multi-Step Pipeline
```yaml
spec:
  templates:
  - name: diamond
    dag:
      tasks:
      - name: download-model
        template: echo
      - name: quantize-awq
        dependencies: [download-model]  # Waits for download
        template: echo
      - name: quantize-gptq
        dependencies: [download-model]  # Waits for download
        template: echo
      - name: select-best
        dependencies: [quantize-awq, quantize-gptq]  # Waits for both
        template: echo
```

**What it does**: Demonstrates parallel execution with dependencies.

**Execution flow**:
```
    download-model
         |
    +----+----+
    |         |
quantize-awq  quantize-gptq  (run in parallel)
    |         |
    +----+----+
         |
    select-best
```

**New concepts**:
- `dag`: Directed Acyclic Graph (defines workflow structure)
- `dependencies`: Which tasks must complete first
- Parallel execution: Multiple tasks run simultaneously

**Real-world use**: This is exactly how the main pipeline works!

---

#### `vllm-pod.yaml` - vLLM Server Pod
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: vllm-test
spec:
  containers:
  - name: vllm
    image: vllm/vllm-openai:latest
    args:
    - --model=facebook/opt-125m
    - --max-model-len=2048
    ports:
    - containerPort: 8000
    resources:
      limits:
        memory: 4Gi
      requests:
        memory: 2Gi
```

**What it does**: Runs a vLLM server with a small language model.

**New concepts**:
- `args`: Arguments passed to the container
- `ports`: Which ports the container exposes
- `resources`: Memory/CPU limits and requests
  - `requests`: Minimum resources needed
  - `limits`: Maximum resources allowed

**Try it**:
```bash
kubectl create -f basics/vllm-pod.yaml
kubectl port-forward vllm-test 8000:8000
# In another terminal:
curl http://localhost:8000/v1/models
```

---

### 📁 `manifests/` - Infrastructure Setup

These files install the required software (Argo Workflows, Kubeflow) into your cluster.

#### `manifests/kustomization.yaml` - Main Configuration
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: kubeflow

resources:
- argo-workflows/
- kubeflow-training/
```

**What it does**: Tells Kubernetes to install both Argo and Kubeflow.

**Kustomization**: A tool for managing multiple Kubernetes YAML files.

**Analogy**: Like a shopping list that says "install these packages".

---

#### `manifests/argo-workflows/kustomization.yaml`
```yaml
resources:
- https://github.com/argoproj/argo-workflows/releases/download/v3.4.0/install.yaml

patchesStrategicMerge:
- rbac-patch.yaml
```

**What it does**:
1. Downloads Argo Workflows installation from GitHub
2. Applies custom RBAC (permissions) patches

**RBAC (Role-Based Access Control)**: Defines who can do what.

---

#### `manifests/argo-workflows/rbac-patch.yaml`
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: argo-cluster-role
rules:
- apiGroups: [""]
  resources: ["pods", "configmaps"]
  verbs: ["create", "get", "list", "delete"]
```

**What it does**: Gives Argo permission to create/manage pods and other resources.

**Components**:
- `ClusterRole`: Set of permissions
- `apiGroups`: Which APIs to access
- `resources`: What types of objects (pods, services, etc.)
- `verbs`: What actions (create, delete, update, etc.)

**Why needed**: Kubernetes is secure by default - you must explicitly grant permissions.

---

#### `manifests/kubeflow-training/`
Contains Custom Resource Definitions (CRDs) for ML training jobs:
- `kubeflow.org_tfjobs.yaml`: TensorFlow training jobs
- `kubeflow.org_pytorchjobs.yaml`: PyTorch training jobs
- `kubeflow.org_mxjobs.yaml`: MXNet training jobs
- `kubeflow.org_xgboostjobs.yaml`: XGBoost training jobs

**What are CRDs**: They teach Kubernetes about new types of objects.

**Analogy**: Like teaching your building manager about new room types (gym, pool) beyond just apartments.

**Example TFJob**:
```yaml
apiVersion: kubeflow.org/v1
kind: TFJob  # New type Kubernetes didn't know about!
metadata:
  name: my-training
spec:
  tfReplicaSpecs:
    Worker:
      replicas: 4  # 4 workers for distributed training
```

---

### 📁 `code/` - Main Application

#### Storage: `model-pvc.yaml`
```yaml
kind: PersistentVolumeClaim
apiVersion: v1
metadata:
  name: llm-model-storage
  namespace: kubeflow
spec:
  accessModes: [ "ReadWriteMany" ]
  resources:
    requests:
      storage: 20Gi
```

**What it does**: Requests 20GB of storage for models.

**Key settings**:
- `ReadWriteMany`: Multiple pods can read/write simultaneously
- `20Gi`: 20 gigabytes of space

**Where it's used**: All workflow steps and the vLLM server mount this storage.

**Analogy**: A shared storage locker that everyone can access.

---

#### Workflow: `workflow.yaml`
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: vllm-llm-pipeline-
  namespace: kubeflow
spec:
  entrypoint: llm-pipeline
  volumes:
  - name: model-storage
    persistentVolumeClaim:
      claimName: llm-model-storage
  
  templates:
  - name: llm-pipeline
    steps:
    - - name: model-acquisition-step
        template: model-acquisition-step
    - - name: model-optimization-steps
        template: model-optimization-steps
    - - name: model-selection-step
        template: model-selection-step
    - - name: deploy-inference-service
        template: deploy-inference-service
```

**What it does**: Defines the complete 4-step ML pipeline.

**Structure breakdown**:

1. **Workflow metadata**:
   - `generateName`: Creates unique names (vllm-llm-pipeline-abc123)
   - `namespace`: Runs in the kubeflow namespace

2. **Shared volumes**:
   - Mounts the PVC so all steps can access models

3. **Pipeline steps**:
   - Each `-` is a step
   - `- -` means steps at the same level run in sequence
   - Sub-items in a step can run in parallel

**Execution**:
```
Step 1: model-acquisition         [Sequential]
   ↓
Step 2: model-optimization         [Sequential group]
   ├─ optimize-fp16   ┐
   ├─ optimize-awq    ├─ [Parallel within step]
   └─ optimize-gptq   ┘
   ↓
Step 3: model-selection           [Sequential]
   ↓
Step 4: deploy-inference-service  [Sequential]
```

---

#### Each Workflow Step Template:

**Model Acquisition Template**:
```yaml
- name: model-acquisition-step
  serviceAccountName: argo
  memoize:
    key: "model-download-{{workflow.parameters.model_name}}"
    maxAge: "24h"
  container:
    image: vllm-utils:v0.1
    command: ["python", "/model-acquisition.py"]
    env:
    - name: MODEL_NAME
      value: "facebook/opt-125m"
    volumeMounts:
    - name: model-storage
      mountPath: /models
```

**Components explained**:
- `serviceAccountName`: Which permissions to use
- `memoize`: Cache results for 24 hours (don't re-download)
- `container`: What to run
  - `image`: Docker image with our Python scripts
  - `command`: What script to execute
  - `env`: Environment variables
  - `volumeMounts`: Connect PVC to container at `/models`

**What happens**: Downloads model from HuggingFace to `/models/base/`

---

**Model Optimization Templates**:
```yaml
- name: optimize-fp16
  container:
    image: vllm-utils:v0.1
    command: 
    - python
    - /model-optimization.py
    - --source_model_dir=/models/base
    - --optimized_model_dir=/models/optimized/fp16
    - --optimization_type=fp16
    volumeMounts:
    - name: model-storage
      mountPath: /models
```

**What happens**: 
- Reads from `/models/base/`
- Creates optimized version
- Saves to `/models/optimized/fp16/`

Three of these run **in parallel** (fp16, awq, gptq).

---

**Model Selection Template**:
```yaml
- name: model-selection-step
  container:
    image: vllm-utils:v0.1
    command: ["python", "/model-selection.py"]
    volumeMounts:
    - name: model-storage
      mountPath: /models
```

**What happens**:
- Evaluates all 3 optimized models
- Picks the best one
- Copies winner to `/models/production/`

---

**Deploy Inference Service Template**:
```yaml
- name: deploy-inference-service
  serviceAccountName: argo
  resource:
    action: create
    manifest: |
      apiVersion: serving.kserve.io/v1beta1
      kind: InferenceService
      metadata:
        name: vllm-llm-service
      spec:
        predictor:
          containers:
          - name: vllm
            image: vllm/vllm-openai:latest
            args: [--model=/models/production]
```

**What happens**: Creates a KServe InferenceService (explained next).

**Key concept**: `resource` action means "create a Kubernetes resource". It's like saying "kubectl create -f <manifest>".

---

#### Serving: `inference-service.yaml`
```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: vllm-llm-service
  namespace: kubeflow
spec:
  predictor:
    minReplicas: 1
    maxReplicas: 3
    containers:
    - name: vllm
      image: vllm/vllm-openai:latest
      args:
      - --model=/models/production
      - --served-model-name=llm-model
      - --max-model-len=2048
      ports:
      - containerPort: 8000
      resources:
        limits:
          memory: 8Gi
          cpu: 4
        requests:
          memory: 4Gi
          cpu: 2
      volumeMounts:
      - name: model-storage
        mountPath: /models
        readOnly: true
```

**What it does**: Deploys vLLM server with autoscaling.

**Components**:
- `InferenceService`: KServe's custom resource for serving
- `predictor`: The ML model server configuration
  - `minReplicas: 1`: Always keep at least 1 pod
  - `maxReplicas: 3`: Scale up to 3 pods max
  - `containers`: The vLLM server configuration
    - `args`: vLLM startup arguments
    - `ports`: Expose port 8000
    - `resources`: CPU/memory requirements
    - `volumeMounts`: Access model storage (read-only)

**What KServe does automatically**:
1. Creates a Deployment with vLLM pods
2. Creates a Service for stable addressing
3. Sets up autoscaling based on traffic
4. Configures health checks
5. Manages rolling updates

---

#### Autoscaling: `autoscaled-inference-service.yaml`
```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: vllm-llm-service
  annotations:
    autoscaling.knative.dev/target: "10"
    autoscaling.knative.dev/metric: "concurrency"
spec:
  predictor:
    scaleTarget: 10
    scaleMetric: concurrency
    containers:
    - name: vllm
      # ... (same as inference-service.yaml)
```

**What's different**: Adds autoscaling configuration.

**Autoscaling settings**:
- `scaleTarget: 10`: Target 10 concurrent requests per pod
- `scaleMetric: concurrency`: Scale based on concurrent requests

**How it works**:
```
Traffic: 5 requests  → 1 pod  (5 < 10, don't scale)
Traffic: 15 requests → 2 pods (15/2 = 7.5 per pod)
Traffic: 50 requests → 5 pods (50/5 = 10 per pod)
Traffic: 2 requests  → 1 pod  (scale down)
```

---

#### Alternative: `vllm-service.yaml`
```yaml
apiVersion: v1
kind: Service
metadata:
  name: vllm-service
spec:
  selector:
    app: vllm-server
  ports:
  - port: 8000
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-server
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm-server
  template:
    metadata:
      labels:
        app: vllm-server
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        # ... rest of config
```

**What it does**: Simple deployment without KServe.

**When to use**:
- ✅ Testing/development
- ✅ Learning Kubernetes basics
- ✅ Fixed workload (no autoscaling needed)

**Comparison**:

| Feature | vllm-service.yaml | inference-service.yaml |
|---------|------------------|----------------------|
| Autoscaling | ❌ Manual | ✅ Automatic |
| Setup | Simpler | More complex |
| Features | Basic | Production-ready |
| Good for | Learning | Production |

---

#### Testing: `test-pod.yaml`
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: llm-test-pod
spec:
  containers:
  - name: test
    image: vllm-utils:v0.1
    command: ['sleep', 'infinity']
    volumeMounts:
    - name: model-storage
      mountPath: /models
```

**What it does**: Creates a pod you can enter to debug/test.

**Usage**:
```bash
# Create pod
kubectl create -f test-pod.yaml

# Enter pod
kubectl exec -it llm-test-pod -- bash

# Check models
ls -la /models/

# Run tests
python /test-service.py
```

**Why useful**: Lets you explore the PVC contents and test scripts manually.

---

## How Everything Connects

### The Big Picture

```
┌─────────────────────────────────────────────────────────────┐
│  Kubernetes Cluster                                          │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Namespace: kubeflow                                │    │
│  │                                                      │    │
│  │  ┌─────────────────────────────────────────┐       │    │
│  │  │  PersistentVolumeClaim                  │       │    │
│  │  │  Name: llm-model-storage (20GB)         │       │    │
│  │  │  /models/                                │       │    │
│  │  │  ├── base/                               │       │    │
│  │  │  ├── optimized/                          │       │    │
│  │  │  └── production/                         │       │    │
│  │  └─────────────────────────────────────────┘       │    │
│  │               ↑                                      │    │
│  │               │ (mounted by)                         │    │
│  │               │                                      │    │
│  │  ┌────────────┴────────────────────────────┐       │    │
│  │  │  Argo Workflow                           │       │    │
│  │  │  Name: vllm-llm-pipeline-xxxxx           │       │    │
│  │  │                                           │       │    │
│  │  │  Step 1: model-acquisition               │       │    │
│  │  │    Pod: downloads model to /models/base  │       │    │
│  │  │                                           │       │    │
│  │  │  Step 2: optimization (parallel)         │       │    │
│  │  │    Pod 1: FP16  → /models/optimized/fp16 │       │    │
│  │  │    Pod 2: AWQ   → /models/optimized/awq  │       │    │
│  │  │    Pod 3: GPTQ  → /models/optimized/gptq │       │    │
│  │  │                                           │       │    │
│  │  │  Step 3: model-selection                 │       │    │
│  │  │    Pod: copies best to /models/production│       │    │
│  │  │                                           │       │    │
│  │  │  Step 4: deploy-inference-service        │       │    │
│  │  │    Creates InferenceService ↓            │       │    │
│  │  └──────────────────────────────────────────┘       │    │
│  │                                                      │    │
│  │  ┌──────────────────────────────────────────┐       │    │
│  │  │  InferenceService: vllm-llm-service      │       │    │
│  │  │  (Created by workflow step 4)            │       │    │
│  │  │                                           │       │    │
│  │  │  ┌────────────────────────────────┐      │       │    │
│  │  │  │  vLLM Pod 1                    │      │       │    │
│  │  │  │  - Mounts /models/production   │      │       │    │
│  │  │  │  - Serves on port 8000         │      │       │    │
│  │  │  └────────────────────────────────┘      │       │    │
│  │  │                                           │       │    │
│  │  │  ┌────────────────────────────────┐      │       │    │
│  │  │  │  vLLM Pod 2 (autoscaled)       │      │       │    │
│  │  │  │  - Same config as Pod 1        │      │       │    │
│  │  │  └────────────────────────────────┘      │       │    │
│  │  │                                           │       │    │
│  │  │  ┌────────────────────────────────┐      │       │    │
│  │  │  │  Service (load balancer)       │      │       │    │
│  │  │  │  - Routes traffic to pods      │      │       │    │
│  │  │  │  - Port 8000                   │      │       │    │
│  │  │  └────────────────────────────────┘      │       │    │
│  │  └──────────────────────────────────────────┘       │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## Common Operations

### 1. View Resources

```bash
# See all pods
kubectl get pods

# See workflows
kubectl get workflows

# See inference services
kubectl get inferenceservices

# See storage
kubectl get pvc

# Detailed info
kubectl describe pod <pod-name>
kubectl describe inferenceservice vllm-llm-service
```

### 2. Check Logs

```bash
# Pod logs
kubectl logs <pod-name>

# Follow logs (live)
kubectl logs -f <pod-name>

# Previous container logs (if crashed)
kubectl logs <pod-name> --previous
```

### 3. Execute Commands in Pods

```bash
# Run a command
kubectl exec <pod-name> -- ls /models

# Interactive shell
kubectl exec -it <pod-name> -- bash

# Run Python script
kubectl exec <pod-name> -- python /test-service.py
```

### 4. Port Forwarding

```bash
# Forward pod port to localhost
kubectl port-forward <pod-name> 8000:8000

# Forward service port
kubectl port-forward svc/vllm-llm-service 8000:8000

# Now access at http://localhost:8000
```

### 5. Debugging

```bash
# Why is pod failing?
kubectl describe pod <pod-name>
kubectl logs <pod-name>

# Check events
kubectl get events --sort-by='.lastTimestamp'

# Check resource usage
kubectl top pods
kubectl top nodes
```

---

## Summary: Kubernetes Resource Types

| Resource Type | What It Is | Example in Project |
|--------------|------------|-------------------|
| **Pod** | Single container instance | Workflow steps, vLLM server |
| **Deployment** | Manages multiple pods | vLLM server deployment |
| **Service** | Stable network endpoint | vllm-llm-service |
| **PVC** | Persistent storage | llm-model-storage |
| **Namespace** | Logical separation | kubeflow |
| **ConfigMap** | Configuration data | Workflow cache |
| **Secret** | Sensitive data | API keys (if needed) |
| **Workflow** | Multi-step pipeline | vllm-llm-pipeline |
| **InferenceService** | ML serving | vllm-llm-service |

---

## Learning Path

```
Day 1: Basics
├─ Run hello-world.yaml (understand Pods)
├─ Run argo-hello-world.yaml (understand Workflows)
└─ Run vllm-pod.yaml (understand containers)

Day 2: Storage & Networking
├─ Create PVC (understand storage)
├─ Deploy vllm-service.yaml (understand Services)
└─ Port-forward and test (understand networking)

Day 3: Advanced
├─ Run complete workflow.yaml (understand pipelines)
├─ Explore InferenceService (understand KServe)
└─ Test autoscaling (understand scaling)

Day 4: Operations
├─ kubectl get/describe/logs (understand debugging)
├─ Modify resources (understand updates)
└─ Monitor metrics (understand observability)
```

---

## Quick Reference Commands

```bash
# Setup
kubectl create namespace kubeflow
kubectl config set-context --current --namespace=kubeflow

# Deploy
kubectl create -f <file.yaml>
kubectl apply -f <file.yaml>  # Create or update

# View
kubectl get <resource-type>
kubectl get pods
kubectl get workflows
kubectl get inferenceservices

# Details
kubectl describe <resource-type> <name>
kubectl logs <pod-name>

# Interactive
kubectl exec -it <pod-name> -- bash
kubectl port-forward <pod-name> 8000:8000

# Delete
kubectl delete <resource-type> <name>
kubectl delete pod my-pod
kubectl delete -f <file.yaml>

# Cleanup
kubectl delete namespace kubeflow  # Deletes everything in namespace
```

---

## Next Steps

1. **Run the basics examples** in order
2. **Read the main README.md** for project overview
3. **Follow QUICKSTART.md** to run the complete pipeline
4. **Experiment**: Modify YAML files and see what happens
5. **Debug**: Use `kubectl describe` and `logs` to investigate issues

---

## Additional Resources

- [Kubernetes Official Docs](https://kubernetes.io/docs/)
- [Argo Workflows Docs](https://argoproj.github.io/argo-workflows/)
- [KServe Docs](https://kserve.github.io/website/)
- [vLLM Docs](https://docs.vllm.ai/)

---

**You're now ready to understand every component in the vLLM project!** 🎉

Start with the `basics/` examples and work your way up. Don't worry if it seems complex - Kubernetes has a learning curve, but each concept builds on the previous one.

Happy learning! 🚀

