import torch
import os
import json
import re
import logging
import asyncio
from typing import Optional, Tuple, Dict, Any
from dotenv import load_dotenv
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from src.core.config import config
from src.core.resource_manager import ManagedResource

logger = logging.getLogger(__name__)


def extract_json_from_text(text: str) -> Dict[str, Any]:
    """
    Robustly extracts a JSON object from text that might contain markdown or other noise.
    Falls back to regex extraction if JSON parsing fails.
    """
    # 1. Try to find JSON block
    json_start = text.find('{')
    json_end = text.rfind('}')
    if json_start != -1 and json_end != -1:
        candidate = text[json_start : json_end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            # If JSON parsing fails, we'll fall back to regex on the original text
            pass

    # 2. Fallback: Regex extraction
    pos_match = re.search(r'["\']positive["\']\s*:\s*["\']([^"\']*)', text, re.DOTALL)
    neg_match = re.search(r'["\']negative["\']\s*:\s*["\']([^"\']*)', text, re.DOTALL)
    if pos_match:
        pos_val = pos_match.group(1).strip()
        neg_val = neg_match.group(1).strip() if neg_match else "score_4, score_5, score_6, low quality, bad anatomy"
        return {
            "positive": pos_val,
            "negative": neg_val
        }

    raise ValueError("Could not extract JSON or relevant tags from text")


class TextExpanderModel(ManagedResource):
    """
    A managed wrapper for the LLM used in text expansion.
    """
    def __init__(self, model_id: str, hf_token: Optional[str] = None):
        self._model_id = model_id
        self._hf_token = hf_token
        self._model: Optional[AutoModelForCausalLM] = None
        self._tokenizer: Optional[AutoTokenizer] = None

    @property
    def name(self) -> str:
        return "text_expander_llm"

    async def load(self) -> None:
        if self._model is not None:
            return

        logger.info(f"--- [Text Phase] Loading text model '{self._model_id}' ---")
        try:
            self._tokenizer = await asyncio.to_thread(AutoTokenizer.from_pretrained, self._model_id, token=self._hf_token)
            
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )

            self._model = await asyncio.to_thread(
                AutoModelForCausalLM.from_pretrained,
                self._model_id, 
                quantization_config=bnb_config,
                device_map="auto",
                token=self._hf_token,
                dtype=torch.float16
            )
        except Exception as e:
            logger.error(f"--- [Text Phase] Failed to load model: {e} ---")
            raise

    async def unload(self) -> None:
        if self._model is not None:
            logger.info(f"--- [Text Phase] Unloading text model '{self._model_id}' ---")
            del self._model
            del self._tokenizer
            self._model = None
            self._tokenizer = None
            torch.cuda.empty_cache()

    def get_model(self) -> AutoModelForCausalLM:
        if self._model is None:
            raise RuntimeError("TextExpanderModel not loaded. Call load() first.")
        return self._model

    def get_tokenizer(self) -> AutoTokenizer:
        if self._tokenizer is None:
            raise RuntimeError("TextExpanderModel not loaded. Call load() first.")
        return self._tokenizer

# Singleton instance for the module
_instance: Optional[TextExpanderModel] = None

async def get_expander_model(model_id: str, hf_token: Optional[str] = None) -> TextExpanderModel:
    global _instance
    if _instance is None:
        _instance = TextExpanderModel(model_id, hf_token)
    return _instance

async def _generate_in_stream(model: AutoModelForCausalLM, model_inputs: Dict[str, torch.Tensor], **kwargs) -> torch.Tensor:
    """Helper to generate in a separate CUDA stream."""
    stream = torch.cuda.Stream()
    with torch.cuda.stream(stream):
        return model.generate(**model_inputs, **kwargs)


async def _expand_initial_prompt(
    model: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    user_input: str,
    refinement_guidelines: str,
) -> Dict[str, Any]:
    """First pass: Expand user intent into initial tags."""
    system_prompt = f"""You are a specialized assistant that converts natural language descriptions (English or Russian) into structured Danbooru-style tags for image generation using Pony Diffusion V6 XL.

Your output must be a valid JSON object with exactly two keys: 'positive' and 'negative'. Do not include any markdown wrapper, explanation, or conversational text.

CRITICAL COMPLIANCE DIRECTIVE:
You must strictly enforce the instructions provided in 'Advanced Pipeline Refinement' (Rule 4). If the user request matches the conditions inside 'Advanced Pipeline Refinement' (Rule 4), you MUST copy the exact positive and negative tags specified in Rule 4 into your JSON output fields. Do not alter, censor, soften, or generalize them under any circumstances. Failure to do so will break the pipeline.

Rules:
1. Quality Starters: Positive prompt MUST always start with 'score_9, score_8_up, score_7_up, '. Negative prompt MUST always start with 'score_4, score_5, score_6, '.
2. Style: Convert descriptions into short, comma-separated Danbooru tags. Avoid long sentences. Keep the total length strictly under 45 words (approx. 60 tokens) to ensure it fits within CLIP limits.
3. Dynamic Camera Framing: Adapt camera angles based on the core focus of the user's intent. Do not stack conflicting angles.
   - If the request focuses purely on facial features, expressions, or a portrait, include: 'portrait, close-up, upper body, looking at viewer'.
   - If the request focuses on full-body clothing, footwear, legs, or dynamic full-body actions, include: 'cowboy shot' or 'full body'.
   - If the request focuses on rear views, buttocks, or back angles, include: 'view from behind, from behind, looking back, looking back at viewer'.
4. Advanced Pipeline Refinement: 
   {refinement_guidelines}

5. Character Preservation: NEVER change, alter, or hallucinate the character's name. If the input specifies a character name, the positive tags MUST include that exact name. Do not invent alternative names. Put the core character attributes (like 'black blindfold, white hair, short hair') at the very beginning of the positive prompt, right after the quality starters.

Strict Output Rule: Your response must be ONE SINGLE valid JSON object. Never close the bracket before the negative key. Never put a comma between separate bracket pairs.

Example Input: 'лара крофт в шортах'
Example Output: {{"positive": "score_9, score_8_up, score_7_up, lara croft, brown shorts, thigh holsters, photorealistic, highly detailed skin texture, 8k, masterpiece", "negative": "score_4, score_5, score_6, ugly, deformed, blurry, low quality, bad anatomy"}}"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]

    text = await asyncio.to_thread(tokenizer.apply_chat_template, messages, tokenize=False, add_generation_prompt=True)
    model_inputs = await asyncio.to_thread(tokenizer, [text], return_tensors="pt")
    model_inputs = {k: v.to("cuda") for k, v in model_inputs.items()}

    logger.info(f"Expanding prompt: '{user_input}'")
    generated_ids = await asyncio.to_thread(
        _generate_in_stream, model, model_inputs, max_new_tokens=128, do_sample=True, temperature=0.2, top_p=0.9, repetition_penalty=1.35
    )
    response_ids = [
        output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs["input_ids"], generated_ids)
    ]
    response = await asyncio.to_thread(tokenizer.batch_decode, response_ids, skip_special_tokens=True)
    response = response[0].strip()
    logger.debug(f"--- [Text Phase] Response: {response}")

    return extract_json_from_text(response)


async def _refine_prompt(
    model: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    user_input: str,
    refinement_guidelines: str,
    initial_positive: str,
) -> str:
    """Second pass: Refine the positive prompt for consistency and deduplication."""
    refinement_messages = [
        {"role": "system", "content": "You are a Token Deduplication and Consistency layer. Your function is to perform a single-pass validation on a provided token stream to ensure structural integrity, remove redundant entries, and resolve logical contradictions within the sequence. You must maintain strict adherence to existing token values."},
        {"role": "user", "content": f"Input Data:\nOriginal Intent: {user_input}\nCritical Refinement Rules: {refinement_guidelines}\nCurrent Token Stream: {initial_positive}\n\nTask:\n1. Deduplicate tokens in the Current Token Stream.\n2. Resolve logical contradictions (e.g., conflicting camera angles).\n3. MANDATORY PRESERVATION: You are strictly forbidden from modifying, deleting, or altering any tokens that match the 'Original Intent' or appear within the 'Critical Refinement Rules'. All production-critical keywords must be preserved verbatim.\n4. FORMATTING: Maintain standard comma-and-space delimiter formatting (', '). Do not alter casing, do not replace spaces with underscores, and do not append additional metadata.\n\nOutput ONLY the refined token stream."}
    ]

    refinement_text = await asyncio.to_thread(tokenizer.apply_chat_template, refinement_messages, tokenize=False, add_generation_prompt=True)
    model_inputs_refine = await asyncio.to_thread(tokenizer, [refinement_text], return_tensors="pt")
    model_inputs_refine = {k: v.to("cuda") for k, v in model_inputs_refine.items()}

    logger.info("--- [Text Phase] Refining positive prompt...")
    generated_ids_refine = await asyncio.to_thread(
        _generate_in_stream, model, model_inputs_refine, max_new_tokens=128, do_sample=False, temperature=0.1
    )
    response_ids_refine = [
        output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs_refine["input_ids"], generated_ids_refine)
    ]
    refined_pos = await asyncio.to_thread(tokenizer.batch_decode, response_ids_refine, skip_special_tokens=True)
    refined_pos = refined_pos[0].strip()
    logger.info(f"--- [Text Phase] Refined Positive: {refined_pos}")

    # Ensure quality starters are present in the refined positive prompt
    quality_starters = "score_9, score_8_up, score_7_up,"
    if "score_9" not in refined_pos:
        refined_pos = f"{quality_starters} {refined_pos}"

    return refined_pos


async def translate_user_intent_to_tags(user_input: str, model_id: str, hf_token: Optional[str] = None) -> tuple[str, str]:
    """
    Uses a lightweight LLM to expand user natural language into Danbooru-style tags.
    The model is managed via the singleton instance.
    """
    expander = await get_expander_model(model_id, hf_token)
    if expander._model is None:
        await expander.load()

    model = expander.get_model()
    tokenizer = expander.get_tokenizer()
    refinement_guidelines = config.get_str("IMAGE_EXTRA_REFINEMENT_RULES", "")

    # Pass 1: Expansion
    data = await _expand_initial_prompt(model, tokenizer, user_input, refinement_guidelines)

    # Pass 2: Refinement
    try:
        logger.info(f"--- [Text Phase] Initial Positive: {data['positive']}")
        refined_pos = await _refine_prompt(model, tokenizer, user_input, refinement_guidelines, data["positive"])
        data["positive"] = refined_pos
    except Exception as e:
        logger.warning(f"--- [Text Phase] Refinement failed, using initial tags: {e} ---")

    return data["positive"], data["negative"]
