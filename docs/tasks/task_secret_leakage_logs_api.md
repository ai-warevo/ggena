# Task: Prevent Secret Leakage in Logs and API Errors

## Context
A security assessment identified a medium-severity issue regarding secret leakage through logs and error responses.

## Vulnerability Details
- **Location:** `src/core/logging_setup.py` and `src/app/server.py` (Line 139)
- **Description:** 
    1. The logging configuration lacks filters to redact sensitive environment variables (e.g., `HF_TOKEN`).
    2. The FastAPI server returns raw exception strings (`str(e)`) in HTTP 500 responses.
- **Impact:** Sensitive information can be leaked through application logs or directly to API consumers.

## Objective
1. Implement a custom `logging.Filter` that redacts sensitive keys (like `HF_TOKEN`) from log messages.
2. Update the FastAPI error handling to return generic error messages in production while logging detailed exceptions internally.

## Instructions for Agent
1. Analyze `src/core/logging_setup.py` and implement a redaction filter.
2. Analyze `src/app/server.py` and update the exception handling logic.
3. Ensure that sensitive information is still available in internal logs (if appropriate) but not leaked to users or unredacted log files.
