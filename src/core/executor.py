import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.commands import BaseCommand, CommandContext, CommandResult


logger = logging.getLogger(__name__)


@dataclass
class AuditEntry:
    """
    An entry in the command audit log.
    """

    timestamp: datetime
    command_type: str
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class CommandExecutor:
    """
    Executes commands and maintains an audit log of executed commands.
    """

    def __init__(self, context: CommandContext):
        self._context = context
        self._audit_log: List[Dict[str, Any]] = []

    async def execute(self, command: BaseCommand) -> CommandResult:
        """
        Executes a command and records the result in the audit log.
        """
        command_name = command.__class__.__name__
        logger.info(f"Executing command: {command_name}")

        try:
            result = await command.execute(self._context)
        except Exception as e:
            logger.exception(f"Unexpected error executing command {command_name}: {e}")
            result = CommandResult(success=False, error_message=str(e))

        # Audit logging
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "command": command_name,
            "success": result.success,
            "error_message": result.error_message,
            "metadata": result.metadata,
        }
        self._audit_log.append(audit_entry)

        return result

    def get_audit_log(self) -> List[Dict[str, Any]]:
        """
        Returns the history of executed commands.
        """
        return self._audit_log
