# Task: Implement Non-Root User in Dockerfile

## Context
A security assessment identified a medium-severity issue where the container runs as root by default.

## Vulnerability Details
- **Location:** `Dockerfile`
- **Description:** The Dockerfile does not define a non-root `USER`. By default, all processes run with root privileges.
- **Impact:** Increases the severity of any container escape or application compromise.

## Objective
Modify the `Dockerfile` to create a dedicated non-root user and switch to it using the `USER` instruction.

## Instructions for Agent
1. Review the `Dockerfile`.
2. Add instructions to create a new user (e.g., `ggena_user`).
3. Ensure that all necessary directories and files have the correct permissions for this user.
4. Switch to the non-root user at the end of the Dockerfile.
5. Verify that the application can still run correctly as a non-root user.
