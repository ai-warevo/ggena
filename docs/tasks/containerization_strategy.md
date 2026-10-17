# Task: Implement Multi-Stage Docker Builds for Ggena

## Context
The current containerization uses `huggingface/transformers-pytorch-gpu`, which is functional but heavy. We want to implement a multi-stage build to separate the build environment (containing `uv` and compilers) from the runtime environment to reduce production image size and improve security.

## Objective
Implement the proposed multi-stage `Dockerfile.prod` as described in `docs/reports/devops_roadmap.md`.

## Requirements
- Use a builder stage with `uv`.
- Use a lightweight runtime stage.
- Ensure non-root user is used.
- Copy only necessary artifacts from the builder to the runtime.
