import argparse
import sys
import os
import asyncio
import threading
import signal
from datetime import datetime
import logging

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

async def main():
    setup_logging()
    parser = argparse.ArgumentParser(description="AI Generator Orchestrator")
    parser.add_argument("module", help="The name of the generator module (e.g., 'image', 'audio')")
    parser.add_argument("prompt", nargs="?", help="Prompt for the generation")
    
    # Standardized common parameter for most generators
    parser.add_argument("--num-outputs", type=int, help="Number of outputs to generate")
    parser.add_argument("--output", help="Path to save generated files (directory or file pattern)")
    
    # Generic modality-specific parameters
    parser.add_argument("--param", action='append', help="Additional parameters in key=value format (e.g., --param width=832)")
    
    args = parser.parse_args()

    # 0. Initialize core components
    config = ConfigManager()
    registry = GeneratorRegistry()

    # 1. Discover generators
    discover_and_register_generators("src.generators", registry)

    if not args.prompt:
        logger.error("Prompt is required.")
        parser.print_help()
        sys.exit(1)

    # 2. Get generator from registry
    try:
        generator = registry.get(args.module, config=config, registry=registry)
        if not generator:
            available = registry.list_available()
            error_msg = f"Module '{args.module}' is not registered or not implemented."
            if available:
                error_msg += f"\nAvailable modules: {', '.join(available)}"
            raise RegistryError(error_msg)

        # 3. Parse extra parameters
        extra_params = {}
        if args.param:
            for p in args.param:
                try:
                    key, value = p.split('=', 1)
                    # Try to convert to int/float if possible
                    try:
                        if '.' in value:
                            value = float(value)
                        else:
                            value = int(value)
                    except ValueError:
                        pass # Keep as string
                    extra_params[key] = value
                except ValueError:
                    logger.warning(f"Invalid parameter format '{p}'. Use key=value.")
        
        # 4. Construct Request
        num_outputs = args.num_outputs if args.num_outputs is not None else extra_params.pop("num_outputs", 1)

        request = GenerationRequest(
            prompt=args.prompt,
            num_outputs=num_outputs,
            parameters=extra_params
        )

        # Setup shutdown event and signal handling
        shutdown_event = threading.Event()

        def handle_sigint(sig, frame):
            logger.info("[Orchestrator] Interrupt received (CTRL+C). Signaling shutdown...")
            shutdown_event.set()

        # Register signal handler for SIGINT (CTRL+C)
        signal.signal(signal.SIGINT, handle_sigint)

        # 5. Execute generation via Command Pattern
        logger.info(f"--- [Orchestrator] Dispatching request to '{args.module}' generator ---")
        
        context = CommandContext(registry=registry, config=config, shutdown_event=shutdown_event)
        executor = CommandExecutor(context)
        command = GenerationCommand(module=args.module, request=request)
        result = await executor.execute(command)

        # 6. Handle Response
        if result.success:
            response = result.result
            logger.info("--- [Orchestrator] Generation Successful! ---")
            
            # If user requested output saving
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
