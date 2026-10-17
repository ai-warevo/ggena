from pydantic import BaseModel
from typing import Dict, Any, Optional, List

class RequestModel(BaseModel):
    prompt: str
    positive_prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    num_outputs: Optional[int] = 1
    parameters: Optional[Dict[str, Any]] = {}

class ResponseModel(BaseModel):
    success: bool
    output_paths: List[str] = []
    metadata: Dict[str, Any] = {}
    error_message: Optional[str] = None
