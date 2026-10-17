# Refactoring Report - Ggena Project

## 1. Executive Summary
The current codebase exhibits significant architectural debt characterized by "God functions" that violate the Single Responsibility Principle (SRP). Specifically, key orchestration points in the API server and the image generation pipeline are monolithic, making them difficult to test, maintain, and extend. High indentation levels and deeply nested error handling increase cognitive load and the risk of regression during future changes.

## 2. Refactoring Targets

### Target A: `src/app/server.py` -> `websocket_generate`
- **Description**: The WebSocket endpoint responsible for real-time generation updates.
- **Issues**: 
    - **Deep Nesting**: Multiple levels of `while True`, `try-except`, and `if-else`.
    - **Mixed Concerns**: Handles WebSocket protocol (receiving/sending JSON), parameter extraction, generation orchestration, and error reporting in a single block.
    - **Complexity**: Nested function definitions (`create_callback`, `create_image_callback`) inside the main loop make it hard to follow.

### Target B: `src/generators/image/image_generator.py` -> `generate`
- **Description**: The core method for triggering SDXL image generation.
- **Issues**: 
    - **God Function**: Spans ~180 lines and manages prompt expansion, LoRA loading, CLIP encoding, batching logic, inference execution, and post-processing.
    - **SRP Violation**: It is responsible for too many distinct stages of the pipeline.
    - **Error Handling**: Large `try-except` blocks that wrap almost the entire method, making it hard to pinpoint specific failure points.

### Target C: `src/generators/image/text_expander.py` -> `translate_user_intent_to_tags`
- **Description**: LLM-based prompt refinement logic.
- **Issues**: 
    - **Orchestration Bloat**: Manages a complex two-pass (expansion + refinement) process within one function.
    - **Fragile Parsing**: Contains inline regex and JSON recovery logic that should be encapsulated.

## 3. Detailed Refactoring Plans

### Plan A: Decomposing `websocket_generate`
1.  **Extract Message Handler**: Create a private method `_handle_ws_message(self, websocket, data)` to process incoming JSON.
2.  **Extract Generation Orchestrator**: Move the core generation logic (calling the generator and handling callbacks) into a dedicated service or method.
3.  **Flatten Control Flow**: Use guard clauses for early returns when `data.get("type") != "generate"` or when validation fails.
4.  **Decouple Callbacks**: Move callback creation to helper methods that return standard callable objects.

### Plan B: Decomposing `ImageGenerator.generate`
1.  **Stage-Based Decomposition**: Break the method into clearly defined private stages:
    - `_get_expanded_prompts(...)`: Handles text expansion and LoRA application.
    - `_prepare_embeddings(...)`: Handles CLIP encoding and device movement.
    - `_execute_inference_batches(...)`: Manages the loop over batches and calls the model.
2.  **Parameter Object**: Use the existing `ImageParameters` more strictly to avoid manual dictionary lookups.
3.  **Error Isolation**: Wrap each stage in its own specific error handling to provide better diagnostic information (e.g., distinguishing between a LoRA failure and an Inference failure).

### Plan C: Decomposing `translate_user_intent_to_tags`
1.  **Pass Separation**: Split into `_expand_initial_prompt(...)` and `_refine_prompt(...)`.
2.  **Robust Parsing Utility**: Extract the JSON/Regex recovery logic into a standalone utility function `extract_json_from_text(text: str) -> Dict[str, Any]`.

## 4. Code Snippets (Illustrative)

### Target B: Image Generator Refactoring

#### Before (Simplified)
```python
async def generate(self, request):
    # ... prompt expansion logic ...
    # ... lora loading logic ...
    # ... encoding logic ...
    for i in range(0, num_outputs, batch_size):
        # ... inference loop ...
        # ... image saving ...
    return response
```

#### After (Proposed)
```python
async def generate(self, request: GenerationRequest) -> GenerationResponse:
    try:
        params = self._validate_params(request.parameters)
        prompts = await self._prepare_prompts(request, params)
        embeddings = await self._encode_inputs(prompts)
        
        output_bytes = await self._run_inference_loop(
            embeddings, 
            params, 
            on_image_ready=params.on_image_ready
        )
        
        return self._build_success_response(output_bytes, prompts)
    except GgenaError as e:
        return self._build_error_response(e)
```

## 5. Recommended Verification Steps
1.  **Unit Testing**: Implement `pytest` suites for the new private methods (e.g., testing `_prepare_prompts` with various LoRA strings).
2.  **Integration Testing**: Run existing WebSocket client tests to ensure the API contract remains unchanged.
3.  **Regression Check**: Compare the pixel-level output (or at least the metadata/prompt consistency) of the new generator against the original implementation.
4.  **Performance Benchmarking**: Ensure that decomposing functions doesn't introduce significant overhead in the hot path (inference loop).
