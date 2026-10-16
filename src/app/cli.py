import argparse
import sys
import os
import asyncio
import threading
import signal
from datetime import datetime
import logging
from typing import Any

from src.core.commands import GenerationCommand, CommandContext
from src.core.executor import CommandExecutor
from src.core.types import GenerationRequest
from src.core.registry import GeneratorRegistry
from src.core.utils import discover_and_register_generators
from src.core.config import ConfigManager
from src.core.exceptions import (
    RegistryError, 
    ValidationError, 
    GeneratorError, 
    GgenaError
)
from src.core.logging_setup import setup_logging

logger = logging.getLogger(__name__)

def parse_arguments() -> argparse.Namespace:
    """Parses command line arguments."""
    parser = argparse.ArgumentParser(description="AI Generator Orchestrator")
    parser.add_argument("module", help="The name of the generator module (e.g., 'image', 'audio')")
    parser.add_argument("prompt", help="Prompt for the generation")
    
    # Standardized common parameter for most generators
    parser.add_argument("--num-outputs", type=int, help="Number of outputs to generate")
    parser.add_argument("--output", help="Path to save generated files (directory or file pattern)")
    
    # Generic modality-specific parameters
    parser.add_argument("--param", action='append', help="Additional parameters in key=value format (e.g., --param width=832)")
    
    return parser.parse_args()

def initialize_environment() -> tuple[ConfigManager, GeneratorRegistry]:
    """Initializes core components and discovers generators."""
    config = ConfigManager()
    registry = GeneratorRegistry()
    discover_and_register_generators("src.generators", registry)
    return config, registry

def get_generator(registry: GeneratorRegistry, module: str, config: ConfigManager) -> Any:
    """Retrieves the requested generator from the registry."""
    generator = registry.get(module, config=config, registry=registry)
    if not generator:
        available = registry.list_available()
        error_msg = f"Module '{module}' is not registered or not implemented."
        if available:
            error_msg += f"\nAvailable modules: {', '.join(available)}"
        raise RegistryError(error_msg)
    return generator

def process_parameters(generator: Any, args: argparse.Namespace) -> tuple[dict, int]:
    """Parses and validates extra parameters."""
    extra_params = {}
    if args.param:
        for p in args.param:
            try:
                key, value = p.split('=', 1)
                extra_params[key] = value
            except ValueError:
                logger.warning(f"Invalid parameter format '{p}'. Use key=value.")

    # Validate extra parameters using generator's schema
    if generator.parameter_schema:
        try:
            validated_model = generator.parameter_schema.model_validate(extra_params)
            extra_params = validated_model.model_dump()
        except Exception as e:
            raise ValidationError(f"Invalid parameters for '{generator.__class__.__name__}': {str(e)}")

    # Determine num_outputs
    num_outputs = args.num_outputs if args.num_outputs is not None else extra_params.pop("num_outputs", 1)
    return extra_params, num_outputs

def setup_signal_handling() -> threading.Event:
    """Sets up signal handling for graceful shutdown."""
    shutdown_event = threading.Event()

    def handle_sigint(sig, frame):
        logger.info("[Orchestrator] Interrupt received (CTRL+C). Signaling shutdown...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, handle_sigint)
    return shutdown_event

def handle_output(args: argparse.Namespace, response: Any) -> None:
    """Handles saving the generation results to disk."""
    if args.output and response.output_files_bytes:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Determine base directory and filename pattern
        if os.path.isdir(args.output):
            base_dir = args.output
            file_pattern = f"{timestamp}_%d.png"
        elif os.path.isfile(args.output):
            base_dir = os.path.dirname(args.output) or "."
            name, ext = os.path.splitext(os.path.basename(args.output))
            file_pattern = f"{name}_{timestamp}_%d{ext}"
        else:
            # Assume it's a directory path that doesn't exist yet
            base_dir = args.output
            file_pattern = f"{timestamp}_%d.png"

        os.makedirs(base_dir, exist_ok=True)

        for i, img_bytes in enumerate(response.output_files_bytes):
            filename = file_pattern % (i + 1)
            full_path = os.path.join(base_dir, filename)
            with open(full_path, "wb") as f:
                f.write(img_bytes)
            logger.info(f"  - Saved to: {full_path}")
    elif response.output_files_bytes:
        logger.info(f"  - Generated {len(response.output_files_bytes)} files (use --output to save)")
    else:
        logger.info("  - No file data returned.")

    if response.metadata:
        logger.info(f"Metadata: {response.metadata}")

async def main():
    setup_logging()
    args = parse_arguments()

    try:
        config, registry = initialize_environment()
        generator = get_generator(registry, args.module, config)
        extra_params, num_outputs = process_parameters(generator, args)

        request = GenerationRequest(
            prompt=args.prompt,
            num_outputs=num_outputs,
            parameters=extra_params
        )

        shutdown_event = setup_signal_handling()

        logger.info(f"--- [Orchestrator] Dispatching request to '{args.module}' generator ---")
        
        context = CommandContext(registry=registry, config=config, shutdown_event=shutdown_event)
        executor = CommandExecutor(context)
        command = GenerationCommand(module=args.module, request=request)
        result = await executor.execute(command)

        if result.success:
            logger.info("--- [Orchestrator] Generation Successful! ---")
            handle_output(args, result.result)
        else:
            logger.error("--- [Orchestrator] Generation Failed ---")
            logger.error(f"Error: {result.error_message}")
            sys.exit(1)

    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.warning("--- [Orchestrator] Generation interrupted by user ---")
        sys.exit(1)
    except RegistryError as e:
        logger.error(f"[Registry Error] {e}")
        sys.exit(1)
    except ValidationError as e:
        logger.error(f"[Validation Error] {e}")
        sys.exit(1)
    except GeneratorError as e:
        logger.error(f"[Generator Error] {e}")
        sys.exit(1)
    except GgenaError as e:
        logger.error(f"[Framework Error] {e}")
        sys.exit(1)
    except Exception as e:
        logger.error("--- [Orchestrator] Unexpected error during execution ---")
        logger.exception(str(e))
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
