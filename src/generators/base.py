from abc import ABC, abstractmethod
from typing import Any

from src.core.types import GenerationRequest, GenerationResponse

class BaseGenerator(ABC):
    """
    Abstract Base Class for all AI generators in the ggena framework.

    All specific generator implementations (e.g., ImageGenerator, AudioGenerator) 
    must inherit from this class and implement the `generate` method. 
    This ensures a consistent interface across different modalities.
    """

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
