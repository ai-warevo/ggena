# Task: Implement GitHub Actions CI/CD Pipeline for Ggena

## Context
We need a robust CI pipeline to ensure code quality and security at every pull request and push to `main`.

## Objective
Create `.github/workflows/ci.yml` with jobs for `quality`, `test`, and `container-scan` as proposed in `docs/reports/devops_roadmap.md`.

## Requirements
- **Quality Job**: Linting (Ruff), Type Checking (Mypy), and Security Scan (Safety).
- **Test Job**: Run Pytest in a containerized environment.
- **Container Scan Job**: Build the image locally and scan it with Trivy for CRITICAL and HIGH vulnerabilities.
