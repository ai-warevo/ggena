import argparse
import sys
import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

from src.generators.image.generator import generate_image

def main():
    parser = argparse.ArgumentParser(description="AI Generator Orchestrator")
    parser.add_argument("module", choices=["audio", "music", "image", "video"], help="Module to run")
    parser.add_argument("prompt", nargs="?", help="Prompt for the generator")
    parser.add_argument("--negative-prompt", dest="negative_prompt", help="Negative prompt for the generator")

    args = parser.parse_args()

    if args.module == "image":
        # Fallback для prompt и negative_prompt
        prompt = args.prompt if args.prompt else os.getenv("DEFAULT_PROMPT", "")
        neg_prompt = args.negative_prompt if args.negative_prompt else os.getenv("DEFAULT_NEGATIVE_PROMPT", "")
        generate_image(prompt, neg_prompt)
    elif args.module in ["audio", "music", "video"]:
        print(f"Module '{args.module}' is not implemented yet.")
        sys.exit(0)
    else:
        print(f"Unknown module: {args.module}")
        sys.exit(1)

if __name__ == "__main__":
    main()
