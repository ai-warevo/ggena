# Task: Advanced Memory Management (Offloading & Resource Manager)

## Context
The current "pre-load all models" strategy risks OOM errors. We need more intelligent VRAM management.

## Objective
1. **Model Offloading**: Use `accelerate`'s `enable_model_cpu_offload()` or `enable_sequential_cpu_offload()` for the SDXL pipeline in `src/generators/image/image_generator.py`.
2. **Unified Resource Manager**: Implement a central manager to track VRAM usage and decide whether to keep both LLM and SDXL in memory or swap them.

## Relevant Files
- `src/generators/image/image_generator.py`
- `src/generators/image/text_expander.py`
- `src/app/server.py` (for integration)
