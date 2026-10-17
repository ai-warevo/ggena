import os
import logging
import signal
import threading
import argparse
from datetime import datetime
from typing import Any

from src.core.exceptions import RegistryError, ValidationError

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

def get_generator(registry: Any, module: str, config: Any) -> Any:
    """Retrieves the requested generator from the registry."""
    generator = registry.get(module, config=config, registry=registry)
    if not generator:
        available = registry.list_available()
        error_msg = f"Module '{module}' is not registered or not implemented."
        if available:
            error_msg += f"\nAvailable modules: {', '.join(available)}"
        raise RegistryError(error_msg)
    return generator

def setup_signal_handling() -> threading.Event:
    """Sets up signal handling for graceful shutdown."""
    shutdown_event = threading.Event()

    def handle_sigint(sig, frame):
        logger.info("[Orchestrator] Interrupt received (CTRL+C). Signaling shutdown...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, handle_sigint)
    return shutdown_event

def handle_output(args: Any, response: Any) -> None:
    """Handles saving the generation results to disk."""
    if args.output and response.output_files_bytes:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Resolve absolute paths for validation
        abs_output = os.path.abspath(args.output)
        safe_base = os.getcwd()

        # Determine the directory we will actually be writing into
        if os.path.isdir(abs_output):
            target_dir = abs_output
        elif os.path.isfile(abs_output):
            target_dir = os.path.dirname(abs_output)
        else:
            # If it doesn't exist, we treat the path as a directory (as per current implementation)
            target_dir = abs_output

        # Validate target_dir is within safe_base
        try:
            if os.path.commonpath([safe_base]) != os.path.commonpath([safe_base, target_dir]):
                raise ValidationError(f"Security Error: Output path '{args.output}' is outside the allowed directory.")
        except ValueError:
            raise ValidationError(f"Security Error: Output path '{args.output}' is on a different drive or invalid.")

        # Determine base directory and filename pattern (using validated abs_output)
        if os.path.isdir(abs_output):
            base_dir = abs_output
            file_pattern = f"{timestamp}_%d.png"
        elif os.path.isfile(abs_output):
            base_dir = os.path.dirname(abs_output) or "."
            name, ext = os.path.splitext(os.path.basename(abs_output))
            file_pattern = f"{name}_{timestamp}_%d{ext}"
        else:
            # Assume it's a directory path that doesn't exist yet
            base_dir = abs_output
            file_pattern = f"{timestamp}_%d.png"

        os.makedirs(base_dir, exist_ok=True)

        for i, img_bytes in enumerate(response.output_files_bytes):
            filename = file_pattern % (i + 1)
            full_path = os.path.join(base_dir, filename)
            with open(full_path, "wb") as f:
                f.write(img_bytes)
            logger.info("  - Saved to: %s", full_path)
    elif response.output_files_bytes:
        logger.info("  - Generated %d files (use --output to save)", len(response.output_files_bytes))
    else:
        logger.info("  - No file data returned.")

    if response.metadata:
        logger.info("Metadata: %s", response.metadata)
