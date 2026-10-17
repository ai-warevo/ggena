# Task: Fix Path Traversal in CLI Output

## Context
A security assessment identified a high-severity path traversal vulnerability in the CLI interface.

## Vulnerability Details
- **Location:** `src/app/cli.py` (Lines 94-127)
- **Description:** The `--output` argument is used to define the save path without any validation or sanitization.
- **Impact:** A user can overwrite arbitrary files on the host system by providing paths like `/home/user/.ssh/authorized_keys`.

## Objective
Implement path validation for the `--output` argument in `src/app/cli.py`. Ensure that all output files are saved within a designated, safe directory.

## Instructions for Agent
1. Analyze `src/app/cli.py`.
2. Implement a sanitization mechanism to ensure the output path is restricted to an allowed directory.
3. Verify that attempts to use `..` or absolute paths outside the sandbox are blocked.
