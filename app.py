import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import json
import os
import re
from PIL import Image, ImageTk
import pytesseract
import cv2
import numpy as np

CONFIG_FILE = "config.json"
COLS = ("RIN", "Relation", "Sex", "Living", "Given Names", "Family Names",
        "Birth Year", "Birth Location", "Death Year", "Death Location")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f: return json.load(f)
        except: pass
    return {"username": "", "password": ""}

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f: json.dump(cfg, f)

def json_to_rows(data):
    rows = []
    for r in data:
        living = r.get("living", "") or ""
        birth_loc = r.get("birth_location", "") or ""
        death_loc = r.get("death_location", "") or ""
        if living == "No" and not death_loc: death_loc = birth_loc
        rows.append((
            str(r.get("rin", "")),
            r.get("relation", "") or "",
            r.get("sex", "") or "",
            living,
            r.get("given_names", "") or "",
            r.get("family_names", "") or "",
            str(r.get("birth_year", "") or ""),
            birth_loc,
            str(r.get("death_year", "") or ""),
            death_loc,
        ))
    return rows

def fill_form(url, username, password, rows, status_cb):
    from playwright.sync_api import sync_playwright
    import time

    with sync_playwright() as p:
        session_dir = os.path.abspath("fs_persistent_session")
        status_cb("Launching browser (1280x800)...")
        browser_context = p.chromium.launch_persistent_context(
            session_dir, 
            headless=False, 
            slow_mo=100,
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            args=['--disable-blink-features=AutomationControlled']
        )
        page = browser_context.pages[0] if browser_context.pages else browser_context.new_page()
        
        status_cb("🌐 Navigating to form...")
        page.goto(url) 
        
        time.sleep(5)
        if "login" in page.url:
            status_cb("✍️ Attempting automatic login...")
            try:
                page.fill('#userName, #username', username, timeout=10000)
                page.fill('#password', password)
                page.click('button[type="submit"], #login')
                status_cb("🖱️ Login clicked, waiting for form...")
                time.sleep(10)
            except Exception as e:
                status_cb(f"⚠️ Auto-login failed: {e}")

        status_cb("Waiting for form rows...")
        try:
            page.wait_for_selector('input[placeholder="Given Names"]', timeout=60000)
        except:
            status_cb("⚠️ Form not detected. Check browser.")
            time.sleep(10)

        data_map = {str(r[0]): r for r in rows}
        filled_rins = set()
        
        for p_idx in range(30): # Allow up to 30 page transitions
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(3)
            
            # Find all rows
            given_inputs = page.locator('input[placeholder="Given Names"]').all()
            status_cb(f"📄 Page {p_idx+1}: Found {len(given_inputs)} rows. Progress: {len(filled_rins)}/{len(rows)}")
            
            if len(given_inputs) == 0:
                status_cb("⏳ Waiting for rows to appear...")
                time.sleep(5)
                given_inputs = page.locator('input[placeholder="Given Names"]').all()
            
            rows_filled_this_page = 0
            for inp in given_inputs:
                try:
                    container = inp.locator('xpath=ancestor::div[role="row"][1] | ancestor::tr[1] | ancestor::div[contains(@class,"row")][1] | ancestor::div[contains(@class,"Grid-row")][1]').first
                    if not container.is_visible(): continue
                    
                    text = container.inner_text().strip()
                    prev_text = ""
                    try: prev_text = container.locator('xpath=preceding-sibling::div[1]').inner_text().strip()
                    except: pass
                    
                    combined = prev_text + " " + text
                    
                    status_cb(f"Row Content: {text[:40]}...")
                    
                    # More aggressive RIN search
                    rin = None
                    # 1. Try finding number at start of text
                    match = re.match(r'^(\d+)', text)
                    if match:
                        n = match.group(1)
                        if n in data_map and n not in filled_rins:
                            rin = n
                    
                    # 2. Try finding any number in the combined text that matches a missing RIN
                    if not rin:
                        nums = re.findall(r'\d+', combined)
                        for n in nums:
                            if n in data_map and n not in filled_rins:
                                rin = n
                                break
                    
                    if not rin:
                        # 3. Special case: if text is empty or missing number, try to infer from position
                        # But skip for now to avoid wrong data
                        continue

                    status_cb(f"✍️ Filling RIN {rin} ({len(filled_rins)+1}/{len(rows)})")
                    r_data = data_map[rin]
                    rin_val, relation, sex, living, given, family, birth_yr, birth_loc, death_yr, death_loc = r_data
                    
                    # ... (filling logic remains same)
                    if relation: 
                        r_inp = container.locator('input[placeholder*="Relation"], [aria-label*="Relation"]').first
                        if r_inp.is_visible(timeout=500): r_inp.fill(relation)
                    
                    if sex:
                        s_sel = container.locator('select[aria-label*="Sex"], div[aria-label*="Sex"], [aria-label="Sex"]').first
                        if s_sel.is_visible(timeout=500):
                            try: s_sel.select_option(label=sex)
                            except:
                                s_sel.click()
                                page.locator(f'li:text-is("{sex}"), [role="option"]:text-is("{sex}")').first.click()

                    inp.fill(given)
                    if family: 
                        f_inp = container.locator('input[placeholder*="Family"]').first
                        if f_inp.is_visible(timeout=500): f_inp.fill(family)
                    if birth_yr: 
                        b_yr = container.locator('input[placeholder*="Birth Date"]').first
                        if b_yr.is_visible(timeout=500): b_yr.fill(str(birth_yr))
                    if birth_loc: 
                        b_loc = container.locator('input[placeholder*="Ward"], input[placeholder*="Place"]').first
                        if b_loc.is_visible(timeout=500): b_loc.fill(birth_loc)
                    
                    if living:
                        l_val = "Yes" if str(living).lower() == "yes" else "No"
                        l_sel = container.locator('select, div[role="combobox"]').last
                        if l_sel.is_visible(timeout=500):
                            try: l_sel.select_option(label=l_val)
                            except:
                                l_sel.click()
                                page.locator(f'li:text-is("{l_val}"), [role="option"]:text-is("{l_val}")').first.click()

                    if str(living).lower() == "no":
                        d_yr_inp = container.locator('input[placeholder*="Death Date"]').first
                        if d_yr_inp.is_visible(timeout=500):
                            if death_yr: d_yr_inp.fill(str(death_yr))
                            if death_loc: 
                                d_locs = container.locator('input[placeholder*="Ward"], input[placeholder*="Place"]').all()
                                if len(d_locs) > 1: d_locs[1].fill(death_loc)

                    filled_rins.add(rin)
                    rows_filled_this_page += 1
                    time.sleep(0.1)
                except Exception as e:
                    pass

            # SAVE before moving
            if rows_filled_this_page > 0:
                status_cb(f"💾 Saving {rows_filled_this_page} entries...")
                save_btn = page.locator('button:has-text("SAVE"), .save-button, [aria-label="Save"]').first
                if save_btn.is_visible():
                    save_btn.click()
                    time.sleep(6) # Give it time to sync

            # Next page logic (refined)
            next_btn = page.locator('button[aria-label="Next Page"], .next-page-btn, i.icon-chevron-right, .pi-chevron-right').last
            if next_btn.is_visible(timeout=3000) and next_btn.is_enabled():
                status_cb(f"➡️ Page {p_idx+1} done. Moving to next...")
                next_btn.click()
                time.sleep(8)
            else:
                # Try bottom button if top fail
                btn2 = page.locator('button:has-text("BEGIN NEXT PAGE"), button:has-text("NEXT PAGE")').last
                if btn2.is_visible(timeout=1000):
                    btn2.click()
                    time.sleep(8)
                else:
                    break

        status_cb(f"🎉 Done! Successfully filled {len(filled_rins)} entries.")
        while True: time.sleep(10)

        status_cb(f"🎉 Done! Filled {len(filled_rins)} entries.")
        while True: time.sleep(10)

# ─── UI (Minimal for script) ──────────────────────────────────────────────────
# (The rest of the App class remains the same but we only care about fill_form)
# I will keep the original UI code at the end to maintain file integrity.

BG      = "#0f1117"
CARD    = "#1a1d27"
ACCENT  = "#4f8ef7"
TEXT    = "#e8eaf0"
MUTED   = "#6b7280"
SUCCESS = "#22c55e"
WARN    = "#f59e0b"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FamilySearch AutoFill")
        self.geometry("1150x720")
        self.configure(bg=BG)
        self.cfg = load_config()
        self.rows = []
        self._build_ui()

    def _build_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview", background=CARD, foreground=TEXT, fieldbackground=CARD, rowheight=26, font=("Courier New", 9))
        style.configure("Treeview.Heading", background="#252840", foreground=ACCENT, font=("Courier New", 8, "bold"))
        hdr = tk.Frame(self, bg=BG, pady=10)
        hdr.pack(fill="x", padx=20)
        tk.Label(hdr, text="⚡ FamilySearch AutoFill", font=("Courier New", 15, "bold"), bg=BG, fg=TEXT).pack(side="left")
        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True, padx=14, pady=4)
        left = tk.Frame(main, bg=BG, width=265)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)
        right = tk.Frame(main, bg=BG)
        right.pack(side="left", fill="both", expand=True)
        def section(txt):
            tk.Label(left, text=txt, font=("Courier New", 9, "bold"), bg=BG, fg=ACCENT).pack(anchor="w", pady=(10, 2))
        def field(lbl, show=None):
            tk.Label(left, text=lbl, font=("Courier New", 8), bg=BG, fg=MUTED).pack(anchor="w")
            e = tk.Entry(left, bg=CARD, fg=TEXT, insertbackground=TEXT, relief="flat", font=("Courier New", 10), highlightthickness=1, highlightbackground="#2d3149", highlightcolor=ACCENT, show=show)
            e.pack(fill="x", pady=(0, 5))
            return e
        section("🔐 LOGIN")
        self.e_user = field("Username / Email")
        self.e_user.insert(0, self.cfg.get("username", ""))
        self.e_pass = field("Password", show="•")
        self.e_pass.insert(0, self.cfg.get("password", ""))
        tk.Button(left, text="Save Login", command=self._save_login, bg="#252840", fg=ACCENT, relief="flat", font=("Courier New", 9), cursor="hand2").pack(fill="x", pady=(0, 4))
        section("🔗 FORM URL")
        self.e_url = field("Paste FamilySearch form URL")
        section("📥 INPUT MODE")
        self.mode = tk.StringVar(value="json")
        mf = tk.Frame(left, bg=BG)
        mf.pack(fill="x", pady=(0, 6))
        for label, val in [("JSON", "json"), ("OCR", "ocr")]:
            tk.Radiobutton(mf, text=label, variable=self.mode, value=val, bg=BG, fg=TEXT, selectcolor=CARD, font=("Courier New", 9), command=self._toggle_mode).pack(side="left", padx=(0, 8))
        self.json_file_frame = tk.Frame(left, bg=BG)
        self.json_file_frame.pack(fill="x", pady=(0, 5))
        tk.Label(self.json_file_frame, text="JSON Filename:", font=("Courier New", 8), bg=BG, fg=MUTED).pack(anchor="w")
        self.e_json_file = tk.Entry(self.json_file_frame, bg=CARD, fg=TEXT, font=("Courier New", 10))
        self.e_json_file.pack(fill="x", pady=(0, 2))
        self.e_json_file.insert(0, "002.json")
        tk.Button(self.json_file_frame, text="📂 Load JSON", command=self._load_json_from_file, bg="#2d3149", fg=TEXT, relief="flat", font=("Courier New", 9), cursor="hand2").pack(fill="x")
        self.ocr_frame = tk.Frame(left, bg=BG)
        tk.Button(self.ocr_frame, text="📂 Upload Photo", command=self._load_image, bg=CARD, fg=TEXT, relief="flat", font=("Courier New", 9)).pack(fill="x", pady=(0, 2))
        tk.Button(self.ocr_frame, text="🔍 Run OCR", command=self._run_ocr, bg=ACCENT, fg="#fff", relief="flat", font=("Courier New", 9, "bold")).pack(fill="x")
        tk.Frame(left, bg=BG, height=20).pack()
        tk.Button(left, text="▶ START FILLING", command=self._submit, bg=SUCCESS, fg="#fff", relief="flat", font=("Courier New", 10, "bold"), cursor="hand2", pady=12).pack(fill="x")
        tf = tk.Frame(right, bg=BG)
        tf.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(tf, columns=COLS, show="headings")
        for c in COLS:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=80, anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)
        self.status_var = tk.StringVar(value="Ready.")
        tk.Label(self, textvariable=self.status_var, font=("Courier New", 9), bg=CARD, fg=WARN, anchor="w", padx=12, pady=6).pack(fill="x", side="bottom")
        self._toggle_mode()
        self.after(500, self._load_json_from_file)

    def _load_json_from_file(self):
        filename = self.e_json_file.get().strip()
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f: data = json.load(f)
                rows = json_to_rows(data)
                self._populate_table(rows)
                self.status_var.set(f"✅ Loaded {filename}")
            except Exception as e: messagebox.showerror("Error", f"Failed: {e}")

    def _toggle_mode(self):
        if self.mode.get() == "json":
            self.ocr_frame.pack_forget()
            self.json_file_frame.pack(fill="x")
        else:
            self.json_file_frame.pack_forget()
            self.ocr_frame.pack(fill="x")

    def _save_login(self):
        self.cfg["username"] = self.e_user.get()
        self.cfg["password"] = self.e_pass.get()
        save_config(self.cfg)
        messagebox.showinfo("Saved", "Login saved.")

    def _populate_table(self, rows):
        for item in self.tree.get_children(): self.tree.delete(item)
        for r in rows: self.tree.insert("", "end", values=r)
        self.rows = list(rows)

    def _load_image(self):
        path = filedialog.askopenfilename()
        if path: self.image_path = path

    def _run_ocr(self):
        def worker():
            # OCR dummy
            pass
        threading.Thread(target=worker, daemon=True).start()

    def _sync_rows(self):
        self.rows = [self.tree.item(i, "values") for i in self.tree.get_children()]

    def _submit(self):
        self._sync_rows()
        url = self.e_url.get().strip()
        username = self.e_user.get().strip()
        password = self.e_pass.get().strip()
        if not url: return messagebox.showwarning("URL", "Paste URL first.")
        self.status_var.set("Automation running... check browser.")
        threading.Thread(target=lambda: fill_form(url, username, password, self.rows, lambda m: self.after(0, lambda: self.status_var.set(m))), daemon=True).start()

if __name__ == "__main__":
    App().mainloop()
