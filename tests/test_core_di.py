import unittest
from unittest.mock import MagicMock
from src.core.config import ConfigManager
from src.core.registry import GeneratorRegistry
from src.generators.base import BaseGenerator

class MockGenerator(BaseGenerator):
    @property
    def parameter_schema(self):
        return None
    async def generate(self, request):
        return None

class TestCoreDI(unittest.TestCase):
    def test_config_manager(self):
        # Create a config manager with some dummy env vars (simulated via _env_vars)
        config = ConfigManager()
        config._env_vars = {"TEST_KEY": "test_value", "TEST_INT": "123"}
        
        self.assertEqual(config.get_str("TEST_KEY"), "test_value")
        self.assertEqual(config.get_int("TEST_INT"), 123)

    def test_registry_di(self):
        # Create a registry instance
        registry = GeneratorRegistry()
        
        # Create a mock generator class
        class MyGenerator(MockGenerator):
            pass
            
        # Register it
        registry.register("my_mod", MyGenerator)
        
        # Retrieve it
        instance = registry.get("my_mod")
        self.assertIsInstance(instance, MyGenerator)
        
        # Check availability
        self.assertIn("my_mod", registry.list_available())

if __name__ == "__main__":
    unittest.main()
