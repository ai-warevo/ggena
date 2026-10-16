# Task: Inference Optimization (torch.compile, Quantization, Flash Attention)

## Context
The current inference execution in Ggena can be improved by leveraging modern PyTorch and hardware optimizations.

## Objective
Implement the following optimizations:
1. **`torch.compile`**: Wrap the UNet and VAE components of the SDXL pipeline in `src/generators/image/image_generator.py` with `torch.compile(model, mode="reduce-overhead")`.
2. **Quantization**: Apply 4-bit or 8-bit quantization to the LLM in `src/generators/image/text_expander.py` using `BitsAndBytesConfig`.
3. **Flash Attention**: Ensure that `diffusers` is configured to use Flash Attention 2 where supported.

## Relevant Files
- `src/generators/image/image_generator.py`
- `src/generators/image/text_expander.py`
