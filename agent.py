import os
import subprocess
import shutil
import time
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

# ---------------------------------------------------------
# 1. THE TOOLS (With Built-In Rate Limiting)
# ---------------------------------------------------------

@tool
def list_directory(directory_path: str = ".") -> str:
    """
    Lists all files and folders in the specified directory. 
    Use this FIRST to explore a repository and see what files exist before trying to read or run them.
    """
    time.sleep(15)  # API Rate Limiter
    try:
        if not os.path.exists(directory_path):
            return f"Error: Directory '{directory_path}' does not exist."
        files = os.listdir(directory_path)
        return f"Contents of '{directory_path}':\n" + "\n".join(files)
    except Exception as e:
        return f"Error listing directory: {str(e)}"

@tool
def read_local_file(file_path: str) -> str:
    """Reads the content of a local file and returns it as a string."""
    time.sleep(15)  # API Rate Limiter
    try:
        if not os.path.exists(file_path):
            return f"Error: The file '{file_path}' does not exist."
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file {file_path}: {str(e)}"

@tool
def write_to_file(file_path: str, content: str) -> str:
    """Writes the provided string content to a local file, overwriting existing content."""
    time.sleep(15)  # API Rate Limiter
    try:
        directory = os.path.dirname(file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Success: Content successfully written to {file_path}"
    except Exception as e:
        return f"Error: Failed to write to {file_path}. Details: {str(e)}"

@tool
def run_python_script(file_path: str) -> str:
    """
    Executes a Python script SECURELY inside an isolated Docker container.
    Returns the console output or the traceback error message.
    """
    time.sleep(15)  # API Rate Limiter
    try:
        if not os.path.exists(file_path):
            return f"Error: Cannot run '{file_path}' because it does not exist."
            
        abs_file_path = os.path.abspath(file_path)
        dir_name = os.path.dirname(abs_file_path)
        file_name = os.path.basename(abs_file_path)

        docker_cmd = [
            "docker", "run", 
            "--rm",                  
            "-v", f"{dir_name}:/app", 
            "-w", "/app",            
            "python:3.13-slim",      
            "python", file_name      
        ]
        
        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=15 
        )
        
        if result.returncode == 0:
            return f"Execution Successful! Output:\n{result.stdout}"
        else:
            return f"Execution Failed! Traceback Error:\n{result.stderr}"
            
    except subprocess.TimeoutExpired:
        return "Error: Script execution timed out (Infinite loop detected)."
    except Exception as e:
        return f"System Error executing script: {str(e)}"


# ---------------------------------------------------------
# 2. THE ENVIRONMENT (The Multi-File Trap)
# ---------------------------------------------------------

def setup_dummy_repo():
    """Creates a multi-file repository with linked bugs across different files."""
    repo_name = "test_repo"
    
    if os.path.exists(repo_name):
        shutil.rmtree(repo_name)
    os.makedirs(repo_name)

    # File 1: utils.py has a variable NameError
    utils_code = """
def calculate_discount(price, discount_rate):
    # Bug 1: NameError (dicount_rate is misspelled)
    discount_amount = price * dicount_rate
    return price - discount_amount
"""
    # File 2: main.py has an ImportError
    main_code = """
# Bug 2: Incorrect import name (should be calculate_discount)
from utils import calc_discount

def main():
    price = 200
    rate = 0.1
    final_price = calc_discount(price, rate)
    print(f"Final price is: {final_price}")

if __name__ == "__main__":
    main()
"""
    with open(os.path.join(repo_name, "utils.py"), "w", encoding="utf-8") as f:
        f.write(utils_code.strip())
        
    with open(os.path.join(repo_name, "main.py"), "w", encoding="utf-8") as f:
        f.write(main_code.strip())
        
    print(f"--- Created multi-file repository in '{repo_name}/' ---")
    return repo_name


# ---------------------------------------------------------
# 3. THE AGENT ENGINE
# ---------------------------------------------------------

def main():
    repo_dir = setup_dummy_repo()

    # Initialize Gemini with Retry Logic
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.0,
        max_retries=5  # Resilient to temporary network or quota hiccups
    )

    system_prompt = (
        "You are an autonomous, self-healing Python Software Engineer. "
        "You are tasked with debugging a repository. Follow these exact steps:\n"
        "1. Use list_directory to see what files exist in the target folder.\n"
        "2. Read the files to understand the imports and architecture.\n"
        "3. Run the main entry point script to generate the initial traceback error.\n"
        "4. Trace the error. If it points to a different file, read that file, fix it, and save it.\n"
        "5. Re-run the main script to verify. \n"
        "6. Continue this loop until the main script executes with 0 errors. "
        "Always use the full relative paths provided (e.g., 'test_repo/main.py')."
    )

    tools = [list_directory, read_local_file, write_to_file, run_python_script]
    agent_executor = create_react_agent(llm, tools)

    user_command = f"Please explore the '{repo_dir}' directory, find the bugs causing '{repo_dir}/main.py' to crash, and fix them across all necessary files."
    print("Starting the Multi-File Self-Healing Loop...\n")

    inputs = {
        "messages": [
            ("system", system_prompt),
            ("user", user_command)
        ]
    }
    
    # Run the agent (grab a coffee, the rate limiting makes it think methodically!)
    for chunk in agent_executor.stream(inputs, stream_mode="values"):
        chunk["messages"][-1].pretty_print()
        
        # MASTER RATE LIMITER: Force a 15-second pause after every single agent step
        time.sleep(15)

if __name__ == "__main__":
    main()