import asyncio
import base64
import structlog
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Request
from pydantic import ValidationError as PydanticValidationError

from src.core.types import GenerationRequest
from src.core.exceptions import GgenaError, ValidationError, GeneratorError, RegistryError
from src.core.commands import GenerationCommand
from src.core.metrics import ACTIVE_GENERATIONS, GENERATION_ERRORS
from src.app.server.models import RequestModel, ResponseModel

logger = structlog.get_logger(__name__)

router = APIRouter()

@router.post("/generate/{module}", response_model=ResponseModel)
async def generate(module: str, request_data: RequestModel, request: Request):
    """
    Endpoint to trigger generation for a specific module via HTTP POST.
    """
    registry = request.app.state.registry
    config = request.app.state.config
    try:
        generator = registry.get_instance(module, config=config)

        # Validate parameters against the generator's schema
        try:
            schema = generator.parameter_schema
            validated_params = schema(**request_data.parameters).model_dump()
        except PydanticValidationError as e:
            raise ValidationError(f"Invalid parameters for module '{module}': {str(e)}", details=e.errors())

        core_request = GenerationRequest(
            prompt=request_data.prompt,
            positive_prompt=request_data.positive_prompt,
            negative_prompt=request_data.negative_prompt,
            num_outputs=request_data.num_outputs,
            parameters=validated_params
        )

        logger.info("--- [Server] Processing request for module", module=module, prompt=request_data.prompt)
        
        ACTIVE_GENERATIONS.inc()
        try:
            command = GenerationCommand(module=module, request=core_request)
            result = await request.app.state.executor.execute(command)

            if not result.success:
                # If the generator returned success=False, it might have its own error message
                raise GeneratorError(result.error_message or "Generation failed.")
            return result.result
        finally:
            ACTIVE_GENERATIONS.dec()

    except RegistryError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail={"message": str(e), "details": e.details})
    except GeneratorError as e:
        GENERATION_ERRORS.labels(module=module, error_type="GeneratorError").inc()
        raise HTTPException(status_code=500, detail=str(e))
    except GgenaError as e:
        GENERATION_ERRORS.labels(module=module, error_type="GgenaError").inc()
        raise HTTPException(status_code=500, detail=f"Framework error: {str(e)}")
    except Exception as e:
        logger.exception("--- [Server] Unexpected error during generation ---", module=module)
        GENERATION_ERRORS.labels(module=module, error_type="UnexpectedError").inc()
        # We need to access config here too. 
        # In the original code it was 'config' from global scope (from src.core.config import config).
        # But we should probably use request.app.state.config if possible, or just import it.
        from src.core.config import config as global_config
        if global_config.get_bool("PRODUCTION", False):
            raise HTTPException(status_code=500, detail="An internal server error occurred.")
        else:
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.websocket("/ws/generate/{module}")
async def websocket_generate(websocket: WebSocket, module: str):
    """
    WebSocket endpoint for real-time generation with progress updates.
    """
    await websocket.accept()
    logger.info("--- [WS] Connection established ---", module=module)
    loop = asyncio.get_running_loop()

    try:
        # Access app state from websocket.
        # In FastAPI, websocket has access to the app via websocket.app
        app = websocket.app
        registry = app.state.registry
        shutdown_event = app.state.shutdown_event
        config = app.state.config

        while True:
            # Wait for a message from the client
            data = await websocket.receive_json()
            logger.debug("--- [WS] Received message ---", module=module, data=data)
            
            if data.get("type") == "generate":
                logger.info("--- [WS] 'generate' type detected ---", module=module)
                try:
                    generator = registry.get_instance(module, config=config)
                    if not generator:
                        raise RegistryError(f"Module '{module}' not found.")

                    # Extract parameters from the request
                    prompt = data.get("prompt")
                    pos_prompt = data.get("positive_prompt")
                    neg_prompt = data.get("negative_prompt", "")
                    steps = int(data.get("steps", 30))
                    cfg_scale = float(data.get("cfg_scale", 7.0))
                    width = int(data.get("width", 1024))
                    height = int(data.get("height", 1024))
                    num_outputs = int(data.get("num_outputs", 1))

                    logger.info("--- [WS] Parameters ---", module=module, prompt=prompt, steps=steps, cfg_scale=cfg_scale, res=f"{width}x{height}", num_outputs=num_outputs)

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
                                logger.error("--- [WS] Error in on_image_ready callback ---", module=module, error=str(e))

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
                                        logger.error("--- [WS] Error encoding image bytes ---", module=module, error=str(e))
                                        await websocket.send_json({"type": "error", "message": f"Failed to encode images: {e}"})
                    finally:
                        ACTIVE_GENERATIONS.dec()

                except RegistryError as e:
                    logger.error("--- [WS] Registry error ---", module=module, error=str(e))
                    await websocket.send_json({"type": "error", "message": str(e)})
                except ValidationError as e:
                    logger.error("--- [WS] Validation error ---", module=module, error=str(e))
                    await websocket.send_json({"type": "error", "message": str(e)})
                except GeneratorError as e:
                    GENERATION_ERRORS.labels(module=module, error_type="GeneratorError").inc()
                    logger.error("--- [WS] Generation error ---", module=module, error=str(e))
                    await websocket.send_json({"type": "error", "message": str(e)})
                except GgenaError as e:
                    GENERATION_ERRORS.labels(module=module, error_type="GgenaError").inc()
                    logger.error("--- [WS] Framework error ---", module=module, error=str(e))
                    await websocket.send_json({"type": "error", "message": str(e)})
                except Exception as e:
                    logger.exception("--- [WS] Unexpected error in loop ---", module=module)
                    GENERATION_ERRORS.labels(module=module, error_type="UnexpectedError").inc()
                    from src.core.config import config as global_config
                    if global_config.get_bool("PRODUCTION", False):
                        await websocket.send_json({"type": "error", "message": "An internal server error occurred."})
                    else:
                        await websocket.send_json({"type": "error", "message": f"Unexpected error: {str(e)}"})

            except WebSocketDisconnect:
                logger.info("--- [WS] Client disconnected ---", module=module)
            except Exception as e:
                logger.error("--- [WS] Unexpected error in loop ---", module=module, error=str(e))
                try:
                    await websocket.send_json({"type": "error", "message": str(e)})
                except:
                    pass

    except Exception as e:
        logger.error("--- [WS] Unexpected error in loop ---", module=module, error=str(e))
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass

@router.post("/generate/{module}", response_model=ResponseModel)
async def generate(module: str, request_data: RequestModel, request: Request):
    """
    Endpoint to trigger generation for a specific module via HTTP POST.
    """
    registry = request.app.state.registry
    config = request.app.state.config
    try:
        generator = registry.get_instance(module, config=config)

        # Validate parameters against the generator's schema
        try:
            schema = generator.parameter_schema
            validated_params = schema(**request_data.parameters).model_dump()
        except PydanticValidationError as e:
            raise ValidationError(f"Invalid parameters for module '{module}': {str(e)}", details=e.errors())

        core_request = GenerationRequest(
            prompt=request_data.prompt,
            positive_prompt=request_data.positive_prompt,
            negative_prompt=request_data.negative_prompt,
            num_outputs=request_data.num_outputs,
            parameters=validated_params
        )

        logger.info("--- [Server] Processing request for module", module=module, prompt=request_data.prompt)
        
        ACTIVE_GENERATIONS.inc()
        try:
            command = GenerationCommand(module=module, request=core_request)
            result = await request.app.state.executor.execute(command)

            if not result.success:
                # If the generator returned success=False, it might have its own error message
                raise GeneratorError(result.error_message or "Generation failed.")
            return result.result
        finally:
            ACTIVE_GENERATIONS.dec()

    except RegistryError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail={"message": str(e), "details": e.details})
    except GeneratorError as e:
        GENERATION_ERRORS.labels(module=module, error_type="GeneratorError").inc()
        raise HTTPException(status_code=500, detail=str(e))
    except GgenaError as e:
        GENERATION_ERRORS.labels(module=module, error_type="GgenaError").inc()
        raise HTTPException(status_code=500, detail=f"Framework error: {str(e)}")
    except Exception as e:
        logger.exception("--- [Server] Unexpected error during generation ---", module=module)
        GENERATION_ERRORS.labels(module=module, error_type="UnexpectedError").inc()
        # We need to access config here too. 
        # In the original code it was 'config' from global scope (from src.core.config import config).
        # But we should probably use request.app.state.config if possible, or just import it.
        # The original used `if config.get_bool("PRODUCTION", False):`.
        # Let's see how to get config.
        from src.core.config import config as global_config
        if global_config.get_bool("PRODUCTION", False):
            raise HTTPException(status_code=500, detail="An internal server error occurred.")
        else:
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.websocket("/ws/generate/{module}")
async def websocket_generate(websocket: WebSocket, module: str):
    """
    WebSocket endpoint for real-time generation with progress updates.
    """
    await websocket.accept()
    logger.info("--- [WS] Connection established ---", module=module)
    loop = asyncio.get_running_loop()

    try:
        # Access app state from websocket.
        # In FastAPI, websocket has access to the app via websocket.app
        app = websocket.app
        registry = app.state.registry
        shutdown_event = app.state.shutdown_event
        config = app.state.config

        while True:
            # Wait for a message from the client
            data = await websocket.receive_json()
            logger.debug("--- [WS] Received message ---", module=module, data=data)
            
            if data.get("type") == "generate":
                logger.info("--- [WS] 'generate' type detected ---", module=module)
                try:
                    generator = registry.get_instance(module, config=config)
                    if not generator:
                        raise RegistryError(f"Module '{module}' not found.")

                    # Extract parameters from the request
                    prompt = data.get("prompt")
                    pos_prompt = data.get("positive_prompt")
                    neg_prompt = data.get("negative_prompt", "")
                    steps = int(data.get("steps", 30))
                    cfg_scale = float(data.get("cfg_scale", 7.0))
                    width = int(data.get("width", 1024))
                    height = int(data.get("height", 1024))
                    num_outputs = int(data.get("num_outputs", 1))

                    logger.info("--- [WS] Parameters ---", module=module, prompt=prompt, steps=steps, cfg_scale=cfg_scale, res=f"{width}x{height}", num_outputs=num_outputs)

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
                                logger.error("--- [WS] Error in on_image_ready callback ---", module=module, error=str(e))

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
                                        logger.error("--- [WS] Error encoding image bytes ---", module=module, error=str(e))
                                        await websocket.send_json({"type": "error", "message": f"Failed to encode images: {e}"})
                    finally:
                        ACTIVE_GENERATIONS.dec()

                except RegistryError as e:
                    logger.error("--- [WS] Registry error ---", module=module, error=str(e))
                    await websocket.send_json({"type": "error", "message": str(e)})
                except ValidationError as e:
                    logger.error("--- [WS] Validation error ---", module=module, error=str(e))
                    await websocket.send_json({"type": "error", "message": str(e)})
                except GeneratorError as e:
                    GENERATION_ERRORS.labels(module=module, error_type="GeneratorError").inc()
                    logger.error("--- [WS] Generation error ---", module=module, error=str(e))
                    await websocket.send_json({"type": "error", "message": str(e)})
                except GgenaError as e:
                    GENERATION_ERRORS.labels(module=module, error_type="GgenaError").inc()
                    logger.error("--- [WS] Framework error ---", module=module, error=str(e))
                    await websocket.send_json({"type": "error", "message": str(e)})
                except Exception as e:
                    logger.exception("--- [WS] Unexpected error in loop ---", module=module)
                    GENERATION_ERRORS.labels(module=module, error_type="UnexpectedError").inc()
                    from src.core.config import config as global_config
                    if global_config.get_bool("PRODUCTION", False):
                        await websocket.send_json({"type": "error", "message": "An internal server error occurred."})
                    else:
                        await websocket.send_json({"type": "error", "message": f"Unexpected error: {str(e)}"})

            except WebSocketDisconnect:
                logger.info("--- [WS] Client disconnected ---", module=module)
            except Exception as e:
                logger.error("--- [WS] Unexpected error in loop ---", module=module, error=str(e))
                try:
                    await websocket.send_json({"type": "error", "message": str(e)})
                except:
                    pass

    except Exception as e:
        logger.error("--- [WS] Unexpected error in loop ---", module=module, error=str(e))
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
