# Refactoring Roadmap: ggena Framework

## Phase 1: Foundation (Immediate)
- [ ] **Standardize Types**: Update `BaseGenerator` to use actual `GenerationRequest` and `GenerationResponse` from `src.core.types`.
- [ ] **Modern Packaging**: Add `pyproject.toml` and migrate dependencies from manual management to a standard tool (e.g., `poetry` or `pip`).
- [ ] **Async Transition**: Convert `BaseGenerator.generate` to an `async` method.

## Phase 2: Robustness (Short-term)
- [ ] **Pydantic Integration**: Implement modality-specific parameter validation using Pydantic models.
- [ ] **Enhanced Error Handling**: Define a custom exception hierarchy (`GgenaError` -> `GeneratorError`, `ValidationError`, etc.).
- [ ] **Dependency Injection**: Refactor `ConfigManager` and `Registry` to support injection into generator constructors.

## Phase 3: Scalability (Long-term)
- [ ] **Command Pattern**: Implement a task queue/command system for handling long-running or batch generation jobs.
- [ ] **Plugin Architecture**: Formalize the discovery mechanism to allow third-party developers to install generators as separate Python packages.
