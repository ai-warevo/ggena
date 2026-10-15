# Task: Create BaseGenerator ABC

## Context
The current project uses procedural functions for generation, which lacks a formal contract. To implement the Strategy pattern and allow for dynamic discovery, we need a common interface that all generators must follow.

## Reference
- Main Report: <docs/reports/architectural_report.md>

## Objective
Create an Abstract Base Class (ABC) in `src/generators/base.py` that defines the required interface for any AI generator in the framework.

## Instructions
1. Create a new file `src/generators/base.py`.
2. Define an abstract class `BaseGenerator` using Python's `abc` module.
3. The class should include:
    - An abstract method `generate(self, request: GenerationRequest) -> GenerationResponse`.
    - (Note: `GenerationRequest` and `GenerationResponse` will be defined in the next task, so for now, use type hints that can be updated or use `Any`).
4. Ensure the class is well-documented with docstrings explaining its purpose.

## Definition of Done
- [ ] `src/generators/base.py` exists.
- [ ] `BaseGenerator` is an ABC.
- [ ] The interface is designed to be extensible for different modalities (image, audio, etc.).
