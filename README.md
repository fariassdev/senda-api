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

Rename the `.env.example` file to `.env` in the root of the project and populate it with your keys.

The scripts will automatically load this environment variable.

**Note**: This project is configured to connect to an endpoint at `http://localhost:8880`. Make sure the TTS service is running locally at that address.