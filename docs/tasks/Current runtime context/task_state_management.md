# Task: State Management Refinement

## Context
The current frontend uses multiple global variables (e.g., `imageHistory`, `currentRotationIndex`) to manage state, which is difficult to debug and scale.

## Objective
Encapsulate the application state into a single, centralized `AppState` object.

## Requirements
1. **Centralized State Object**: 
   - Create an `AppState` object that holds all relevant UI and application data.
   - Refactor existing code to read from and write to this object instead of individual global variables.

## Constraints
- Use Vanilla JS/ES6+.
- Do not introduce heavy frameworks.
- Maintain existing functionality.

## Acceptance Criteria
- [ ] All key pieces of state are contained within a single `AppState` object.
- [ ] The application functions correctly with the new centralized state management.
- [ ] Global variable usage is minimized/eliminated in favor of the `AppState`.
