"""
Test Service - Run inside a pod to test model loading
"""
import os
from pathlib import Path

def check_model_files(model_path):
    """Check if model files exist"""
    print(f"Checking model files at: {model_path}")
    
    if not os.path.exists(model_path):
        print(f"❌ Model path does not exist: {model_path}")
        return False
    
    # Check for common model files
    required_files = ["config.json"]
    optional_files = ["pytorch_model.bin", "model.safetensors", "tokenizer.json"]
    
    print("\nRequired files:")
    for file in required_files:
        file_path = os.path.join(model_path, file)
        exists = os.path.exists(file_path)
        status = "✓" if exists else "❌"
        print(f"  {status} {file}")
        if not exists:
            return False
    
    print("\nOptional files:")
    for file in optional_files:
        file_path = os.path.join(model_path, file)
        exists = os.path.exists(file_path)
        status = "✓" if exists else "  "
        print(f"  {status} {file}")
    
    print("\nAll files in directory:")
    for item in os.listdir(model_path):
        item_path = os.path.join(model_path, item)
        if os.path.isfile(item_path):
            size = os.path.getsize(item_path)
            print(f"  - {item} ({size:,} bytes)")
        else:
            print(f"  - {item}/ (directory)")
    
    return True

def main():
    print("=" * 60)
    print("Model Loading Test")
    print("=" * 60)
    
    # Check different model paths
    paths_to_check = [
        "/models/base",
        "/models/optimized/fp16",
        "/models/optimized/awq",
        "/models/optimized/gptq",
        "/models/production"
    ]
    
    for path in paths_to_check:
        print(f"\n{'=' * 60}")
        if check_model_files(path):
            print(f"✓ Model ready at {path}")
        else:
            print(f"⚠ Model not ready at {path}")
    
    print(f"\n{'=' * 60}")
    print("Test complete")

if __name__ == "__main__":
    main()

