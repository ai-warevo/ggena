# Refactoring Task: Decomposing CLI (`src/app/cli.py`)

You are a senior developer tasked with decomposing the monolithic `src/app/cli.py` into a modular package structure.

## Context
The current CLI implementation handles argument parsing, environment initialization, signal handling, and output management all in one file.

## Refactoring Plan
Create a new directory `src/app/cli/` and move logic as follows:
1. **Initialize Package**: Create `src/app/cli/__init__.py`.
2. **`main.py`**: The entry point that calls `asyncio.run(main())`.
3. **`args.py`**: Contains `parse_arguments()` and `process_parameters()`.
4. **`env.py`**: Contains `initialize_environment()`.
5. **`utils.py`**: Contains `get_generator()`, `setup_signal_handling()`, and `handle_output()`.

## Verification
- Ensure the CLI still functions identically with the new structure.
- Verify that all imports in the new files are correctly updated to use relative or absolute package imports (e.g., `from src.app.cli.args import ...`).
- Confirm that the package is correctly recognized by Python (presence of `__init__.py`).
