# Task: Implement Generator Registry & Config Manager

## Context
The Orchestrator currently has hardcoded imports for generators, which violates the Open/Closed Principle. We need a way to dynamically discover available generators and a centralized way to manage configuration (replacing direct `os.getenv` calls).

## Reference
- Main Report: <docs/reports/architectural_report.md>
- Previous Tasks: <docs/tasks/architect/01_foundation_base_generator.md>, <docs/tasks/architect/02_foundation_core_types.md>

## Objective
Implement a `GeneratorRegistry` for dynamic discovery and a `ConfigManager` for centralized configuration management.

## Instructions
### Part A: Generator Registry
1. Create `src/core/registry.py`.
2. Implement a `GeneratorRegistry` class that allows:
    - `register(name, generator_class)`: To add a new generator to the registry.
    - `get(name)`: To retrieve a generator instance by its name.
3. The registry should facilitate "self-registration" (e.g., when a module is imported, it registers itself).

### Part B: Config Manager
1. Create `src/core/config.py`.
2. Implement a `ConfigManager` class that:
    - Loads configuration from `.env` using `python-dotenv`.
    - Provides typed access to settings (e.g., `config.get_int("IMAGE_GEN_COUNT")`).
    - Provides default values if keys are missing.

## Definition of Done
- [ ] `src/core/registry.py` and `src/core/config.py` exist.
- [ ] The Registry can successfully store and retrieve generator classes.
- [ ] The ConfigManager provides a clean, centralized interface for all settings.
