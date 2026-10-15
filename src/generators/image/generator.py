import torch
from diffusers import DiffusionPipeline
import sys
import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

def generate_image(prompt=None, output_path=None):
    # Если промпт не передан, берем из .env
    if prompt is None:
        prompt = os.getenv("DEFAULT_PROMPT", "A beautiful landscape")
    
    # Если путь не передан, создаем его на основе настроек или дефолта
    if output_path is None:
        output_dir = os.getenv("OUTPUT_DIR", ".")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "generated_image.png")

    print(f"--- Starting Image Generation ---")
    print(f"Prompt: {prompt}")
    print(f"Target Path: {output_path}")
    
    try:
        # Берем модель из .env
        model_id = os.getenv("MODEL_ID", "stabilityai/sdxl-turbo")
        
        print(f"Loading model '{model_id}' to GPU...")
        pipe = DiffusionPipeline.from_pretrained(
            model_id, 
            torch_dtype=torch.float16, 
            variant="fp16"
        )
        pipe.to("cuda")

        print("Generating... (this might take a few seconds)")
        # Для Turbo guidance_scale должен быть 0.0
        image = pipe(prompt=prompt, guidance_scale=0.0, num_inference_steps=1).images[0]

        print(f"Saving image to: {output_path}")
        image.save(output_path)
        print("--- Success! ---")
        
    except Exception as e:
        print(f"--- Error ---")
        print(str(e))
        sys.exit(1)

if __name__ == "__main__":
    # Если аргумент передан в командной строке, используем его
    user_prompt = sys.argv[1] if len(sys.argv) > 1 else None
    generate_image(user_prompt)
