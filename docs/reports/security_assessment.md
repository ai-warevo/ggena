# Security Assessment Report - Ggena Framework

**Date:** 2026-10-17
**Status:** Draft
**Auditor:** AI Security Agent (DevSecOps)

## Executive Summary
The security audit of the `ggena` framework identified several critical and high-severity vulnerabilities, primarily related to **Path Traversal**, **Container Configuration**, and **Secret Management**. While the core logic is well-structured using Pydantic for parameter validation, the boundaries between user input and the filesystem/environment are insufficiently guarded.

---

## 1. Identified Vulnerabilities

### [HIGH] Path Traversal via LoRA Loading
- **Location:** `src/generators/image/image_generator.py` (Lines 201-218)
- **Description:** The generator parses `<lora:filename:weight>` from the user prompt. The `filename` is used directly to construct a path: `f"civitai_cache/{filename}.safetensors"`. An attacker can provide a filename like `../../etc/passwd` to attempt to load arbitrary files from the system.
- **Impact:** Unauthorized file access and potential remote code execution if an attacker can trick the system into loading a malicious `.safetensors` or similar file from an unexpected location.

### [HIGH] Insecure Docker Volume Mounting
- **Location:** `docker-compose.yml` (Line 21)
- **Description:** The configuration `- .:/workspace` mounts the entire project root directory into the container.
- **Impact:** If the application is compromised, the attacker has full read/write access to the entire source code repository on the host machine, including `.env` files and potentially other sensitive data in the workspace.

### [HIGH] Path Traversal via CLI Output
- **Location:** `src/app/cli.py` (Lines 94-127)
- **Description:** The `--output` argument is used to define the save path without any validation or sanitization.
- **Impact:** A user can overwrite arbitrary files on the host system by providing paths like `/home/user/.ssh/authorized_keys`.

### [MEDIUM] Running Container as Root
- **Location:** `Dockerfile`
- **Description:** The Dockerfile does not define a non-root `USER`. By default, all processes run with root privileges.
- **Impact:** Increases the severity of any container escape or application compromise, granting the attacker full control over the container environment.

### [MEDIUM] Secret Leakage in Logs & API Errors
- **Location:** `src/core/logging_setup.py` and `src/app/server.py` (Line 139)
- **Description:** 
    1. The logging configuration lacks filters to redact sensitive environment variables (e.g., `HF_TOKEN`).
    2. The FastAPI server returns raw exception strings (`str(e)`) in HTTP 500 responses.
- **Impact:** Sensitive information (tokens, internal paths, library versions) can be leaked through application logs or directly to API consumers.

### [LOW] Permissive CORS Policy
- **Location:** `src/app/server.py` (Line 81)
- **Description:** `allow_origins=["*"]` is used in the CORS middleware.
- **Impact:** While useful for development, it allows any website to make requests to the API, increasing the risk of Cross-Site Request Forgery (CSRF) if authentication is added later.

---

## 2. Hardening Recommendations

### Dockerfile & docker-compose.yml
1.  **Implement Non-Root User:** Add a dedicated user in the `Dockerfile` and switch to it using the `USER` instruction.
    ```dockerfile
    RUN useradd -m ggena_user
    USER ggena_user
    ```
2.  **Restrict Volume Mounts:** Instead of mounting `.`, only mount specific, necessary directories (e.g., a dedicated `outputs/` or `cache/` folder).
3.  **Use Specific Base Images:** Move away from large, unverified base images to official Python or NVIDIA CUDA images to reduce the attack surface.
4.  **Avoid Editable Installs in Production:** Use `pip install .` instead of `pip install -e .` in the production Dockerfile.

### Code Hardening
1.  **Sanitize All Paths:** Implement a utility function to validate that all user-provided paths are contained within an allowed "sandbox" directory. Use `os.path.abspath` and check prefixes.
2.  **Secure LoRA Loading:** Validate the `filename` in the LoRA regex to ensure it only contains alphanumeric characters, underscores, or hyphens, and explicitly forbid `..` or `/`.
3.  **Redact Logs:** Implement a custom `logging.Filter` that scans log messages for known sensitive keys (like `HF_TOKEN`) and replaces them with `[REDACTED]`.
4.  **Generic API Errors:** In production, return generic error messages to the client (e.g., "Internal Server Error") while logging the detailed exception internally for debugging.

---

## 3. Security Checklist for Future Development

- [ ] **Input Validation:** Does every user-provided string that touches the filesystem undergo strict sanitization?
- [ ] **Least Privilege:** Is this new component running with the minimum necessary permissions?
- [ ] **Secret Hygiene:** Are secrets being loaded from a secure manager (e.g., AWS Secrets Manager, HashiCorp Vault) instead of plain `.env` files in production?
- [ ] **Dependency Check:** Have all new dependencies been vetted for known vulnerabilities?
- [ ] **Logging Audit:** Does the new logging statement risk exposing PII or credentials?

---

## 4. Automated Security Scanning Pipeline

To maintain a high security posture, integrate the following into the CI/CD pipeline:

1.  **SCA (Software Composition Analysis):** Use `safety` or `snyk` to scan `pyproject.toml` for vulnerable dependencies on every push.
2.  **SAST (Static Application Security Testing):** Integrate `bandit` to scan Python code for common security issues (like the use of `os.system` or insecure regex).
3.  **Container Scanning:** Use `Trivy` or `Docker Scout` to scan the built Docker image for OS-level vulnerabilities and misconfigurations.
4.  **Secret Scanning:** Use `gitleaks` or GitHub Secret Scanning to ensure no secrets are accidentally committed to the repository.
