# Task: Hardware-Specific Tuning (CUDA Streams & TensorRT)

## Context
Advanced optimizations for NVIDIA hardware can further increase performance.

## Objective
1. **CUDA Streams**: Use separate CUDA streams for text expansion and image generation phases to allow overlapping of CPU-bound preprocessing and GPU-bound inference.
2. **TensorRT Integration**: Consider exporting the SDXL UNet to a TensorRT engine.
