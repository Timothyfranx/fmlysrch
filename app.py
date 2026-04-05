import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import json
import os
import re
import time
from playwright.sync_api import sync_playwright

# --- CONFIG & GLOBALS ---
CONFIG_FILE = "config.json"
BG      = "#0f1117"
CARD    = "#1a1d27"
ACCENT  = "#4f8ef7"
TEXT    = "#e8eaf0"
MUTED   = "#6b7280"
SUCCESS = "#22c55e"
WARN    = "#f59e0b"

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
        if str(living).lower() == "no" and not death_loc: death_loc = birth_loc
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

# --- CORE FILLING LOGIC ---

def fill_single_form(page, rows, status_cb, form_id):
    data_map = {str(r[0]): r for r in rows}
    filled_rins = set()
    total_to_fill = len(rows)
    
    status_cb(f"[{form_id}] Starting fill for {total_to_fill} people...")

    for p_idx in range(40): # Max 40 page transitions
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(2)
        
        # Identify rows by Given Names input
        given_inputs = page.locator('input[placeholder*="Given Name"]').all()
        if not given_inputs:
            time.sleep(3)
            given_inputs = page.locator('input[placeholder*="Given Name"]').all()
            
        status_cb(f"[{form_id}] Page {p_idx+1}: Found {len(given_inputs)} rows.")
        
        filled_on_this_page = 0
        for inp in given_inputs:
            try:
                # Find row container
                container = inp.locator('xpath=ancestor::div[role="row"][1] | ancestor::tr[1] | ancestor::div[contains(@class,"row")][1]').first
                if not container.is_visible(): continue
                
                # RIN Detection
                row_text = container.inner_text().strip()
                prev_text = ""
                try: prev_text = container.locator('xpath=preceding-sibling::div[1]').inner_text().strip()
                except: pass
                
                combined_text = prev_text + " " + row_text
                rin = None
                nums = re.findall(r'\d+', combined_text)
                for n in nums:
                    if n in data_map and n not in filled_rins:
                        rin = n
                        break
                
                if not rin: continue

                # Data Mapping
                r_data = data_map[rin]
                _, rel, sex, living, given, family, b_yr, b_loc, d_yr, d_loc = r_data
                
                # --- FILLING ---
                # 1. Relation
                if rel:
                    r_inp = container.locator('input[placeholder*="Relation"], [aria-label*="Relation"]').first
                    if r_inp.is_visible(timeout=200): r_inp.fill(rel)
                
                # 2. Sex
                if sex:
                    s_sel = container.locator('select, [aria-label*="Sex"]').first
                    if s_sel.is_visible(timeout=200):
                        try: s_sel.select_option(label=sex)
                        except:
                            s_sel.click()
                            page.locator(f'li:text-is("{sex}"), [role="option"]:text-is("{sex}")').first.click()

                # 3. Names
                inp.fill(given)
                if family:
                    f_inp = container.locator('input[placeholder*="Family"]').first
                    if f_inp.is_visible(timeout=200): f_inp.fill(family)
                
                # 4. Birth
                if b_yr:
                    by_inp = container.locator('input[placeholder*="Birth Date"]').first
                    if by_inp.is_visible(timeout=200): by_inp.fill(str(b_yr))
                if b_loc:
                    bl_inp = container.locator('input[placeholder*="Ward"], input[placeholder*="Place"]').first
                    if bl_inp.is_visible(timeout=200): bl_inp.fill(b_loc)
                
                # 5. Living?
                l_val = "Yes" if str(living).lower() == "yes" else "No"
                l_sel = container.locator('select').last
                if l_sel.is_visible(timeout=200):
                    try: l_sel.select_option(label=l_val)
                    except:
                        l_sel.click()
                        page.locator(f'li:text-is("{l_val}"), [role="option"]:text-is("{l_val}")').first.click()

                # 6. Death
                if l_val == "No":
                    if d_yr:
                        dy_inp = container.locator('input[placeholder*="Death Date"]').first
                        if dy_inp.is_visible(timeout=200): dy_inp.fill(str(d_yr))
                    if d_loc:
                        dl_inps = container.locator('input[placeholder*="Ward"], input[placeholder*="Place"]').all()
                        if len(dl_inps) > 1: dl_inps[1].fill(d_loc)

                filled_rins.add(rin)
                filled_on_this_page += 1
            except: pass

        # SAVE Page
        if filled_on_this_page > 0:
            status_cb(f"[{form_id}] 💾 Saving page...")
            save_btn = page.locator('button:has-text("SAVE"), .save-btn, [aria-label="Save"]').first
            if save_btn.is_visible():
                save_btn.click()
                time.sleep(4)

        # NEXT Page
        next_btn = page.locator('button[aria-label="Next Page"], .next-page-btn, i.icon-chevron-right').last
        if next_btn.is_visible(timeout=2000) and next_btn.is_enabled():
            next_btn.click()
            time.sleep(5)
        else:
            if len(filled_rins) >= total_to_fill:
                break
            else:
                # Try bottom button
                b_next = page.locator('button:has-text("NEXT PAGE"), button:has-text("BEGIN NEXT PAGE")').last
                if b_next.is_visible(timeout=500):
                    b_next.click()
                    time.sleep(5)
                else:
                    break

    status_cb(f"[{form_id}] ✅ Completed! Total: {len(filled_rins)} rows.")

def start_automation(urls, username, password, status_cb):
    with sync_playwright() as p:
        session_dir = os.path.abspath("fs_persistent_session")
        browser_context = p.chromium.launch_persistent_context(
            session_dir, headless=False, slow_mo=50,
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            args=['--disable-blink-features=AutomationControlled']
        )
        
        main_page = browser_context.pages[0]
        main_page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # 1. Login
        status_cb("🌐 Checking login...")
        main_page.goto("https://www.familysearch.org/auth/familysearch/login")
        time.sleep(3)
        if "login" in main_page.url:
            status_cb("✍️ Logging in...")
            main_page.fill('#userName, #username', username)
            main_page.fill('#password', password)
            main_page.click('button[type="submit"], #login')
            time.sleep(8)
        
        # 2. Parallel Tabs
        threads = []
        for url in urls:
            url = url.strip()
            if not url: continue
            
            # Extract ID (last 4 digits)
            match = re.search(r'(\d{4})$', url)
            form_id = match.group(1) if match else "Unknown"
            json_file = f"{form_id}.json"
            
            if not os.path.exists(json_file):
                status_cb(f"❌ Error: {json_file} not found for URL.")
                continue
            
            with open(json_file, "r") as f:
                data = json.load(f)
            rows = json_to_rows(data)
            
            # Open new tab
            new_tab = browser_context.new_page()
            new_tab.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            new_tab.goto(url)
            
            # Process in thread (Parallel)
            t = threading.Thread(target=fill_single_form, args=(new_tab, rows, status_cb, form_id))
            t.start()
            threads.append(t)
            time.sleep(5) # Stagger starts slightly

        for t in threads: t.join()
        status_cb("🎉 ALL TASKS FINISHED. Browser open for review.")
        
        # Keep open indefinitely
        while True: time.sleep(100)

# --- UI CLASS ---

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FamilySearch Multi-Fill Pro")
        self.geometry("900x700")
        self.configure(bg=BG)
        self.cfg = load_config()
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=BG, pady=15)
        hdr.pack(fill="x", padx=25)
        tk.Label(hdr, text="🚀 MULTI-TAB AUTOFILL", font=("Segoe UI", 18, "bold"), bg=BG, fg=ACCENT).pack(side="left")
        
        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True, padx=25)
        
        # Login Info
        lf = tk.LabelFrame(main, text=" Authentication ", bg=BG, fg=MUTED, font=("Segoe UI", 9), padx=15, pady=10)
        lf.pack(fill="x", pady=(0, 15))
        
        tk.Label(lf, text="Username:", bg=BG, fg=TEXT).grid(row=0, column=0, sticky="w")
        self.e_user = tk.Entry(lf, bg=CARD, fg=TEXT, insertbackground=TEXT, width=30)
        self.e_user.grid(row=0, column=1, padx=10, pady=5)
        self.e_user.insert(0, self.cfg.get("username", ""))
        
        tk.Label(lf, text="Password:", bg=BG, fg=TEXT).grid(row=0, column=2, sticky="w", padx=(20, 0))
        self.e_pass = tk.Entry(lf, bg=CARD, fg=TEXT, insertbackground=TEXT, width=30, show="•")
        self.e_pass.grid(row=0, column=3, padx=10, pady=5)
        self.e_pass.insert(0, self.cfg.get("password", ""))

        # URL Input
        uf = tk.LabelFrame(main, text=" Form URLs (one per line) ", bg=BG, fg=MUTED, font=("Segoe UI", 9), padx=15, pady=10)
        uf.pack(fill="both", expand=True)
        
        self.txt_urls = scrolledtext.ScrolledText(uf, bg=CARD, fg=TEXT, insertbackground=TEXT, font=("Consolas", 10), height=12)
        self.txt_urls.pack(fill="both", expand=True, pady=5)
        self.txt_urls.insert(tk.END, "https://www.familysearch.org/en/oral-gen/pedigree-form/NG35_002_20260323_1205")

        # Action
        self.btn_start = tk.Button(self, text="⚡ START PARALLEL FILLING", command=self._on_start, bg=SUCCESS, fg="#fff", font=("Segoe UI", 11, "bold"), pady=12, cursor="hand2")
        self.btn_start.pack(fill="x", padx=25, pady=20)

        # Status
        self.status_box = scrolledtext.ScrolledText(self, bg="#000", fg=WARN, font=("Consolas", 9), height=8)
        self.status_box.pack(fill="x", side="bottom")

    def _log(self, msg):
        self.status_box.insert(tk.END, f"> {msg}\n")
        self.status_box.see(tk.END)

    def _on_start(self):
        self.cfg["username"] = self.e_user.get()
        self.cfg["password"] = self.e_pass.get()
        save_config(self.cfg)
        
        urls = self.txt_urls.get("1.0", tk.END).splitlines()
        if not any(urls): return messagebox.showwarning("Empty", "Please paste at least one URL.")
        
        self.btn_start.config(state="disabled", text="RUNNING...")
        threading.Thread(target=lambda: start_automation(urls, self.cfg["username"], self.cfg["password"], self._log), daemon=True).start()

if __name__ == "__main__":
    App().mainloop()
