"""
Model Acquisition - Download LLM from HuggingFace Hub
This replaces data-ingestion.py from the original project
"""
import os
from huggingface_hub import snapshot_download

# Model to download - using a small model for demo
# For production, use: meta-llama/Llama-2-7b-chat-hf, mistralai/Mistral-7B-v0.1, etc.
MODEL_NAME = os.getenv("MODEL_NAME", "facebook/opt-125m")
LOCAL_DIR = os.getenv("LOCAL_DIR", "/models/base")

print(f"Downloading model: {MODEL_NAME}")
print(f"Destination: {LOCAL_DIR}")

snapshot_download(
    repo_id=MODEL_NAME,
    local_dir=LOCAL_DIR,
    local_dir_use_symlinks=False,
    resume_download=True
)

print(f"✓ Model downloaded successfully to {LOCAL_DIR}")

