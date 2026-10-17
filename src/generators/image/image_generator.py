import torch
import random
from diffusers import StableDiffusionXLPipeline
import io
from datetime import datetime
from typing import List, Optional, Dict, Any, Callable, Type
import asyncio
import logging
import os
import re

from pydantic import BaseModel, Field, ValidationError as PydanticValidationError
from src.generators.base import BaseGenerator
from src.core.types import GenerationRequest, GenerationResponse
from src.core.exceptions import GeneratorError, ValidationError, GenerationCancelledError
from src.core.config import config
from .text_expander import translate_user_intent_to_tags, get_expander_model
from src.core.resource_manager import ManagedResource

logger = logging.getLogger(__name__)

def encode_infinite_prompt(pipe, prompt_text, negative_prompt_text):
    """Helper to encode long prompts by chunking them logically."""
    def get_prompt_chunks(text, tokenizer, max_tokens=75):
        words = text.split(", ")
        chunks = []
        current_chunk = []
        for word in words:
            test_str = ", ".join(current_chunk + [word])
            if len(tokenizer.encode(test_str)) > max_tokens:
                if current_chunk:
                    chunks.append(", ".join(current_chunk))
                    current_chunk = [word]
                else:
                    chunks.append(word)
                    current_chunk = []
            else:
                current_chunk.append(word)
        if current_chunk:
            chunks.append(", ".join(current_chunk))
        return chunks if chunks else [""]

    pos_chunks = get_prompt_chunks(prompt_text, pipe.tokenizer)
    neg_chunks = get_prompt_chunks(negative_prompt_text, pipe.tokenizer)
    
    # Pad to equal chunk count
    max_chunks = max(len(pos_chunks), len(neg_chunks))
    pos_chunks += [""] * (max_chunks - len(pos_chunks))
    neg_chunks += [""] * (max_chunks - len(neg_chunks))
    
    pos_embeds_all, neg_embeds_all = [], []
    pooled_pos_all, pooled_neg_all = [], []
    
    for p_chunk, n_chunk in zip(pos_chunks, neg_chunks):
        # Native encode_prompt handles single chunks perfectly
        p_embeds, n_embeds, p_pool, n_pool = pipe.encode_prompt(
            prompt=p_chunk,
            negative_prompt=n_chunk
        )
        pos_embeds_all.append(p_embeds)
        neg_embeds_all.append(n_embeds)
        pooled_pos_all.append(p_pool)
        pooled_neg_all.append(n_pool)
        
    # Concatenate hidden states along sequence length (dim=1)
    final_pos_embeds = torch.cat(pos_embeds_all, dim=1)
    final_neg_embeds = torch.cat(neg_embeds_all, dim=1)
    
    # Take the pooled embeddings from the first core chunk
    final_pooled_pos = pooled_pos_all[0]
    final_pooled_neg = pooled_neg_all[0]
    
    return final_pos_embeds, final_neg_embeds, final_pooled_pos, final_pooled_neg

class ImageParameters(BaseModel):
    """
    Pydantic model for validating image generation parameters.
    """
    width: int = Field(1024, ge=256, le=4096)
    height: int = Field(768, ge=256, le=4096)
    guidance_scale: float = Field(7.0, ge=1.0, le=20.0)
    num_inference_steps: int = Field(30, ge=1, le=100)
    on_image_ready: Optional[Callable[[bytes, Dict[str, Any]], Any]] = None
    callback_on_step_end: Optional[Callable] = None

class ImageGenerator(BaseGenerator, ManagedResource):
    """
    Implementation of the Image Generation strategy using SDXL (Pony V6).
    """

    @property
    def parameter_schema(self) -> Type[BaseModel]:
        return ImageParameters

    @property
    def name(self) -> str:
        return "image"

    def __init__(self, config=None):
        super().__init__(config=config)
        self._pipe: Optional[StableDiffusionXLPipeline] = None
        # Use injected config if available, otherwise fallback to a default (for backward compatibility during transition)
        if self._config:
            self._model_id: str = self._config.get_str("IMAGE_MODEL_ID", "stablediffusionapi/Pony-Diffusion-V6-XL")
        else:
            # This part is for backward compatibility if someone still uses the old way
            import src.core.config as global_config
            self._model_id: str = global_config.config.get_str("IMAGE_MODEL_ID", "stablediffusionapi/Pony-Diffusion-V6-XL")

    def _generate_random_prompt_from_env(self, character_name: str) -> str:
        """Generates a randomized prompt using environment-driven token pools."""
        starters = self._config.get_str("IMAGE_POSITIVE_STARTER", "").split(";")
        base_chars = self._config.get_str("RANDOM_BASE_CHARACTER_TAGS", "").split(";")
        actions_pool = self._config.get_str("RANDOM_ACTIONS", "").split(";")
        skin_pool = self._config.get_str("RANDOM_SKIN_DETAILS", "").split(";")
        camera_pool = self._config.get_str("RANDOM_CAMERA_ANGLES", "").split(";")
        light_pool = self._config.get_str("RANDOM_LIGHTING", "").split(";")
        env_pool = self._config.get_str("RANDOM_ENVIRONMENT", "").split(";")

        def safe_choice(lst: list[str]) -> str:
            # Filter empty strings from split results
            valid = [item.strip() for item in lst if item.strip()]
            return random.choice(valid) if valid else ""

        starter = safe_choice(starters)
        base_char_tag = safe_choice(base_chars)
        action = safe_choice(actions_pool)
        skin = safe_choice(skin_pool)
        camera = safe_choice(camera_pool)
        light = safe_choice(light_pool)
        env = safe_choice(env_pool)

        # Pipeline Merging: 1. Starters, 2. Name + base_chars, 3. Action, 4. Skin, 5. Camera, 6. Light, 7. Env
        tokens = []
        if starter: tokens.append(starter)
        if character_name: tokens.append(character_name)
        if base_char_tag: tokens.append(base_char_tag)
        if action: tokens.append(action)
        if skin: tokens.append(skin)
        if camera: tokens.append(camera)
        if light: tokens.append(light)
        if env: tokens.append(env)

        # Flatten all commas, strip white spaces, and filter duplicates
        flattened = []
        for t in tokens:
            for part in t.split(","):
                clean_part = part.strip()
                if clean_part:
                    flattened.append(clean_part)

        return ", ".join(list(dict.fromkeys(flattened)))

    async def load(self) -> None:
        if self._pipe is None:
            logger.info("Loading model '%s' to GPU with offloading...", self._model_id)
            # Use injected config if available, otherwise fallback
            hf_token = None
            if self._config:
                hf_token = self._config.get_str("HF_TOKEN")
            else:
                import src.core.config as global_config
                hf_token = global_config.config.get_str("HF_TOKEN")

            self._pipe = StableDiffusionXLPipeline.from_pretrained(
                self._model_id, 
                dtype=torch.float16, 
                variant="fp16",
                safety_checker=None,
                requires_safety_checker=False,
                token=hf_token,
                attn_implementation="flash_attention_2"
            )
            # Use accelerate's model offloading to save VRAM
            self._pipe.enable_model_cpu_offload()

            # --- [TensorRT Phase] Check for existing TensorRT engine ---
            trt_engine_path = self._config.get_str("TENSORRT_UNET_PATH")
            if trt_engine_path and os.path.exists(trt_engine_path):
                logger.info("--- [TensorRT Phase] TensorRT engine found at %s. (Loading logic placeholder) ---", trt_engine_path)
                # ponytail: <ceiling>, implement actual TRT loading via tensorrt or torch-tensorrt
                pass

            if self._config.get_bool("ENABLE_TORCH_COMPILE", False):
                logger.info("Compiling UNet and VAE with torch.compile (mode='reduce-overhead')...")
                try:
                    self._pipe.unet = torch.compile(self._pipe.unet, mode="reduce-overhead")
                    self._pipe.vae = torch.compile(self._pipe.vae, mode="reduce-overhead")
                except Exception as e:
                    logger.warning("torch.compile failed for UNet/VAE: %s. Proceeding without compilation.", e)
            else:
                logger.info("Skipping torch.compile (ENABLE_TORCH_COMPILE is false or not set).")

    async def unload(self) -> None:
        if self._pipe is not None:
            logger.info("Unloading SDXL pipeline...")
            # Disable offloading before deleting to avoid issues
            try:
                self._pipe.disable_model_cpu_offload()
            except Exception:
                pass
            del self._pipe
            self._pipe = None
            torch.cuda.empty_cache()

    async def _get_expanded_prompts(self, request: GenerationRequest, context: Optional[Any]) -> tuple[str, str, str]:
        """Handles text expansion and LoRA application."""
        # 1. Determine Prompts (Priority: Request > Text Expander)
        req_pos = request.positive_prompt
        req_neg = request.negative_prompt

        if req_pos:
            expanded_pos = req_pos
            expanded_neg = req_neg if req_neg else ""
        elif request.prompt == "random":
            logger.info("--- [Image Phase] Generating random prompt from environment ---")
            character_name = request.parameters.get("character", "")
            expanded_pos = self._generate_random_prompt_from_env(character_name)
            
            neg_pool = self._config.get_str("IMAGE_NEGATIVE_STARTER", "").split(";")
            valid_neg = [item.strip() for item in neg_pool if item.strip()]
            expanded_neg = random.choice(valid_neg) if valid_neg else ""
            
            req_pos = expanded_pos
        elif request.prompt:
            logger.info("--- [Image Phase] Expanding original prompt ---")
            # Use the managed text expander model via context or singleton
            model_id = self._config.get_str("TEXT_MODEL_ID", "Qwen/Qwen2.5-1.5B-Instruct")
            hf_token = self._config.get_str("HF_TOKEN")
            
            if context and context.resource_manager:
                # Ensure text expander model is loaded via resource manager
                await context.resource_manager.acquire("text_expander_llm")
            
            exp_pos, exp_neg_from_llm = await translate_user_intent_to_tags(request.prompt, model_id, hf_token)
            expanded_pos = exp_pos
            req_pos = exp_pos
            expanded_neg = req_neg if req_neg else exp_neg_from_llm
        else:
            expanded_pos = ""
            expanded_neg = ""

        logger.info("Original Prompt: %s", request.prompt)
        logger.info("Expanded Positive Prompt: %s", expanded_pos)
        logger.info("Expanded Negative Prompt: %s", expanded_neg)

        # --- [LoRA Phase] Dynamic LoRA loading ---
        lora_pattern = r'<lora:(.*?):([\d\.]+)>'
        matches = list(re.finditer(lora_pattern, expanded_pos))
        if matches:
            for match in matches:
                filename = match.group(1)
                weight = float(match.group(2))
                # Clean the text prompt string by completely removing the <lora...> block
                expanded_pos = expanded_pos.replace(match.group(0), "").strip()

                # Validate filename to prevent path traversal (only alphanumeric, underscores, or hyphens)
                if not re.match(r'^[a-zA-Z0-9_-]+$', filename):
                    logger.warning("--- [LoRA Warning] Invalid LoRA filename: %s (path traversal attempt or invalid characters) ---", filename)
                    continue

                lora_path = f"civitai_cache/{filename}.safetensors"
                if os.path.exists(lora_path):
                    logger.info("--- [LoRA Phase] Dynamically loading %s.safetensors with weight %s ---", filename, weight)
                    self._pipe.load_lora_weights("civitai_cache/", weight_name=f"{filename}.safetensors", adapter_name=filename)
                    self._pipe.set_adapters([filename], adapter_weights=[weight])
                else:
                    logger.warning("--- [LoRA Warning] File not found at %s ---", lora_path)
        
        return expanded_pos, expanded_neg, req_pos

    async def _prepare_embeddings(self, expanded_pos: str, expanded_neg: str) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """Handles CLIP encoding and device movement."""
        logger.info("--- [Image Phase] Encoding prompts ---")
        prompt_embeds, negative_prompt_embeds, pooled_prompt_embeds, negative_pooled_prompt_embeds = await asyncio.to_thread(
            encode_infinite_prompt, self._pipe, expanded_pos, expanded_neg
        )

        # Move embeddings to the same device as the pipeline (which might be CPU due to offloading!)
        device = self._pipe.device
        prompt_embeds = prompt_embeds.to(device)
        negative_prompt_embeds = negative_prompt_embeds.to(device)
        pooled_prompt_embeds = pooled_prompt_embeds.to(device)
        negative_pooled_prompt_embeds = negative_pooled_prompt_embeds.to(device)

        return prompt_embeds, negative_prompt_embeds, pooled_prompt_embeds, negative_pooled_prompt_embeds

    async def _execute_inference_batches(
        self, 
        request: GenerationRequest, 
        params: ImageParameters, 
        embeddings: tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor],
        req_pos: str,
        expanded_neg: str
    ) -> List[bytes]:
        """Manages the loop over batches and calls the model."""
        prompt_embeds, negative_prompt_embeds, pooled_prompt_embeds, negative_pooled_prompt_embeds = embeddings
        output_files_bytes = []
        
        max_batch_size = self._config.get_int("IMAGE_MAX_BATCH_SIZE", 1)
        for i in range(0, request.num_outputs, max_batch_size):
            current_batch_size = min(max_batch_size, request.num_outputs - i)

            if self._shutdown_event and self._shutdown_event.is_set():
                logger.warning("--- [Image Phase] Shutdown signal detected before starting next batch! ---")
                raise GenerationCancelledError("Generation cancelled due to shutdown.")

            logger.info("Generating batch of %d images (starting from index %d)...", current_batch_size, i)

            # Prepare batched embeddings
            batched_prompt_embeds = prompt_embeds.repeat(current_batch_size, 1, 1)
            batched_negative_prompt_embeds = negative_prompt_embeds.repeat(current_batch_size, 1, 1)
            batched_pooled_prompt_embeds = pooled_prompt_embeds.repeat(current_batch_size, 1)
            batched_negative_pooled_prompt_embeds = negative_pooled_prompt_embeds.repeat(current_batch_size, 1)

            # Wrap the callback to check for shutdown
            def wrapped_callback(pipe, step_index, timestep, callback_kwargs):
                if self._shutdown_event and self._shutdown_event.is_set():
                    logger.warning("--- [Image Phase] Shutdown signal detected in callback! ---")
                    raise GenerationCancelledError("Generation cancelled due to shutdown.")
                if params.callback_on_step_end:
                    return params.callback_on_step_end(pipe, step_index, timestep, callback_kwargs)
                return callback_kwargs

            # Use to_thread with a custom function that uses a CUDA stream (implied by the original code's comment)
            def _run_inference_in_stream():
                return self._pipe(
                    prompt_embeds=batched_prompt_embeds,
                    negative_prompt_embeds=batched_negative_prompt_embeds,
                    pooled_prompt_embeds=batched_pooled_prompt_embeds,
                    negative_pooled_prompt_embeds=batched_negative_pooled_prompt_embeds,
                    guidance_scale=params.guidance_scale, 
                    num_inference_steps=params.num_inference_steps,
                    width=params.width,
                    height=params.height,
                    callback_on_step_end=wrapped_callback
                )

            result = await asyncio.to_thread(_run_inference_in_stream)

            # Process the batch of images
            for j in range(current_batch_size):
                image = result.images[j]

                # Always get bytes
                buffer = io.BytesIO()
                await asyncio.to_thread(image.save, buffer, format="PNG")
                img_bytes = buffer.getvalue()
                output_files_bytes.append(img_bytes)

                # Check for streaming callback
                if params.on_image_ready:
                    await asyncio.to_thread(params.on_image_ready, img_bytes, {
                        "positive_prompt": req_pos,
                        "negative_prompt": expanded_neg,
                        "model_id": self._model_id
                    })

        return output_files_bytes

    async def generate(self, request: GenerationRequest, context: Optional[Any] = None) -> GenerationResponse:
        """
        Generates images based on the provided request.
        Uses text expansion for better prompt quality.
        Returns image bytes in output_images.
        """
        logger.info("--- [Image Phase] Starting Image Generation ---")
        
        try:
            # 0. Validate parameters
            try:
                params = ImageParameters(**request.parameters)
            except PydanticValidationError as e:
                raise ValidationError(f"Invalid image parameters: {str(e)}", details=e.errors())

            # 1. Load pipeline if not already loaded
            if self._pipe is None:
                await self.load()

            # 2. Expansion & LoRA
            try:
                expanded_pos, expanded_neg, req_pos = await self._get_expanded_prompts(request, context)
            except GenerationCancelledError:
                raise
            except Exception as e:
                logger.error("--- [Image Phase] Error during prompt expansion or LoRA loading: %s ---", e)
                raise GeneratorError(f"Prompt/LoRA error: {e}")

            # 3. Embeddings
            try:
                embeddings = await self._prepare_embeddings(expanded_pos, expanded_neg)
            except GenerationCancelledError:
                raise
            except Exception as e:
                logger.error("--- [Image Phase] Error during embedding preparation: %s ---", e)
                raise GeneratorError(f"Embedding error: {e}")

            # 4. Inference
            try:
                output_files_bytes = await self._execute_inference_batches(request, params, embeddings, req_pos, expanded_neg)
            except GenerationCancelledError:
                raise
            except Exception as e:
                logger.error("--- [Image Phase] Error during inference execution: %s ---", e)
                raise GeneratorError(f"Inference error: {e}")

            # 5. Cleanup & Response
            logger.info("--- All images generated successfully! ---")
            logger.info("--- [LoRA Phase] Unloading LoRA weights from GPU memory ---")
            self._pipe.unload_lora_weights()
            
            return GenerationResponse(
                success=True, 
                output_files_bytes=output_files_bytes,
                metadata={
                    "model_id": self._model_id,
                    "positive_prompt": req_pos,
                    "negative_prompt": expanded_neg
                }
            )

        except GenerationCancelledError as e:
            logger.warning("--- [Image Phase] Generation cancelled: %s ---", e)
            return GenerationResponse(success=False, error_message=str(e))
        except ValidationError as e:
            logger.error("--- [Image Phase] Validation error: %s ---", e)
            return GenerationResponse(success=False, error_message=str(e))
        except GeneratorError as e:
            # This catches the errors we raised in stages
            logger.error("--- [Image Phase] Generator error: %s ---", e)
            return GenerationResponse(success=False, error_message=str(e))
        except Exception as e:
            logger.error("--- Error during image generation ---")
            logger.exception(str(e))
            return GenerationResponse(success=False, error_message=str(e))
