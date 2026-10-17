import sys
import os
import unittest
from unittest.mock import MagicMock, AsyncMock, patch

# Add current directory to sys.path to allow importing src
sys.path.append(os.getcwd())

# Mock dependencies BEFORE any other imports that might use them
sys.modules["torch"] = MagicMock()
sys.modules["transformers"] = MagicMock()
sys.modules["dotenv"] = MagicMock()

from src.generators.image.text_expander import (
    extract_json_from_text, 
    _expand_initial_prompt, 
    _refine_prompt,
    translate_user_intent_to_tags
)

class TestTextExpanderUtils(unittest.TestCase):
    def test_extract_json_from_text_valid_json(self):
        text = 'Here is the result: {"positive": "tag1, tag2", "negative": "bad, ugly"}'
        expected = {"positive": "tag1, tag2", "negative": "bad, ugly"}
        self.assertEqual(extract_json_from_text(text), expected)

    def test_extract_json_from_text_markdown_wrapped(self):
        text = '```json\n{"positive": "tag1", "negative": "tag2"}\n```'
        expected = {"positive": "tag1", "negative": "tag2"}
        self.assertEqual(extract_json_from_text(text), expected)

    def test_extract_json_from_text_regex_fallback(self):
        text = '"positive": "tag1", "negative": "tag2"' 
        expected = {"positive": "tag1", "negative": "tag2"}
        self.assertEqual(extract_json_from_text(text), expected)

    def test_extract_json_from_text_no_match(self):
        text = "just some random text"
        with self.assertRaisesRegex(ValueError, "Could not extract JSON or relevant tags from text"):
            extract_json_from_text(text)

class TestTextExpanderMethods(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_model = MagicMock()
        self.mock_tokenizer = MagicMock()
        self.user_input = "a cute cat"
        self.refinement_guidelines = "rule 4 content"

    @patch("src.generators.image.text_expander.asyncio.to_thread")
    async def test_expand_initial_prompt_success(self, mock_to_thread):
        # 1. apply_chat_template
        # 2. tokenizer call
        # 3. _generate_in_stream (which is also a to_thread call)
        # 4. batch_decode
        
        mock_to_thread.side_effect = [
            "templated_text",
            {"input_ids": MagicMock(), "attention_mask": MagicMock()},
            MagicMock(), # generated_ids
            ["{\"positive\": \"cat\", \"negative\": \"dog\"}"] # batch_decode
        ]
        self.mock_tokenizer.apply_chat_template = MagicMock(return_value="templated_text")
        self.mock_tokenizer.return_value = {"input_ids": MagicMock(), "attention_mask": MagicMock()}
        self.mock_tokenizer.batch_decode = AsyncMock(return_value=["{\"positive\": \"cat\", \"negative\": \"dog\"}"])

        result = await _expand_initial_prompt(
            self.mock_model, self.mock_tokenizer, self.user_input, self.refinement_guidelines
        )
        
        self.assertEqual(result["positive"], "cat")
        self.assertEqual(result["negative"], "dog")

    @patch("src.generators.image.text_expander.asyncio.to_thread")
    async def test_refine_prompt_success(self, mock_to_thread):
        # 1. apply_chat_template
        # 2. tokenizer call
        # 3. _generate_in_stream
        # 4. batch_decode
        
        mock_to_thread.side_effect = [
            "refinement_templated_text",
            {"input_ids": MagicMock(), "attention_mask": MagicMock()},
            MagicMock(), # generated_ids
            ["refined cat"] # batch_decode
        ]
        self.mock_tokenizer.apply_chat_template = MagicMock(return_value="refinement_templated_text")
        self.mock_tokenizer.return_value = {"input_ids": MagicMock(), "attention_mask": MagicMock()}
        self.mock_tokenizer.batch_decode = AsyncMock(return_value=["refined cat"])

        result = await _refine_prompt(
            self.mock_model, self.mock_tokenizer, self.user_input, self.refinement_guidelines, "cat"
        )
        
        # Since 'score_9' is not in 'refined cat', it should prepend quality starters
        self.assertTrue(result.startswith("score_9, score_8_up, score_7_up,"))
        self.assertIn("refined cat", result)

    @patch("src.generators.image.text_expander.get_expander_model", new_callable=AsyncMock)
    @patch("src.generators.image.text_expander._expand_initial_prompt", new_callable=AsyncMock)
    @patch("src.generators.image.text_expander._refine_prompt", new_callable=AsyncMock)
    @patch("src.core.config.config.get_str")
    async def test_translate_user_intent_to_tags(self, mock_get_str, mock_refine, mock_expand, mock_get_model):
        # Setup
        mock_get_str.return_value = "guidelines"
        mock_expander = MagicMock()
        mock_expander._model = MagicMock()
        mock_expander.get_model.return_value = self.mock_model
        mock_expander.get_tokenizer.return_value = self.mock_tokenizer

        mock_expand.return_value = {"positive": "cat", "negative": "dog"}
        mock_refine.return_value = "refined cat"

        # Execute
        pos, neg = await translate_user_intent_to_tags("cat", "model_id")

        # Assert
        self.assertEqual(pos, "refined cat")
        self.assertEqual(neg, "dog")
        mock_expand.assert_called_once()
        mock_refine.assert_called_once()

if __name__ == "__main__":
    unittest.main()
