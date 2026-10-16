# Maintainability & Clean Code Report

## 1. Identified Code Smells

### 🚨 Inconsistent Logging (High Priority)
The codebase exhibits a significant inconsistency in how information and errors are communicated. While `src/core/executor.py` correctly utilizes the standard Python `logging` module, the majority of the application—including critical paths in `src/app/cli.py` and `src/generators/image/image_generator.py`—relies heavily on `print()` statements.
- **Impact**: Makes it difficult to manage log levels (DEBUG vs INFO), redirect output to files, or integrate with professional observability tools.
- **Recommendation**: Replace all `print()` calls with a configured `logging` instance.

### 🏗️ Monolithic Functions (Medium Priority)
The `main()` function in `src/app/cli.py` is performing too many responsibilities: argument parsing, dependency initialization, generator discovery, parameter processing, signal handling, command execution, and file I/O for saving results.
- **Impact**: Reduces readability, makes unit testing individual steps impossible, and increases the risk of side effects during refactoring.
- **Recommendation**: Decompose `main()` into smaller, single-responsibility functions (e.g., `setup_environment()`, `parse_extra_params()`, `handle_output()`).

### 🛠️ Technical Debt: Transition Artifacts (Medium Priority)
In `src/generators/image/image_generator.py`, there is logic to handle both injected configuration and a global fallback (`import src.core.config as global_config`).
- **Impact**: This "backward compatibility" code complicates the class logic and violates the principle of Dependency Injection, which the project is moving towards.
- **Recommendation**: Once the transition to the modular package structure is complete, remove all global configuration fallbacks and strictly enforce dependency injection via the constructor.

### 🧩 Manual Parameter Parsing (Low Priority)
The CLI manually parses `--param key=value` strings into a dictionary in `src/app/cli.py`.
- **Impact**: This is error-prone and bypasses the robust validation provided by Pydantic models already defined in the generators.
- **Recommendation**: Leverage the `parameter_schema` property of the generator to validate these parameters directly using Pydantic's `model_validate()` method.

---

## 2. Proposed Coding Standards

To ensure long-term maintainability, all contributors should adhere to the following rules:

### 🐍 Pythonic Idioms & Style
- **PEP 8**: Strict adherence to PEP 8 for indentation, spacing, and line length.
- **Naming Conventions**:
    - `PascalCase` for Classes.
    - `snake_case` for functions, methods, and variables.
    - `UPPER_SNAKE_CASE` for constants.
- **Type Hinting**: All public-facing functions, class methods, and complex variable assignments **must** include type hints. Use `mypy` or `pyright` in CI/CD to enforce this.

### 📝 Documentation
- **Standard**: Use **Google Style Docstrings**.
- **Scope**: Every class and public method must have a docstring explaining its purpose, arguments (with types), and return values.
- **CLI**: Ensure all new CLI arguments are documented in the `argparse` description.

### 🪵 Logging & Error Handling
- **Logging**: Never use `print()` for application logic. Use `logging.getLogger(__name__)`.
    - `DEBUG`: Fine-grained informational events that are most useful to debug an application.
    - `INFO`: Confirmation that things are working as expected.
    - `WARNING`: An indication that something unexpected happened, or indicative of some problem in the near future (e.g. ‘disk space low’). The software is still working as expected.
    - `ERROR`: Due to a more serious problem, the software has not been able to perform some function.
- **Exceptions**: Define custom exceptions in `src/core/exceptions.py` rather than using generic `Exception`. Catch specific errors whenever possible.

---

## 3. Testing Strategy

### 🧪 Unit Testing (`pytest`)
**Goal**: Test individual components in isolation.
- **Mocking**: Use `unittest.mock` to mock heavy ML dependencies (e.g., `torch`, `diffusers`, `transformers`). This allows running tests in CI environments without GPUs.
- **Focus**: `ConfigManager`, `GeneratorRegistry`, `CommandExecutor`, and individual `BaseCommand` implementations.

### 🔗 Integration Testing
**Goal**: Test the interaction between core components.
- **Scenario**: Execute a `GenerationCommand` through the `CommandExecutor` using a `MockGenerator`. This verifies that the registry, context, and executor work together correctly without needing actual AI models.

### 🚀 End-to-End (E2E) Testing
**Goal**: Verify the entire system from user input to output.
- **Scenario**: Use `subprocess` to run the `cli.py` with a set of predefined arguments and verify that the expected files are created in the `outputs/` directory.

---

## 4. Refactoring Examples

### Example 1: Replacing `print` with `logging`

**Before:**
```python
def _load_pipeline(self):
    if self._pipe is None:
        print(f"Loading model '{self._model_id}' to GPU...")
        # ... loading logic ...
```

**After:**
```python
import logging

logger = logging.getLogger(__name__)

def _load_pipeline(self):
    if self._pipe is None:
        logger.info("Loading model '%s' to GPU...", self._model_id)
        # ... loading logic ...
```

### Example 2: Refactoring Monolithic CLI `main`

**Before:**
```python
async def main():
    # 50 lines of arg parsing, config init, registry discovery...
    # 30 lines of parameter parsing...
    # 40 lines of execution and output saving...
```

**After:**
```python
async def main():
    args = parse_arguments()
    context = initialize_context(args)
    
    try:
        result = await execute_generation(args, context)
        handle_output(result, args.output)
    except GgenaError as e:
        logger.error("Generation failed: %s", e)
        sys.exit(1)

def parse_arguments(): ...
def initialize_context(args) -> CommandContext: ...
def execute_generation(args, context) -> CommandResult: ...
def handle_output(result, output_path): ...
```

### Example 3: Upgrading `dataclasses` to `pydantic` for Validation

**Before (`src/core/types.py`):**
```python
@dataclass(frozen=True)
class GenerationRequest:
    prompt: str
    num_outputs: int = 1
    parameters: Dict[str, Any] = field(default_factory=dict)
```

**After:**
```python
from pydantic import BaseModel, Field

class GenerationRequest(BaseModel):
    prompt: str
    num_outputs: int = Field(default=1, ge=1)
    parameters: Dict[str, Any] = Field(default_factory=dict)
```
