import uvicorn
import asyncio
import base64
import torch
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, ValidationError
from typing import Dict, Any, Optional, List

from src.core.registry import registry
from src.core.types import GenerationRequest, GenerationResponse
from src.core.utils import discover_and_register_generators

# Pydantic models for FastAPI request/response validation
class RequestModel(BaseModel):
    prompt: str
    positive_prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    num_outputs: Optional[int] = 1
    parameters: Optional[Dict[str, Any]] = {}

class ResponseModel(BaseModel):
    success: bool
    output_paths: List[str] = []
    metadata: Dict[str, Any] = {}
    error_message: Optional[str] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- [Server] Starting up ---")
    # 1. Discover and register all generators
    discover_and_register_generators("src.generators")
    
    # Create a shutdown event to signal all running generators
    shutdown_event = threading.Event()

    # 2. Pre-load models by getting singleton instances and setting shutdown event
    available = registry.list_available()
    print(f"--- [Server] Available modules: {available} ---")
    for module in available:
        print(f"--- [Server] Pre-loading model for '{module}'... ---")
        generator = registry.get_instance(module)
        if hasattr(generator, "set_shutdown_event"):
            generator.set_shutdown_event(shutdown_event)
    
    # RTX 4080 Optimizations
    torch.backends.cuda.matmul.allow_tf32 = True
    print("--- [Server] All models pre-loaded and GPU optimized! ---")

    yield

    print("--- [Server] Shutting down ---")
    shutdown_event.set()
    # Allow a small grace period for generators to catch the event
    await asyncio.sleep(1)

app = FastAPI(title="ggena API Server", lifespan=lifespan)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (CSS, JS)
app.mount("/static", StaticFiles(directory="src/app/frontend"), name="static")

@app.get("/")
async def read_index():
    """Serves the main frontend page."""
    return FileResponse("src/app/frontend/index.html")

@app.post("/generate/{module}", response_model=ResponseModel)
async def generate(module: str, request: RequestModel):
    """
    Endpoint to trigger generation for a specific module via HTTP POST.
    """
    generator = registry.get_instance(module)
    if not generator:
        raise HTTPException(status_code=404, detail=f"Module '{module}' not found.")

    # Validate parameters against the generator's schema
    try:
        schema = generator.parameter_schema
        validated_params = schema(**request.parameters).model_dump()
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

    core_request = GenerationRequest(
        prompt=request.prompt,
        positive_prompt=request.positive_prompt,
        negative_prompt=request.negative_prompt,
        num_outputs=request.num_outputs,
        parameters=validated_params
    )

    print(f"--- [Server] Processing request for '{module}': {request.prompt} ---")
    
    try:
        response = await generator.generate(core_request)
        if not response.success:
            raise HTTPException(status_code=500, detail=response.error_message)
        return response
    except Exception as e:
        print(f"--- [Server] Error during generation: {str(e)} ---")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/generate/{module}")
async def websocket_generate(websocket: WebSocket, module: str):
    """
    WebSocket endpoint for real-time generation with progress updates.
    """
    await websocket.accept()
    print(f"--- [WS] Connection established for module '{module}' ---")
    loop = asyncio.get_running_loop()

    try:
        while True:
            # Wait for a message from the client
            data = await websocket.receive_json()
            print(f"--- [WS] Received message: {data} ---")
            
            if data.get("type") == "generate":
                print(f"--- [WS] 'generate' type detected for module '{module}' ---")
                generator = registry.get_instance(module)
                if not generator:
                    print(f"--- [WS] Error: Module '{module}' not found in registry ---")
                    await websocket.send_json({"type": "error", "message": f"Module '{module}' not found."})
                    continue

                # Extract parameters from the request
                prompt = data.get("prompt")
                pos_prompt = data.get("positive_prompt")
                neg_prompt = data.get("negative_prompt", "")
                steps = int(data.get("steps", 30))
                cfg_scale = float(data.get("cfg_scale", 7.0))
                width = int(data.get("width", 1024))
                height = int(data.get("height", 1024))
                num_outputs = int(data.get("num_outputs", 1))

                print(f"--- [WS] Parameters: prompt='{prompt}', steps={steps}, cfg={cfg_scale}, res={width}x{height}, num_outputs={num_outputs} ---")

                # Define the callback to send progress via WebSocket
                def create_callback(total_steps):
                    def callback_on_step_end(pipe, step_index, timestep, callback_kwargs):
                        progress_data = {
                            "type": "progress",
                            "step": step_index + 1,
                            "total_steps": total_steps
                        }
                        # Schedule the message sending on the event loop from the worker thread
                        asyncio.run_coroutine_threadsafe(websocket.send_json(progress_data), loop)
                        return callback_kwargs
                    return callback_on_step_end
                
                # Define the callback to send images via WebSocket as they are ready
                def create_image_callback():
                    images_sent_via_streaming = False
                    def on_image_ready(img_bytes, metadata):
                        nonlocal images_sent_via_streaming
                        images_sent_via_streaming = True
                        try:
                            img_b64 = base64.b64encode(img_bytes).decode("utf-8")
                            image_data = {
                                "type": "image",
                                "images": [f"data:image/png;base64,{img_b64}"],
                                "positive_prompt": metadata.get("positive_prompt"),
                                "negative_prompt": metadata.get("negative_prompt")
                            }
                            asyncio.run_coroutine_threadsafe(websocket.send_json(image_data), loop)
                        except Exception as e:
                            print(f"--- [WS] Error in on_image_ready callback: {e} ---")

                    return on_image_ready, lambda: images_sent_via_streaming
                
                callback = create_callback(steps)
                on_image_ready, get_streaming_status = create_image_callback()

                # Prepare core request with parameters and the callbacks
                core_request = GenerationRequest(
                    prompt=prompt,
                    positive_prompt=pos_prompt,
                    negative_prompt=neg_prompt,
                    num_outputs=num_outputs,
                    parameters={
                        "num_inference_steps": steps,
                        "guidance_scale": cfg_scale,
                        "width": width,
                        "height": height,
                        "callback_on_step_end": callback,
                        "on_image_ready": on_image_ready
                    }
                )

                print(f"--- [WS] Starting generation for '{module}' ---")

                try:
                    response = await generator.generate(core_request)
                except Exception as e:
                    print(f"--- [WS] Generation error: {e} ---")
                    response = None

                if response is None or not response.success:
                    error_msg = response.error_message if response else "Unknown error"
                    print(f"--- [WS] Generation failed: {error_msg} ---")
                    await websocket.send_json({"type": "error", "message": error_msg})
                else:
                    if get_streaming_status():
                        print(f"--- [WS] Generation successful (images already streamed)! ---")
                    else:
                        print(f"--- [WS] Generation successful! Sending images... ---")
                        # Convert output to Base64 and send as a list
                        if response.output_files_bytes:
                            try:
                                images_base64 = []
                                for img_bytes in response.output_files_bytes:
                                    img_b64 = base64.b64encode(img_bytes).decode("utf-8")
                                    images_base64.append(f"data:image/png;base64,{img_b64}")
                                
                                await websocket.send_json({
                                    "type": "image", 
                                    "images": images_base64,
                                    "positive_prompt": response.metadata.get("positive_prompt"),
                                    "negative_prompt": response.metadata.get("negative_prompt")
                                })
                            except Exception as e:
                                print(f"--- [WS] Error encoding image bytes: {e} ---")
                                await websocket.send_json({"type": "error", "message": f"Failed to encode images: {e}"})

    except WebSocketDisconnect:
        print(f"--- [WS] Client disconnected from module '{module}' ---")
    except Exception as e:
        print(f"--- [WS] Unexpected error in loop: {e} ---")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
