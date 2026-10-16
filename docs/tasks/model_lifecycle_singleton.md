# Task: Implement Singleton Model Pattern for Text Expander

## Context
The current implementation of `src/generators/image/text_expander.py` loads the LLM from disk and moves it to VRAM on every single request, then deletes it. This causes massive latency.

## Objective
Refactor `src/generators/image/text_expander.py` to use a Singleton pattern so that the model is loaded once and reused across multiple requests.

## Relevant Files
- `src/generators/image/text_expander.py`

## Instructions
1. Analyze `src/generators/image/text_expander.py`.
2. Implement a mechanism (e.g., a class variable or a module-level cache) to keep the model in memory.
3. Ensure that subsequent requests reuse the existing model instance.
4. Verify that VRAM is not being unnecessarily cleared between requests unless explicitly required.
