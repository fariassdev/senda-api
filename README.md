# Senda: AI-Powered Meditation Scripts 🧘‍♀️

Senda is a Python-based tool for generating and playing guided meditation scripts. It leverages Google's Generative AI (Gemini) to create the scripts and a local text-to-speech (Kokoro TTS) service to stream the audio.

## ✨ Features

*   ✨ **AI Script Generation**: Automatically create unique meditation scripts using Gemini.
*   📚 **Course Architecture**: Design comprehensive meditation courses with multiple lessons.
*   🗣️ **Text-to-Speech**: Convert generated scripts into audio via a local TTS service.
*   🎧 **Audio Streaming**: Play meditation audio directly from the command line.
*   📦 **Batch Generation**: Generate scripts and audio for entire courses at once.
*   🌐 **REST API**: Exposes course management functionalities through a FastAPI interface.

## 🚀 Getting Started

### Using Docker (Recommended)

To build and run the application using Docker, run the following command from the project root:

```bash
docker-compose up --build
```

This will start the PostgreSQL database, the Kokoro TTS service, and the FastAPI application. The API will be available at `http://localhost:8000`.

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
2.  **Add your Gemini API key** to the `.env` file:
    ```
    GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
    ```


## 💻 Usage

Senda provides several scripts for different tasks. All commands should be run from the root of the project.

### FastAPI Server

Senda includes a FastAPI server to manage courses.

*   ▶️ **Run the development server:**
    This command starts the server with auto-reload enabled. The API will be available at `http://localhost:8000`.
    ```sh
    uvicorn src.senda.api.main:app
    ```

## 🛠️ Development Conventions

*   📦 **Package Management**: The project uses `uv` for managing dependencies, as defined in `pyproject.toml`.
*   🔑 **Environment Variables**: A `.env` file is used to store the `GEMINI_API_KEY`.
*   📁 **Source Code**: All Python source code is located in the `src/senda` directory.

