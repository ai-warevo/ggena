import sys
import os
from unittest.mock import MagicMock

# Add current directory to sys.path to allow importing src
sys.path.append(os.getcwd())

# Mock dependencies BEFORE any other imports that might use them
class MockException(Exception):
    pass

class MockBaseModel:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
    @classmethod
    def validate(cls, data):
        return cls(**data)

class MockField:
    def __init__(self, default=None, ge=None, le=None):
        self.default = default
        self.ge = ge
        self.le = le

class MockPydantic:
    BaseModel = MockBaseModel
    Field = MockField
    ValidationError = MockException

sys.modules["torch"] = MagicMock()
sys.modules["diffusers"] = MagicMock()
sys.modules["pydantic"] = MockPydantic
sys.modules["dotenv"] = MagicMock()
sys.modules["transformers"] = MagicMock()
sys.modules["bitsandbytes"] = MagicMock()

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

# Now import the generator
from src.generators.image.image_generator import ImageGenerator, ImageParameters
from src.core.types import GenerationRequest
from src.core.exceptions import GeneratorError, ValidationError, GenerationCancelledError

class TestImageGenerator(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_config = MagicMock()
        # Default config values
        self.mock_config.get_str.side_effect = lambda key, default=None: {
            "IMAGE_MODEL_ID": "test-model",
            "HF_TOKEN": "test-token",
            "TEXT_MODEL_ID": "test-text-model",
            "TENSORRT_UNET_PATH": None,
        }.get(key, default)
        self.mock_config.get_int.side_effect = lambda key, default: {
            "IMAGE_MAX_BATCH_SIZE": 1
        }.get(key, default)

        self.generator = ImageGenerator(config=self.mock_config)
        # Mock the pipeline
        self.mock_pipe = MagicMock()
        self.mock_pipe.device = "cpu"
        self.mock_pipe.load_lora_weights = MagicMock()
        self.mock_pipe.set_adapters = MagicMock()
        self.mock_pipe.unload_lora_weights = MagicMock()
        self.mock_pipe.enable_model_cpu_offload = MagicMock()
        self.mock_pipe.disable_model_cpu_offload = MagicMock()
        self.generator._pipe = self.mock_pipe

    @patch("src.generators.image.image_generator.translate_user_intent_to_tags", new_callable=AsyncMock)
    async def test_get_expanded_prompts_with_request(self, mock_translate):
        # Setup
        request = MagicMock(spec=GenerationRequest)
        request.positive_prompt = "a cute cat"
        request.negative_prompt = "ugly"
        request.prompt = ""

        # Execute
        expanded_pos, expanded_neg, req_pos = await self.generator._get_expanded_prompts(request, None)

        # Assert
        self.assertEqual(expanded_pos, "a cute cat")
        self.assertEqual(expanded_neg, "ugly")
        self.assertEqual(req_pos, "a cute cat")
        mock_translate.assert_not_called()

    @patch("src.generators.image.image_generator.translate_user_intent_to_tags", new_callable=AsyncMock)
    async def test_get_expanded_prompts_with_expansion(self, mock_translate):
        # Setup
        request = MagicMock(spec=GenerationRequest)
        request.positive_prompt = ""
        request.negative_prompt = ""
        request.prompt = "a cute cat"

        mock_translate.return_value = ("expanded pos", "expanded neg")

        # Execute
        expanded_pos, expanded_neg, req_pos = await self.generator._get_expanded_prompts(request, None)

        # Assert
        self.assertEqual(expanded_pos, "expanded pos")
        self.assertEqual(expanded_neg, "expanded neg")
        self.assertEqual(req_pos, "expanded pos")
        mock_translate.assert_called_once()

    async def test_get_expanded_prompts_with_lora(self):
        # Setup
        request = MagicMock(spec=GenerationRequest)
        request.positive_prompt = "a cat <lora:test_lora:0.5>"
        request.negative_prompt = ""
        request.prompt = ""

        with patch("os.path.exists", return_value=True):
            # Execute
            expanded_pos, expanded_neg, req_pos = await self.generator._get_expanded_prompts(request, None)

            # Assert
            self.assertEqual(expanded_pos, "a cat") 
            self.mock_pipe.load_lora_weights.assert_called_once()
            self.mock_pipe.set_adapters.assert_called_once()

    @patch("src.generators.image.image_generator.encode_infinite_prompt", new_callable=MagicMock)
    async def test_prepare_embeddings(self, mock_encode):
        # Setup
        import torch
        mock_encode.return_value = (
            torch.randn(1, 77, 768),
            torch.randn(1, 77, 768),
            torch.randn(1, 768),
            torch.randn(1, 768)
        )

        # Execute
        embeddings = await self.generator._prepare_embeddings("pos", "neg")

        # Assert
        self.assertEqual(len(embeddings), 4)
        mock_encode.assert_called_once()

    async def test_execute_inference_batches(self):
        # Setup
        import torch
        request = MagicMock(spec=GenerationRequest)
        request.num_outputs = 2
        params = ImageParameters(width=1024, height=768, guidance_scale=7.0, num_inference_steps=30)
        
        embeddings = (
            torch.randn(1, 77, 768),
            torch.randn(1, 77, 768),
            torch.randn(1, 768),
            torch.randn(1, 768)
        )

        mock_image = MagicMock()
        mock_result = MagicMock()
        mock_result.images = [mock_image, mock_image]
        self.mock_pipe.return_value = mock_result

        with patch("io.BytesIO") as mock_bytes_io:
            mock_buffer = MagicMock()
            mock_buffer.getvalue.return_value = b"fake_image_bytes"
            mock_bytes_io.return_value = mock_buffer

            # Execute
            output = await self.generator._execute_inference_batches(request, params, embeddings, "pos", "neg")

            # Assert
            self.assertEqual(len(output), 2)
            self.assertEqual(output[0], b"fake_image_bytes")

    async def test_generate_validation_error(self):
        # Setup
        request = MagicMock(spec=GenerationRequest)
        request.parameters = {"width": 10} # Invalid width (min 256)
        request.positive_prompt = ""
        request.negative_prompt = ""
        request.prompt = ""
        request.num_outputs = 1

        # We need to make sure ImageParameters raises the error when instantiated with invalid data
        with patch("src.generators.image.image_generator.ImageParameters", side_effect=ValidationError("Invalid image parameters: some error")):
            # Execute
            response = await self.generator.generate(request)

            # Assert
            self.assertFalse(response.success)
            self.assertIn("Invalid image parameters", response.error_message)

if __name__ == "__main__":
    unittest.main()
