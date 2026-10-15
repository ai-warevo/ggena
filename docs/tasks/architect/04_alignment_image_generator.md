# Task: Refactor Image Generator to use New Architecture

## Context
Now that the foundation (BaseGenerator, Types, Registry, Config) is in place, we need to align our existing implementations with this new architecture. The `image_generator.py` currently uses procedural functions and direct environment variable access.

## Reference
- Main Report: <docs/reports/architectural_report.md>
- Foundation Tasks: <docs/tasks/architect/01_foundation_base_generator.md>, <docs/tasks/architect/02_foundation_core_types.md>, <docs/tasks/architect/03_foundation_registry_and_config.md>

## Objective
Refactor the image generation module to inherit from `BaseGenerator` and use the new standardized types and configuration manager.

## Instructions
1. Update `src/generators/image/image_generator.py`:
    - Convert the `generate_image` function into a class `ImageGenerator` that inherits from `BaseGenerator`.
    - Implement the `generate(self, request: GenerationRequest) -> GenerationResponse` method.
    - Replace all `os.getenv` calls with the new `ConfigManager`.
    - Use the fields from `GenerationRequest` instead of individual arguments.
    - Return a `GenerationResponse` object containing the paths to generated images.
2. Update `src/generators/image/__init__.py` to facilitate the registration of this generator in the `GeneratorRegistry`.
3. Ensure that `text_expander.py` is still correctly utilized within the new class structure.

## Definition of Done
- [ ] `ImageGenerator` implements `BaseGenerator`.
- [ ] The module uses `GenerationRequest` and `GenerationResponse`.
- [ ] Configuration is handled via `ConfigManager`.
- [ ] The generator can be successfully instantiated via the `GeneratorRegistry`.
