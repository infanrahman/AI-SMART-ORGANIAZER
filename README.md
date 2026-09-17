# 🗂️ AI Smart Organizer (Local Agentic AI)

An intelligent, 100% private, local file organization tool powered by **Ollama** and **Meta's Llama 3.1**. It combines a clean desktop GUI with an automated background watcher daemon and a one-click undo rollback mechanism.

---

## ✨ Features

- **🔒 100% Local & Private:** Runs entirely on your own computer using Ollama and Llama 3.1. Zero API costs, zero data sent to external servers.
- **⚡ High-Performance Batch Categorization:** Employs an agentic ReAct loop that plans and categorizes entire folders in batches, organizing dozens of files in seconds.
- **🖥️ Desktop GUI (Option A):** Includes a native folder picker so you can organize any folder (Downloads, Desktop, etc.) on demand.
- **🕒 Background Auto-Cleaner Daemon (Option C):** An automatic background watcher thread that monitors your chosen directory and auto-organizes newly downloaded files at custom intervals.
- **↩️ One-Click Undo Rollback:** Keeps a local manifest of all moves so you can reverse the organization with a single click.
- **🛡️ Defensive AI Engineering:** Built-in smart routing and fallback JSON extractors to safeguard against LLM hallucinations and argument formatting inconsistencies.

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.10+**
- **[Ollama](https://ollama.com/)** installed and running on your system.
- Download the Llama 3.1 model:
  ```powershell
  ollama run llama3.1
  ```
  *(Type `/bye` to exit the chat prompt once the download completes)*

### 2. Installation
Clone this repository and install dependencies:
```powershell
git clone https://github.com/infanrahman/AI-SMART-ORGANIAZER.git
cd AI-SMART-ORGANIAZER
pip install -r requirements.txt
```

### 3. Running the Desktop Application
To launch the full desktop app with GUI, background watcher, and undo controls:
```powershell
python app.py
```

### 4. Running the CLI Script (Optional)
To run the terminal-based organizer:
```powershell
python organizer.py
```

---

## 🛠️ Architecture

```
User Action (GUI or Watcher Daemon)
               │
               ▼
      Directory Pre-Scan (Python)
               │
               ▼
     Llama 3.1 Prompting (Ollama)
               │
               ▼
         Agent Reasoning
 (Decides categories: Documents, Images, etc.)
               │
               ▼
     Tool Execution (Smart Router)
               │
        ┌──────┴──────┐
        ▼             ▼
   Batch Moves     Undo Log
```

---

## 📄 License
MIT License
