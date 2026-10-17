# Refactoring Task: Improving `ConfigManager` in `src/core/config.py`

You are a senior developer tasked with refactoring the `ConfigManager` to improve its reliability and type safety.

## Context
The `ConfigManager` is the central source of truth for application configuration, loading settings from environment variables or `.env` files.

## Issues
- **Manual Parsing Fallback**: The fallback parser for when `python-dotenv` is missing is quite basic and might not handle all edge cases (e.g., multi-line values, complex quoting).
- **Lack of Schema Validation**: It provides typed getters (`get_int`, `get_bool`), but there's no way to validate the entire configuration against a schema at startup.
- **Global Instance Side Effects**: The module creates a global `config = ConfigManager()` instance, which can make unit testing difficult due to shared state and reliance on environment variables.

## Refactoring Plan
1. **Improve Fallback Parser**: Enhance the manual `.env` parser to be more robust or explicitly require `python-dotenv` in production environments.
2. **Introduce Configuration Schema**: Integrate with `Pydantic` to allow defining a formal schema for configuration, enabling validation of all settings upon initialization.
3. **Dependency Injection Friendly**: Refactor the module to avoid the global instance side effect, encouraging users to instantiate and inject `ConfigManager` where needed (e.g., via the `GeneratorRegistry`).

## Verification
- Implement unit tests that verify correct parsing of various `.env` formats.
- Add a test case demonstrating configuration validation using a Pydantic schema.
- Ensure that refactoring doesn't break existing code that relies on the current `get_*` methods.
