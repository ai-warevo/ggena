import os
from typing import Any, Optional, TypeVar

T = TypeVar('T')

class ConfigManager:
    """
    Centralized configuration manager for the ggena framework.
    Loads settings from a .env file and provides typed access to them.
    Includes a fallback parser if python-dotenv is not available.
    """
    def __init__(self, env_path: Optional[str] = None):
        self._env_vars = {}
        self._load_env(env_path)

    def _load_env(self, env_path: Optional[str]):
        # Try using python-dotenv if available
        try:
            from dotenv import load_dotenv
            load_dotenv(dotenv_path=env_path)
            # After loading with dotenv, we can just use os.getenv
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
        except ValueError:
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Retrieves a boolean configuration value."""
        value = self._get_raw(key)
        if value is None:
            return default
        return value.lower() in ("true", "1", "yes", "on")

    def get_float(self, key: str, default: Optional[float] = None) -> Optional[float]:
        """Retrieves a float configuration value."""
        value = self._get_raw(key)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            return default

    def get_any(self, key: str, default: Any = None) -> Any:
        """Retrieves a configuration value as-is."""
        val = self._get_raw(key)
        return val if val is not None else default

# Global instance for easy access throughout the application
config = ConfigManager()
