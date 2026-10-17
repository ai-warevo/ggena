import structlog
from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError as PydanticValidationError

from src.core.types import GenerationRequest
from src.core.exceptions import GgenaError, ValidationError, GeneratorError, RegistryError
from src.core.commands import GenerationCommand
from src.core.metrics import ACTIVE_GENERATIONS, GENERATION_ERRORS
from src.app.server.models import RequestModel, ResponseModel

logger = structlog.get_logger(__name__)

router = APIRouter()

@router.post("/generate/{module}", response_model=ResponseModel)
async def generate(module: str, request_data: RequestModel, request: Request):
    """
    Endpoint to trigger generation for a specific module via HTTP POST.
    """
    registry = request.app.state.registry
    config = request.app.state.config
    try:
        generator = registry.get_instance(module, config=config)

        # Validate parameters against the generator's schema
        try:
            schema = generator.parameter_schema
            validated_params = schema(**request_data.parameters).model_dump()
        except PydanticValidationError as e:
            raise ValidationError(f"Invalid parameters for module '{module}': {str(e)}", details=e.errors())

        core_request = GenerationRequest(
            prompt=request_data.prompt,
            positive_prompt=request_data.positive_prompt,
            negative_prompt=request_data.negative_prompt,
            num_outputs=request_data.num_outputs,
            parameters=validated_params
        )

        logger.info("--- [Server] Processing request for module", module=module, prompt=request_data.prompt)
        
        ACTIVE_GENERATIONS.inc()
        try:
            command = GenerationCommand(module=module, request=core_request)
            result = await request.app.state.executor.execute(command)

            if not result.success:
                # If the generator returned success=False, it might have its own error message
                raise GeneratorError(result.error_message or "Generation failed.")
            return result.result
        finally:
            ACTIVE_GENERATIONS.dec()

    except RegistryError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail={"message": str(e), "details": e.details})
    except GeneratorError as e:
        GENERATION_ERRORS.labels(module=module, error_type="GeneratorError").inc()
        raise HTTPException(status_code=500, detail=str(e))
    except GgenaError as e:
        GENERATION_ERRORS.labels(module=module, error_type="GgenaError").inc()
        raise HTTPException(status_code=500, detail=f"Framework error: {str(e)}")
    except Exception as e:
        logger.exception("--- [Server] Unexpected error during generation ---", module=module)
        GENERATION_ERRORS.labels(module=module, error_type="UnexpectedError").inc()
        from src.core.config import config as global_config
        if global_config.get_bool("PRODUCTION", False):
            raise HTTPException(status_code=500, detail="An internal server error occurred.")
        else:
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
