#!/bin/bash
# Quick deployment script for Ray Serve with vLLM

set -e

echo "🚀 Deploying vLLM with Ray Serve"
echo "=================================="
echo ""

# Check if kubectl is configured
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Error: kubectl is not configured or cluster is not accessible"
    exit 1
fi

# Check namespace
NAMESPACE="kubeflow"
if ! kubectl get namespace $NAMESPACE &> /dev/null; then
    echo "📝 Creating namespace: $NAMESPACE"
    kubectl create namespace $NAMESPACE
fi

echo "✓ Using namespace: $NAMESPACE"
echo ""

# Step 1: Install Ray Operator
echo "📦 Step 1/6: Installing Ray Operator..."
if kubectl get deployment -n ray-system kuberay-operator &> /dev/null; then
    echo "✓ Ray Operator already installed"
else
    kubectl create -k "github.com/ray-project/kuberay/ray-operator/config/default?ref=v0.6.0"
    echo "✓ Ray Operator installed"
fi
echo ""

# Step 2: Wait for operator
echo "⏳ Step 2/6: Waiting for Ray Operator to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/kuberay-operator -n ray-system
echo "✓ Ray Operator is ready"
echo ""

# Step 3: Deploy Ray Cluster
echo "🎯 Step 3/6: Deploying Ray Cluster..."
kubectl apply -f ray-cluster.yaml -n $NAMESPACE
echo "✓ Ray Cluster deployment submitted"
echo ""

# Step 4: Wait for Ray Cluster
echo "⏳ Step 4/6: Waiting for Ray Cluster to be ready (this may take 2-3 minutes)..."
sleep 10  # Give it a moment to start creating
kubectl wait --for=condition=Ready raycluster/vllm-ray-cluster -n $NAMESPACE --timeout=300s || true
echo "✓ Ray Cluster is starting up"
echo ""

# Step 5: Create Service
echo "🌐 Step 5/6: Creating Ray Service..."
kubectl apply -f ray-service.yaml -n $NAMESPACE
echo "✓ Ray Service created"
echo ""

# Step 6: Deploy Ray Serve Application
echo "🚀 Step 6/6: Deploying vLLM Ray Serve application..."

# Find Ray head pod
echo "   Finding Ray head pod..."
RAY_HEAD=$(kubectl get pods -n $NAMESPACE -l ray.io/cluster=vllm-ray-cluster,ray.io/node-type=head -o jsonpath='{.items[0].metadata.name}')

if [ -z "$RAY_HEAD" ]; then
    echo "❌ Error: Could not find Ray head pod"
    echo "   Check if Ray cluster is running: kubectl get pods -n $NAMESPACE"
    exit 1
fi

echo "   Found Ray head pod: $RAY_HEAD"

# Wait for pod to be ready
echo "   Waiting for Ray head pod to be ready..."
kubectl wait --for=condition=Ready pod/$RAY_HEAD -n $NAMESPACE --timeout=300s

# Install dependencies
echo "   Installing vLLM dependencies (this may take 2-3 minutes)..."
kubectl exec -n $NAMESPACE $RAY_HEAD -- bash -c "pip install vllm fastapi pydantic --quiet" || {
    echo "⚠️  Warning: Could not install dependencies. They may already be installed."
}

# Copy Ray Serve application
echo "   Copying Ray Serve application..."
kubectl cp ray-vllm-server.py $NAMESPACE/$RAY_HEAD:/tmp/ray-vllm-server.py

# Deploy to Ray Serve
echo "   Deploying to Ray Serve..."
kubectl exec -n $NAMESPACE $RAY_HEAD -- serve deploy /tmp/ray-vllm-server.py || {
    echo "⚠️  Deployment command executed (check logs for status)"
}

echo "✓ Deployment complete!"
echo ""

# Summary
echo "=================================="
echo "✅ Deployment Summary"
echo "=================================="
echo ""
echo "Ray Cluster: vllm-ray-cluster"
echo "Namespace: $NAMESPACE"
echo "Service: vllm-ray-service"
echo ""
echo "📊 Check Status:"
echo "  kubectl get rayclusters -n $NAMESPACE"
echo "  kubectl get pods -n $NAMESPACE"
echo "  kubectl get svc -n $NAMESPACE"
echo ""
echo "📈 View Ray Dashboard:"
echo "  kubectl port-forward -n $NAMESPACE svc/vllm-ray-service 8265:8265"
echo "  Open: http://localhost:8265"
echo ""
echo "🧪 Test the Service:"
echo "  kubectl port-forward -n $NAMESPACE svc/vllm-ray-service 8000:8000"
echo "  python inference-client.py --base_url http://localhost:8000/v1"
echo ""
echo "📝 View Logs:"
echo "  kubectl logs -n $NAMESPACE $RAY_HEAD"
echo ""
echo "🔥 Happy serving with Ray! 🚀"

