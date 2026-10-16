import unittest
from unittest.mock import MagicMock, patch
from src.generators.image.image_generator import ImageGenerator
from src.core.config import ConfigManager
from src.core.registry import GeneratorRegistry

class TestDependencyInjection(unittest.TestCase):
    def test_image_generator_with_mocked_config(self):
        # 1. Create a mocked ConfigManager
        mock_config = MagicMock(spec=ConfigManager)
        mock_config.get_str.side_effect = lambda key, default=None: {
            "IMAGE_MODEL_ID": "mock-model-id",
            "HF_TOKEN": "mock-token"
        }.get(key, default)

        # 2. Create a mocked GeneratorRegistry (though not strictly needed for this test)
        mock_registry = MagicMock(spec=GeneratorRegistry)

        # 3. Instantiate ImageGenerator with the mocked config
        generator = ImageGenerator(config=mock_config, registry=mock_registry)

        # 4. Verify that the generator uses the mocked config
        self.assertEqual(generator._model_id, "mock-model-id")
        self.assertEqual(generator._config, mock_config)

    def test_image_generator_with_no_config_fallback(self):
        # This tests the backward compatibility part I added
        # We need to patch src.core.config.config
        with patch('src.core.config.config') as mock_global_config:
            mock_global_config.get_str.side_effect = lambda key, default=None: {
                "IMAGE_MODEL_ID": "fallback-model-id",
                "HF_TOKEN": "fallback-token"
            }.get(key, default)

            generator = ImageGenerator(config=None, registry=None)
            self.assertEqual(generator._model_id, "fallback-model-id")

if __name__ == "__main__":
    unittest.main()
