# Task: Improve Developer Experience with Makefile Automation

## Context
The current `Makefile` lacks standard automation for testing and linting, and there's a discrepancy in the README regarding `make dcu`.

## Objective
Update the `Makefile` to include commands for `lint`, `test`, `setup`, `clean`, and an alias `dcu` for `up`, as proposed in `docs/reports/devops_roadmap.md`.

## Requirements
- Implement `lint` (Ruff).
- Implement `test` (Pytest).
- Implement `setup` (uv installation).
- Implement `clean` (removing caches).
- Add `dcu` as an alias for `up`.
- Ensure the Makefile supports different tracks (`dev`, `prod`).
