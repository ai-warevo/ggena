import asyncio
import base64
from typing import Any, Callable, Dict, Tuple
import structlog
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Request

from src.core.types import GenerationRequest
from src.core.exceptions import GgenaError, ValidationError, GeneratorError, RegistryError
from src.core.metrics import ACTIVE_GENERATIONS, GENERATION_ERRORS
from src.app.server.models import RequestModel, ResponseModel

logger = structlog.get_logger(__name__)

router = APIRouter()

@router.websocket("/ws/generate/{module}")
async def websocket_generate(websocket: WebSocket, module: str):
    """
    WebSocket endpoint for real-time generation with progress updates.
    """
    await websocket.accept()
    logger.info("--- [WS] Connection established ---", module=module)
    loop = asyncio.get_running_loop()

    try:
        app = websocket.app
        registry = app.state.registry
        config = app.state.config

        while True:
            data = await websocket.receive_json()
            logger.debug("--- [WS] Received message ---", module=module, data=data)
            await _handle_ws_message(websocket, module, data, registry, config, loop)

    except WebSocketDisconnect:
        logger.info("--- [WS] Client disconnected ---", module=module)
    except Exception as e:
        logger.error("--- [WS] Unexpected error in connection loop ---", module=module, error=str(e))
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass

async def _handle_ws_message(websocket: WebSocket, module: str, data: dict, registry: Any, config: Any, loop: asyncio.AbstractEventLoop):
    if data.get("type") != "generate":
        return

    logger.info("--- [WS] 'generate' type detected ---", module=module)
    try:
        await _orchestrate_generation(websocket, module, data, registry, config, loop)
    except (RegistryError, ValidationError, GeneratorError, GgenaError) as e:
        if isinstance(e, RegistryError):
            logger.error("--- [WS] Registry error ---", module=module, error=str(e))
        elif isinstance(e, ValidationError):
            logger.error("--- [WS] Validation error ---", module=module, error=str(e))
        elif isinstance(e, GeneratorError):
            GENERATION_ERRORS.labels(module=module, error_type="GeneratorError").inc()
            logger.error("--- [WS] Generation error ---", module=module, error=str(e))
        elif isinstance(e, GgenaError):
            GENERATION_ERRORS.labels(module=module, error_type="GgenaError").inc()
            logger.error("--- [WS] Framework error ---", module=module, error=str(e))
        await websocket.send_json({"type": "error", "message": str(e)})
    except Exception as e:
        logger.exception("--- [WS] Unexpected error in _handle_ws_message ---", module=module)
        GENERATION_ERRORS.labels(module=module, error_type="UnexpectedError").inc()
        from src.core.config import config as global_config
        if global_config.get_bool("PRODUCTION", False):
            await websocket.send_json({"type": "error", "message": "An internal server error occurred."})
        else:
            await websocket.send_json({"type": "error", "message": f"Unexpected error: {str(e)}"})

async def _orchestrate_generation(websocket: WebSocket, module: str, data: dict, registry: Any, config: Any, loop: asyncio.AbstractEventLoop):
    generator = registry.get_instance(module, config=config)
    if not generator:
        raise RegistryError(f"Module '{module}' not found.")

    params = _extract_params(data)
    logger.info("--- [WS] Parameters ---", module=module, prompt=params["prompt"], steps=params["steps"], cfg_scale=params["cfg_scale"], res=f"{params['width']}x{params['height']}", num_outputs=params["num_outputs"])

    callback, (on_image_ready, get_streaming_status) = _create_callbacks(websocket, loop, module, params["steps"])

    core_request = GenerationRequest(
        prompt=params["prompt"],
        positive_prompt=params["positive_prompt"],
        negative_prompt=params["negative_prompt"],
        num_outputs=params["num_outputs"],
        parameters={
            "num_inference_steps": params["steps"],
            "guidance_scale": params["cfg_scale"],
            "width": params["width"],
            "height": params["height"],
            "callback_on_step_end": callback,
            "on_image_ready": on_image_ready
        }
    )

    logger.info("--- [WS] Starting generation ---", module=module)
    ACTIVE_GENERATIONS.inc()
    try:
        response = await generator.generate(core_request)
        if not response.success:
            error_msg = response.error_message or "Unknown error"
            logger.error("--- [WS] Generation failed ---", module=module, error=error_msg)
            await websocket.send_json({"type": "error", "message": error_msg})
        else:
            if get_streaming_status():
                logger.info("--- [WS] Generation successful (images already streamed)! ---", module=module)
            else:
                logger.info("--- [WS] Generation successful! Sending images... ---", module=module)
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
                        logger.error("--- [WS] Error encoding image bytes ---", module=module, error=str(e))
                        await websocket.send_json({"type": "error", "message": f"Failed to encode images: {e}"})
    finally:
        ACTIVE_GENERATIONS.dec()

def _extract_params(data: dict) -> dict:
    return {
        "prompt": data.get("prompt"),
        "positive_prompt": data.get("positive_prompt"),
        "negative_prompt": data.get("negative_prompt", ""),
        "steps": int(data.get("steps", 30)),
        "cfg_scale": float(data.get("cfg_scale", 7.0)),
        "width": int(data.get("width", 1024)),
        "height": int(data.get("height", 1024)),
        "num_outputs": int(data.get("num_outputs", 1))
    }

def _create_callbacks(websocket: WebSocket, loop: asyncio.AbstractEventLoop, module: str, total_steps: int) -> Tuple[Callable, Tuple[Callable, Callable]]:
    def callback_on_step_end(pipe, step_index, timestep, callback_kwargs):
        progress_data = {
            "type": "progress",
            "step": step_index + 1,
            "total_steps": total_steps
        }
        asyncio.run_coroutine_threadsafe(websocket.send_json(progress_data), loop)
        return callback_kwargs

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
                logger.error("--- [WS] Error in on_image_ready callback ---", module=module, error=str(e))

        return on_image_ready, lambda: images_sent_via_streaming

    return callback_on_step_end, create_image_callback()
