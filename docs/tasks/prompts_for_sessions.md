# Prompts for New Sessions

Use these prompts to start a new session for each specific task. Each prompt includes a reference to the main architectural report for context.

---

## Phase 1: Foundation

### Task 1: Standardize Types
**Prompt:**
> I am working on refactoring the `ggena` framework. 
> 
> **Context:** Please read the architectural analysis report at `docs/reports/architectural_analysis_report.md` to understand the current state and why this is necessary.
> 
> **Objective:** Update `BaseGenerator` (in `src/core/base.py` or similar) to use actual `GenerationRequest` and `GenerationResponse` from `src.core.types` instead of generic types or `Any`. Ensure that all existing generators are updated to comply with these standardized types.
> 
> **Steps:**
> 1. Inspect `src/core/types.py` to understand the structure of `GenerationRequest` and `GenerationResponse`.
> 2. Update `BaseGenerator` definition.
> 3. Refactor all implementations in `src/generators/` to use these types.
> 4. Verify that the orchestrator (`src/app`) still works correctly with the updated types.

### Task 2: Modern Packaging
**Prompt:**
> I am working on refactoring the `ggena` framework.
> 
> **Context:** Please read the architectural analysis report at `docs/reports/architectural_analysis_report.md`.
> 
> **Objective:** Add a `pyproject.toml` file to the project root and migrate dependency management from manual installation/requirements files to a standard tool (like `pip` with `pyproject.toml` or `poetry`).
> 
> **Steps:**
> 1. Identify all current dependencies used in the project.
> 2. Create a `pyproject.toml` file defining project metadata and dependencies.
> 3. Ensure the project can be installed in editable mode (`pip install -e .`).
> 4. Verify that the CLI and Server still run correctly after this change.

### Task 3: Async Transition
**Prompt:**
> I am working on refactoring the `ggena` framework.
> 
> **Context:** Please read the architectural analysis report at `docs/reports/architectural_analysis_report.md`.
> 
> **Objective:** Convert the `BaseGenerator.generate` method to be an `async` method (`async def generate(...)`). This is part of a larger transition to support native async implementations for I/O or GPU bound operations.
> 
> **Steps:**
> 1. Update `BaseGenerator` in `src/core/base.py`.
> 2. Refactor all generator implementations in `src/generators/` to use `async def generate`.
> 3. Update the Orchestrator layer (`src/app`) to `await` the `generate` calls.
> 4. Ensure that any synchronous code within generators is handled appropriately (e.g., using `run_in_executor` if necessary, though the goal is native async).

---

## Phase 2: Robustness

### Task 4: Pydantic Integration
**Prompt:**
> I am working on refactoring the `ggena` framework.
> 
> **Context:** Please read the architectural analysis report at `docs/reports/architectural_analysis_report.md`.
> 
> **Objective:** Implement modality-specific parameter validation using Pydantic models. Currently, parameters are passed as a raw `Dict[str, Any]`, which is error-prone.
> 
> **Steps:**
> 1. Define a way for each generator to specify its own `ParameterSchema` (a Pydantic model).
> 2. Update the orchestration logic to fetch this schema and validate the incoming request parameters against it before calling the generator.
> 3. Refactor at least one existing generator (e.g., an image generator) to use a Pydantic model for its parameters.

### Task 5: Enhanced Error Handling
**Prompt:**
> I am working on refactoring the `ggena` framework.
> 
> **Context:** Please read the architectural analysis report at `docs/reports/architectural_analysis_report.md`.
> 
> **Objective:** Define a custom exception hierarchy to improve error reporting and handling across the framework.
> 
> **Steps:**
> 1. Create a base exception class `GgenaError`.
> 2. Derive specific exceptions such as `GeneratorError`, `ValidationError`, `RegistryError`, etc.
> 3. Refactor core components (Registry, Orchestrator, Generators) to raise these specific exceptions instead of generic ones.
> 4. Ensure the API/CLI layer catches these exceptions and returns meaningful error messages.

### Task 6: Dependency Injection
**Prompt:**
> I am working on refactoring the `ggena` framework.
> 
> **Context:** Please read the architectural analysis report at `docs/reports/architectural_analysis_report.md`.
> 
> **Objective:** Refactor `ConfigManager` and `Registry` to support Dependency Injection (DI). The current heavy reliance on global singletons makes testing difficult.
> 
> **Steps:**
> 1. Modify the `Registry` and `ConfigManager` so they can be instantiated and passed into generators via their constructors.
> 2. Update the Orchestrator to manage these instances and inject them where needed.
> 3. Demonstrate that this makes it easier to mock dependencies for unit testing.

---

## Phase 3: Scalability

### Task 7: Command Pattern
**Prompt:**
> I am working on refactoring the `ggena` framework.
> 
> **Context:** Please read the architectural analysis report at `docs/reports/architectural_analysis_report.md`.
> 
> **Objective:** Implement a Command Pattern for task execution to enable features like task queuing, retries, and audit logging.
> 
> **Steps:**
> 1. Create a `GenerationCommand` class that encapsulates all data needed for a generation request.
> 2. Refactor the Orchestrator to create and execute these commands instead of calling generators directly.
> 3. (Optional/Advanced) Implement a simple queue or registry of executed commands for auditing purposes.

### Task 8: Plugin Architecture
**Prompt:**
> I am working on refactoring the `ggena` framework.
> 
> **Context:** Please read the architectural analysis report at `docs/reports/architectural_analysis_report.md`.
> 
> **Objective:** Formalize the discovery mechanism to allow third-party developers to install generators as separate Python packages (plugins).
> 
> **Steps:**
> 1. Research and implement a standard way for plugins to register themselves (e.g., using `entry_points` in `pyproject.toml`).
> 2. Update the `Registry`'s discovery logic to look for these entry points.
> 3. Verify that a new "plugin" package can be installed and automatically discovered by the core framework without changing any core code.
