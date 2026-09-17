import os
import shutil
import json
import re
import time
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import ollama

MODEL = "llama3.1"
UNDO_FILE = "undo_history.json"

class SmartOrganizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Local AI Smart Organizer & Auto-Cleaner")
        self.root.geometry("820x640")
        self.root.minsize(700, 520)

        # State variables
        self.target_dir = tk.StringVar(value=os.path.abspath("messy_folder"))
        self.is_running = False
        self.watcher_enabled = tk.BooleanVar(value=False)
        self.watcher_interval = tk.IntVar(value=30)
        self.watcher_thread = None
        self.stop_watcher = threading.Event()

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
            text="🗂️ Local AI Smart Organizer", 
            font=("Segoe UI", 16, "bold")
        ).pack(side=tk.LEFT)

        self.status_badge = ttk.Label(
            header_frame, 
            text="⚪ Idle", 
            font=("Segoe UI", 10, "bold"),
            foreground="#666666"
        )
        self.status_badge.pack(side=tk.RIGHT, padx=5)

        # 2. Folder Selection Section
        folder_group = ttk.LabelFrame(main_frame, text=" 📂 Target Directory ", padding="10")
        folder_group.pack(fill=tk.X, pady=(0, 10))

        folder_entry = ttk.Entry(folder_group, textvariable=self.target_dir, font=("Consolas", 10))
        folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        browse_btn = ttk.Button(folder_group, text="Browse...", command=self._browse_folder)
        browse_btn.pack(side=tk.RIGHT)

        # 3. Action Buttons & Auto-Cleaner Controls
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 10))

        btn_frame = ttk.Frame(controls_frame)
        btn_frame.pack(side=tk.LEFT)

        self.run_btn = ttk.Button(
            btn_frame, 
            text="🚀 Organize Now", 
            command=self.start_manual_organize
        )
        self.run_btn.pack(side=tk.LEFT, padx=(0, 6))

        self.undo_btn = ttk.Button(
            btn_frame, 
            text="↩️ Undo Last Run", 
            command=self.undo_last_run
        )
        self.undo_btn.pack(side=tk.LEFT, padx=(0, 6))

        watcher_frame = ttk.LabelFrame(controls_frame, text=" 🕒 Background Auto-Cleaner ", padding="5")
        watcher_frame.pack(side=tk.RIGHT)

        self.watcher_chk = ttk.Checkbutton(
            watcher_frame, 
            text="Enable Auto-Watch", 
            variable=self.watcher_enabled,
            command=self._on_watcher_toggle
        )
        self.watcher_chk.pack(side=tk.LEFT, padx=5)

        ttk.Label(watcher_frame, text="Every:").pack(side=tk.LEFT, padx=(5, 2))
        interval_spin = ttk.Spinbox(
            watcher_frame, 
            from_=5, 
            to=3600, 
            textvariable=self.watcher_interval, 
            width=5
        )
        interval_spin.pack(side=tk.LEFT)
        ttk.Label(watcher_frame, text="sec").pack(side=tk.LEFT, padx=(2, 5))

        # 4. Activity Log Box
        log_group = ttk.LabelFrame(main_frame, text=" 📜 Live Activity & Agent Reasoning ", padding="10")
        log_group.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(
            log_group, 
            wrap=tk.WORD, 
            font=("Consolas", 9), 
            bg="#1e1e1e", 
            fg="#dcdcdc", 
            insertbackground="white",
            relief=tk.FLAT
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(log_group, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

        bottom_bar = ttk.Frame(main_frame)
        bottom_bar.pack(fill=tk.X, pady=(6, 0))
        clear_btn = ttk.Button(bottom_bar, text="Clear Log", command=self._clear_log)
        clear_btn.pack(side=tk.RIGHT)

        self.log("Ready. Select any folder and click 'Organize Now' or enable 'Auto-Watch'.")

    # --- UI Helpers ---
    def _browse_folder(self):
        selected = filedialog.askdirectory(initialdir=self.target_dir.get())
        if selected:
            self.target_dir.set(os.path.abspath(selected))
            self.log(f"Selected directory: {self.target_dir.get()}")

    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.root.after(0, self._append_log_text, f"[{timestamp}] {message}\n")

    def _append_log_text(self, text):
        self.log_text.insert(tk.END, text)
        self.log_text.see(tk.END)

    def _clear_log(self):
        self.log_text.delete(1.0, tk.END)

    def set_status(self, text, color):
        self.root.after(0, lambda: self.status_badge.config(text=text, foreground=color))

    # --- Option C: Background Watcher ---
    def _on_watcher_toggle(self):
        if self.watcher_enabled.get():
            sec = self.watcher_interval.get()
            self.set_status(f"🟢 Watching ({sec}s)", "#2e7d32")
            self.log(f"🕒 Auto-Cleaner enabled for '{self.target_dir.get()}' (check every {sec}s).")
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
                            self.log(f"🕒 [Auto-Cleaner] Found {len(loose_files)} loose file(s). Auto-organizing...")
                            self._run_agent_thread()

    def _get_loose_files(self, directory):
        """Returns safe list of loose files, ignoring system/temp files."""
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

    # --- Option A: Manual Organize ---
    def start_manual_organize(self):
        if self.is_running:
            messagebox.showinfo("Busy", "Organizer is already running!")
            return
        self._run_agent_thread()

    def _run_agent_thread(self):
        self.is_running = True
        self.run_btn.config(state=tk.DISABLED)
        self.set_status("🤖 AI Organizing...", "#1565c0")
        thread = threading.Thread(target=self._agent_worker, daemon=True)
        thread.start()

    # --- High-Performance Agent Engine ---
    def _agent_worker(self):
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

        self.log(f"📋 Found {len(loose_files)} loose file(s) to organize in '{target}'.")
        self.log(f"🚀 Sending file list to {MODEL} for batch categorization...")

        moves_recorded = []

        # Tool 1: High-efficiency batch move tool
        def organize_category(category_name: str, files: list) -> str:
            """Creates a category folder and moves the specified list of files into it.
            
            Args:
                category_name: The destination category (e.g. 'Documents', 'Images', 'Installers', 'Archives', 'Code').
                files: List of file names to move into this category folder.
            """
            clean_cat = os.path.basename(str(category_name).strip('/\\'))
            cat_dir = os.path.join(target, clean_cat)
            os.makedirs(cat_dir, exist_ok=True)
            
            if isinstance(files, str):
                files = [f.strip() for f in files.split(",") if f.strip()]
            elif not isinstance(files, list):
                files = [str(files)]

            moved = 0
            for fname in files:
                clean_f = os.path.basename(str(fname).strip('/\\'))
                src = os.path.join(target, clean_f)
                dst = os.path.join(cat_dir, clean_f)
                if os.path.exists(src) and not os.path.isdir(src):
                    try:
                        shutil.move(src, dst)
                        moves_recorded.append({"src": src, "dst": dst, "file": clean_f, "folder": clean_cat})
                        moved += 1
                    except Exception as ex:
                        self.log(f"   ⚠️ Could not move '{clean_f}': {ex}")

            self.log(f"📦 [Batch Action] Sorted {moved} file(s) into '{clean_cat}/'")
            return f"Success: Moved {moved} files into '{clean_cat}/'"

        # Tool 2: Single file move fallback
        def move_file(file_name: str, folder_name: str) -> str:
            """Moves a single file into a folder."""
            clean_folder = os.path.basename(str(folder_name).strip('/\\'))
            clean_file = os.path.basename(str(file_name).strip('/\\'))
            src = os.path.join(target, clean_file)
            dst = os.path.join(target, clean_folder, clean_file)
            os.makedirs(os.path.join(target, clean_folder), exist_ok=True)
            try:
                if os.path.exists(src):
                    shutil.move(src, dst)
                    moves_recorded.append({"src": src, "dst": dst, "file": clean_file, "folder": clean_folder})
                    self.log(f"🚚 [Agent Action] Moved '{clean_file}' -> '{clean_folder}/'")
                    return f"Success: Moved {clean_file}"
                return f"File not found: {clean_file}"
            except Exception as e:
                return f"Error: {str(e)}"

        tools_list = [organize_category, move_file]

        system_prompt = (
            "You are an expert file organizer.\n"
            "Your goal is to organize all files provided by the user into logical category folders.\n"
            "Categories to consider:\n"
            "- Documents (pdf, docx, txt, xlsx, pptx, csv)\n"
            "- Images (png, jpg, jpeg, gif, svg, webp)\n"
            "- Installers (exe, msi, dmg, iso)\n"
            "- Archives (zip, rar, 7z, tar, gz)\n"
            "- Code (py, js, html, css, cpp, json)\n"
            "- Audio & Video (mp3, wav, mp4, mkv)\n\n"
            "INSTRUCTION: Use the 'organize_category' tool to organize files in batches. "
            "Group every single file from the list into its appropriate category."
        )

        user_prompt = (
            f"Here are the {len(loose_files)} loose files to organize:\n"
            f"{json.dumps(loose_files, indent=2)}\n\n"
            "Please call 'organize_category' for each category to group and move all these files now."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        turns = 0
        max_turns = 10

        while turns < max_turns:
            turns += 1
            self.log("🤔 Agent is analyzing and sorting...")
            try:
                response = ollama.chat(
                    model=MODEL,
                    messages=messages,
                    tools=tools_list
                )
            except Exception as e:
                self.log(f"❌ Ollama connection error: {str(e)}")
                break

            message = response.get("message", {})
            messages.append(message)

            tool_calls = message.get("tool_calls")
            if not tool_calls:
                fallback = self._extract_fallback_tool_calls(message.get("content", ""))
                if fallback:
                    tool_calls = fallback

            if not tool_calls:
                self.log(f"✅ Agent Finished: {message.get('content', 'All files processed.')}")
                break

            for tool_call in tool_calls:
                t_name = tool_call["function"]["name"]
                args = tool_call["function"]["arguments"]

                result = ""
                try:
                    if t_name == "organize_category":
                        cat = (
                            args.get('category_name') 
                            or args.get('folder_name') 
                            or args.get('category') 
                            or args.get('name')
                        )
                        f_list = (
                            args.get('files') 
                            or args.get('file_names') 
                            or args.get('file_list') 
                            or []
                        )
                        if cat:
                            result = organize_category(cat, f_list)
                        else:
                            result = "Error: missing category_name"

                    elif t_name == "move_file":
                        f_name = args.get('file_name') or args.get('filename') or args.get('file')
                        d_name = args.get('folder_name') or args.get('destination_path') or args.get('destination')
                        if f_name and d_name:
                            result = move_file(f_name, d_name)
                        else:
                            result = f"Error: missing args in {args}"
                    else:
                        result = f"Tool {t_name} not found"
                except Exception as ex:
                    result = f"Error: {str(ex)}"

                messages.append({
                    "role": "tool",
                    "content": str(result),
                    "name": t_name
                })

        if moves_recorded:
            self._save_undo_history(moves_recorded)
            self.log(f"💾 Completed! Successfully moved {len(moves_recorded)} file(s). Saved to Undo history.")
        else:
            self.log("ℹ️ No files were moved.")

        self._finish_agent_run()

    def _extract_fallback_tool_calls(self, content):
        if not content: return []
        calls = []
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

    def _save_undo_history(self, moves):
        try:
            with open(UNDO_FILE, "w", encoding="utf-8") as f:
                json.dump(moves, f, indent=2)
        except Exception as e:
            self.log(f"⚠️ Could not save undo history: {e}")

    # --- Safety Feature: Undo Last Run ---
    def undo_last_run(self):
        if self.is_running:
            messagebox.showinfo("Busy", "Cannot undo while an organizing job is running.")
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
        messagebox.showinfo("Undo Complete", f"Successfully restored {restored_count} file(s) to their original locations.")

    def _finish_agent_run(self):
        self.is_running = False
        self.root.after(0, lambda: self.run_btn.config(state=tk.NORMAL))
        if self.watcher_enabled.get():
            sec = self.watcher_interval.get()
            self.set_status(f"🟢 Watching ({sec}s)", "#2e7d32")
        else:
            self.set_status("⚪ Idle", "#666666")

def main():
    root = tk.Tk()
    app = SmartOrganizerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
