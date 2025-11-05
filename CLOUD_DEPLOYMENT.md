# Cloud Deployment Guide - vLLM Project

**Deploy to AWS, GCP, Azure, or Any Kubernetes Platform**

---

## ✅ Yes, This Project is 100% Cloud-Portable!

**Why?** Because it's built on **Kubernetes**, the universal cloud standard.

```
This Project
    ↓
  Kubernetes (Standard API)
    ↓
┌─────────┬─────────┬─────────┬─────────┐
│   AWS   │   GCP   │  Azure  │  Others │
│   EKS   │   GKE   │   AKS   │ On-Prem │
└─────────┴─────────┴─────────┴─────────┘
```

**Think of it like**: You write once in HTML (Kubernetes), and it works on any browser (cloud platform)!

---

## 🌐 What Works Everywhere (No Changes Needed)

### ✅ Core Components (100% Portable)

| Component | Portability |
|-----------|-------------|
| All Python scripts (`*.py`) | ✅ 100% portable |
| Workflow logic (`workflow.yaml`) | ✅ 100% portable |
| InferenceService (`inference-service.yaml`) | ✅ 100% portable |
| Argo Workflows | ✅ 100% portable |
| KServe | ✅ 100% portable |
| Kubeflow Training Operator | ✅ 100% portable |
| Basic Kubernetes resources | ✅ 100% portable |
| Docker images | ✅ 100% portable |

**Bottom line**: 95% of your code runs unchanged on any cloud! 🎉

---

## 🔧 What Needs Cloud-Specific Configuration

### ⚙️ Minor Adjustments Required (5% of code)

| Component | What Changes | Difficulty |
|-----------|-------------|------------|
| Storage class | Cloud provider name | Easy |
| GPU node selection | GPU types available | Easy |
| Load balancer | Cloud LB annotations | Easy |
| Ingress | Cloud ingress controller | Medium |
| Managed services | Optional optimizations | Medium |

**These are just configuration changes, not code rewrites!**

---

## ☁️ Deployment by Cloud Platform

### 1. Amazon Web Services (AWS)

#### **Kubernetes Service: Amazon EKS**

**Step 1: Create EKS Cluster**
```bash
# Using eksctl (easiest)
eksctl create cluster \
  --name vllm-cluster \
  --region us-west-2 \
  --nodegroup-name gpu-nodes \
  --node-type g4dn.xlarge \
  --nodes 2 \
  --nodes-min 1 \
  --nodes-max 5

# Or using AWS Console / Terraform / CloudFormation
```

**Step 2: Install GPU Support**
```bash
# Install NVIDIA device plugin
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.0/nvidia-device-plugin.yml
```

**Step 3: Configure Storage**
```yaml
# model-pvc-aws.yaml
kind: PersistentVolumeClaim
apiVersion: v1
metadata:
  name: llm-model-storage
spec:
  accessModes: [ "ReadWriteOnce" ]
  storageClassName: gp3  # AWS EBS gp3 (SSD)
  resources:
    requests:
      storage: 100Gi
```

**Step 4: Deploy Infrastructure**
```bash
# Same commands as before!
kubectl create ns kubeflow
kubectl kustomize manifests | kubectl apply -f -
```

**Step 5: Build & Push Image**
```bash
# Push to Amazon ECR
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-west-2.amazonaws.com

docker build -t vllm-utils:v0.1 .
docker tag vllm-utils:v0.1 123456789.dkr.ecr.us-west-2.amazonaws.com/vllm-utils:v0.1
docker push 123456789.dkr.ecr.us-west-2.amazonaws.com/vllm-utils:v0.1
```

**Step 6: Update Image References**
```yaml
# In workflow.yaml, update:
image: 123456789.dkr.ecr.us-west-2.amazonaws.com/vllm-utils:v0.1
```

**Step 7: Run the Pipeline!**
```bash
kubectl create -f code/workflow.yaml
# Everything else works the same!
```

#### **AWS-Specific Optimizations**

**Use S3 for Model Storage:**
```yaml
# workflow.yaml - model acquisition step
env:
- name: AWS_ACCESS_KEY_ID
  valueFrom:
    secretKeyRef:
      name: aws-credentials
      key: access_key
- name: AWS_SECRET_ACCESS_KEY
  valueFrom:
    secretKeyRef:
      name: aws-credentials
      key: secret_key
```

**Use AWS Load Balancer:**
```yaml
# inference-service-aws.yaml
metadata:
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: nlb
    service.beta.kubernetes.io/aws-load-balancer-scheme: internet-facing
```

**GPU Instance Types:**
```yaml
# Best for LLMs on AWS:
# - g4dn.xlarge: 1x T4 GPU (16GB) - $0.52/hr
# - g4dn.12xlarge: 4x T4 GPU (64GB) - $3.91/hr
# - g5.xlarge: 1x A10G (24GB) - $1.01/hr
# - p4d.24xlarge: 8x A100 (320GB) - $32.77/hr

nodeSelector:
  node.kubernetes.io/instance-type: g5.xlarge
```

---

### 2. Google Cloud Platform (GCP)

#### **Kubernetes Service: Google Kubernetes Engine (GKE)**

**Step 1: Create GKE Cluster**
```bash
gcloud container clusters create vllm-cluster \
  --region us-central1 \
  --machine-type n1-standard-8 \
  --num-nodes 2 \
  --enable-autoscaling \
  --min-nodes 1 \
  --max-nodes 5

# Add GPU node pool
gcloud container node-pools create gpu-pool \
  --cluster vllm-cluster \
  --region us-central1 \
  --machine-type n1-standard-8 \
  --accelerator type=nvidia-tesla-t4,count=1 \
  --num-nodes 1 \
  --enable-autoscaling \
  --min-nodes 1 \
  --max-nodes 3
```

**Step 2: Install GPU Drivers**
```bash
kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/container-engine-accelerators/master/nvidia-driver-installer/cos/daemonset-preloaded.yaml
```

**Step 3: Configure Storage**
```yaml
# model-pvc-gcp.yaml
kind: PersistentVolumeClaim
apiVersion: v1
metadata:
  name: llm-model-storage
spec:
  accessModes: [ "ReadWriteOnce" ]
  storageClassName: standard-rwo  # GCP Persistent Disk
  resources:
    requests:
      storage: 100Gi
```

**Step 4: Push to Google Container Registry**
```bash
gcloud auth configure-docker

docker build -t vllm-utils:v0.1 .
docker tag vllm-utils:v0.1 gcr.io/my-project/vllm-utils:v0.1
docker push gcr.io/my-project/vllm-utils:v0.1
```

**Step 5: Deploy**
```bash
# Same workflow!
kubectl create ns kubeflow
kubectl kustomize manifests | kubectl apply -f -
kubectl create -f code/workflow.yaml
```

#### **GCP-Specific Optimizations**

**Use GCS for Model Storage:**
```yaml
# Instead of PVC, use GCS bucket
env:
- name: MODEL_DIR
  value: "gs://my-models-bucket/llama-2-7b"
- name: GOOGLE_APPLICATION_CREDENTIALS
  value: "/var/secrets/gcp/key.json"
volumeMounts:
- name: gcp-credentials
  mountPath: /var/secrets/gcp
```

**Use Google Cloud Load Balancer:**
```yaml
metadata:
  annotations:
    cloud.google.com/neg: '{"ingress": true}'
```

**GPU Instance Types:**
```yaml
# Best for LLMs on GCP:
# - n1-standard-8 + T4: 1x T4 (16GB) - ~$0.50/hr
# - a2-highgpu-1g: 1x A100 (40GB) - $3.67/hr
# - a2-highgpu-2g: 2x A100 (80GB) - $7.35/hr

nodeSelector:
  cloud.google.com/gke-accelerator: nvidia-tesla-t4
```

---

### 3. Microsoft Azure

#### **Kubernetes Service: Azure Kubernetes Service (AKS)**

**Step 1: Create AKS Cluster**
```bash
# Create resource group
az group create --name vllm-rg --location eastus

# Create AKS cluster
az aks create \
  --resource-group vllm-rg \
  --name vllm-cluster \
  --node-count 2 \
  --node-vm-size Standard_NC6s_v3 \
  --enable-cluster-autoscaler \
  --min-count 1 \
  --max-count 5 \
  --generate-ssh-keys

# Get credentials
az aks get-credentials --resource-group vllm-rg --name vllm-cluster
```

**Step 2: Install GPU Support**
```bash
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.0/nvidia-device-plugin.yml
```

**Step 3: Configure Storage**
```yaml
# model-pvc-azure.yaml
kind: PersistentVolumeClaim
apiVersion: v1
metadata:
  name: llm-model-storage
spec:
  accessModes: [ "ReadWriteOnce" ]
  storageClassName: managed-premium  # Azure Premium SSD
  resources:
    requests:
      storage: 100Gi
```

**Step 4: Push to Azure Container Registry**
```bash
# Create ACR
az acr create --resource-group vllm-rg --name vllmregistry --sku Basic

# Login
az acr login --name vllmregistry

# Build and push
docker build -t vllm-utils:v0.1 .
docker tag vllm-utils:v0.1 vllmregistry.azurecr.io/vllm-utils:v0.1
docker push vllmregistry.azurecr.io/vllm-utils:v0.1

# Attach ACR to AKS
az aks update -n vllm-cluster -g vllm-rg --attach-acr vllmregistry
```

**Step 5: Deploy**
```bash
kubectl create ns kubeflow
kubectl kustomize manifests | kubectl apply -f -
kubectl create -f code/workflow.yaml
```

#### **Azure-Specific Optimizations**

**Use Azure Blob Storage:**
```yaml
env:
- name: AZURE_STORAGE_CONNECTION_STRING
  valueFrom:
    secretKeyRef:
      name: azure-storage
      key: connection_string
- name: MODEL_DIR
  value: "https://mystorageaccount.blob.core.windows.net/models/"
```

**Use Azure Load Balancer:**
```yaml
metadata:
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-internal: "false"
```

**GPU Instance Types:**
```yaml
# Best for LLMs on Azure:
# - Standard_NC6s_v3: 1x V100 (16GB) - $3.06/hr
# - Standard_NC12s_v3: 2x V100 (32GB) - $6.12/hr
# - Standard_ND96asr_v4: 8x A100 (320GB) - $27.20/hr

nodeSelector:
  agentpool: gpupool
```

---

### 4. Other Platforms

#### **On-Premises / Private Cloud**
```bash
# Use kubeadm, Rancher, or OpenShift
# Same Kubernetes manifests work!
kubectl create ns kubeflow
kubectl kustomize manifests | kubectl apply -f -
```

#### **DigitalOcean Kubernetes (DOKS)**
```bash
doctl kubernetes cluster create vllm-cluster \
  --region nyc1 \
  --size s-2vcpu-4gb \
  --count 3

# Same workflow!
```

#### **Linode Kubernetes Engine (LKE)**
```bash
# Create via Linode console
# Download kubeconfig
# Deploy same way!
```

#### **Oracle Cloud (OKE)**
```bash
# Create via OCI console
# Free tier includes A1 Ampere VMs
# Deploy same manifests
```

---

## 🔄 Cloud Migration Checklist

### Moving from Local to Cloud

**Step 1: Cluster Creation**
- [ ] Create Kubernetes cluster on target cloud
- [ ] Configure kubectl access
- [ ] Install GPU drivers (if using GPUs)

**Step 2: Container Registry**
- [ ] Push Docker images to cloud registry
- [ ] Update image references in YAMLs
- [ ] Configure pull credentials (if private)

**Step 3: Storage Configuration**
- [ ] Update PVC storage class
- [ ] Adjust storage size if needed
- [ ] Consider cloud object storage (S3/GCS/Blob)

**Step 4: Infrastructure Installation**
- [ ] Deploy Argo Workflows
- [ ] Deploy Kubeflow Training Operator
- [ ] Deploy KServe (with Knative/Istio)

**Step 5: Application Deployment**
- [ ] Create namespace
- [ ] Create PVC
- [ ] Run workflow
- [ ] Deploy InferenceService

**Step 6: Networking**
- [ ] Configure ingress/load balancer
- [ ] Set up DNS (optional)
- [ ] Configure TLS/SSL (optional)

**Step 7: Monitoring & Observability**
- [ ] Install Prometheus
- [ ] Configure Grafana dashboards
- [ ] Set up alerts

---

## 📝 Cloud-Specific File Variations

### Storage Classes by Cloud

**AWS (EBS)**:
```yaml
storageClassName: gp3        # General Purpose SSD
storageClassName: io2        # High IOPS SSD
storageClassName: efs-sc     # Elastic File System (ReadWriteMany)
```

**GCP (Persistent Disk)**:
```yaml
storageClassName: standard-rwo    # Standard Persistent Disk
storageClassName: premium-rwo     # SSD Persistent Disk
storageClassName: standard-rwx    # Filestore (ReadWriteMany)
```

**Azure (Managed Disks)**:
```yaml
storageClassName: managed         # Standard HDD
storageClassName: managed-premium # Premium SSD
storageClassName: azurefile       # Azure Files (ReadWriteMany)
```

---

## 🚀 Multi-Cloud Deployment

### Deploy to Multiple Clouds Simultaneously!

```bash
# Configure multiple contexts
kubectl config use-context aws-cluster
kubectl create -f workflow.yaml

kubectl config use-context gcp-cluster
kubectl create -f workflow.yaml

kubectl config use-context azure-cluster
kubectl create -f workflow.yaml
```

**Use case**: Geographic distribution, vendor redundancy, cost optimization

---

## 💰 Cost Comparison

### Estimated Monthly Costs (7B Model, Single GPU)

| Cloud | Instance Type | GPU | Cost/Hour | Cost/Month* |
|-------|--------------|-----|-----------|-------------|
| **AWS** | g5.xlarge | 1x A10G | $1.01 | ~$730 |
| **GCP** | n1 + T4 | 1x T4 | $0.50 | ~$360 |
| **Azure** | NC6s_v3 | 1x V100 | $3.06 | ~$2,203 |
| **Lambda Labs** | gpu_1x_a10 | 1x A10 | $0.60 | ~$432 |

*24/7 usage, 730 hours/month

**Cost optimization tips**:
- Use spot/preemptible instances (50-90% cheaper)
- Scale to zero when idle
- Use smaller quantized models
- Multi-region for best pricing

---

## 🔐 Security Considerations

### Secrets Management by Cloud

**AWS Secrets Manager**:
```yaml
env:
- name: HF_TOKEN
  valueFrom:
    secretKeyRef:
      name: aws-secret
      key: huggingface_token
```

**GCP Secret Manager**:
```yaml
env:
- name: HF_TOKEN
  valueFrom:
    secretKeyRef:
      name: gcp-secret
      key: huggingface_token
```

**Azure Key Vault**:
```yaml
env:
- name: HF_TOKEN
  valueFrom:
    secretKeyRef:
      name: azure-keyvault-secret
      key: huggingface_token
```

---

## 📊 Feature Comparison

| Feature | AWS EKS | GCP GKE | Azure AKS |
|---------|---------|---------|-----------|
| **Managed Control Plane** | ✅ | ✅ | ✅ |
| **Auto-scaling** | ✅ | ✅ | ✅ |
| **GPU Support** | ✅ | ✅ | ✅ |
| **Serverless Nodes** | Fargate | Autopilot | Virtual Nodes |
| **Integrated Registry** | ECR | GCR | ACR |
| **Load Balancer** | ALB/NLB | Cloud LB | Azure LB |
| **Monitoring** | CloudWatch | Cloud Monitoring | Azure Monitor |
| **Cost** | $$ | $ | $$$ |
| **Ease of Use** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

---

## 🎯 Best Practices

### 1. Use Infrastructure as Code
```bash
# Terraform
terraform/
├── aws/
├── gcp/
└── azure/

# Or Pulumi, CloudFormation, ARM templates
```

### 2. Implement CI/CD
```yaml
# GitHub Actions example
name: Deploy to Cloud
on: push
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: azure/k8s-set-context@v1
    - run: kubectl apply -f manifests/
```

### 3. Monitor Costs
```bash
# Use cloud cost management tools
# - AWS Cost Explorer
# - GCP Cloud Billing
# - Azure Cost Management
```

### 4. Implement Auto-scaling
```yaml
# Cluster autoscaler
# Horizontal Pod Autoscaler
# Knative autoscaling (built-in KServe)
```

### 5. Backup & Disaster Recovery
```bash
# Backup PVCs regularly
# Use Velero for Kubernetes backups
# Replicate across regions
```

---

## 🔄 Migration Between Clouds

**Same manifests work everywhere!**

```bash
# Backup from AWS
kubectl get all -n kubeflow -o yaml > backup.yaml

# Switch context to GCP
kubectl config use-context gcp-cluster

# Restore to GCP
kubectl apply -f backup.yaml
```

**What to update**:
- Storage class names
- Image registry URLs
- Load balancer annotations
- GPU node selectors

---

## ✅ Summary

### What's Portable (95%+ of project)
✅ All Python scripts  
✅ Workflow logic  
✅ InferenceService configs  
✅ Argo Workflows  
✅ KServe  
✅ Kubeflow operators  
✅ Docker images  

### What's Cloud-Specific (5% of project)
⚙️ Storage class names  
⚙️ Container registry URLs  
⚙️ GPU instance types  
⚙️ Load balancer annotations  
⚙️ (Optional) Managed services integration  

---

## 🚀 Quick Start by Cloud

### AWS
```bash
eksctl create cluster --name vllm --node-type g4dn.xlarge
kubectl create ns kubeflow
kubectl kustomize manifests | kubectl apply -f -
kubectl create -f code/workflow.yaml
```

### GCP
```bash
gcloud container clusters create vllm --machine-type n1-standard-8
kubectl create ns kubeflow
kubectl kustomize manifests | kubectl apply -f -
kubectl create -f code/workflow.yaml
```

### Azure
```bash
az aks create --name vllm --node-vm-size Standard_NC6s_v3
kubectl create ns kubeflow
kubectl kustomize manifests | kubectl apply -f -
kubectl create -f code/workflow.yaml
```

**See? Almost identical!** That's the power of Kubernetes! 🎉

---

## 🎓 Learning Resources

- [AWS EKS Workshop](https://eksworkshop.com/)
- [GCP GKE Tutorials](https://cloud.google.com/kubernetes-engine/docs/tutorials)
- [Azure AKS Learning Path](https://learn.microsoft.com/en-us/azure/aks/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)

---

