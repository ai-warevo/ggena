import torch
from diffusers import StableDiffusionXLPipeline
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

def generate_image(prompt: str, negative_prompt: str, num_images: int = 1, output_path=None):
    """
    Initializes SDXL pipeline and generates images.
    Includes self-healing logic for Pony V6 tags.
    """
    prompt = prompt or ""
    negative_prompt = negative_prompt or ""

    if prompt and "score_9" not in prompt:
        prompt = f"score_9, score_8_up, score_7_up, {prompt}"
    
    if not negative_prompt or "score_4" not in negative_prompt:
        base_neg = "score_4, score_5, score_6, " if negative_prompt else "score_4, score_5, score_6, "
        negative_prompt = f"{base_neg}{negative_prompt.replace(base_neg, '').strip()}"
        if not negative_prompt.strip():
             negative_prompt = "score_4, score_5, score_6, low quality, bad anatomy"

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
