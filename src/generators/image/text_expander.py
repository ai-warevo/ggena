import torch
import os
import json
from dotenv import load_dotenv
from transformers import AutoModelForCausalLM, AutoTokenizer

# Загружаем переменные из .env
load_dotenv()

def translate_user_intent_to_tags(user_input: str) -> tuple[str, str]:
    """
    Uses a lightweight LLM to expand user natural language into Danbooru-style tags.
    Ensures VRAM is cleared after execution.
    """
    model_id = os.getenv("TEXT_MODEL_ID", "Qwen/Qwen2.5-1.5B-Instruct")
    print(f"--- [Text Phase] Loading text model '{model_id}' ---")

    try:
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForCausalLM.from_pretrained(
            model_id, 
            torch_dtype=torch.float16, 
            device_map="cuda"
        )

        refinement_guidelines = os.getenv("EXTRA_REFINEMENT_RULES", "")
        system_prompt = f"""You are a specialized assistant that converts natural language descriptions (English or Russian) into structured Danbooru-style tags for image generation using Pony Diffusion V6 XL.

Your output must be a valid JSON object with exactly two keys: 'positive' and 'negative'. Do not include any markdown wrapper or explanation.

Rules:
1. Quality Starters: Positive prompt MUST always start with 'score_9, score_8_up, score_7_up, '. Negative prompt MUST always start with 'score_4, score_5, score_6, '.
2. Style: Convert descriptions into short, comma-separated Danbooru tags. Avoid long sentences. Always append aesthetic tags to positive: 'photorealistic, highly detailed skin texture, 8k, masterpiece'. Always add basic negatives: 'ugly, deformed, blurry, low quality, bad anatomy, bad hands'.
3. Dynamic Camera Framing: Adapt camera angles based on user intent. 
   - If the user asks for facial features, expressions, or a portrait, include: 'portrait, close-up, upper body, looking at viewer'.
   - If the user asks for lower body, explicit anatomy, or dynamic poses, include: 'cowboy shot' or 'full body'.
   - If the user asks for rear views, buttocks, or back angles, include: 'view from behind, from behind, looking back, looking back at viewer'.
4. Advanced Pipeline Refinement: 
   {refinement_guidelines}

Example Input: 'лара крофт в шортах'
Example Output: {{"positive": "score_9, score_8_up, score_7_up, lara croft, brown shorts, thigh holsters, photorealistic, highly detailed skin texture, 8k, masterpiece", "negative": "score_4, score_5, score_6, ugly, deformed, blurry, low quality, bad anatomy, bad hands"}}"""


        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]

        text = tokenizer.apply_chat_template(
            messages, 
            tokenize=False, 
            add_generation_prompt=True
        )
        model_inputs = tokenizer([text], return_tensors="pt").to("cuda")

        print(f"Expanding prompt: '{user_input}'")
        generated_ids = model.generate(
            **model_inputs, 
            max_new_tokens=256,
            do_sample=False
        )
        response_ids = [
            output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        response = tokenizer.batch_decode(response_ids, skip_special_tokens=True)[0].strip()

        # Clean up VRAM immediately before returning
        del model
        del tokenizer
        torch.cuda.empty_cache()

        # Parse JSON response
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()

        data = json.loads(response)
        return data["positive"], data["negative"]

    except Exception as e:
        print(f"--- [Text Phase] Error or parsing failure: {e} ---")
        # Fallback to basic prompt if LLM fails
        fallback_pos = f"score_9, score_8_up, score_7_up, {user_input}"
        fallback_neg = "score_4, score_5, score_6, low quality, bad anatomy"
        # Ensure cleanup even on error if model was loaded
        if 'model' in locals(): del model
        if 'tokenizer' in locals(): del tokenizer
        torch.cuda.empty_cache()
        return fallback_pos, fallback_neg
