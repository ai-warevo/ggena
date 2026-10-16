# Task: Implement Batch Processing for Image Generation

## Context
Currently, when multiple images are requested (`num_outputs > 1`), they are generated one by one in a synchronous loop in `src/generators/image/image_generator.py`, which underutilizes the GPU.

## Objective
Refactor `src/generators/image/image_generator.py` to use batch inference for multiple outputs instead of a sequential loop.

## Implementation Details
To prevent Out-Of-Memory (OOM) errors, especially when generating high-resolution images or using heavy models, the implementation will use **chunked batching**. 

Instead of processing all requested images in a single massive batch, they will be split into smaller groups (chunks). The size of these chunks is controlled by a new configuration parameter:
- `IMAGE_MAX_BATCH_SIZE`: Defines the maximum number of images to process in a single GPU inference pass. Defaults to `1` for maximum compatibility and safety.

## Relevant Files
- `src/generators/image/image_generator.py`: Implementation of batching logic and chunked loop.
- `src/core/config.py`: Used to retrieve the `IMAGE_MAX_BATCH_SIZE` setting.
- `docs/tasks/batch_processing.md`: This task document.

