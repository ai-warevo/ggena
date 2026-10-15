import torch
from diffusers import StableDiffusionXLPipeline
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

def generate_image(prompt: str, negative_prompt: str, num_images: int = 1, output_path=None):
    """
    Initializes SDXL pipeline and generates images.
    Includes self-healing logic for Pony V6 tags.
    """
    # Ensure strings are not None
    prompt = prompt or ""
    negative_prompt = negative_prompt or ""

    # --- Self-Healing Logic (Removing the "crutches") ---
    # If positive prompt is missing Pony scores, add them.
    if prompt and "score_9" not in prompt:
        prompt = f"score_9, score_8_up, score_7_up, {prompt}"
    
    # If negative prompt is empty or missing Pony scores, fix it.
    if not negative_prompt or "score_4" not in negative_prompt:
        base_neg = "score_4, score_5, score_6, " if negative_prompt else "score_4, score_5, score_6, "
        negative_prompt = f"{base_neg}{negative_prompt.replace(base_neg, '').strip()}"
        if not negative_prompt.strip(): # If it was just empty
             negative_prompt = "score_4, score_5, score_6, low quality, bad anatomy"

    # Настройка пути сохранения
    output_dir = os.getenv("OUTPUT_DIR", ".")
    os.makedirs(output_dir, exist_ok=True)

    print(f"--- [Image Phase] Starting Image Generation (SDXL / Pony V6) ---")
    print(f"Final Prompt: {prompt}")
    print(f"Final Negative Prompt: {negative_prompt}")
    print(f"Number of images: {num_images}")
    
    try:
        model_id = os.getenv("IMAGE_MODEL_ID", "stablediffusionapi/Pony-Diffusion-V6-XL")
        
        print(f"Loading model '{model_id}' to GPU...")
        pipe = StableDiffusionXLPipeline.from_pretrained(
            model_id, 
            torch_dtype=torch.float16, 
            variant="fp16",
            safety_checker=None,
            requires_safety_checker=False
        )
        pipe.to("cuda")

        # Генерируем временную метку один раз для всей пачки
        timestamp = datetime.now().strftime("%Y_%m_%d__%H_%M_%S")

        for i in range(num_images):
            counter = i + 1
            filename = f"{timestamp}_{counter}.png"
            current_output_path = output_path if output_path else os.path.join(output_dir, filename)

            print(f"\nGenerating image {i+1}/{num_images}... (RTX 4080 power activated!)")
            
            image = pipe(
                prompt=prompt, 
                negative_prompt=negative_prompt,
                guidance_scale=7.0, 
                num_inference_steps=30,
                width=832,
                height=1216
            ).images[0]

            print(f"Saving image to: {current_output_path}")
            image.save(current_output_path)
        
        print("\n--- All images generated successfully! ---")
        
    except Exception as e:
        print(f"--- Error ---")
        print(str(e))
        sys.exit(1)

if __name__ == "__main__":
    # Usage: python generator.py "<user_prompt>" [num_images]
    user_input = sys.argv[1] if len(sys.argv) > 1 else None
    num_images = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    if not user_input:
        print("Usage: python generator.py '<user_prompt>' [num_images]")
        sys.exit(1)

    # Note: This part is for standalone usage of this file.
    # In the refactored version, we'll import these from text_expander and image_generator.
    from src.generators.image.text_expander import translate_user_intent_to_tags
    
    # Step 1: Text expansion (LLM)
    pos_prompt, neg_prompt = translate_user_intent_to_tags(user_input)

    # Step 2: Image generation (SDXL)
    generate_image(pos_prompt, neg_prompt, num_images)
