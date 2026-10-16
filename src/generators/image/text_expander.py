import torch
import os
import json
import re
import logging
import asyncio
from dotenv import load_dotenv
from transformers import AutoModelForCausalLM, AutoTokenizer
from src.core.config import config

logger = logging.getLogger(__name__)

async def translate_user_intent_to_tags(user_input: str) -> tuple[str, str]:
    """
    Uses a lightweight LLM to expand user natural language into Danbooru-style tags.
    Ensures VRAM is cleared after execution.
    """
    model_id = config.get_str("TEXT_MODEL_ID", "Qwen/Qwen2.5-1.5B-Instruct")
    hf_token = config.get_str("HF_TOKEN")
    logger.info(f"--- [Text Phase] Loading text model '{model_id}' ---")

    try:
        tokenizer = await asyncio.to_thread(AutoTokenizer.from_pretrained, model_id, token=hf_token)
        model = await asyncio.to_thread(
            AutoModelForCausalLM.from_pretrained,
            model_id, 
            dtype=torch.float16, 
            device_map="cuda",
            token=hf_token
        )

        refinement_guidelines = config.get_str("IMAGE_EXTRA_REFINEMENT_RULES", "")
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
Example Output: {{"positive": "score_9, score_8_up, score_7_up, lara croft, brown shorts, thigh holsters, photorealistic, highly detailed skin texture, 8k, masterpiece", "negative": "score_4, score_5, score_6, ugly, deformed, blurry, low quality, bad anatomy, bad hands"}}"""


        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]

        text = await asyncio.to_thread(tokenizer.apply_chat_template, messages, tokenize=False, add_generation_prompt=True)
        model_inputs = await asyncio.to_thread(tokenizer, [text], return_tensors="pt")
        # Move to cuda if not already there (though tokenizer might have done it or it's on CPU)
        model_inputs = {k: v.to("cuda") for k, v in model_inputs.items()}

        logger.info(f"Expanding prompt: '{user_input}'")
        generated_ids = await asyncio.to_thread(
            model.generate,
            **model_inputs, 
            max_new_tokens=128,
            do_sample=True,
            temperature=0.2,
            top_p=0.9,
            repetition_penalty=1.35
        )
        response_ids = [
            output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        response = await asyncio.to_thread(tokenizer.batch_decode, response_ids, skip_special_tokens=True)
        response = response[0].strip()
        logger.debug(f"--- [Text Phase] Response: {response}")

        # Robustly extract JSON content if it's wrapped in markdown or has surrounding text
        json_start = response.find('{')
        json_end = response.rfind('}')
        if json_start != -1 and json_end != -1:
            response = response[json_start : json_end + 1]

        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            # Fallback: try to extract positive and negative tags using regex if JSON is malformed or truncated
            pos_match = re.search(r'["\']positive["\']\s*:\s*["\']([^"\']*)', response, re.DOTALL)
            neg_match = re.search(r'["\']negative["\']\s*:\s*["\']([^"\']*)', response, re.DOTALL)
            if pos_match:
                pos_val = pos_match.group(1).strip()
                neg_val = neg_match.group(1).strip() if neg_match else "score_4, score_5, score_6, low quality, bad anatomy"
                data = {
                    "positive": pos_val,
                    "negative": neg_val
                }
            else:
                raise
        
        # --- [Text Phase] Second Pass: Refinement of Positive Prompt ---
        try:
            logger.info(f"--- [Text Phase] Initial Positive: {data['positive']}")
            refinement_messages = [
                {"role": "system", "content": "You are a Token Deduplication and Consistency layer. Your function is to perform a single-pass validation on a provided token stream to ensure structural integrity, remove redundant entries, and resolve logical contradictions within the sequence. You must maintain strict adherence to existing token values."},
                {"role": "user", "content": f"Input Data:\nOriginal Intent: {user_input}\nCritical Refinement Rules: {refinement_guidelines}\nCurrent Token Stream: {data['positive']}\n\nTask:\n1. Deduplicate tokens in the Current Token Stream.\n2. Resolve logical contradictions (e.g., conflicting camera angles).\n3. MANDATORY PRESERVATION: You are strictly forbidden from modifying, deleting, or altering any tokens that match the 'Original Intent' or appear within the 'Critical Refinement Rules'. All production-critical keywords must be preserved verbatim.\n4. FORMATTING: Maintain standard comma-and-space delimiter formatting (', '). Do not alter casing, do not replace spaces with underscores, and do not append additional metadata.\n\nOutput ONLY the refined token stream."}
            ]

            refinement_text = await asyncio.to_thread(tokenizer.apply_chat_template, refinement_messages, tokenize=False, add_generation_prompt=True)
            model_inputs_refine = await asyncio.to_thread(tokenizer, [refinement_text], return_tensors="pt")
            model_inputs_refine = {k: v.to("cuda") for k, v in model_inputs_refine.items()}

            logger.info("--- [Text Phase] Refining positive prompt...")
            generated_ids_refine = await asyncio.to_thread(
                model.generate,
                **model_inputs_refine, 
                max_new_tokens=128,
                do_sample=False,
                temperature=0.1
            )
            response_ids_refine = [
                output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs_refine.input_ids, generated_ids_refine)
            ]
            refined_pos = await asyncio.to_thread(tokenizer.batch_decode, response_ids_refine, skip_special_tokens=True)
            refined_pos = refined_pos[0].strip()
            logger.info(f"--- [Text Phase] Refined Positive: {refined_pos}")

            # Ensure quality starters are present in the refined positive prompt
            quality_starters = "score_9, score_8_up, score_7_up,"
            if "score_9" not in refined_pos:
                refined_pos = f"{quality_starters} {refined_pos}"
            
            data["positive"] = refined_pos
        except Exception as e:
            logger.warning(f"--- [Text Phase] Refinement failed, using initial tags: {e} ---")

        del model
        del tokenizer
        torch.cuda.empty_cache()

        return data["positive"], data["negative"]

    except Exception as e:
        logger.error(f"--- [Text Phase] Error or parsing failure: {e} ---")
        fallback_pos = f"score_9, score_8_up, score_7_up, {user_input}"
        fallback_neg = "score_4, score_5, score_6, low quality, bad anatomy"

        if 'model' in locals(): del model
        if 'tokenizer' in locals(): del tokenizer
        torch.cuda.empty_cache()
        return fallback_pos, fallback_neg
