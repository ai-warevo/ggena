from src.core.config import ConfigManager
from src.core.registry import GeneratorRegistry
from src.core.utils import discover_and_register_generators

def initialize_environment() -> tuple[ConfigManager, GeneratorRegistry]:
    """Initializes core components and discovers generators."""
    config = ConfigManager()
    registry = GeneratorRegistry()
    discover_and_register_generators("src.generators", registry)
    return config, registry
