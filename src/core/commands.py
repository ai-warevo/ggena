from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Generic, List, Optional, TypeVar
import threading

from src.core.types import GenerationRequest, GenerationResponse


T = TypeVar("T")


@dataclass(frozen=True)
class CommandResult(Generic[T]):
    """
    The result of a command execution.
    """

    success: bool
    result: Optional[T] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CommandContext:
    """
    Context containing dependencies required for command execution.
    """

    registry: Any
    config: Any
    shutdown_event: Optional[threading.Event] = None


class BaseCommand(ABC):
    """
    Abstract base class for all commands.
    """

    @abstractmethod
    async def execute(self, context: CommandContext) -> CommandResult:
        """
    Execute the command using the provided context.
    """

    pass


@dataclass(frozen=True)
class GenerationCommand(BaseCommand):
    """
    Encapsulates a generation request as a command.
    """

    module: str
    request: GenerationRequest

    async def execute(self, context: CommandContext) -> CommandResult[GenerationResponse]:
        try:
            # For CLI, we might want a fresh instance, but for simplicity in this refactor 
            # and to match server behavior, we use get_instance. 
            # In CLI, the registry is fresh anyway.
            generator = context.registry.get_instance(
                self.module, config=context.config
            )
            if not generator:
                return CommandResult(
                    success=False, error_message=f"Module '{self.module}' not found."
                )

            if context.shutdown_event and hasattr(generator, "set_shutdown_event"):
                generator.set_shutdown_event(context.shutdown_event)

            response = await generator.generate(self.request)
            if not response.success:
                return CommandResult(
                    success=False, error_message=response.error_message or "Generation failed."
                )

            return CommandResult(success=True, result=response)
        except Exception as e:
            return CommandResult(success=False, error_message=str(e))
