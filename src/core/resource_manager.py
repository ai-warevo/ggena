import torch
import logging
import time
from typing import Dict, Set, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

@runtime_checkable
class ManagedResource(Protocol):
    """
    A protocol for objects that can be loaded and unloaded to manage VRAM.
    """
    async def load(self) -> None: ...
    async def unload(self) -> None: ...
    @property
    def name(self) -> str: ...

class ResourceManager:
    """
    Central manager to track VRAM usage and decide whether to keep 
    resources in memory or swap them.
    """
    def __init__(self, config):
        self._config = config
        self._resources: Dict[str, ManagedResource] = {}
        self._active_resources: Set[str] = set()
        self._last_access: Dict[str, float] = {}
        # Threshold for VRAM usage (in MB) before we consider unloading inactive resources.
        # Default to 4GB if not specified.
        self._vram_threshold_mb = self._config.get_int("VRAM_THRESHOLD_MB", 4000)

    def register(self, resource: ManagedResource):
        """Registers a managed resource."""
        self._resources[resource.name] = resource
        self._last_access[resource.name] = time.time()
        logger.info(f"--- [ResourceManager] Registered resource '{resource.name}' ---")

    async def acquire(self, name: str) -> ManagedResource:
        """Acquires a resource, loading it if necessary and managing VRAM."""
        if name not in self._resources:
            raise ValueError(f"Resource '{name}' is not registered.")

        resource = self._resources[name]

        if name in self._active_resources:
            self._last_access[name] = time.time()
            return resource

        # Check VRAM before loading
        try:
            free_bytes, total_bytes = torch.cuda.mem_get_info()
            usage_mb = (total_bytes - free_bytes) / (1024 * 1024)
        except Exception as e:
            logger.warning(f"Could not get VRAM info: {e}. Proceeding with caution.")
            usage_mb = 0

        logger.info(f"--- [ResourceManager] Current VRAM usage: {usage_mb:.2f} MB ---")

        if usage_mb > self._vram_threshold_mb:
            logger.info(f"--- [ResourceManager] VRAM threshold exceeded ({self._vram_threshold_mb} MB). Attempting eviction... ---")
            await self._evict_inactive()
            
            # Re-check usage after eviction
            try:
                free_bytes, total_bytes = torch.cuda.mem_get_info()
                usage_mb = (total_bytes - free_bytes) / (1024 * 1024)
            except Exception:
                pass

        logger.info(f"--- [ResourceManager] Loading resource '{name}' ---")
        try:
            await resource.load()
            self._active_resources.add(name)
            self._last_access[name] = time.time()
        except Exception as e:
            logger.error(f"Failed to load resource '{name}': {e}")
            raise

        return resource

    async def release(self, name: str):
        """Releases a resource (marks it as inactive). Note: doesn't necessarily unload immediately."""
        if name in self._active_resources:
            # We don't necessarily want to unload immediately on every release
            # because the next request might need it again.
            # But for this implementation, we'll just mark it as inactive.
            self._active_resources.remove(name)
            self._last_access[name] = time.time()
            logger.info(f"--- [ResourceManager] Resource '{name}' is now inactive ---")

    async def _evict_inactive(self):
        """Unloads inactive resources using LRU strategy until usage is below threshold."""
        # Get all inactive resources sorted by last access time (LRU)
        inactive_resources = []
        for name in self._resources:
            if name not in self._active_resources:
                inactive_resources.append(name)
        
        # Sort by timestamp ascending (oldest first)
        inactive_resources.sort(key=lambda n: self._last_access.get(n, 0))

        for name in inactive_resources:
            # Check if we still need to evict
            try:
                free_bytes, total_bytes = torch.cuda.mem_get_info()
                usage_mb = (total_bytes - free_bytes) / (1024 * 1024)
                if usage_mb <= self._vram_threshold_mb:
                    break
            except Exception:
                # If we can't check, just keep evicting one or stop? 
                # Let's try to evict at least one if we entered this method.
                pass

            logger.info(f"--- [ResourceManager] Evicting inactive resource '{name}' ---")
            try:
                await self._resources[name].unload()
            except Exception as e:
                logger.error(f"Failed to unload resource '{name}': {e}")
                # We continue to try and evict other resources even if one fails

    def get_active_resources(self) -> Set[str]:
        return self._active_resources
