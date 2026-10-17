# Refactoring Task: Improving `ResourceManager` in `src/core/resource_manager.py`

You are a senior developer tasked with refactoring the `ResourceManager` to improve its robustness and predictability.

## Context
The `ResourceManager` is responsible for managing VRAM usage by loading and unloading `ManagedResource` objects.

## Issues
- **Simplistic Eviction Policy**: The current eviction policy (`_evict_inactive`) only evicts one resource at a time and doesn't consider the importance or frequency of use (LRU/LFU).
- **VRAM Monitoring Accuracy**: It relies on `torch.cuda.memory_allocated()`, which might not reflect the true system VRAM state or include overhead from other processes.
- **Error Handling in Resource Lifecycle**: If a resource's `load()` or `unload()` fails, the manager might end up in an inconsistent state (e.g., marking a failed load as active).

## Refactoring Plan
1. **Implement Better Eviction Strategy**: Replace the simple "evict one" logic with a more robust strategy like Least Recently Used (LRU) based on resource access timestamps.
2. **Enhance VRAM Monitoring**: Add support for monitoring total available VRAM and potentially use more reliable methods to check memory pressure.
3. **Robust Lifecycle Management**: Ensure that `_active_resources` is only updated if `load()` or `unload()` succeeds, and implement proper error handling/cleanup during failures.

## Verification
- Implement unit tests for the new eviction strategy using mock resources.
- Verify that resource state remains consistent even when `load()` or `unload()` raises exceptions.
