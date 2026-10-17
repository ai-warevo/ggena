import argparse
import logging
from typing import Any
from src.core.exceptions import ValidationError

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
