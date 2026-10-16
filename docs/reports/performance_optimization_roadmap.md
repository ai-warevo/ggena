# Performance Optimization Roadmap for Ggena

## Executive Summary
This report analyzes the current execution pipeline of the Ggena project, focusing on maximizing hardware utilization (GPU/CPU), minimizing latency, and optimizing memory management for large-scale AI model inference. The primary bottlenecks identified are inefficient model lifecycle management in the text expansion phase and missed opportunities for advanced inference optimizations like compilation and quantization.

---

## 1. Current Bottleneck Analysis (Theoretical)

### 1.1 Critical: Model Lifecycle Overhead (Latency)
* **Location**: `src/generators/image/text_expander.py`
* **Issue**: The LLM used for text expansion is loaded from disk and moved to VRAM on *every single request*, and then explicitly deleted and cleared from cache (`torch.cuda.empty_cache()`) at the end of the function.
* **Impact**: Massive latency penalty (seconds per request) due to I/O and GPU memory allocation overhead. This prevents the system from ever reaching high throughput.

### 1.2 Sub-optimal Inference Execution (Latency & Throughput)
* **Location**: `src/generators/image/image_generator.py`
* **Issue**: The Stable Diffusion XL (SDXL) pipeline is executed using standard PyTorch calls without leveraging modern optimizations like `torch.compile`.
* **Impact**: Slower inference steps compared to compiled kernels.

### 1.3 Sequential Image Generation (Throughput)
* **Location**: `src/generators/image/image_generator.py`
* **Issue**: When multiple images are requested (`num_outputs > 1`), they are generated one by one in a synchronous loop.
* **Impact**: Underutilization of GPU compute power, especially for smaller batch sizes where the GPU could handle multiple images in parallel.

### 1.4 VRAM Pressure & Management (Memory)
* **Issue**: The current strategy is "pre-load all models on startup" (`src/app/server.py`). While this minimizes latency, it risks `OutOfMemory` (OOM) errors if the combined VRAM requirements of the LLM and SDXL exceed available capacity. There is no intelligent offloading or swapping mechanism.

---

## 2. Specific Code-Level Optimizations

### 2.1 Inference Optimization (`torch` & `diffusers`)
* **Implement `torch.compile`**: Wrap the UNet and VAE components of the SDXL pipeline with `torch.compile(model, mode="reduce-overhead")`. This can provide a significant speedup on modern NVIDIA GPUs (Ampere and newer).
* **Quantization (bitsandbytes)**: 
    * Apply 4-bit or 8-bit quantization to the LLM in `text_expander.py` using `BitsAndBytesConfig`.
    * Consider quantizing the SDXL weights if VRAM becomes a bottleneck, although this may impact image quality.
* **Flash Attention**: Ensure that `diffusers` is configured to use Flash Attention 2 (if supported by the hardware) to speed up the attention mechanisms in both LLM and SDXL.

### 2.2 Memory Management (VRAM/RAM)
* **Singleton Model Pattern**: Refactor `text_expander.py` to load the model once and reuse it across requests. This is the highest priority fix.
* **Model Offloading**: Use `accelerate`'s `enable_model_cpu_offload()` or `enable_sequential_cpu_offload()` for the SDXL pipeline to allow running larger models on limited VRAM by moving parts of the model to RAM when not in use.
* **Unified Resource Manager**: Implement a central manager that tracks VRAM usage and decides whether to keep both the LLM and SDXL in memory or swap them based on recent usage patterns.

### 2.3 Concurrency & Throughput
* **Batch Processing**: Refactor `image_generator.py` to use batch inference for `num_outputs > 1`. Instead of a loop, pass a batch of prompts/embeddings to the pipeline.
* **Async I/O Optimization**: Ensure all file saving and network-bound tasks (like downloading weights) are fully asynchronous to prevent blocking the main execution thread.

---

## 3. Hardware-Specific Tuning (NVIDIA/CUDA)

* **TF32 Enablement**: The server already enables `torch.backends.cuda.matmul.allow_tf32 = True`. This should be maintained for Ampere+ GPUs.
* **CUDA Streams**: For advanced implementations, use separate CUDA streams for the text expansion and image generation phases to allow overlapping of CPU-bound preprocessing and GPU-bound inference.
* **TensorRT Integration**: For production environments with fixed model architectures, consider exporting the SDXL UNet to a TensorRT engine for maximum possible throughput on NVIDIA hardware.

---

## 4. Scaling Strategies

| Strategy | Description | Benefit |
| :--- | :--- | :--- |
| **Worker Queues** | Use a task queue (e.g., Redis/Celery) to decouple API requests from GPU execution. | Prevents API timeouts and allows for controlled load. |
| **Dynamic Batching** | Implement a middleware that collects incoming requests over a short window (e.g., 50ms) and batches them together. | Maximizes GPU utilization by increasing batch sizes dynamically. |
| **Multi-GPU Orchestration** | Distribute different models or different requests across multiple GPUs using a load balancer. | Linear scaling of throughput with hardware investment. |

---
*Report generated by ML Performance & Systems Optimization Expert Agent.*
