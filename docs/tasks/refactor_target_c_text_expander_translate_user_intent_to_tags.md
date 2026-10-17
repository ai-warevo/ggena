# Refactoring Task: Decomposing `translate_user_intent_to_tags` in `src/generators/image/text_expander.py`

You are a senior developer tasked with refactoring the LLM-based prompt refinement logic in `src/generators/image/text_expander.py`.

## Context
The method `translate_user_intent_to_tags` manages a complex two-pass (expansion + refinement) process within one function.

## Issues
- **Orchestration Bloat**: Manages a complex two-pass (expansion + refinement) process within one function.
- **Fragile Parsing**: Contains inline regex and JSON recovery logic that should be encapsulated.

## Refactoring Plan
1. **Pass Separation**: Split into `_expand_initial_prompt(...)` and `_refine_prompt(...)`.
2. **Robust Parsing Utility**: Extract the JSON/Regex recovery logic into a standalone utility function `extract_json_from_text(text: str) -> Dict[str, Any]`.

## Verification
- Implement unit tests for the new private methods and the parsing utility.
