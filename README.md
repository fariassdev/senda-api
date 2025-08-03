# **Senda Meditation Scripts**

This project contains a set of Python tools and scripts to generate and play guided meditation scripts using generative AI and text-to-speech services.

## **🚀 Getting Started**

Follow these instructions to get the project up and running on your local machine.

### **Prerequisites**

Make sure you have the following tools installed:

* **Python 3.13+**  
* **uv**: An extremely fast Python package installer and manager. You can install it from [its official website](https://github.com/astral-sh/uv).

### **Installation**

1. **Clone the repository** (or if you already have it, navigate to the root directory):  
   ```sh
   git clone https://github.com/fariassdev/senda.git 
   cd senda
   ```

2. **Create a virtual environment** using uv:
   ```sh
   uv venv
   ```

   This will create a `.venv` folder in your project with the Python interpreter and necessary tools.  
3. **Activate the virtual environment**:  
   * On macOS/Linux:
     ```sh
     source .venv/bin/activate
     ```

   * On Windows (PowerShell):
     ```sh
     .venv\Scripts\activate
     ```

4. **Install the dependencies** and the project in editable mode. This allows you to modify the code and see the changes instantly without reinstalling.
   ```sh
   uv pip install -e .
   ```

## **⚙️ Configuration**

Before running the scripts, you need to set up your API keys.

Create a file named `.env` in the root of the project and add your keys:

`GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"`

The scripts will automatically load this environment variable.

## **▶️ Usage**

Once installed, you can interact with the project in several ways.

### **Generate a New Meditation Script**

To generate a new script in JSON format using Google GenAI, run the following script:

```sh
python src/senda/generate_meditation_course_script.py
```

The output will be printed directly to the console.

### **Play a Meditation Script**

To listen to the predefined meditation script through a local text-to-speech service (as configured in `meditation_practice_audio_stream.py`), run:

```sh
python src/senda/meditation_practice_audio_stream.py
```

**Note**: This script is configured to connect to an endpoint at `http://localhost:8880`. Make sure the TTS service is running locally at that address.