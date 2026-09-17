"""
AI Smart Organizer v2.0
Owned and Developed by Infan Rahman (infanarahman4@gmail.com)
GitHub: https://github.com/infanrahman/AI-SMART-ORGANIAZER
"""

import os
import shutil
import json
import re
import time
import hashlib
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import ollama

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

MODEL = "llama3.1"
UNDO_FILE = "undo_history.json"

# --- Content Inspection Helper ---
def extract_file_snippet(file_path: str, max_chars: int = 350) -> str:
    """Extracts a readable text preview from text documents, code, and PDFs."""
    ext = os.path.splitext(file_path)[1].lower()
    
    # 1. PDF Documents
    if ext == ".pdf":
        if not PYPDF_AVAILABLE:
            return "[PDF Document - content extraction unavailable]"
        try:
            reader = pypdf.PdfReader(file_path)
            if len(reader.pages) > 0:
                text = reader.pages[0].extract_text() or ""
                clean_text = " ".join(text.split())
                return clean_text[:max_chars] if clean_text else "[PDF with scanned image/no selectable text]"
            return "[Empty PDF]"
        except Exception as e:
            return f"[PDF read error: {str(e)[:50]}]"

    # 2. Text and Code files
    text_exts = {
        '.txt', '.md', '.py', '.js', '.ts', '.html', '.css', '.json',
        '.csv', '.xml', '.log', '.sql', '.yaml', '.yml', '.ini', '.sh'
    }
    if ext in text_exts:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(max_chars)
                clean_content = " ".join(content.split())
                return clean_content if clean_content else "[Empty text file]"
        except Exception as e:
            return f"[Text read error: {str(e)[:50]}]"

    # 3. Media & Binaries
    if ext in {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico'}:
        size_kb = os.path.getsize(file_path) // 1024
        return f"[Image file - {size_kb} KB]"
    if ext in {'.zip', '.rar', '.7z', '.tar', '.gz'}:
        return "[Compressed Archive]"
    if ext in {'.exe', '.msi', '.dmg', '.iso'}:
        return "[Software Installer/Executable]"

    return f"[Binary/Data file: {ext}]"

def compute_sha256(file_path: str) -> str:
    """Compute SHA-256 hash to detect duplicate files."""
    try:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""

# --- Main Application GUI ---
class AdvancedOrganizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Smart Organizer v2.0 - Content-Aware & Auto-Cleaner")
        self.root.geometry("900x700")
        self.root.minsize(750, 560)

        # State variables
        self.target_dir = tk.StringVar(value=os.path.abspath("messy_folder"))
        self.custom_prompt = tk.StringVar(value="")
        self.is_running = False
        self.watcher_enabled = tk.BooleanVar(value=False)
        self.watcher_interval = tk.IntVar(value=30)
        self.watcher_thread = None
        self.stop_watcher = threading.Event()

        # Staged plan for approval
        self.staged_plan = []  # List of {"file": ..., "category": ..., "reason": ...}

        self._build_ui()
        self._start_watcher_daemon()

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")

        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(
            header_frame, 
            text="🧠 AI Smart Organizer v2.0", 
            font=("Segoe UI", 16, "bold")
        ).pack(side=tk.LEFT)

        self.status_badge = ttk.Label(
            header_frame, 
            text="⚪ Idle", 
            font=("Segoe UI", 10, "bold"),
            foreground="#666666"
        )
        self.status_badge.pack(side=tk.RIGHT, padx=5)

        # 2. Target Directory Selection
        folder_group = ttk.LabelFrame(main_frame, text=" 📂 Target Directory ", padding="8")
        folder_group.pack(fill=tk.X, pady=(0, 8))

        folder_entry = ttk.Entry(folder_group, textvariable=self.target_dir, font=("Consolas", 10))
        folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        browse_btn = ttk.Button(folder_group, text="Browse...", command=self._browse_folder)
        browse_btn.pack(side=tk.RIGHT)

        # 3. Custom Natural Language Instruction Box
        prompt_group = ttk.LabelFrame(main_frame, text=" 💬 Custom AI Instructions (Optional) ", padding="8")
        prompt_group.pack(fill=tk.X, pady=(0, 8))

        prompt_entry = ttk.Entry(
            prompt_group, 
            textvariable=self.custom_prompt, 
            font=("Segoe UI", 9)
        )
        prompt_entry.pack(fill=tk.X)
        ttk.Label(
            prompt_group, 
            text="💡 Example: 'Put tax files in Taxes, recipes in Cooking, and group code projects by language.'", 
            font=("Segoe UI", 8), 
            foreground="#666666"
        ).pack(anchor=tk.W, pady=(3, 0))

        # 4. Action Buttons & Auto-Cleaner Controls
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 10))

        btn_frame = ttk.Frame(controls_frame)
        btn_frame.pack(side=tk.LEFT)

        self.preview_btn = ttk.Button(
            btn_frame, 
            text="🔍 1. Preview Plan", 
            command=self.start_preview_plan
        )
        self.preview_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.execute_btn = ttk.Button(
            btn_frame, 
            text="✅ 2. Approve & Move", 
            command=self.execute_staged_plan,
            state=tk.DISABLED
        )
        self.execute_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.instant_btn = ttk.Button(
            btn_frame, 
            text="⚡ Instant Organize", 
            command=self.start_instant_organize
        )
        self.instant_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.undo_btn = ttk.Button(
            btn_frame, 
            text="↩️ Undo Last", 
            command=self.undo_last_run
        )
        self.undo_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Auto-Cleaner Daemon Settings
        watcher_frame = ttk.LabelFrame(controls_frame, text=" 🕒 Auto-Cleaner ", padding="5")
        watcher_frame.pack(side=tk.RIGHT)

        self.watcher_chk = ttk.Checkbutton(
            watcher_frame, 
            text="Auto-Watch", 
            variable=self.watcher_enabled,
            command=self._on_watcher_toggle
        )
        self.watcher_chk.pack(side=tk.LEFT, padx=3)

        ttk.Label(watcher_frame, text="Every:").pack(side=tk.LEFT)
        interval_spin = ttk.Spinbox(
            watcher_frame, 
            from_=5, 
            to=3600, 
            textvariable=self.watcher_interval, 
            width=4
        )
        interval_spin.pack(side=tk.LEFT, padx=2)
        ttk.Label(watcher_frame, text="s").pack(side=tk.LEFT)

        # 5. Tabbed View: Plan Preview Table vs. Live Console Log
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Plan Table
        table_frame = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(table_frame, text=" 📋 Plan Preview Table ")

        columns = ("file", "category", "reason")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("file", text="File Name")
        self.tree.heading("category", text="Proposed Category")
        self.tree.heading("reason", text="Detected Content / Reasoning")

        self.tree.column("file", width=220, anchor=tk.W)
        self.tree.column("category", width=140, anchor=tk.W)
        self.tree.column("reason", width=420, anchor=tk.W)

        tree_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Tab 2: Activity Log
        log_frame = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(log_frame, text=" 📜 Live Activity Log ")

        self.log_text = tk.Text(
            log_frame, 
            wrap=tk.WORD, 
            font=("Consolas", 9), 
            bg="#1e1e1e", 
            fg="#dcdcdc", 
            insertbackground="white",
            relief=tk.FLAT
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=log_scroll.set)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Bottom Clear Log Bar & Author Credit
        bottom_bar = ttk.Frame(main_frame)
        bottom_bar.pack(fill=tk.X, pady=(5, 0))
        ttk.Label(
            bottom_bar, 
            text="Developed & Owned by Infan Rahman (infanarahman4@gmail.com)", 
            font=("Segoe UI", 8), 
            foreground="#888888"
        ).pack(side=tk.LEFT)
        clear_btn = ttk.Button(bottom_bar, text="Clear Log", command=self._clear_log)
        clear_btn.pack(side=tk.RIGHT)

        self.log("AI Smart Organizer v2.0 ready. Supports Content Inspection and Custom Prompts.")

    # --- UI Helpers ---
    def _browse_folder(self):
        selected = filedialog.askdirectory(initialdir=self.target_dir.get())
        if selected:
            self.target_dir.set(os.path.abspath(selected))
            self.log(f"Target directory set to: {self.target_dir.get()}")
            self._clear_plan_table()

    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.root.after(0, self._append_log_text, f"[{timestamp}] {message}\n")

    def _append_log_text(self, text):
        self.log_text.insert(tk.END, text)
        self.log_text.see(tk.END)

    def _clear_log(self):
        self.log_text.delete(1.0, tk.END)

    def _clear_plan_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.staged_plan = []
        self.execute_btn.config(state=tk.DISABLED)

    def set_status(self, text, color):
        self.root.after(0, lambda: self.status_badge.config(text=text, foreground=color))

    # --- Background Auto-Cleaner ---
    def _on_watcher_toggle(self):
        if self.watcher_enabled.get():
            sec = self.watcher_interval.get()
            self.set_status(f"🟢 Watching ({sec}s)", "#2e7d32")
            self.log(f"🕒 Auto-Cleaner activated for '{self.target_dir.get()}' (every {sec}s).")
        else:
            self.set_status("⚪ Idle", "#666666")
            self.log("⏸️ Auto-Cleaner paused.")

    def _start_watcher_daemon(self):
        self.watcher_thread = threading.Thread(target=self._watcher_loop, daemon=True)
        self.watcher_thread.start()

    def _watcher_loop(self):
        while not self.stop_watcher.is_set():
            time.sleep(1)
            if self.watcher_enabled.get() and not self.is_running:
                interval = max(3, self.watcher_interval.get())
                for _ in range(interval):
                    if not self.watcher_enabled.get() or self.stop_watcher.is_set():
                        break
                    time.sleep(1)

                if self.watcher_enabled.get() and not self.is_running:
                    target = self.target_dir.get()
                    if os.path.exists(target):
                        loose_files = self._get_loose_files(target)
                        if loose_files:
                            self.log(f"🕒 [Auto-Cleaner] Found {len(loose_files)} loose files. Auto-organizing...")
                            self._run_agent_thread(auto_execute=True)

    def _get_loose_files(self, directory):
        if not os.path.isdir(directory):
            return []
        ignored_exts = ('.tmp', '.crdownload', '.part', '.ini', '.lnk')
        try:
            return [
                f for f in os.listdir(directory)
                if os.path.isfile(os.path.join(directory, f))
                and not f.startswith(".")
                and not f.lower().endswith(ignored_exts)
            ]
        except Exception:
            return []

    # --- Action Triggers ---
    def start_preview_plan(self):
        """Analyze files & content to create a plan for user review (Dry-run)."""
        if self.is_running:
            messagebox.showinfo("Busy", "Agent is currently busy.")
            return
        self._run_agent_thread(auto_execute=False)

    def start_instant_organize(self):
        """Analyze files & content and move them immediately."""
        if self.is_running:
            messagebox.showinfo("Busy", "Agent is currently busy.")
            return
        self._run_agent_thread(auto_execute=True)

    def _run_agent_thread(self, auto_execute: bool):
        self.is_running = True
        self.preview_btn.config(state=tk.DISABLED)
        self.instant_btn.config(state=tk.DISABLED)
        self.execute_btn.config(state=tk.DISABLED)
        self.set_status("🤖 AI Analyzing...", "#1565c0")
        
        thread = threading.Thread(
            target=self._agent_worker, 
            args=(auto_execute,), 
            daemon=True
        )
        thread.start()

    # --- Content-Aware AI Engine ---
    def _agent_worker(self, auto_execute: bool):
        target = self.target_dir.get()
        if not os.path.isdir(target):
            self.log(f"❌ Folder not found: {target}")
            self._finish_agent_run()
            return

        loose_files = self._get_loose_files(target)
        if not loose_files:
            self.log(f"ℹ️ Folder is already clean! No loose files found in '{target}'.")
            self._finish_agent_run()
            return

        self.log(f"🔍 Reading content snippets from {len(loose_files)} file(s)...")

        # Extract content previews for the LLM
        file_dossiers = []
        for fname in loose_files:
            full_path = os.path.join(target, fname)
            snippet = extract_file_snippet(full_path)
            file_dossiers.append({
                "filename": fname,
                "content_preview": snippet
            })

        self.log(f"🧠 Prompting {MODEL} with file content and custom rules...")

        # Structured planning tool
        staged_results = []

        def propose_organization_plan(categories: list) -> str:
            """Proposes categories and file assignments based on content analysis.
            
            Args:
                categories: A list of category objects, each containing:
                            'category_name' (str) - Name of the category folder
                            'files' (list[str]) - List of file names in this category
                            'reason' (str) - Brief explanation of why these files belong here
            """
            for cat_entry in categories:
                cat_name = os.path.basename(str(cat_entry.get("category_name", "General")).strip('/\\'))
                f_list = cat_entry.get("files", [])
                reason = cat_entry.get("reason", "Content match")
                if isinstance(f_list, str): f_list = [f_list]

                for f in f_list:
                    clean_f = os.path.basename(str(f).strip('/\\'))
                    staged_results.append({
                        "file": clean_f,
                        "category": cat_name,
                        "reason": reason
                    })
            return f"Received plan for {len(staged_results)} files."

        custom_rules = self.custom_prompt.get().strip()
        custom_rule_text = f"\nUser Custom Rules: '{custom_rules}'\n" if custom_rules else ""

        system_prompt = (
            "You are an expert content-aware file organizer.\n"
            "You will be given a list of files along with their extracted text content previews.\n"
            "Analyze the text inside each file and categorize them into logical folders.\n"
            f"{custom_rule_text}\n"
            "Common categories: Documents, Invoices, Financial, Code, Personal, Recipes, Images, Archives, Installers.\n"
            "INSTRUCTION: Call 'propose_organization_plan' with the list of categories, files, and brief reasons."
        )

        user_prompt = (
            f"Here are the {len(file_dossiers)} files with their content previews:\n"
            f"{json.dumps(file_dossiers, indent=2)}\n\n"
            "Call 'propose_organization_plan' to categorize all these files."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = ollama.chat(
                model=MODEL,
                messages=messages,
                tools=[propose_organization_plan]
            )
            message = response.get("message", {})
            tool_calls = message.get("tool_calls") or []

            # If tool calls are present, execute the planning tool
            for tc in tool_calls:
                args = tc.get("function", {}).get("arguments", {})
                cats = args.get("categories") or args.get("plan") or []
                if isinstance(cats, list):
                    propose_organization_plan(cats)

            # Fallback JSON extractor if model printed JSON into chat text
            if not staged_results:
                raw_text = message.get("content", "")
                staged_results = self._extract_fallback_plan(raw_text, loose_files)

        except Exception as e:
            self.log(f"❌ Ollama Error: {str(e)}")

        # Fallback: if AI missed any files, place them in a default category
        handled_files = {item["file"] for item in staged_results}
        for f in loose_files:
            if f not in handled_files:
                ext = os.path.splitext(f)[1].upper().replace('.', '') or 'Other'
                staged_results.append({
                    "file": f,
                    "category": f"{ext}_Files",
                    "reason": "Categorized by extension fallback"
                })

        self.staged_plan = staged_results

        # Update GUI Table
        self.root.after(0, self._populate_plan_table, staged_results)

        if auto_execute:
            self.log("⚡ Auto-Executing organization plan...")
            self._execute_moves(staged_results, target)
        else:
            self.log(f"📋 Generated plan for {len(staged_results)} files. Review in table and click 'Approve & Move'.")
            self.root.after(0, lambda: self.notebook.select(0)) # Switch to Table tab

        self._finish_agent_run()

    def _extract_fallback_plan(self, text, all_files):
        """Extract plan if model outputted raw JSON into chat."""
        plan = []
        try:
            for match in re.finditer(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text):
                data = json.loads(match.group(0))
                if "category_name" in data and "files" in data:
                    cat = data["category_name"]
                    files = data.get("files", [])
                    reason = data.get("reason", "Extracted from content")
                    if isinstance(files, str): files = [files]
                    for f in files:
                        plan.append({"file": f, "category": cat, "reason": reason})
        except Exception:
            pass
        return plan

    def _populate_plan_table(self, plan):
        self._clear_plan_table()
        self.staged_plan = plan
        for item in plan:
            self.tree.insert("", tk.END, values=(item["file"], item["category"], item["reason"]))
        if plan:
            self.execute_btn.config(state=tk.NORMAL)

    # --- Plan Execution ---
    def execute_staged_plan(self):
        if not self.staged_plan:
            messagebox.showinfo("Empty", "No staged plan to execute. Click 'Preview Plan' first.")
            return

        target = self.target_dir.get()
        self.execute_btn.config(state=tk.DISABLED)
        self.log(f"🚀 Executing plan for {len(self.staged_plan)} file(s)...")

        threading.Thread(
            target=self._execute_moves, 
            args=(self.staged_plan, target), 
            daemon=True
        ).start()

    def _execute_moves(self, plan, target):
        moves_recorded = []
        moved_count = 0

        for item in plan:
            fname = item["file"]
            cat_name = os.path.basename(item["category"].strip('/\\'))
            src = os.path.join(target, fname)
            cat_dir = os.path.join(target, cat_name)
            dst = os.path.join(cat_dir, fname)

            if os.path.exists(src) and not os.path.isdir(src):
                try:
                    os.makedirs(cat_dir, exist_ok=True)
                    shutil.move(src, dst)
                    moves_recorded.append({
                        "src": src, 
                        "dst": dst, 
                        "file": fname, 
                        "folder": cat_name
                    })
                    moved_count += 1
                    self.log(f"🚚 Moved '{fname}' -> '{cat_name}/'")
                except Exception as ex:
                    self.log(f"   ⚠️ Error moving '{fname}': {ex}")

        if moves_recorded:
            self._save_undo_history(moves_recorded)
            self.log(f"💾 Done! Successfully organized {moved_count} file(s). Saved to Undo history.")
            self.root.after(0, self._clear_plan_table)
            self.root.after(0, lambda: messagebox.showinfo("Complete", f"Successfully organized {moved_count} file(s)!"))
        else:
            self.log("ℹ️ No files were moved.")

    def _save_undo_history(self, moves):
        try:
            with open(UNDO_FILE, "w", encoding="utf-8") as f:
                json.dump(moves, f, indent=2)
        except Exception as e:
            self.log(f"⚠️ Could not save undo history: {e}")

    # --- Safety Undo ---
    def undo_last_run(self):
        if self.is_running:
            messagebox.showinfo("Busy", "Cannot undo while organizer is active.")
            return

        if not os.path.exists(UNDO_FILE):
            messagebox.showinfo("Undo", "No previous organization history found.")
            return

        try:
            with open(UNDO_FILE, "r", encoding="utf-8") as f:
                moves = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read undo file: {e}")
            return

        if not moves:
            messagebox.showinfo("Undo", "Undo history is empty.")
            return

        restored_count = 0
        self.log(f"↩️ Starting Undo for {len(moves)} file(s)...")

        for item in reversed(moves):
            src, dst = item["src"], item["dst"]
            if os.path.exists(dst):
                try:
                    shutil.move(dst, src)
                    self.log(f"   Restored: '{item['file']}'")
                    restored_count += 1
                except Exception as ex:
                    self.log(f"   ⚠️ Failed to restore '{item['file']}': {ex}")

        os.remove(UNDO_FILE)
        self.log(f"✅ Undo complete! Restored {restored_count} file(s).")
        messagebox.showinfo("Undo Complete", f"Successfully restored {restored_count} file(s) to original locations.")

    def _finish_agent_run(self):
        self.is_running = False
        self.root.after(0, lambda: self.preview_btn.config(state=tk.NORMAL))
        self.root.after(0, lambda: self.instant_btn.config(state=tk.NORMAL))
        if self.watcher_enabled.get():
            sec = self.watcher_interval.get()
            self.set_status(f"🟢 Watching ({sec}s)", "#2e7d32")
        else:
            self.set_status("⚪ Idle", "#666666")

def main():
    root = tk.Tk()
    app = AdvancedOrganizerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
