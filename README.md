# vLLM Distributed Inference Project

This project demonstrates production-grade distributed LLM inference patterns using vLLM, following the same architecture as the traditional ML project but adapted for Large Language Models.

## Architecture

- **Kubernetes**: Container orchestration
- **Argo Workflows**: Pipeline orchestration
- **vLLM**: High-performance LLM inference
- **KServe**: Model serving with autoscaling
- **Kubeflow Training Operator**: (Optional) For fine-tuning

## Cluster Setup

Navigate to the project directory:
```bash
cd vllm-project/
```

### Create Cluster

Via `kind`:
```bash
go install sigs.k8s.io/kind@v0.17.0
kind create cluster --name vllm-cluster --image kindest/node:v1.25.3 --config kind-gpu-config.yaml
```

Or via `k3d`:
```bash
k3d cluster create vllm-cluster --image rancher/k3s:v1.25.3-k3s1
```

### Install Infrastructure

```bash
kubectl create ns kubeflow
kubectl config set-context --current --namespace=kubeflow
kubectl kustomize manifests | kubectl apply -f -
```

This installs:
- Argo Workflows
- Kubeflow Training Operator (for optional fine-tuning)
- Required RBAC permissions

## Learning Path

Start with basic examples to understand each component:

1. **Kubernetes basics**: `basics/hello-world.yaml`
2. **Argo Workflows**: `basics/argo-hello-world.yaml`
3. **Workflow DAG**: `basics/argo-dag-diamond.yaml`
4. **vLLM Pod**: `basics/vllm-pod.yaml`

## Run Complete LLM Pipeline

See detailed instructions [here](code/README.md).

## Workflow Overview

```
1. Model Acquisition  → Download LLM from HuggingFace
2. Model Optimization → Create quantized versions (FP16, AWQ, GPTQ)
3. Model Selection    → Evaluate and choose best version
4. Deploy Serving     → KServe + vLLM with autoscaling
```

## Clean-up

```bash
kubectl delete ns kubeflow
k3d cluster delete vllm-cluster
# or
kind delete cluster --name vllm-cluster
```

