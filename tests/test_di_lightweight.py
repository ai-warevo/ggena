import unittest
from unittest.mock import MagicMock
from src.generators.base import BaseGenerator
from src.core.config import ConfigManager
from src.core.registry import GeneratorRegistry
from pydantic import BaseModel

class DummyParameters(BaseModel):
    foo: str = "bar"

class DummyGenerator(BaseGenerator):
    @property
    def parameter_schema(self) -> type[BaseModel]:
        return DummyParameters

    async def generate(self, request):
        return MagicMock()

class TestLightweightDI(unittest.TestCase):
    def test_registry_injection(self):
        # 1. Setup dependencies
        mock_config = MagicMock(spec=ConfigManager)
        mock_config.get_str.return_value = "test-val"
        
        registry = GeneratorRegistry()
        registry.register("dummy", DummyGenerator)

        # 2. Get instance with injected config
        generator = registry.get("dummy", config=mock_config)
        
        self.assertIsNotNone(generator)
        self.assertEqual(generator._config, mock_config)

    def test_singleton_injection(self):
        mock_config = MagicMock(spec=ConfigManager)
        registry = GeneratorRegistry()
        registry.register("dummy", DummyGenerator)

        # Get first instance (singleton)
        gen1 = registry.get_instance("dummy", config=mock_config)
        # Get second instance (should be same singleton)
        gen2 = registry.get_instance("dummy", config=mock_config)

        self.assertIs(gen1, gen2)
        self.assertEqual(gen1._config, mock_config)

if __name__ == "__main__":
    unittest.main()
