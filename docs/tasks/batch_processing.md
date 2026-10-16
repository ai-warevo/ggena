# Task: Implement Batch Processing for Image Generation

## Context
Currently, when multiple images are requested (`num_outputs > 1`), they are generated one by one in a synchronous loop in `src/generators/image/image_generator.py`, which underutilizes the GPU.

## Objective
Refactor `src/generators/image/image_generator.py` to use batch inference for multiple outputs instead of a sequential loop.

## Relevant Files
- `src/generators/image/image_generator.py`
