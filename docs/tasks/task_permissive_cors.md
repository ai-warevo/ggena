# Task: Restrict CORS Policy

## Context
A security assessment identified a low-severity issue with a permissive CORS policy.

## Vulnerability Details
- **Location:** `src/app/server.py` (Line 81)
- **Description:** `allow_origins=["*"]` is used in the CORS middleware.
- **Impact:** Allows any website to make requests to the API, increasing CSRF risk.

## Objective
Restrict the CORS policy in `src/app/server.py` by replacing the wildcard `"*"` with a list of allowed origins (e.g., from an environment variable or configuration).

## Instructions for Agent
1. Analyze `src/app/server.py`.
2. Replace the wildcard origin with a more restrictive set of allowed origins.
3. Consider using an environment variable to configure allowed origins for different environments (dev vs prod).
