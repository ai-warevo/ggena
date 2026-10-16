from typing import Any, Dict, Optional

class GgenaError(Exception):
    """Base exception for all ggena framework errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

class RegistryError(GgenaError):
    """Raised when there is an error in the GeneratorRegistry."""
    pass

class ValidationError(GgenaError):
    """Raised when parameter validation fails."""
    pass

class GeneratorError(GgenaError):
    """Raised during generator execution."""
    pass

class OrchestratorError(GgenaError):
    """Raised by the orchestration layer (CLI/Server)."""
    pass

class GenerationCancelledError(GgenaError):
    """Raised when a generation is interrupted by a shutdown signal."""
    pass
