import sys
from unittest.mock import MagicMock

# Mock torch before importing src.core.resource_manager
mock_torch = MagicMock()
sys.modules["torch"] = mock_torch

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from src.core.resource_manager import ResourceManager

class MockResource:
    def __init__(self, name: str):
        self._name = name
        self.load_called = 0
        self.unload_called = 0
        self.is_loaded = False

    @property
    def name(self) -> str:
        return self._name

    async def load(self) -> None:
        self.load_called += 1
        self.is_loaded = True

    async def unload(self) -> None:
        self.unload_called += 1
        self.is_loaded = False

class MockConfig:
    def __init__(self, vram_threshold=4000):
        self.vram_threshold = vram_threshold

    def get_int(self, key, default):
        if key == "VRAM_THRESHOLD_MB":
            return self.vram_threshold
        return default

class TestResourceManager(unittest.IsolatedAsyncioTestCase):
    async def test_resource_manager_acquire_and_release(self):
        config = MockConfig()
        rm = ResourceManager(config)
        res = MockResource("res1")
        rm.register(res)

        mock_torch.cuda.mem_get_info.return_value = (1024*1024*1024, 1024*1024*1024) # 1GB free, 1GB total -> 0 usage
        
        acquired = await rm.acquire("res1")
        self.assertEqual(acquired, res)
        self.assertIn("res1", rm.get_active_resources())
        self.assertEqual(res.load_called, 1)
        self.assertTrue(res.is_loaded)

        await rm.release("res1")
        self.assertNotIn("res1", rm.get_active_resources())

    async def test_resource_manager_eviction_lru(self):
        # Set threshold low to trigger eviction
        config = MockConfig(vram_threshold=10) 
        rm = ResourceManager(config)
        
        res1 = MockResource("res1")
        res2 = MockResource("res2")
        res3 = MockResource("res3")
        rm.register(res1)
        rm.register(res2)
        rm.register(res3)

        # 1. Acquire all resources to make them active
        mock_torch.cuda.mem_get_info.return_value = (100 * 1024 * 1024, 100 * 1024 * 1024) # 0 usage
        await rm.acquire("res1")
        await asyncio.sleep(0.01)
        await rm.acquire("res2")
        await asyncio.sleep(0.01)
        await rm.acquire("res3")

        # 2. Release res1 and res3 (making them inactive). res2 remains active.
        await rm.release("res1")
        await asyncio.sleep(0.01)
        await rm.release("res3")

        # 3. Trigger eviction by acquiring a new resource or just checking usage
        mock_torch.cuda.mem_get_info.return_value = (5 * 1024 * 1024, 100 * 1024 * 1024) # Usage 95MB > 10MB

        res4 = MockResource("res4")
        rm.register(res4)
        await rm.acquire("res4")

        # res1 was released first, so it should be the first to be evicted (LRU).
        self.assertEqual(res1.unload_called, 1)
        # res3 was released second, so it should be next if we still need more space.
        self.assertEqual(res3.unload_called, 1)
        self.assertIn("res4", rm.get_active_resources())

    async def test_resource_manager_error_handling_load(self):
        config = MockConfig()
        rm = ResourceManager(config)
        res = MockResource("res_fail")
        # Use a real async function to ensure load_called is incremented if we wanted, 
        # but here we want it to fail.
        async def failing_load():
            raise Exception("Load failed")
        res.load = failing_load
        rm.register(res)

        mock_torch.cuda.mem_get_info.return_value = (1024**3, 1024**3)
        
        with self.assertRaisesRegex(Exception, "Load failed"):
            await rm.acquire("res_fail")
        
        self.assertNotIn("res_fail", rm.get_active_resources())

    async def test_resource_manager_error_handling_unload(self):
        config = MockConfig(vram_threshold=10)
        rm = ResourceManager(config)
        
        res1 = MockResource("res1")
        res2 = MockResource("res2")
        
        # Use a real async function to ensure unload_called is incremented before failing
        async def failing_unload():
            res1.unload_called += 1
            raise Exception("Unload failed")
        res1.unload = failing_unload
        
        rm.register(res1)
        rm.register(res2)

        # 1. Load res1 and release it (inactive)
        mock_torch.cuda.mem_get_info.return_value = (100 * 1024 * 1024, 100 * 1024 * 1024)
        await rm.acquire("res1")
        await rm.release("res1")

        # 2. Trigger eviction by acquiring res2 with high usage
        mock_torch.cuda.mem_get_info.return_value = (5 * 1024 * 1024, 100 * 1024 * 1024) # Usage 95MB > 10MB
        
        # This should attempt to unload res1, fail, and then continue.
        await rm.acquire("res2")
        self.assertEqual(res1.unload_called, 1)

if __name__ == "__main__":
    unittest.main()
