from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass(frozen=True)
class GenerationRequest:
    """
    Standardized request object for all AI generation tasks.
    """
    prompt: str
    positive_prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    num_outputs: int = 1
    # Additional modality-specific parameters (e.g., aspect_ratio, seed, etc.)
    parameters: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class GenerationResponse:
    """
    Standardized response object for all AI generation tasks.
    """
    success: bool
    output_files_bytes: List[bytes] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
