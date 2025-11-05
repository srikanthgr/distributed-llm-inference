# Quick Start Guide - 5 Minutes to Running LLM

Get from zero to serving an LLM in under 10 minutes!

## Prerequisites

- Kubernetes cluster (kind/k3d/minikube)
- kubectl configured
- Docker installed

## Step-by-Step

### 1. Create Cluster (2 min)
```bash
k3d cluster create vllm-cluster --image rancher/k3s:v1.25.3-k3s1
```

### 2. Install Infrastructure (2 min)
```bash
cd vllm-project/
kubectl create ns kubeflow
kubectl config set-context --current --namespace=kubeflow
kubectl kustomize manifests | kubectl apply -f -
```

Wait for pods to be ready:
```bash
kubectl get pods -n kubeflow -w
# Wait until all pods show Running
```

### 3. Build Image (1 min)
```bash
cd code/
docker build -f Dockerfile -t vllm-utils:v0.1 .
k3d image import vllm-utils:v0.1 --cluster vllm-cluster
```

### 4. Create Storage (10 sec)
```bash
kubectl create -f model-pvc.yaml
```

### 5. Run Pipeline (5+ min)
```bash
kubectl create -f workflow.yaml
```

Monitor progress:
```bash
kubectl get workflows -w
kubectl get pods -w
```

### 6. Test Service (30 sec)

Once workflow completes:
```bash
# Port forward
kubectl port-forward svc/vllm-llm-service 8000:8000 &

# Test
python inference-client.py
```

## Troubleshooting

**Workflow stuck?**
```bash
kubectl get workflow -o yaml | grep -A 20 status
kubectl logs -l workflows.argoproj.io/workflow=vllm-llm-pipeline
```

**Service not ready?**
```bash
kubectl describe inferenceservice vllm-llm-service
kubectl get pods -l serving.kserve.io/inferenceservice=vllm-llm-service
```

**Out of resources?**
```bash
# Use smaller model
# Edit workflow.yaml, change MODEL_NAME to "facebook/opt-125m"
```

## Next Steps

- Explore `basics/` for learning examples
- Read `code/README.md` for detailed docs
- Check `ARCHITECTURE.md` for design patterns
- Customize model in `workflow.yaml`

## Clean Up

```bash
kubectl delete workflow --all
kubectl delete inferenceservice --all
kubectl delete pvc llm-model-storage
k3d cluster delete vllm-cluster
```

Happy serving! 🚀

