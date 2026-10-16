# Task: Technical Debt: Transition Artifacts (Medium Priority)

## Context
In `src/generators/image/image_generator.py`, there is logic to handle both injected configuration and a global fallback (`import src.core.config as global_config`). This "backward compatibility" code complicates the class logic and violates the principle of Dependency Injection, which the project is moving towards.

## Objective
Once the transition to the modular package structure is complete, remove all global configuration fallbacks and strictly enforce dependency injection via the constructor.

## Instructions for New Session
1.  Examine `src/generators/image/image_generator.py` for any remaining global configuration imports or usage.
2.  Ensure that all necessary configurations are passed through the constructor (Dependency Injection).
3.  Remove any code related to the old global fallback mechanism.

---
**Current runtime context.** This snapshot supersedes earlier runtime-context snapshots.
