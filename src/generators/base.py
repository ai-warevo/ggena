from abc import ABC, abstractmethod
from typing import Any

# Placeholder types to be replaced by actual dataclasses in future tasks
GenerationRequest = Any
GenerationResponse = Any

class BaseGenerator(ABC):
    """
    Abstract Base Class for all AI generators in the ggena framework.

    All specific generator implementations (e.g., ImageGenerator, AudioGenerator) 
    must inherit from this class and implement the `generate` method. 
    This ensures a consistent interface across different modalities.
    """

    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResponse:
        """
        Generates content based on the provided request.

        Args:
            request (GenerationRequest): The generation request object.

        Returns:
            GenerationResponse: The generation response object.
        """
        pass
