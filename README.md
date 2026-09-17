# 🧠 AI Smart Organizer v2.0 (Content-Aware Agentic AI)

An intelligent, 100% private, local file organization system powered by **Ollama**, **Meta's Llama 3.1**, and **pypdf**. It reads inside your documents and code, follows natural language custom instructions, provides a visual plan review table before touching files, and includes an automated background watcher daemon.

---

## 👤 Author & Ownership
- **Developer & Owner:** **Infan Rahman**
- **Email:** [infanarahman4@gmail.com](mailto:infanarahman4@gmail.com)
- **GitHub:** [@infanrahman](https://github.com/infanrahman)

---

## ✨ What's New in v2.0

- **🔍 Deep Content Inspection:** The agent doesn't just read filenames anymore. It opens and reads the text inside `.pdf`, `.txt`, `.py`, `.json`, `.csv`, `.md`, `.log`, and `.html` files to understand what the document is actually about (e.g. distinguishing an Invoice from a Tax Form, Recipe, or Code project).
- **💬 Custom Natural Language Instructions:** A dedicated prompt bar in the GUI. You can type instructions like:
  > *"Put all tax files in Taxes, cooking recipes in Personal/Recipes, and Discord bots in Dev/Bots."*  
  The agent dynamically adapts its entire folder tree to your instructions!
- **📋 Visual Plan Review Table (Dry-Run Mode):**
  - Click **"🔍 1. Preview Plan"** to inspect a neat table displaying every file, its proposed category, and the AI's content-detected reasoning.
  - Click **"✅ 2. Approve & Move"** only when you are satisfied with the proposed plan.
- **⚡ Instant Mode & Background Auto-Cleaner:** Prefer automation? Click **"⚡ Instant Organize"** or enable **"Auto-Watch"** to let the background daemon clean your folders automatically.
- **↩️ One-Click Undo Rollback:** Reverses all moves and restores original paths if needed.
- **🔒 100% Local & Private:** Zero API costs, zero data sent to external servers.

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.10+**
- **[Ollama](https://ollama.com/)** running with `llama3.1`:
  ```powershell
  ollama run llama3.1
  ```

### 2. Installation
```powershell
git clone https://github.com/infanrahman/AI-SMART-ORGANIAZER.git
cd AI-SMART-ORGANIAZER
pip install -r requirements.txt
```

### 3. Launch the Application
```powershell
python app.py
```

---

## 🛠️ Architecture Flow

```
   Target Directory
         │
         ▼
 🔍 Content Extractor (PDFs, Code, Text)
         │
         ▼
 🧠 Ollama (Llama 3.1) + Custom User Rules
         │
         ▼
 📋 Plan Generator (Category + Reason)
         │
  ┌──────┴──────────────┐
  ▼                     ▼
Dry-Run Table     Instant / Auto-Watch
  │                     │
  ▼                     ▼
User Approval ────▶ Batch Move & Undo Log
```

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.  
Copyright (c) 2026 **Infan Rahman** (`infanarahman4@gmail.com`). All rights reserved.
