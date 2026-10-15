import argparse
import sys
import os
from dotenv import load_dotenv

load_dotenv()

from src.generators.image import generate_image, translate_user_intent_to_tags

def main():
    parser = argparse.ArgumentParser(description="AI Generator Orchestrator")
    parser.add_argument("module", choices=["audio", "music", "image", "video"], help="Module to run")
    parser.add_argument("prompt", nargs="?", help="Prompt for the generator")
    parser.add_argument("--num-images", type=int, default=int(os.getenv("IMAGE_GEN_COUNT", 1)), help="Number of images to generate")


    args = parser.parse_args()

    if args.module == "image":
        if not args.prompt:
            raise "?"

        print(f"--- [Orchestrator] Expanding user prompt via LLM ---")
        pos_prompt, neg_prompt = translate_user_intent_to_tags(args.prompt)

        generate_image(pos_prompt, neg_prompt, num_images=args.num_images)
    elif args.module in ["audio", "music", "video"]:
        print(f"Module '{args.module}' is not implemented yet.")
        sys.exit(0)
    else:
        print(f"Unknown module: {args.module}")
        sys.exit(1)

if __name__ == "__main__":
    main()
