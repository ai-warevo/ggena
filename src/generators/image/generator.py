import torch
from diffusers import StableDiffusionXLPipeline
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

def generate_image(prompt: str, negative_prompt: str, num_images: int = 1, output_path=None):
    if not prompt:
        prompt = ""
    if "score_9" not in prompt and prompt != "":
        prompt = f"score_9, score_8_up, score_7_up, {prompt}"
        
    if not negative_prompt:
        negative_prompt = ""

    # Настройка пути сохранения
    output_dir = os.getenv("OUTPUT_DIR", ".")
    os.makedirs(output_dir, exist_ok=True)

    print(f"--- Starting Image Generation (SDXL / Pony V6) ---")
    print(f"Prompt: {prompt}")
    print(f"Negative Prompt: {negative_prompt}")
    print(f"Number of images: {num_images}")
    
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

        # Генерируем временную метку один раз для всей пачки
        timestamp = datetime.now().strftime("%Y_%m_%d__%H_%M_%S")

        for i in range(num_images):
            counter = i + 1
            if num_images > 1:
                filename = f"{timestamp}_{counter}.png"
                current_output_path = os.path.join(output_dir, filename)
            else:
                # Если просили одну картинку и передали конкретный путь - используем его
                # Иначе используем timestamp для единообразия или старый формат? 
                # Пользователь сказал "префикс у файлов должен быть...", значит лучше всегда использовать timestamp.
                filename = f"{timestamp}_{counter}.png"
                current_output_path = output_path if output_path else os.path.join(output_dir, filename)

            print(f"\nGenerating image {i+1}/{num_images}... (RTX 4080 power activated!)")
            
            image = pipe(
                prompt=prompt, 
                negative_prompt=negative_prompt,
                guidance_scale=7.0, 
                num_inference_steps=30
            ).images[0]

            print(f"Saving image to: {current_output_path}")
            image.save(current_output_path)
        
        print("\n--- All images generated successfully! ---")
        
    except Exception as e:
        print(f"--- Error ---")
        print(str(e))
        sys.exit(1)

if __name__ == "__main__":
    user_prompt = sys.argv[1] if len(sys.argv) > 1 else None
    negative_prompt = sys.argv[2] if len(sys.argv) > 2 else None
    num_images = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    generate_image(user_prompt, negative_prompt, num_images)
