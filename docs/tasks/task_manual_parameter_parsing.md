# Task: Manual Parameter Parsing (Low Priority)

## Context
The CLI manually parses `--param key=value` strings into a dictionary in `src/app/cli.py`. This is error-prone and bypasses the robust validation provided by Pydantic models already defined in the generators.

## Objective
Leverage the `parameter_schema` property of the generator to validate these parameters directly using Pydantic's `model_validate()` method.

## Instructions for New Session
1.  Locate the manual parameter parsing logic in `src/app/cli.py`.
2.  Identify how generators define their `parameter_schema`.
3.  Refactor the parsing logic to use the generator's schema and Pydantic's validation capabilities.

---
**Current runtime context.** This snapshot supersedes earlier runtime-context snapshots.
