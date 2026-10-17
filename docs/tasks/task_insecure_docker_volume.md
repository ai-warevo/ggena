# Task: Restrict Docker Volume Mounts

## Context
A security assessment identified a high-severity insecure volume mounting configuration in the Docker setup.

## Vulnerability Details
- **Location:** `docker-compose.yml` (Line 21)
- **Description:** The configuration `- .:/workspace` mounts the entire project root directory into the container.
- **Impact:** If the application is compromised, the attacker has full read/write access to the entire source code repository on the host machine.

## Objective
Modify `docker-compose.yml` to only mount specific, necessary directories (e.g., a dedicated `outputs/` or `cache/` folder) instead of the entire project root.

## Instructions for Agent
1. Review `docker-compose.yml`.
2. Identify which directories are actually needed by the application inside the container.
3. Update the volume mounts to be as restrictive as possible.
4. Ensure the application can still function with the new mount configuration.
