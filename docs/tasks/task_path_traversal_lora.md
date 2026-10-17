# Task: Fix Path Traversal in LoRA Loading

## Context
A security assessment identified a high-severity path traversal vulnerability in the image generator.

## Vulnerability Details
- **Location:** `src/generators/image/image_generator.py` (Lines 201-218)
- **Description:** The generator parses `<lora:filename:weight>` from the user prompt. The `filename` is used directly to construct a path: `f"civitai_cache/{filename}.safetensors"`. An attacker can provide a filename like `../../etc/passwd` to attempt to load arbitrary files from the system.
- **Impact:** Unauthorized file access and potential remote code execution.

## Objective
Implement strict validation for the LoRA filename. Ensure it only contains alphanumeric characters, underscores, or hyphens, and explicitly forbid `..` or `/`. Use a sandbox directory approach if possible.

## Instructions for Agent
1. Analyze `src/generators/image/image_generator.py`.
2. Implement a sanitization utility or use existing ones to ensure the filename is safe.
3. Verify that no path traversal is possible.
4. Ensure the fix doesn't break legitimate LoRA loading.
