from abc import ABC, abstractmethod
from typing import Any, Type, Optional
import threading

from pydantic import BaseModel
from src.core.types import GenerationRequest, GenerationResponse
from src.core.config import ConfigManager
from src.core.commands import CommandContext

class BaseGenerator(ABC):
    """
    Abstract Base Class for all AI generators in the ggena framework.
    This ensures a consistent interface across different modalities.
    """

    def __init__(self, config: Optional[ConfigManager] = None):
        self._shutdown_event: Optional[threading.Event] = None
        self._config = config

    def set_shutdown_event(self, event: threading.Event):
        """Sets the event that will be used to signal shutdown."""
        self._shutdown_event = event

    @property
    @abstractmethod
    def parameter_schema(self) -> Type[BaseModel]:
        """Returns the Pydantic model used for validating parameters."""
        pass

    @abstractmethod
    async def generate(self, request: GenerationRequest, context: Optional[CommandContext] = None) -> GenerationResponse:
        """
        Generates content based on the provided request.
        """
        pass
