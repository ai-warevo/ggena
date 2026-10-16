# Task: Inconsistent Logging (High Priority)

## Context
The codebase exhibits a significant inconsistency in how information and errors are communicated. While `src/core/executor.py` correctly utilizes the standard Python `logging` module, the majority of the application—including critical paths in `src/app/cli.py` and `src/generators/image/image_generator.py`—relies heavily on `print()` statements.

## Objective
Replace all `print()` calls with a configured `logging` instance.

## Instructions for New Session
1.  Identify all instances of `print()` in the codebase, especially in `src/app/cli.py` and `src/generators/image/image_generator.py`.
2.  Configure a standard logger (e.g., using `logging.getLogger(__name__)`).
3.  Replace `print()` calls with appropriate log levels (`logger.info()`, `logger.error()`, `logger.debug()`, etc.).
4.  Ensure that the logging configuration is consistent across the application.

---
**Current runtime context.** This snapshot supersedes earlier runtime-context snapshots.
