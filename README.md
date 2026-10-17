# ggena

**ggena** — a full-stack orchestrator for managing various AI generators (images, audio, video, etc.) through a unified web interface and API.

## 🚀 Architecture

Ggena combines a powerful Python backend with a responsive web-based frontend to provide both programmatic access and an interactive user experience.

### High-Level Overview
* **Backend**: A FastAPI-powered server that orchestrates AI models, manages execution via a command pattern, and provides real-time updates through WebSockets.
* **Frontend**: A lightweight, modern web UI that communicates with the backend for seamless generation and progress monitoring.

### Tech Stack
| Layer | Technologies |
| :--- | :--- |
| **Backend** | Python 3.10+, FastAPI, Uvicorn, PyTorch, Diffusers, Pydantic |
| **Frontend** | HTML5, CSS3, Modern JavaScript (ES6+) |
| **Communication** | REST API (HTTP POST) & WebSockets (for real-time streaming) |

## ✨ Key Features

* **Dynamic Discovery**: New models can be added by creating a new module, which is automatically registered in the system.
* **Unified Interface**: Standardized requests and responses across all generation types.
* **Real-time Streaming**: WebSocket support for live progress updates and incremental image delivery during generation.
* **GPU Optimized**: Built-in support for hardware acceleration (e.g., TF32 for RTX 40-series) and efficient VRAM management.

## 🛠️ Getting Started

### Running with Docker (Recommended)

The project is pre-configured to work in a Docker container with NVIDIA GPU support.

1. **Build and start the containers:**
   ```bash
   make dcu
   ```

2. **Access the Web UI:**
   Open your browser and navigate to `http://localhost:8000`.

3. **Start the API server (and automatically manage containers):**
   ```bash
   make server
   ```

4. **Generate an image via CLI (inside the container):**
   ```bash
   make gen_image PROMPT="a beautiful landscape" IMAGE_GEN_COUNT=1
   ```

5. **Stop containers:**
   ```bash
   make stop
   ```

### Local Development (Non-Docker)

For local development without Docker, the project uses standard Python packaging (`pyproject.toml`).

1. **Install in editable mode:**
   ```bash
   pip install -e .
   ```

2. **Start the API & Web Server:**
   ```bash
   python src/app/server.py
   ```
   The server will be available at `http://localhost:8000`.

3. **Run via CLI:**
   ```bash
   ggena-cli image "your prompt"
   ```

## 📂 Project Structure

* `src/core`: Core system logic (registry, configuration, base types).
* `src/generators`: Implementation of specific generation strategies (image, audio, video, etc.).
* `src/app`: Orchestrator layer.
    * `server.py`: FastAPI server entry point.
    * `cli.py`: Command-line interface implementation.
    * `frontend/`: Web UI assets (`index.html`, `style.css`, `script.js`).
