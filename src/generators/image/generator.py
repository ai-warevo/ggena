import torch
from diffusers import StableDiffusionXLPipeline
import sys
import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

def generate_image(prompt: str, negative_prompt: str, output_path=None):
    if not prompt:
        prompt = ""
    if "score_9" not in prompt and prompt != "":
        prompt = f"score_9, score_8_up, score_7_up, {prompt}"
        
    if not negative_prompt:
        negative_prompt = ""

    # Настройка пути сохранения
    if output_path is None:
        output_dir = os.getenv("OUTPUT_DIR", ".")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "generated_image.png")

    print(f"--- Starting Image Generation (SDXL / Pony V6) ---")
    print(f"Prompt: {prompt}")
    print(f"Negative Prompt: {negative_prompt}")
    print(f"Target Path: {output_path}")
    
    try:
        model_id = os.getenv("MODEL_ID", "stabilityai/sdxl-turbo")
        
        print(f"Loading model '{model_id}' to GPU...")
        pipe = StableDiffusionXLPipeline.from_pretrained(
            model_id, 
            torch_dtype=torch.float16, 
            variant="fp16",
            safety_checker=None,
            requires_safety_checker=False
        )
        pipe.to("cuda")

        print("Generating... (RTX 4080 power activated!)")
        
        image = pipe(
            prompt=prompt, 
            negative_prompt=negative_prompt,
            guidance_scale=7.0, 
            num_inference_steps=30
        ).images[0]

        print(f"Saving image to: {output_path}")
        image.save(output_path)
        print("--- Success! ---")
        
    except Exception as e:
        print(f"--- Error ---")
        print(str(e))
        sys.exit(1)

if __name__ == "__main__":
    user_prompt = sys.argv[1] if len(sys.argv) > 1 else None
    negative_prompt = sys.argv[2] if len(sys.argv) > 2 else None
    generate_image(user_prompt, negative_prompt)
