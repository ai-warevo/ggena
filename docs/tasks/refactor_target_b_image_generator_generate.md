# Refactoring Task: Decomposing `ImageGenerator.generate` in `src/generators/image/image_generator.py`

You are a senior developer tasked with refactoring the core `generate` method in `src/generators/image/image_generator.py`.

## Context
The core method for triggering SDXL image generation is a "God Function" that manages too many distinct stages of the pipeline.

## Issues
- **God Function**: Spans ~180 lines and manages prompt expansion, LoRA loading, CLIP encoding, batching logic, inference execution, and post-processing.
- **SRP Violation**: It is responsible for too many distinct stages of the pipeline.
- **Error Handling**: Large `try-except` blocks that wrap almost the entire method, making it hard to pinpoint specific failure points.

## Refactoring Plan
1. **Stage-Based Decomposition**: Break the method into clearly defined private stages:
    - `_get_expanded_prompts(...)`: Handles text expansion and LoRA application.
    - `_prepare_embeddings(...)`: Handles CLIP encoding and device movement.
    - `_execute_inference_batches(...)`: Manages the loop over batches and calls the model.
2. **Parameter Object**: Use the existing `ImageParameters` more strictly to avoid manual dictionary lookups.
3. **Error Isolation**: Wrap each stage in its own specific error handling to provide better diagnostic information (e.g., distinguishing between a LoRA failure and an Inference failure).

## Verification
- Implement `pytest` suites for the new private methods.
- Compare pixel-level output or metadata/prompt consistency against the original implementation.
- Ensure no significant overhead is introduced in the inference loop.
