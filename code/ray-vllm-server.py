"""
Ray Serve application for vLLM inference
OpenAI-compatible API for LLM serving
"""
from ray import serve
from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.engine.async_llm_engine import AsyncLLMEngine
from vllm import SamplingParams
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, AsyncGenerator
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="vLLM Ray Serve API", version="1.0.0")

# Request models
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str = "llm-model"
    messages: List[ChatMessage]
    max_tokens: Optional[int] = 100
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    stream: Optional[bool] = False

class CompletionRequest(BaseModel):
    model: str = "llm-model"
    prompt: str
    max_tokens: Optional[int] = 100
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0


@serve.deployment(
    name="vllm-deployment",
    num_replicas=2,
    ray_actor_options={
        "num_gpus": 1,  # Each replica gets 1 GPU
        "num_cpus": 2,
    },
    autoscaling_config={
        "min_replicas": 1,
        "max_replicas": 5,
        "target_num_ongoing_requests_per_replica": 5,
        "upscale_delay_s": 30,
        "downscale_delay_s": 300,
    },
)
@serve.ingress(app)
class VLLMDeployment:
    def __init__(self, model_path: str = "/models/production"):
        """
        Initialize vLLM engine
        
        Args:
            model_path: Path to the model directory
        """
        logger.info(f"Initializing vLLM engine with model: {model_path}")
        
        # vLLM engine configuration
        engine_args = AsyncEngineArgs(
            model=model_path,
            tensor_parallel_size=1,
            dtype="float16",
            max_model_len=2048,
            gpu_memory_utilization=0.9,
            trust_remote_code=True,
        )
        
        # Create async engine
        self.engine = AsyncLLMEngine.from_engine_args(engine_args)
        self.model_path = model_path
        
        logger.info("✓ vLLM engine initialized successfully!")
    
    @app.get("/")
    async def root(self):
        """Health check endpoint"""
        return {
            "status": "healthy",
            "service": "vllm-ray-serve",
            "model": self.model_path
        }
    
    @app.get("/health")
    async def health(self):
        """Health check endpoint"""
        return {"status": "healthy"}
    
    @app.get("/v1/models")
    async def list_models(self):
        """List available models (OpenAI-compatible)"""
        return {
            "object": "list",
            "data": [
                {
                    "id": "llm-model",
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "vllm-ray-serve"
                }
            ]
        }
    
    @app.post("/v1/completions")
    async def completions(self, request: CompletionRequest):
        """
        Text completion endpoint (OpenAI-compatible)
        
        Example:
            POST /v1/completions
            {
                "model": "llm-model",
                "prompt": "Once upon a time",
                "max_tokens": 50
            }
        """
        logger.info(f"Completion request - Prompt: {request.prompt[:50]}...")
        
        try:
            # Sampling parameters
            sampling_params = SamplingParams(
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                top_p=request.top_p,
            )
            
            # Generate
            request_id = f"cmpl-{int(time.time() * 1000)}"
            results = await self.engine.generate(
                request.prompt,
                sampling_params,
                request_id=request_id
            )
            
            # Extract output
            output_text = results.outputs[0].text if results.outputs else ""
            prompt_tokens = len(results.prompt_token_ids)
            completion_tokens = len(results.outputs[0].token_ids) if results.outputs else 0
            
            return {
                "id": request_id,
                "object": "text_completion",
                "created": int(time.time()),
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
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens
                }
            }
        
        except Exception as e:
            logger.error(f"Error during completion: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/v1/chat/completions")
    async def chat_completions(self, request: ChatRequest):
        """
        Chat completion endpoint (OpenAI-compatible)
        
        Example:
            POST /v1/chat/completions
            {
                "model": "llm-model",
                "messages": [
                    {"role": "user", "content": "Hello!"}
                ],
                "max_tokens": 50
            }
        """
        logger.info(f"Chat request - {len(request.messages)} messages")
        
        try:
            # Convert messages to prompt
            prompt = self._messages_to_prompt(request.messages)
            
            # Sampling parameters
            sampling_params = SamplingParams(
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                top_p=request.top_p,
            )
            
            # Generate
            request_id = f"chatcmpl-{int(time.time() * 1000)}"
            results = await self.engine.generate(
                prompt,
                sampling_params,
                request_id=request_id
            )
            
            # Extract output
            output_text = results.outputs[0].text if results.outputs else ""
            prompt_tokens = len(results.prompt_token_ids)
            completion_tokens = len(results.outputs[0].token_ids) if results.outputs else 0
            
            return {
                "id": request_id,
                "object": "chat.completion",
                "created": int(time.time()),
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
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens
                }
            }
        
        except Exception as e:
            logger.error(f"Error during chat completion: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def _messages_to_prompt(self, messages: List[ChatMessage]) -> str:
        """
        Convert chat messages to a prompt string
        
        Note: This is a simple implementation. For production,
        use the model's specific chat template.
        """
        prompt = ""
        for msg in messages:
            if msg.role == "system":
                prompt += f"System: {msg.content}\n\n"
            elif msg.role == "user":
                prompt += f"User: {msg.content}\n\n"
            elif msg.role == "assistant":
                prompt += f"Assistant: {msg.content}\n\n"
        
        prompt += "Assistant:"
        return prompt


# Create deployment binding
deployment = VLLMDeployment.bind()

