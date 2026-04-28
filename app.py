import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog, filedialog
import threading
import json
import os
import re
import time
import copy
import uuid
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright

# --- CONFIG & STYLING ---
CONFIG_FILE = "config.json"
BG      = "#0f172a"
CARD    = "#1e293b"
ACCENT  = "#38bdf8"
TEXT    = "#f1f5f9"
MUTED   = "#94a3b8"
SUCCESS = "#10b981"
WARN    = "#f59e0b"
DANGER  = "#ef4444"

COLS = ("RIN", "Relation", "Sex", "Living", "Given Names", "Family Names",
        "Birth Year", "Birth Location", "Death Year", "Death Location")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"username": "", "password": "", "profile": "1"}

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f)

def json_to_rows(data):
    rows = []
    for r in data:
        rows.append([
            str(r.get("rin", "")),
            r.get("relation", "") or "",
            r.get("sex", "") or "",
            r.get("living", "") or "",
            r.get("given_names", "") or "",
            r.get("family_names", "") or "",
            str(r.get("birth_year", "") or ""),
            r.get("birth_location", "") or "",
            str(r.get("death_year", "") or ""),
            r.get("death_location", "") or "",
        ])
    return rows

# --- AUTOMATION LOGIC ---

def fill_form_logic(fid, url, username, password, rows, status_cb, worker_idx, profile_id):
    def log(msg): status_cb(f"[{fid}] {msg}")

    try:
        with sync_playwright() as p:
            session_dir = os.path.abspath(f"fs_session_prof_{profile_id}_{worker_idx}")
            log(f"🚀 Worker {worker_idx} starting...")
            
            browser_context = p.chromium.launch_persistent_context(
                session_dir, headless=False, slow_mo=10,
                viewport={'width': 1280, 'height': 650},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                args=['--disable-blink-features=AutomationControlled']
            )
            page = browser_context.pages[0]
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            log("🌐 Opening URL...")
            page.goto(url, wait_until="commit")
            
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except:
                pass
            time.sleep(2)
            
            # Login check
            login_needed = False
            try:
                if "login" in page.url or page.locator('#userName, #username').is_visible(timeout=1500):
                    login_needed = True
            except:
                pass

            if login_needed:
                log("✍️ Auto-login...")
                try:
                    page.fill('#userName, #username', username, timeout=8000)
                    page.fill('#password', password)
                    page.click('button[type="submit"], #login')
                    time.sleep(8)
                except: 
                    log("⚠️ Login screen active. Finish manually...")
                    time.sleep(15)

            log("🔍 Scanning form...")
            try:
                page.wait_for_selector('input[placeholder*="Given Name"]', timeout=30000)
                log("✅ Ready.")
            except:
                log("❌ Form not found.")
                browser_context.close()
                return

            data_map = {str(r[0]): r for r in rows}
            filled_rins = set()
            
            for p_idx in range(50):
                anchors = page.locator('input[placeholder*="Given Name"]').all()
                if not anchors: 
                    break
                
                log(f"📄 Page {p_idx+1}: Filling rows...")
                
                for inp in anchors:
                    try:
                        container = inp.locator('xpath=ancestor::div[role="row"][1] | ancestor::tr[1] | ancestor::div[contains(@class,"row")][1]').first
                        if not container.count():
                            continue
                        
                        # Use text_content for max speed (no reflow)
                        combined_text = container.text_content()
                        nums = re.findall(r'\d+', combined_text)
                        
                        rin = None
                        for n in nums:
                            if n in data_map and n not in filled_rins:
                                rin = n
                                break
                        
                        if not rin:
                            continue

                        r_data = data_map[rin]
                        _, rel, sex, living, given, family, b_yr, b_loc, d_yr, d_loc = r_data
                        
                        # RELATION
                        if rel:
                            r_field = container.locator('input[placeholder*="Relation"]').first
                            if r_field.count() == 0:
                                r_field = container.locator('input').nth(0)
                            if r_field.count():
                                r_field.fill(str(rel))
                                r_field.press("Tab")

                        # SEX
                        if sex:
                            s_field = container.locator('select, [aria-label*="Sex"]').first
                            if s_field.count():
                                try:
                                    s_field.select_option(label=sex)
                                except:
                                    pass

                        # NAMES & VITALS
                        inp.fill(str(given or ""))
                        if family:
                            f_field = container.locator('input[placeholder*="Family"]').first
                            if f_field.count():
                                f_field.fill(str(family))
                        
                        if b_yr:
                            by_field = container.locator('input[placeholder*="Birth Date"]').first
                            if by_field.count():
                                by_field.fill(str(b_yr))
                        
                        if b_loc:
                            bl_field = container.locator('input[placeholder*="Ward"], input[placeholder*="Place"]').first
                            if bl_field.count():
                                bl_field.fill(str(b_loc))
                                page.keyboard.press("Enter")
                        
                        # LIVING
                        if living:
                            l_val = "Yes" if str(living).lower() == "yes" else "No"
                            l_field = container.locator('[aria-label*="Living"], select').last
                            if l_field.count():
                                try:
                                    l_field.select_option(label=l_val)
                                except:
                                    pass

                        if str(living).lower() == "no" and d_yr:
                            dy_field = container.locator('input[placeholder*="Death Date"]').first
                            if dy_field.count():
                                dy_field.fill(str(d_yr))

                        filled_rins.add(rin)
                    except:
                        pass

                # SAVE
                log("💾 Saving page...")
                page.evaluate("window.scrollTo(0, 0)")
                save_btn = page.locator('header a:text-is("SAVE"), button:text-is("SAVE")').first
                if save_btn.count():
                    save_btn.click(no_wait_after=True)
                else:
                    fallback_save = page.locator('button:has-text("SAVE")').first
                    if fallback_save.count():
                        fallback_save.click(no_wait_after=True)
                time.sleep(1.5)

                # NEXT PAGE
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                next_btn = page.locator('button:has-text("PAGE"):not(:has-text("DELETE")), button:has-text("NEXT PAGE")').last
                if next_btn.count() and next_btn.is_enabled():
                    next_btn.click()
                    time.sleep(2) 
                else:
                    arrow = page.locator('i.icon-chevron-right').last
                    if arrow.count():
                        arrow.click()
                        time.sleep(2)
                    else:
                        break

            log(f"✅ FINISHED {fid}")
            browser_context.close()
    except Exception as e:
        log(f"❌ ERROR: {e}")

# --- UI CLASS ---

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FamilySearch Power Tool Pro")
        self.geometry("1100x700")
        self.configure(bg=BG)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        self.cfg = load_config()
        self.all_data = {} 
        self.all_urls = {} 
        self.current_fid = None
        self._search_timer = None
        self.undo_stack = []
        self.redo_stack = []
        
        self._setup_styles()
        self._build_ui()
        self._load_local_jsons()
        self._bind_shortcuts()

    def _on_close(self):
        self.destroy()
        os._exit(0)

    def _restart_app(self):
        import sys
        self.destroy()
        os.execv(sys.executable, ['python3'] + sys.argv)

    def _reload_jsons(self):
        self._load_local_jsons()
        self._log("📂 All data reloaded.")

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=CARD, foreground=MUTED, padding=[15, 5], font=("Segoe UI", 10))
        style.map("TNotebook.Tab", background=[("selected", ACCENT)], foreground=[("selected", BG)])
        style.configure("Treeview", background=CARD, foreground=TEXT, fieldbackground=CARD, rowheight=30, borderwidth=0, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background="#0f172a", foreground=ACCENT, font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", "#334155")])

    def _load_local_jsons(self):
        json_files = [f for f in os.listdir('.') if f.endswith('.json') and f != CONFIG_FILE]
        fids = []
        for jf in json_files:
            fid = jf[:-5]
            try:
                with open(jf, "r") as f:
                    data = json.load(f)
                self.all_data[fid] = json_to_rows(data)
                fids.append(fid)
            except:
                pass
        if fids:
            sorted_fids = sorted(fids)
            self.form_sel['values'] = sorted_fids
            if not self.current_fid or self.current_fid not in sorted_fids:
                self.form_sel.current(0)
                self.current_fid = sorted_fids[0]
            self._refresh_table()

    def _build_ui(self):
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)
        self.tab_auto = tk.Frame(self.nb, bg=BG)
        self.nb.add(self.tab_auto, text="  🤖 AUTOMATION  ")
        self._build_auto_tab()
        self.tab_edit = tk.Frame(self.nb, bg=BG)
        self.nb.add(self.tab_edit, text="  🛠️ DATA EDITOR  ")
        self._build_edit_tab()

    def _build_auto_tab(self):
        frame = tk.Frame(self.tab_auto, bg=BG, padx=40, pady=20)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="FamilySearch Power Tool", font=("Segoe UI", 16, "bold"), bg=BG, fg=TEXT).pack(anchor="w", pady=(0, 10))
        
        group1 = tk.LabelFrame(frame, text=" Login Settings ", bg=BG, fg=ACCENT, padx=15, pady=10)
        group1.pack(fill="x", pady=(0, 15))
        
        r1 = tk.Frame(group1, bg=BG)
        r1.pack(fill="x")
        tk.Label(r1, text="User:", bg=BG, fg=MUTED, width=6).pack(side="left")
        self.e_user = tk.Entry(r1, bg=CARD, fg=TEXT, width=18)
        self.e_user.pack(side="left", padx=5)
        self.e_user.insert(0, self.cfg.get("username", ""))
        
        tk.Label(r1, text="Pass:", bg=BG, fg=MUTED, width=6).pack(side="left", padx=(10, 0))
        self.e_pass = tk.Entry(r1, bg=CARD, fg=TEXT, width=18, show="•")
        self.e_pass.pack(side="left", padx=5)
        self.e_pass.insert(0, self.cfg.get("password", ""))

        tk.Label(r1, text="Profile:", bg=BG, fg=ACCENT, width=8).pack(side="left", padx=(10, 0))
        self.e_prof = tk.Entry(r1, bg="#334155", fg="#fff", width=5)
        self.e_prof.pack(side="left", padx=5)
        self.e_prof.insert(0, self.cfg.get("profile", "1"))

        group2 = tk.LabelFrame(frame, text=" Target URLs ", bg=BG, fg=ACCENT, padx=15, pady=10)
        group2.pack(fill="both", expand=True, pady=(0, 15))
        self.txt_urls = scrolledtext.ScrolledText(group2, bg=CARD, fg=TEXT, height=5, font=("Consolas", 10))
        self.txt_urls.pack(fill="both", expand=True)
        
        action_row = tk.Frame(frame, bg=BG)
        action_row.pack(fill="x", pady=5)
        
        tk.Button(action_row, text="🔄 SYNC", command=self._sync_all, bg="#334155", fg=TEXT, width=15).pack(side="left", padx=(0, 10))
        self.btn_run = tk.Button(action_row, text="🚀 START NITRO FILL", command=self._run_automation, bg=SUCCESS, fg="#fff", state="disabled")
        self.btn_run.pack(side="left", fill="x", expand=True)
        
        self.auto_log = scrolledtext.ScrolledText(frame, bg="#000", fg="#39ff14", height=6, font=("Consolas", 9))
        self.auto_log.pack(fill="both", expand=True)

    def _build_edit_tab(self):
        sidebar = tk.Frame(self.tab_edit, bg=CARD, width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        main_area = tk.Frame(self.tab_edit, bg=BG)
        main_area.pack(side="left", fill="both", expand=True)
        
        tk.Label(sidebar, text="CONTROLS", font=("Segoe UI", 9, "bold"), bg=CARD, fg=ACCENT).pack(pady=(15, 5), padx=20, anchor="w")
        self.form_sel = ttk.Combobox(sidebar, state="readonly")
        self.form_sel.pack(fill="x", padx=15, pady=(5, 15))
        self.form_sel.bind("<<ComboboxSelected>>", self._on_form_switch)
        
        self.e_search = tk.Entry(sidebar, bg=BG, fg=TEXT, borderwidth=0, insertbackground=TEXT, font=("Segoe UI", 10))
        self.e_search.pack(fill="x", padx=15, pady=(5, 15), ipady=2)
        self.e_search.bind("<KeyRelease>", self._on_search_change)
        
        tk.Button(sidebar, text="🔍 Find & Replace", command=self._show_find_replace, bg="#334155", fg=TEXT, borderwidth=0, font=("Segoe UI", 9), pady=6).pack(fill="x", padx=15, pady=3)
        tk.Button(sidebar, text="✨ Bulk Edit", command=self._bulk_edit, bg="#334155", fg=TEXT, borderwidth=0, font=("Segoe UI", 9), pady=6).pack(fill="x", padx=15, pady=3)
        tk.Button(sidebar, text="📂 Reload Disk", command=self._reload_jsons, bg="#334155", fg=TEXT, borderwidth=0, font=("Segoe UI", 9), pady=6).pack(fill="x", padx=15, pady=3)
        
        tk.Frame(sidebar, height=1, bg="#334155").pack(fill="x", padx=15, pady=15)
        tk.Button(sidebar, text="💾 SAVE", command=self._save_to_json, bg=ACCENT, fg=BG, borderwidth=0, font=("Segoe UI", 9, "bold"), pady=10).pack(fill="x", padx=15, pady=3)
        tk.Button(sidebar, text="🔄 RESTART", command=self._restart_app, bg=DANGER, fg="#fff", borderwidth=0, font=("Segoe UI", 8, "bold"), pady=6).pack(fill="x", padx=15, pady=(15, 3))
        
        top_bar = tk.Frame(main_area, bg=BG, padx=20, pady=10)
        top_bar.pack(fill="x")
        self.lbl_stats = tk.Label(top_bar, text="0 records", bg=BG, fg=MUTED, font=("Segoe UI", 9))
        self.lbl_stats.pack(side="left")
        
        tree_frame = tk.Frame(main_area, bg=BG, padx=20)
        tree_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        self.tree = ttk.Treeview(tree_frame, columns=COLS, show="headings", selectmode="extended")
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        for c in COLS:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=100)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        self.tree.bind("<Double-1>", self._on_double_click)

    def _bind_shortcuts(self):
        self.bind_all("<Control-z>", lambda e: self._undo())
        self.bind_all("<Control-y>", lambda e: self._redo())
        self.bind_all("<Control-s>", lambda e: self._save_to_json())
        self.bind_all("<Control-f>", lambda e: self.e_search.focus_set())
        self.bind_all("<Control-r>", lambda e: self._reload_jsons())

    def _push_undo(self):
        self.undo_stack.append(copy.deepcopy(self.all_data))
        if len(self.undo_stack) > 50:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def _undo(self): 
        if self.undo_stack:
            self.redo_stack.append(copy.deepcopy(self.all_data))
            self.all_data = self.undo_stack.pop()
            self._refresh_table()
            self._log("↩️ Undo")

    def _redo(self): 
        if self.redo_stack:
            self.undo_stack.append(copy.deepcopy(self.all_data))
            self.all_data = self.redo_stack.pop()
            self._refresh_table()
            self._log("↪️ Redo")

    def _on_search_change(self, e): 
        if self._search_timer:
            self.after_cancel(self._search_timer)
        self._search_timer = self.after(300, self._refresh_table)

    def _refresh_table(self):
        if not self.current_fid:
            return
        self.update_idletasks()
        query = self.e_search.get().lower()
        for i in self.tree.get_children():
            self.tree.delete(i)
        data = self.all_data[self.current_fid]
        for row in data:
            if not query or any(query in str(cell).lower() for cell in row):
                self.tree.insert("", tk.END, values=row)
        self.lbl_stats.config(text=f"{len(self.tree.get_children())} / {len(data)} records")

    def _show_find_replace(self):
        diag = tk.Toplevel(self)
        diag.title("Find & Replace")
        diag.geometry("400x300")
        diag.configure(bg=CARD)
        diag.transient(self)
        tk.Label(diag, text="FIND:", bg=CARD, fg=MUTED).pack(pady=5)
        e_f = tk.Entry(diag, width=40)
        e_f.pack(pady=5)
        tk.Label(diag, text="REPLACE:", bg=CARD, fg=MUTED).pack(pady=5)
        e_r = tk.Entry(diag, width=40)
        e_r.pack(pady=5)
        def do_rep():
            self._push_undo()
            changed = 0
            f_s, r_s = e_f.get(), e_r.get()
            if not f_s:
                return
            new_d = []
            for row in self.all_data[self.current_fid]:
                nr = [str(c).replace(f_s, r_s) for c in row]
                for i in range(len(row)):
                    if nr[i] != str(row[i]):
                        changed += 1
                new_d.append(nr)
            self.all_data[self.current_fid] = new_d
            self._refresh_table()
            diag.destroy()
            messagebox.showinfo("Done", f"Replaced {changed}")
        tk.Button(diag, text="REPLACE ALL", command=do_rep, bg=ACCENT, fg=BG).pack(pady=20)

    def _on_double_click(self, event):
        item = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not item or not col:
            return
        idx_str = col.replace("#", "")
        idx = int(idx_str) - 1
        old = self.tree.item(item, "values")[idx]
        val = simpledialog.askstring("Edit", "Update:", initialvalue=old)
        if val is not None:
            self._push_undo()
            vals = list(self.tree.item(item, "values"))
            vals[idx] = val
            self.tree.item(item, values=vals)
            rin = vals[0]
            for i, r in enumerate(self.all_data[self.current_fid]):
                if r[0] == rin:
                    self.all_data[self.current_fid][i] = vals
                    break

    def _bulk_edit(self):
        selected = self.tree.selection()
        if not selected:
            return
        diag = tk.Toplevel(self)
        diag.geometry("300x200")
        diag.configure(bg=CARD)
        cb = ttk.Combobox(diag, values=COLS)
        cb.pack(pady=10)
        cb.current(4)
        ent = tk.Entry(diag)
        ent.pack(pady=10)
        def apply():
            self._push_undo()
            col_idx = COLS.index(cb.get())
            val = ent.get()
            for item in selected:
                vals = list(self.tree.item(item, "values"))
                vals[col_idx] = val
                rin = vals[0]
                for i, r in enumerate(self.all_data[self.current_fid]):
                    if r[0] == rin:
                        self.all_data[self.current_fid][i] = vals
                        break
            diag.destroy()
            self._refresh_table()
        tk.Button(diag, text="APPLY", command=apply).pack()

    def _save_to_json(self):
        if not self.current_fid:
            return
        data = []
        for r in self.all_data[self.current_fid]:
            row = {"rin": int(r[0]) if r[0].isdigit() else r[0], "relation": r[1], "sex": r[2], "living": r[3], "given_names": r[4], "family_names": r[5], "birth_year": int(r[6]) if r[6].isdigit() else r[6], "birth_location": r[7], "death_year": int(r[8]) if r[8].isdigit() else r[8], "death_location": r[9]}
            data.append(row)
        with open(f"{self.current_fid}.json", "w") as f:
            json.dump(data, f, indent=2)
        messagebox.showinfo("Saved", f"Success: {self.current_fid}.json")

    def _sync_all(self):
        urls = self.txt_urls.get("1.0", tk.END).strip().splitlines()
        self.all_data = {}
        self.all_urls = {}
        fids = []
        json_files = [f for f in os.listdir('.') if f.endswith('.json') and f != CONFIG_FILE]
        for url in urls:
            url = url.strip()
            if not url:
                continue
            found = False
            for jf in json_files:
                fid = jf[:-5]
                if fid in url:
                    with open(jf, "r") as f:
                        data = json.load(f)
                    self.all_data[fid] = json_to_rows(data)
                    self.all_urls[fid] = url
                    fids.append(fid)
                    found = True
                    self._log(f"✅ Linked {jf}")
                    break
            if not found:
                match = re.search(r'(\d+)', url)
                if match:
                    fid = match.group(1)
                    json_p = f"{fid}.json"
                    if os.path.exists(json_p):
                        with open(json_p, "r") as f:
                            data = json.load(f)
                        self.all_data[fid] = json_to_rows(data)
                        self.all_urls[fid] = url
                        fids.append(fid)
                        found = True
                        self._log(f"✅ Found {json_p}")
        if fids:
            self.form_sel['values'] = fids
            self.form_sel.current(0)
            self.current_fid = fids[0]
            self._refresh_table()
            self.btn_run.config(state="normal", bg=SUCCESS)

    def _on_form_switch(self, e): 
        self.current_fid = self.form_sel.get()
        self._refresh_table()

    def _log(self, m):
        self.after(0, lambda: self.auto_log.insert(tk.END, f"> {m}\n") or self.auto_log.see(tk.END))

    def _run_automation(self):
        user, pwd, prof = self.e_user.get(), self.e_pass.get(), self.e_prof.get()
        self.cfg["username"], self.cfg["password"], self.cfg["profile"] = user, pwd, prof
        save_config(self.cfg)
        def worker():
            try:
                active = [(fid, rows) for fid, rows in self.all_data.items() if fid in self.all_urls]
                with ThreadPoolExecutor(max_workers=2) as ex:
                    futures = [ex.submit(fill_form_logic, fid, self.all_urls[fid], user, pwd, rows, self._log, i+1, prof) for i, (fid, rows) in enumerate(active)]
                    for f in futures:
                        f.result()
            except Exception as e:
                self._log(f"❌ Error: {e}")
            finally:
                self.after(0, lambda: self.btn_run.config(state="normal"))
                self._log("🏁 PROCESS FINISHED.")
        self.btn_run.config(state="disabled")
        threading.Thread(target=worker, daemon=True).start()

if __name__ == "__main__":
    try:
        App().mainloop()
    except KeyboardInterrupt:
        os._exit(0)
