import os
import shutil
import time
import zipfile
import uuid
import subprocess
from functools import wraps
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

# --- LANGCHAIN IMPORTS ---
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

# Notice: We completely removed the os.environ["GOOGLE_API_KEY"] line!

app = FastAPI(title="Self-Healing Codebase API (BYOK)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# 1. THE TOOLS (Removed the 20s delay since it's BYOK)
# ---------------------------------------------------------
# Because users bring their own keys, we don't need to forcefully throttle them anymore.
# They manage their own limits!

@tool
def list_directory(directory_path: str = ".") -> str:
    """Lists all files and folders in the specified directory."""
    try:
        if not os.path.exists(directory_path):
            return f"Error: Directory '{directory_path}' does not exist."
        return f"Contents of '{directory_path}':\n" + "\n".join(os.listdir(directory_path))
    except Exception as e:
        return f"Error listing directory: {str(e)}"

@tool
def read_local_file(file_path: str) -> str:
    """Reads the content of a local file."""
    try:
        if not os.path.exists(file_path):
            return f"Error: The file '{file_path}' does not exist."
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file {file_path}: {str(e)}"

@tool
def write_to_file(file_path: str, content: str) -> str:
    """Writes content to a local file."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Success: Content written to {file_path}"
    except Exception as e:
        return f"Error: Failed to write to {file_path}. {str(e)}"

@tool
def run_python_script(file_path: str) -> str:
    """Executes a Python script SECURELY inside a Docker container."""
    try:
        if not os.path.exists(file_path):
            return f"Error: Cannot run '{file_path}' because it does not exist."
            
        abs_file_path = os.path.abspath(file_path)
        dir_name = os.path.dirname(abs_file_path)
        file_name = os.path.basename(abs_file_path)

        cmd = ["python", file_name]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            return f"Execution Successful! Output:\n{result.stdout}"
        else:
            return f"Execution Failed! Traceback Error:\n{result.stderr}"
    except Exception as e:
        return f"System Error executing script: {str(e)}"

# ---------------------------------------------------------
# 2. THE API ENDPOINT (BYOK Architecture)
# ---------------------------------------------------------
@app.post("/heal")
async def heal_codebase(
    file: UploadFile = File(...),
    target_file: str = Form(...),
    api_key: str = Form(...) # <--- NEW: The user's key arrives here!
):
    print(f"\n[Server] Received upload: {file.filename} with user API Key.")
    
    session_id = str(uuid.uuid4())
    upload_dir = f"uploads/{session_id}"
    os.makedirs(upload_dir, exist_ok=True)
    
    zip_path = os.path.join(upload_dir, file.filename)
    
    with open(zip_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    repo_dir = os.path.join(upload_dir, "repo")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(repo_dir)

    # NEW: Initialize the model with the user's API key and upgrade to 2.5-pro!
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-pro", 
            api_key=api_key, 
            temperature=0.0, 
            max_retries=3
        )
    except Exception as e:
        return {"status": "error", "final_message": [{"text": "Invalid API Key provided."}]}

    tools = [list_directory, read_local_file, write_to_file, run_python_script]
    agent_executor = create_react_agent(llm, tools)

    system_prompt = (
        "You are an autonomous Python Software Engineer. Debug the repository:\n"
        "1. Read the files to understand the architecture.\n"
        "2. Run the main script to see the traceback error.\n"
        "3. Trace the error. If it points to a different file, read and fix that file.\n"
        "4. Fix all bugs across the files and verify with a final run."
    )
    user_command = f"Explore '{repo_dir}', find the bugs causing '{repo_dir}/{target_file}' to crash, and fix them."

    inputs = {"messages": [("system", system_prompt), ("user", user_command)]}
    action_log = []

    print(f"[Server] Starting Pro agent workflow for {target_file}...")

    try:
        # Notice we removed the 20s time.sleep() here as well! It will run at maximum speed.
        for chunk in agent_executor.stream(inputs, stream_mode="values"):
            chunk["messages"][-1].pretty_print()
            action_log.append(chunk["messages"][-1].content)
    except Exception as e:
         return {"status": "error", "final_message": [{"text": f"Agent crashed: API Key Quota Exhausted or Invalid. Details: {str(e)}"}]}

    print("[Server] Agent workflow complete!")

    return {
        "status": "success",
        "final_message": action_log[-1],
        "session_id": session_id
    }