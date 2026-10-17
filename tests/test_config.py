import unittest
import os
import shutil
from typing import Optional
from pydantic import BaseModel, Field
from src.core.config import ConfigManager

class TestConfigSchema(BaseModel):
    api_key: str
    timeout: int = 30
    debug: bool = False

class TestConfigManager(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = os.path.join(os.getcwd(), "tests", "tmp_test_config")
        if not os.path.exists(cls.test_dir):
            os.makedirs(cls.test_dir)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)

    def setUp(self):
        pass

    def test_manual_parsing(self):
        env_content = """
        # This is a comment
        KEY1=value1
        KEY2="value2"
        KEY3='value3'
        KEY4=123
        KEY5=True
        """
        env_file = os.path.join(self.test_dir, ".env")
        with open(env_file, "w", encoding="utf-8") as f:
            f.write(env_content)

        config = ConfigManager(env_path=env_file)

        self.assertEqual(config.get_str("KEY1"), "value1")
        self.assertEqual(config.get_str("KEY2"), "value2")
        self.assertEqual(config.get_str("KEY3"), "value3")
        self.assertEqual(config.get_int("KEY4"), 123)
        self.assertTrue(config.get_bool("KEY5"))

    def test_default_values(self):
        env_file = os.path.join(self.test_dir, "nonexistent")
        config = ConfigManager(env_path=env_file)
        self.assertEqual(config.get_str("NONEXISTENT", "default"), "default")
        self.assertEqual(config.get_int("NONEXISTENT", 42), 42)
        self.assertEqual(config.get_bool("NONEXISTENT", True), True)
        self.assertEqual(config.get_float("NONEXISTENT", 3.14), 3.14)

    def test_invalid_types(self):
        env_content = """
        NOT_INT=abc
        NOT_BOOL=maybe
        """
        env_file = os.path.join(self.test_dir, ".env_invalid")
        with open(env_file, "w", encoding="utf-8") as f:
            f.write(env_content)

        config = ConfigManager(env_path=env_file)
        self.assertEqual(config.get_int("NOT_INT", 10), 10)
        self.assertFalse(config.get_bool("NOT_BOOL", False))

    def test_pydantic_validation(self):
        # Set environment variables for the schema
        os.environ["API_KEY"] = "secret-key"
        os.environ["TIMEOUT"] = "60"
        os.environ["DEBUG"] = "true"

        try:
            config = ConfigManager(schema=TestConfigSchema)
            
            # Test getting from schema via get_* methods (case-insensitive)
            self.assertEqual(config.get_str("api_key"), "secret-key")
            self.assertEqual(config.get_int("timeout"), 60)
            self.assertTrue(config.get_bool("debug"))
            
            # Test getting from schema via get_any
            self.assertEqual(config.get_any("api_key"), "secret-key")
            self.assertEqual(config.get_any("timeout"), 60)

            # Test validation failure
            os.environ["API_KEY"] = "" # Assuming API_KEY is required and non-empty if we used Field(min_length=1)
            # But our schema doesn't have min_length, so let's use a type mismatch
            os.environ["TIMEOUT"] = "not-an-int"
            with self.assertRaises(ValueError):
                ConfigManager(schema=TestConfigSchema)

        finally:
            # Clean up env vars to avoid affecting other tests
            if "API_KEY" in os.environ: del os.environ["API_KEY"]
            if "TIMEOUT" in os.environ: del os.environ["TIMEOUT"]
            if "DEBUG" in os.environ: del os.environ["DEBUG"]

if __name__ == "__main__":
    unittest.main()
