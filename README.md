# Senda: AI-Powered Meditation Scripts 🧘‍♀️

Senda is a Python-based tool for generating and playing guided meditation scripts. It leverages Google's Generative AI (Gemini) to create the scripts and a local text-to-speech (Kokoro TTS) service to stream the audio.

## ✨ Features

*   ✨ **AI Script Generation**: Automatically create unique meditation scripts using Gemini.
*   📚 **Course Architecture**: Design comprehensive meditation courses with multiple lessons.
*   🗣️ **Text-to-Speech**: Convert generated scripts into audio via a local TTS service.
*   📦 **Batch Generation**: Generate scripts and audio for entire courses at once.
*   🌐 **REST API**: Exposes course management functionalities through a FastAPI interface.

## 🚀 Getting Started

### Using Docker (Recommended)

To build and run the application using Docker, run the following command from the project root:

```bash
docker-compose up --build
```

This will start the PostgreSQL database, the Kokoro TTS service, and the FastAPI application. The API will be available at `http://localhost:8000/api`.

### Running Locally

To run the application locally, you will need to have Python 3.13+ and `uv` installed.

#### Installation

1.  **Create and activate a virtual environment:**
    ```sh
    # Unix
    uv venv
    source .venv/bin/activate
    ```

    ```sh
    # Windows
    uv venv
    .venv\Scripts\activate
    ```

2.  **Install dependencies:**
    ```sh
    uv pip install -e .
    ```

#### Configuration

1.  **Create a `.env` file** in the root of the project by copying the example file:
    ```sh
    cp .env.example .env
    ```
2.  **Add your environment variables** to the `.env` file.


## 💻 Usage

Senda includes a FastAPI server to manage meditation courses through a RESTful API.

### ▶️ Run the Development Server

There are several ways to start the server:

1. **Development mode with auto-reload** (recommended during development):
```sh
uvicorn api:app --reload
```

2. **Debug mode** (includes detailed error traces):
```sh
uvicorn api:app --reload --log-level debug
```

3. **Using Python directly**:
```sh
python -m main
```

The API will be available at `http://localhost:8000/api`. You can access:
- API documentation: `http://localhost:8000/api/docs`
- Alternative docs: `http://localhost:8000/api/redoc`
- Health check: `http://localhost:8000/api/health`

## 🛠️ Development Conventions

*   📦 **Package Management**: The project uses `uv` for managing dependencies, as defined in `pyproject.toml`.
*   🔑 **Environment Variables**: A `.env` file is used to store the environment variables.
*   📁 **Source Code**: All Python source code is located in the `src/` directory with a clean, flat structure:
    - `src/api.py` - FastAPI application and all API routes
    - `src/main.py` - Server entry point (runs the FastAPI app)
    - `src/models/` - SQLAlchemy database models
    - `src/services/` - Business logic and AI integration
    - `src/repositories/` - Database operations layer
    - `src/routers/` - FastAPI route handlers
    - `src/schemas/` - Pydantic request/response models
    - `src/core/` - Core utilities (database, auth, Redis)
    - `src/utils/` - Helper functions

