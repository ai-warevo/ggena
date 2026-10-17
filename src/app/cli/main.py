import asyncio
import sys
import logging
from src.app.cli.args import parse_arguments, process_parameters
from src.app.cli.env import initialize_environment
from src.app.cli.utils import get_generator, setup_signal_handling, handle_output

from src.core.commands import GenerationCommand, CommandContext
from src.core.executor import CommandExecutor
from src.core.types import GenerationRequest
from src.core.logging_setup import setup_logging
from src.core.exceptions import (
    RegistryError, 
    ValidationError, 
    GeneratorError, 
    GgenaError
)

logger = logging.getLogger(__name__)

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
