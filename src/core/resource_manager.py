import torch
import logging
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
        # Threshold for VRAM usage (in MB) before we consider unloading inactive resources.
        # Default to 4GB if not specified.
        self._vram_threshold_mb = self._config.get_int("VRAM_THRESHOLD_MB", 4000)

    def register(self, resource: ManagedResource):
        """Registers a managed resource."""
        self._resources[resource.name] = resource
        logger.info(f"--- [ResourceManager] Registered resource '{resource.name}' ---")

    async def acquire(self, name: str) -> ManagedResource:
        """Acquires a resource, loading it if necessary and managing VRAM."""
        if name not in self._resources:
            raise ValueError(f"Resource '{name}' is not registered.")

        resource = self._resources[name]

        if name in self._active_resources:
            return resource

        # Check VRAM before loading
        current_vram_mb = torch.cuda.memory_allocated() / (1024 * 1024)
        logger.info(f"--- [ResourceManager] Current VRAM usage: {current_vram_mb:.2f} MB ---")

        if current_vram_mb > self._vram_threshold_mb:
            logger.info(f"--- [ResourceManager] VRAM threshold exceeded ({self._vram_threshold_mb} MB). Attempting eviction... ---")
            await self._evict_inactive()

        logger.info(f"--- [ResourceManager] Loading resource '{name}' ---")
        await resource.load()
        self._active_resources.add(name)
        return resource

    async def release(self, name: str):
        """Releases a resource (marks it as inactive). Note: doesn't necessarily unload immediately."""
        if name in self._active_resources:
            # We don't necessarily want to unload immediately on every release 
            # because the next request might need it again.
            # But for this implementation, we'll just mark it as inactive.
            self._active_resources.remove(name)
            logger.info(f"--- [ResourceManager] Resource '{name}' is now inactive ---")

    async def _evict_inactive(self):
        """Unloads an inactive resource to free up VRAM."""
        for name in list(self._resources.keys()):
            if name not in self._active_resources:
                logger.info(f"--- [ResourceManager] Evicting inactive resource '{name}' ---")
                await self._resources[name].unload()
                # We don't remove from _resources, just unload it.
                return # Evict one at a time to be safe

    def get_active_resources(self) -> Set[str]:
        return self._active_resources
