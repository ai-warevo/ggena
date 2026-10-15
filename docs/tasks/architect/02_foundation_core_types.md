# Task: Define Core Types (DTOs)

## Context
To ensure type safety and a standardized communication protocol between the Orchestrator and the Generators, we need to move away from passing raw strings/integers and instead use structured Data Transfer Objects (DTOs).

## Reference
- Main Report: <docs/reports/architectural_report.md>
- Previous Task: <docs/tasks/architect/01_foundation_base_generator.md>

## Objective
Define standardized `GenerationRequest` and `GenerationResponse` dataclasses in `src/core/types.py`.

## Instructions
1. Create a new directory `src/core/`.
2. Create a new file `src/core/types.py`.
3. Implement the following using Python `dataclasses`:
    - `GenerationRequest`: Should contain fields like `prompt`, `negative_prompt`, `num_outputs`, and any modality-specific parameters (perhaps as a dictionary or additional optional fields).
    - `GenerationResponse`: Should contain fields like `success` (bool), `output_paths` (list of strings), `metadata` (dict), and `error_message` (optional string).
4. Ensure these classes are easily importable by both the Orchestrator and the Generators.

## Definition of Done
- [ ] `src/core/types.py` exists.
- [ ] `GenerationRequest` and `GenerationResponse` are implemented as dataclasses.
- [ ] The types are robust enough to handle different modalities.
