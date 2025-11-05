"""
Inference Client - Test the deployed vLLM service
"""
import argparse
import json
from openai import OpenAI

def test_inference(base_url, model_name, prompt, max_tokens=100):
    """
    Send inference request to vLLM service
    """
    print(f"Testing inference at: {base_url}")
    print(f"Model: {model_name}")
    print(f"Prompt: {prompt}")
    print("-" * 60)
    
    client = OpenAI(
        base_url=base_url,
        api_key="dummy"  # vLLM doesn't require real API key
    )
    
    try:
        # Chat completion
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7
        )
        
        print("\n✓ Response received:")
        print("-" * 60)
        print(response.choices[0].message.content)
        print("-" * 60)
        print(f"\nTokens used: {response.usage.total_tokens}")
        print(f"  Prompt: {response.usage.prompt_tokens}")
        print(f"  Completion: {response.usage.completion_tokens}")
        
        return response
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return None

def test_streaming(base_url, model_name, prompt, max_tokens=100):
    """
    Test streaming inference
    """
    print(f"\nTesting streaming inference...")
    print(f"Prompt: {prompt}")
    print("-" * 60)
    
    client = OpenAI(
        base_url=base_url,
        api_key="dummy"
    )
    
    try:
        stream = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7,
            stream=True
        )
        
        print("\n✓ Streaming response:")
        print("-" * 60)
        for chunk in stream:
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
        print("\n" + "-" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test vLLM inference service")
    parser.add_argument("--base_url", type=str, 
                        default="http://localhost:8000/v1",
                        help="Base URL of vLLM service")
    parser.add_argument("--model", type=str,
                        default="facebook/opt-125m",
                        help="Model name")
    parser.add_argument("--prompt", type=str,
                        default="What are the key benefits of distributed machine learning?",
                        help="Test prompt")
    parser.add_argument("--max_tokens", type=int, default=100,
                        help="Maximum tokens to generate")
    parser.add_argument("--streaming", action="store_true",
                        help="Test streaming mode")
    
    args = parser.parse_args()
    
    if args.streaming:
        test_streaming(args.base_url, args.model, args.prompt, args.max_tokens)
    else:
        test_inference(args.base_url, args.model, args.prompt, args.max_tokens)

