from abc import ABC, abstractmethod
from typing import Any, Type, Optional
import threading

from pydantic import BaseModel
from src.core.types import GenerationRequest, GenerationResponse

class BaseGenerator(ABC):
    """
    Abstract Base Class for all AI generators in the ggena framework.

    All specific generator implementations (e.g., ImageGenerator, AudioGenerator) 
    must inherit from this class and implement the `generate` method. 
    This ensures a consistent interface across different modalities.
    """

    def __init__(self):
        self._shutdown_event: Optional[threading.Event] = None

    def set_shutdown_event(self, event: threading.Event):
        """Sets the event that will be used to signal shutdown."""
        self._shutdown_event = event

    @property
    @abstractmethod
    def parameter_schema(self) -> Type[BaseModel]:
        """Returns the Pydantic model used for validating parameters."""
        pass

    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """
        Generates content based on the provided request.

        Args:
            request (GenerationRequest): The generation request object.

        Returns:
            GenerationResponse: The generation response object.
        """
        pass
