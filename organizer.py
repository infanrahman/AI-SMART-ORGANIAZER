"""
AI Smart Organizer (CLI Version)
Owned and Developed by Infan Rahman (infanarahman4@gmail.com)
GitHub: https://github.com/infanrahman/AI-SMART-ORGANIAZER
"""

import os
import shutil
import json
import re
import ollama

TARGET_DIRECTORY = "messy_folder"

# --- 1. CLEAN TOOL DEFINITIONS ---
def list_files() -> list:
    """Returns a list of all file names in the messy folder."""
    print(f"[Agent Action] 🔍 Listing files in '{TARGET_DIRECTORY}'...")
    try:
        files = [f for f in os.listdir(TARGET_DIRECTORY) if os.path.isfile(os.path.join(TARGET_DIRECTORY, f))]
        print(f"   -> Found {len(files)} files.")
        return files
    except Exception as e:
        return [f"Error: {str(e)}"]

def create_folder(folder_name: str) -> str:
    """Creates a new folder. 
    
    Args:
        folder_name (str): The name of the folder (e.g., 'Documents' or 'Images').
    """
    folder_name = os.path.basename(folder_name.strip('/\\'))
    print(f"[Agent Action] 📁 Creating folder: '{folder_name}'...")
    path = os.path.join(TARGET_DIRECTORY, folder_name)
    try:
        os.makedirs(path, exist_ok=True)
        return f"Success: Folder '{folder_name}' created."
    except Exception as e:
        return f"Error: {str(e)}"

def move_file(file_name: str, folder_name: str) -> str:
    """Moves a file into a specific category folder.
    
    Args:
        file_name (str): The name of the file to move.
        folder_name (str): The destination folder name.
    """
    clean_folder = os.path.basename(folder_name.strip('/\\'))
    clean_file = os.path.basename(file_name.strip('/\\'))
    
    print(f"[Agent Action] 🚚 Moving '{clean_file}' to '{clean_folder}/'...")
    src = os.path.join(TARGET_DIRECTORY, clean_file)
    dst = os.path.join(TARGET_DIRECTORY, clean_folder, clean_file)
    
    try:
        shutil.move(src, dst)
        return f"Success: Moved {clean_file} to {clean_folder}/"
    except Exception as e:
        return f"Error: {str(e)}"

def extract_fallback_tool_calls(content: str) -> list:
    """Extract tool calls if the model dumped JSON into the text content."""
    if not content:
        return []
    calls = []
    # Search for JSON blocks with a "name" key
    for match in re.finditer(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content):
        snippet = match.group(0)
        try:
            data = json.loads(snippet)
            if isinstance(data, dict) and "name" in data:
                args = data.get("parameters") or data.get("arguments") or {}
                calls.append({"function": {"name": data["name"], "arguments": args}})
        except Exception:
            continue
    return calls

def main():
    print("🤖 Starting the Local Smart Organizer Agent (Powered by Ollama)...\n")
    
    MODEL = "llama3.1"
    
    system_prompt = (
        f"You are an automated file organizer organizing '{TARGET_DIRECTORY}'.\n"
        "Rules:\n"
        "- Call list_files first.\n"
        "- Call create_folder to make 'Documents' and 'Images' folders if they do not exist.\n"
        "- Call move_file for each file: images (.png, .jpg) to 'Images', documents (.pdf, .docx, .txt, .py) to 'Documents'.\n"
        "- Call tools directly. Do not explain your actions in chat text.\n"
        "- Only say 'I am finished' when all files are moved."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Please organize the folder now."}
    ]

    while True:
        print("🤔 Agent is thinking...")
        try:
            response = ollama.chat(
                model=MODEL,
                messages=messages,
                tools=[list_files, create_folder, move_file]
            )
        except Exception as e:
            print(f"❌ Error communicating with Ollama: {e}")
            break

        message = response.get("message", {})
        messages.append(message)

        tool_calls = message.get("tool_calls")
        
        # If model printed JSON into chat text instead of native tool calls, extract it!
        if not tool_calls:
            fallback = extract_fallback_tool_calls(message.get("content", ""))
            if fallback:
                print("   [Info] Intercepted text-based JSON tool call from model.")
                tool_calls = fallback

        if not tool_calls:
            print("\n✅ Agent Finished! Final message:")
            print(message.get("content", ""))
            break
            
        for tool_call in tool_calls:
            tool_name = tool_call["function"]["name"]
            arguments = tool_call["function"]["arguments"]
            
            print(f"   [Debug] LLM attempting to call '{tool_name}' with args: {arguments}")
            
            result = ""
            try:
                if tool_name == "list_files":
                    result = list_files()
                    
                elif tool_name == "create_folder":
                    f_name = (
                        arguments.get('folder_name') 
                        or arguments.get('subdirectory') 
                        or arguments.get('name') 
                        or arguments.get('destination_path')
                        or arguments.get('directory')
                    )
                    if isinstance(f_name, list): f_name = str(f_name[0])
                    
                    if not f_name:
                        result = "Error: You must provide 'folder_name'."
                    else:
                        result = create_folder(f_name)
                        
                elif tool_name == "move_file":
                    f_name = arguments.get('file_name') or arguments.get('filename') or arguments.get('file')
                    d_name = (
                        arguments.get('folder_name') 
                        or arguments.get('destination_path')
                        or arguments.get('destination_folder') 
                        or arguments.get('destination') 
                        or arguments.get('subdirectory') 
                        or arguments.get('target_folder')
                    )
                    
                    if not f_name or not d_name:
                        values = [str(v) for v in arguments.values()]
                        if len(values) == 2:
                            if "." in values[0] and "." not in values[1]:
                                f_name, d_name = values[0], values[1]
                            elif "." in values[1] and "." not in values[0]:
                                f_name, d_name = values[1], values[0]

                    if not f_name or not d_name:
                        result = f"Error: missing arguments in {arguments}"
                    else:
                        result = move_file(f_name, d_name)
                else:
                    print(f"⚠️ Agent tried to call unknown tool: {tool_name}")
                    result = f"Error: Tool {tool_name} not found"
            except Exception as e:
                result = f"Error during execution: {str(e)}"
                
            print(f"   [Status] {result}")
            messages.append({
                "role": "tool",
                "content": str(result),
                "name": tool_name
            })

if __name__ == "__main__":
    main()
