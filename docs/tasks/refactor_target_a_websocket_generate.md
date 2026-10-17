# Refactoring Task: Decomposing `websocket_generate` in `src/app/server.py`

You are a senior developer tasked with refactoring the `websocket_generate` method in `src/app/server.py`.

## Context
The WebSocket endpoint responsible for real-time generation updates is currently monolithic and difficult to maintain.

## Issues
- **Deep Nesting**: Multiple levels of `while True`, `try-except`, and `if-else`.
- **Mixed Concerns**: Handles WebSocket protocol (receiving/sending JSON), parameter extraction, generation orchestration, and error reporting in a single block.
- **Complexity**: Nested function definitions (`create_callback`, `create_image_callback`) inside the main loop make it hard to follow.

## Refactoring Plan
1. **Extract Message Handler**: Create a private method `_handle_ws_message(self, websocket, data)` to process incoming JSON.
2. **Extract Generation Orchestrator**: Move the core generation logic (calling the generator and handling callbacks) into a dedicated service or method.
3. **Flatten Control Flow**: Use guard clauses for early returns when `data.get("type") != "generate"` or when validation fails.
4. **Decouple Callbacks**: Move callback creation to helper methods that return standard callable objects.

## Verification
- Ensure the WebSocket API contract remains unchanged.
- Run existing WebSocket client tests.
