import torch
from diffusers import StableDiffusionXLPipeline
import io
from datetime import datetime
from typing import List, Optional, Dict, Any, Callable, Type
import asyncio

from pydantic import BaseModel, Field
from src.generators.base import BaseGenerator
from src.core.types import GenerationRequest, GenerationResponse
from src.core.config import config
from .text_expander import translate_user_intent_to_tags

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

class ImageGenerator(BaseGenerator):
    """
    Implementation of the Image Generation strategy using SDXL (Pony V6).
    """

    @property
    def parameter_schema(self) -> Type[BaseModel]:
        return ImageParameters

    def __init__(self):
        self._pipe: Optional[StableDiffusionXLPipeline] = None
        self._model_id: str = config.get_str("IMAGE_MODEL_ID", "stablediffusionapi/Pony-Diffusion-V6-XL")

    def _load_pipeline(self):
        if self._pipe is None:
            print(f"Loading model '{self._model_id}' to GPU...")
            hf_token = config.get_str("HF_TOKEN")
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
        print(f"--- [Image Phase] Starting Image Generation ---")
        
        try:
            # 1. Determine Prompts (Priority: Request > Text Expander)
            req_pos = request.positive_prompt
            req_neg = request.negative_prompt

            if req_pos:
                expanded_pos = req_pos
                expanded_neg = req_neg if req_neg else ""
            elif request.prompt:
                print(f"--- [Image Phase] Expanding original prompt ---")
                exp_pos, exp_neg_from_llm = translate_user_intent_to_tags(request.prompt)
                expanded_pos = exp_pos
                expanded_neg = req_neg if req_neg else exp_neg_from_llm
            else:
                expanded_pos = ""
                expanded_neg = ""

            print(f"Original Prompt: {request.prompt}")
            print(f"Expanded Positive Prompt: {expanded_pos}")
            print(f"Expanded Negative Prompt: {expanded_neg}")
            print(f"Number of images requested: {request.num_outputs}")

            # 2. Load pipeline if not already loaded
            await asyncio.to_thread(self._load_pipeline)

            # 2.5 Encode prompts to handle long prompts (CLIP 77-token limit) via chunking
            print(f"--- [Image Phase] Encoding prompts ---")
            prompt_embeds, negative_prompt_embeds, pooled_prompt_embeds, negative_pooled_prompt_embeds = await asyncio.to_thread(
                encode_infinite_prompt, self._pipe, expanded_pos, expanded_neg
            )

            # 3. Generate images
            output_files_bytes = []
            timestamp = datetime.now().strftime("%Y_%m_%d__%H_%M_%S")

            # Validate parameters using the schema
            params = ImageParameters(**request.parameters)

            for i in range(request.num_outputs):
                print(f"\nGenerating image {i+1}/{request.num_outputs}...")
                
                # Use validated parameters
                width = params.width
                height = params.height
                guidance_scale = params.guidance_scale
                num_inference_steps = params.num_inference_steps

                # Use to_thread for the heavy synchronous pipeline call
                result = await asyncio.to_thread(
                    lambda: self._pipe(
                        prompt_embeds=prompt_embeds,
                        negative_prompt_embeds=negative_prompt_embeds,
                        pooled_prompt_embeds=pooled_prompt_embeds,
                        negative_pooled_prompt_embeds=negative_pooled_prompt_embeds,
                        guidance_scale=guidance_scale, 
                        num_inference_steps=num_inference_steps,
                        width=width,
                        height=height
                    )
                )
                image = result.images[0]

                # Always get bytes
                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
                img_bytes = buffer.getvalue()
                output_files_bytes.append(img_bytes)

                # Check for streaming callback
                on_image_ready = params.on_image_ready
                if on_image_ready:
                    await asyncio.to_thread(on_image_ready, img_bytes, {
                        "positive_prompt": expanded_pos,
                        "negative_prompt": expanded_neg,
                        "model_id": self._model_id
                    })

            print("\n--- All images generated successfully! ---")
            return GenerationResponse(
                success=True, 
                output_files_bytes=output_files_bytes,
                metadata={
                    "model_id": self._model_id,
                    "positive_prompt": expanded_pos,
                    "negative_prompt": expanded_neg
                }
            )

        except Exception as e:
            print(f"--- Error during image generation ---")
            print(str(e))
            return GenerationResponse(
                success=False, 
                error_message=str(e)
            )
