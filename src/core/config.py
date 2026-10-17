import os
from typing import Any, Optional, Type, TypeVar

try:
    from pydantic import BaseModel, ValidationError
except ImportError:
    BaseModel = None
    ValidationError = None

T = TypeVar('T')

class ConfigManager:
    """
    Centralized configuration manager for the ggena framework.
    Loads settings from a .env file and provides typed access to them.
    Includes a fallback parser if python-dotenv is not available.
    Supports Pydantic schema validation.
    """
    def __init__(self, env_path: Optional[str] = None, schema: Optional[Type[BaseModel]] = None):
        self._env_vars = {}
        self._schema: Any = None
        self._load_env(env_path)

        if schema is not None:
            if BaseModel is None:
                raise ImportError("Pydantic is required to use a configuration schema.")
            try:
                # We pass os.environ as kwargs. 
                # Note: Pydantic models expect keyword arguments.
                # Environment variables are usually uppercase, but Pydantic fields are often lowercase.
                # To support this, we'll try to match case-insensitively if needed, 
                # but for now, we pass os.environ directly and assume the schema handles it.
                self._schema = schema(**os.environ)
            except ValidationError as e:
                raise ValueError(f"Configuration validation failed: {e}")

    def _load_env(self, env_path: Optional[str]):
        # Try using python-dotenv if available
        try:
            from dotenv import load_dotenv
            load_dotenv(dotenv_path=env_path)
            return
        except ImportError:
            # Fallback to manual parsing
            path = env_path if env_path else ".env"
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        if '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            self._env_vars[key] = value
                            os.environ[key] = value

    def _get_raw(self, key: str) -> Optional[str]:
        # Check schema first if available (case-insensitive match for field names)
        if self._schema:
            # Try exact match first
            if hasattr(self._schema, key):
                val = getattr(self._schema, key)
                return str(val) if val is not None else None
            # Try lowercase match (common for Pydantic fields)
            low_key = key.lower()
            if hasattr(self._schema, low_key):
                val = getattr(self._schema, low_key)
                return str(val) if val is not None else None

        # Check manual vars first (if fallback was used), then os.getenv
        if self._env_vars and key in self._env_vars:
            return self._env_vars[key]
        return os.getenv(key)

    def get_str(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieves a string configuration value."""
        val = self._get_raw(key)
        return val if val is not None else default

    def get_int(self, key: str, default: Optional[int] = None) -> Optional[int]:
        """Retrieves an integer configuration value."""
        value = self._get_raw(key)
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Retrieves a boolean configuration value."""
        value = self._get_raw(key)
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "1", "yes", "on")

    def get_float(self, key: str, default: Optional[float] = None) -> Optional[float]:
        """Retrieves a float configuration value."""
        value = self._get_raw(key)
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def get_any(self, key: str, default: Any = None) -> Any:
        """Retrieves a configuration value as-is."""
        # If schema is present, try to return the actual typed value from the schema
        if self._schema:
            if hasattr(self._schema, key):
                return getattr(self._schema, key)
            low_key = key.lower()
            if hasattr(self._schema, low_key):
                return getattr(self._schema, low_key)

        val = self._get_raw(key)
        return val if val is not None else default

# For backward compatibility, we keep a global instance but it's no longer the only way.
config = ConfigManager()
