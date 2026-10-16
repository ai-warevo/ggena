# Task: Monolithic Functions (Medium Priority)

## Context
The `main()` function in `src/app/cli.py` is performing too many responsibilities: argument parsing, dependency initialization, generator discovery, parameter processing, signal handling, command execution, and file I/O for saving results.

## Objective
Decompose `main()` into smaller, single-responsibility functions (e.g., `setup_environment()`, `parse_extra_params()`, `handle_output()`).

## Instructions for New Session
1.  Analyze the current implementation of `main()` in `src/app/cli.py`.
2.  Identify logical boundaries for decomposition.
3.  Refactor `main()` by extracting these responsibilities into well-defined, testable functions.
4.  Ensure that the new structure maintains existing functionality and improves readability.

---
**Current runtime context.** This snapshot supersedes earlier runtime-context snapshots.
