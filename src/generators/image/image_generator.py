import torch
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
from .text_expander import translate_user_intent_to_tags

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

class ImageGenerator(BaseGenerator):
    """
    Implementation of the Image Generation strategy using SDXL (Pony V6).
    """

    @property
    def parameter_schema(self) -> Type[BaseModel]:
        return ImageParameters

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

    def _load_pipeline(self):
        if self._pipe is None:
            logger.info(f"Loading model '{self._model_id}' to GPU...")
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
                token=hf_token
            )
            self._pipe.to("cuda")

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """
        Generates images based on the provided request.
        Uses text expansion for better prompt quality.
        Returns image bytes in output_images.
        """
        logger.info("--- [Image Phase] Starting Image Generation ---")
        
        try:
            # 1. Determine Prompts (Priority: Request > Text Expander)
            req_pos = request.positive_prompt
            req_neg = request.negative_prompt

            if req_pos:
                expanded_pos = req_pos
                expanded_neg = req_neg if req_neg else ""
            elif request.prompt:
                logger.info("--- [Image Phase] Expanding original prompt ---")
                exp_pos, exp_neg_from_llm = await translate_user_intent_to_tags(request.prompt)
                expanded_pos = exp_pos
                req_pos = exp_pos
                expanded_neg = req_neg if req_neg else exp_neg_from_llm
            else:
                expanded_pos = ""
                expanded_neg = ""

            logger.info(f"Original Prompt: {request.prompt}")
            logger.info(f"Expanded Positive Prompt: {expanded_pos}")
            logger.info(f"Expanded Negative Prompt: {expanded_neg}")
            logger.info(f"Number of images requested: {request.num_outputs}")

            # 2. Load pipeline if not already loaded
            await asyncio.to_thread(self._load_pipeline)

            # --- [LoRA Phase] Dynamic LoRA loading ---
            lora_pattern = r'<lora:(.*?):([\d\.]+)>'
            matches = list(re.finditer(lora_pattern, expanded_pos))
            if matches:
                for match in matches:
                    filename = match.group(1)
                    weight = float(match.group(2))
                    # Clean the text prompt string by completely removing the <lora...> block
                    expanded_pos = expanded_pos.replace(match.group(0), "").strip()

                    lora_path = f"civitai_cache/{filename}.safetensors"
                    if os.path.exists(lora_path):
                        logger.info(f"--- [LoRA Phase] Dynamically loading {filename}.safetensors with weight {weight} ---")
                        self._pipe.load_lora_weights("civitai_cache/", weight_name=f"{filename}.safetensors", adapter_name=filename)
                        self._pipe.set_adapters([filename], adapter_weights=[weight])
                    else:
                        logger.warning(f"--- [LoRA Warning] File not found at {lora_path} ---")

            # 2.5 Encode prompts to handle long prompts (CLIP 77-token limit) via chunking
            logger.info("--- [Image Phase] Encoding prompts ---")
            prompt_embeds, negative_prompt_embeds, pooled_prompt_embeds, negative_pooled_prompt_embeds = await asyncio.to_thread(
                encode_infinite_prompt, self._pipe, expanded_pos, expanded_neg
            )

            # Move embeddings to the same device as the pipeline
            device = self._pipe.device
            prompt_embeds = prompt_embeds.to(device)
            negative_prompt_embeds = negative_prompt_embeds.to(device)
            pooled_prompt_embeds = pooled_prompt_embeds.to(device)
            negative_pooled_prompt_embeds = negative_pooled_prompt_embeds.to(device)

            # 3. Generate images
            output_files_bytes = []
            timestamp = datetime.now().strftime("%Y_%m_%d__%H_%M_%S")

            # Validate parameters using the schema
            try:
                params = ImageParameters(**request.parameters)
            except PydanticValidationError as e:
                raise ValidationError(f"Invalid image parameters: {str(e)}", details=e.errors())

            width = params.width
            height = params.height
            guidance_scale = params.guidance_scale
            num_inference_steps = params.num_inference_steps
            original_callback = params.callback_on_step_end
            on_image_ready = params.on_image_ready

            max_batch_size = self._config.get_int("IMAGE_MAX_BATCH_SIZE", 1)
            for i in range(0, request.num_outputs, max_batch_size):
                current_batch_size = min(max_batch_size, request.num_outputs - i)

                if self._shutdown_event and self._shutdown_event.is_set():
                    logger.warning("--- [Image Phase] Shutdown signal detected before starting next batch! ---")
                    raise GenerationCancelledError("Generation cancelled due to shutdown.")

                logger.info(f"Generating batch of {current_batch_size} images (starting from index {i})...")

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
                    if original_callback:
                        return original_callback(pipe, step_index, timestep, callback_kwargs)
                    return callback_kwargs

                # Use to_thread for the heavy synchronous pipeline call
                result = await asyncio.to_thread(
                    lambda: self._pipe(
                        prompt_embeds=batched_prompt_embeds,
                        negative_prompt_embeds=batched_negative_prompt_embeds,
                        pooled_prompt_embeds=batched_pooled_prompt_embeds,
                        negative_pooled_prompt_embeds=batched_negative_pooled_prompt_embeds,
                        guidance_scale=guidance_scale, 
                        num_inference_steps=num_inference_steps,
                        width=width,
                        height=height,
                        callback_on_step_end=wrapped_callback
                    )
                )

                # Process the batch of images
                for j in range(current_batch_size):
                    image = result.images[j]

                    # Always get bytes
                    buffer = io.BytesIO()
                    await asyncio.to_thread(image.save, buffer, format="PNG")
                    img_bytes = buffer.getvalue()
                    output_files_bytes.append(img_bytes)

                    # Check for streaming callback
                    if on_image_ready:
                        await asyncio.to_thread(on_image_ready, img_bytes, {
                            "positive_prompt": req_pos,
                            "negative_prompt": expanded_neg,
                            "model_id": self._model_id
                        })

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
            logger.warning(f"--- [Image Phase] Generation cancelled: {e} ---")
            return GenerationResponse(
                success=False, 
                error_message=str(e)
            )
        except ValidationError as e:
            logger.error(f"--- [Image Phase] Validation error: {e} ---")
            return GenerationResponse(
                success=False, 
                error_message=str(e)
            )
        except Exception as e:
            logger.error("--- Error during image generation ---")
            logger.exception(str(e))
            return GenerationResponse(
                success=False, 
                error_message=str(e)
            )
