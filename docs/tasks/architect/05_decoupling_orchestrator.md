# Task: Decouple the Orchestrator (main.py)

## Context
The final step in this architectural overhaul is to decouple `src/main.py` from specific generator implementations. The orchestrator should only know about the `GeneratorRegistry` and the `BaseGenerator` interface, making it completely agnostic of which modalities are actually implemented.

## Reference
- Main Report: <docs/reports/architectural_report.md>
- Alignment Task: <docs/tasks/architect/04_alignment_image_generator.md>

## Objective
Rewrite `src/main.py` to use the `GeneratorRegistry` for dynamic dispatching, removing all hardcoded imports of specific generators.

## Instructions
1. Modify `src/main.py`:
    - Remove direct imports like `from src.generators.image import ...`.
    - Import `GeneratorRegistry`, `ConfigManager`, and the necessary types.
    - Update the CLI argument parsing to be more generic (if needed).
    - Use the `GeneratorRegistry` to look up the requested module.
    - Instantiate the generator and call its `.generate()` method with a constructed `GenerationRequest`.
    - Handle the `GenerationResponse` to print results or errors to the user.
2. Ensure that all necessary modules are imported at the start of `main.py` (or via a discovery mechanism) so they can register themselves in the registry.

## Definition of Done
- [ ] `src/main.py` has NO direct imports from `src.generators.*`.
- [ ] The orchestrator works correctly for the "image" module using the new registry-based flow.
- [ ] Adding a new modality (e.g., "audio") would now only require adding the module and registering it, without touching `main.py`.
