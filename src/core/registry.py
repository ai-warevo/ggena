from typing import Dict, Type, Any, Optional
from src.generators.base import BaseGenerator
from src.core.exceptions import RegistryError

class GeneratorRegistry:
    """
    A central registry for all AI generators in the ggena framework.
    Supports dynamic discovery and self-registration of generator implementations.
    """
    _instance: Optional['GeneratorRegistry'] = None
    _registry: Dict[str, Type[BaseGenerator]] = {}
    _instances: Dict[str, BaseGenerator] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GeneratorRegistry, cls).__new__(cls)
        return cls._instance

    def register(self, name: str, generator_class: Type[BaseGenerator]) -> None:
        """
        Registers a new generator class under the given name.
        
        Args:
            name (str): The unique identifier for the generator (e.g., 'image', 'audio').
            generator_class (Type[BaseGenerator]): The class of the generator to register.
        """
        if not issubclass(generator_class, BaseGenerator):
            raise RegistryError(f"Class {generator_class.__name__} must inherit from BaseGenerator")
        
        self._registry[name] = generator_class

    def get(self, name: str) -> Optional[BaseGenerator]:
        """
        Retrieves a NEW instance of the registered generator.
        Useful for CLI/one-off executions.
        
        Args:
            name (str): The identifier of the generator to retrieve.
            
        Returns:
            Optional[BaseGenerator]: A new instance of the generator, or None if not found.
        """
        generator_class = self._registry.get(name)
        if generator_class:
            return generator_class()
        return None

    def get_instance(self, name: str) -> Optional[BaseGenerator]:
        """
        Retrieves a singleton instance of the registered generator.
        Useful for long-running servers to keep models in memory.
        
        Args:
            name (str): The identifier of the generator to retrieve.
            
        Returns:
            Optional[BaseGenerator]: The cached instance of the generator, or None if not found.
        """
        if name in self._instances:
            return self._instances[name]
        
        generator = self.get(name)
        if generator:
            self._instances[name] = generator
            return generator
        return None

    def list_available(self) -> list[str]:
        """Returns a list of all registered generator names."""
        return list(self._registry.keys())

# Global instance for easy access and self-registration
registry = GeneratorRegistry()
