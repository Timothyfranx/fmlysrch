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
from json_repair import repair_json
from json_formatter import format_json
from clean_genealogy import clean_genealogy_json

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

def fill_form_logic(fid, url, username, password, rows, status_cb, worker_idx, profile_id, fill_settings, skip_wait_event=None):
    def log(msg): status_cb(f"[{fid}] {msg}")

    try:
        with sync_playwright() as p:
            session_dir = os.path.abspath(f"fs_session_p{profile_id}_w{worker_idx}")
            log(f"🚀 Worker {worker_idx} starting...")

            browser_context = p.chromium.launch_persistent_context(
                session_dir, headless=False, slow_mo=0,
                viewport={'width': 1280, 'height': 700},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
            )
            page = browser_context.pages[0]
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            log("🌐 Opening URL...")
            
            # Navigation retry loop for network resilience
            max_nav_retries = 3
            for nav_attempt in range(max_nav_retries):
                try:
                    page.goto(url, wait_until="commit", timeout=90000)
                    break 
                except Exception as e:
                    if nav_attempt < max_nav_retries - 1:
                        log(f"⚠️ Network blip (Attempt {nav_attempt+1}). Retrying in 5s...")
                        time.sleep(5)
                    else:
                        raise e

            # Adaptive wait for the page to render
            try:
                page.wait_for_load_state("domcontentloaded", timeout=30000)
            except:
                pass

            # --- DYNAMIC/CLEAN AUTO-LOGIN CHECK FIRST ---
            login_needed = False
            try:
                if "login" in page.url.lower() or page.locator('#userName, #username, [name="username"]').is_visible(timeout=3000):
                    login_needed = True
            except:
                pass

            if login_needed:
                log("✍️ Auto-login triggered instantly...")
                try:
                    # Dismiss cookie banner if it blocks inputs
                    try:
                        cookie_btn = page.locator('#truste-consent-button, button:has-text("Accept All"), button:has-text("Accept Cookies"), .cookie-consent-button').first
                        if cookie_btn.is_visible(timeout=2000):
                            cookie_btn.click()
                            log("🍪 Dismissed cookie consent banner.")
                    except:
                        pass

                    # Target username field more aggressively
                    u_field = page.locator('#userName, #username, [name="username"]').first
                    u_field.wait_for(state="visible", timeout=10000)
                    u_field.click()
                    u_field.fill("") # Standard clear
                    page.keyboard.press("Control+A") # Backup clear
                    page.keyboard.press("Backspace")
                    u_field.type(username, delay=30)

                    # Check for Next button (two-step login)
                    next_btn = page.locator('button:has-text("Next"), #login-next, button:has-text("Continue"), button[type="submit"]')
                    if next_btn.is_visible(timeout=2000):
                        next_btn.click()
                        time.sleep(1)

                    # Target password field
                    p_field = page.locator('#password, [name="password"]').first
                    p_field.wait_for(state="visible", timeout=10000)
                    p_field.click()
                    p_field.fill("")
                    p_field.type(password, delay=30)

                    # Final submit
                    submit_btn = page.locator('button[type="submit"], #login, #login-submit').first
                    submit_btn.click()

                    log("⌛ Redirecting...")
                    try:
                        page.wait_for_url(lambda u: "login" not in u.lower(), timeout=25000)
                    except:
                        pass
                    
                    # Force return to target URL after login
                    log("🔄 Returning to Form...")
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                except Exception as e:
                    log(f"⚠️ Auto-login failed: {e}. Adjust manually during wait period...")

            # --- PERSISTENT USER ADJUSTMENT BUFFER ---
            log("⏳ Waiting up to 120s for manual adjustments. Click '⏭️ SKIP WAIT' to start filling immediately.")
            if skip_wait_event:
                skip_wait_event.wait(timeout=120)
            else:
                time.sleep(120)

            log("🔍 Scanning form...")
            try:
                # Wait for specific form inputs
                page.wait_for_selector('input[placeholder*="Given Name"]', timeout=60000)
                log("✅ Ready.")
            except:
                log("❌ Form not found. Trying one more time...")
                page.goto(url, wait_until="domcontentloaded")
                time.sleep(5)

            data_map = {str(r[0]): r for r in rows}
            filled_rins = set()
            
            for p_idx in range(100):
                # Retry loop for page content
                anchors = []
                for _ in range(3):
                    anchors = page.locator('input[placeholder*="Given Name"]').all()
                    if anchors: break
                    time.sleep(2)
                
                if not anchors:
                    log("⚠️ No records on page. Checking for Next...")
                    page_modified = False
                else:
                    # Check if this page contains any RINs we actually need
                    body_text = page.locator('body').text_content()
                    needed_on_this_page = any(rin in body_text for rin in data_map if rin not in filled_rins)
                    
                    if not needed_on_this_page:
                        log(f"⏭️ Skipping Page {p_idx+1} (No target RINs found)...")
                        page_modified = False
                    else:
                        log(f"📄 Page {p_idx+1}: Filling rows...")
                        page_modified = False
                        
                        for inp in anchors:
                            try:
                                container = inp.locator('xpath=ancestor::div[role="row"][1] | ancestor::tr[1] | ancestor::div[contains(@class,"row")][1]').first
                                if not container.count():
                                    continue
                                
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
                                if rel and fill_settings.get("relation"):
                                    r_field = container.locator('input[placeholder*="Relation"]').first
                                    if r_field.count() == 0:
                                        r_field = container.locator('input').nth(0)
                                    if r_field.count():
                                        r_field.fill(str(rel))
                                        r_field.press("Tab")
                                        page_modified = True

                                # SEX
                                if sex and fill_settings.get("sex"):
                                    s_field = container.locator('select, [aria-label*="Sex"]').first
                                    if s_field.count():
                                        try:
                                            s_field.select_option(label=sex)
                                            page_modified = True
                                        except:
                                            pass

                                # NAMES
                                if fill_settings.get("names"):
                                    if given:
                                        inp.fill(str(given))
                                        page_modified = True
                                    if family:
                                        f_field = container.locator('input[placeholder*="Family"]').first
                                        if f_field.count():
                                            f_field.fill(str(family))
                                            page_modified = True
                                
                                # BIRTH
                                if fill_settings.get("birth"):
                                    if b_yr:
                                        by_field = container.locator('input[placeholder*="Birth Date"]').first
                                        if by_field.count():
                                            by_field.fill(str(b_yr))
                                            page_modified = True
                                    if b_loc:
                                        bl_field = container.locator('input[placeholder*="Ward"], input[placeholder*="Place"]').first
                                        if bl_field.count():
                                            bl_field.fill(str(b_loc))
                                            page.keyboard.press("Enter")
                                            page_modified = True
                                
                                # LIVING & DEATH
                                is_dead = str(living).lower() == "no" or bool(d_yr) or bool(d_loc)
                                should_set_living = fill_settings.get("living") or (is_dead and fill_settings.get("death"))

                                # 1. Handle Living Status - only change if not already "No"
                                if (living or is_dead) and should_set_living:
                                    l_val = "No" if is_dead else "Yes"
                                    l_field = container.locator('select[aria-label*="Living"], select').last
                                    if l_field.count():
                                        try:
                                            current_val = l_field.evaluate("el => el.value")
                                            target_val = "n" if l_val == "No" else "y"
                                            if current_val != target_val:
                                                l_field.select_option(label=l_val)
                                                l_field.evaluate("el => { el.dispatchEvent(new Event('change', {bubbles: true})); el.dispatchEvent(new Event('input', {bubbles: true})); }")
                                                page_modified = True
                                                if l_val == "No":
                                                    # Wait for death sub-row to appear in DOM
                                                    time.sleep(2.0)
                                        except:
                                            pass

                                # 2. Fill Death Data
                                if is_dead and fill_settings.get("death"):
                                    try:
                                        log(f"📍 Filling Death for RIN {rin}...")
                                        # Use JS to find and focus the correct death inputs in the sibling rows
                                        # We return the index/selector or just focus it directly in JS
                                        focused = page.evaluate("""
                                            (givenName) => {
                                                // 1. Find the main row
                                                let mainRow = null;
                                                const allInputs = Array.from(document.querySelectorAll('input'));
                                                for (const inp of allInputs) {
                                                    if ((inp.placeholder || '').toLowerCase().includes('given') && 
                                                        inp.value.toLowerCase().includes(givenName.toLowerCase())) {
                                                        mainRow = inp.closest('[role="row"], tr, .row');
                                                        if (mainRow) break;
                                                    }
                                                }
                                                if (!mainRow) return false;

                                                // 2. Scan siblings for death fields
                                                let sib = mainRow.nextElementSibling;
                                                for (let i = 0; i < 3 && sib; i++) {
                                                    const dInputs = Array.from(sib.querySelectorAll('input'));
                                                    const dDate = dInputs.find(inp => (inp.placeholder || '').toLowerCase().includes('date') || (inp.placeholder || '').toLowerCase().includes('year'));
                                                    const dPlace = dInputs.find(inp => (inp.placeholder || '').toLowerCase().includes('place') || (inp.placeholder || '').toLowerCase().includes('ward'));
                                                    
                                                    if (dDate || dPlace) {
                                                        // We'll focus the first one we need to fill and return metadata
                                                        return { found: true, dateId: !!dDate, placeId: !!dPlace };
                                                    }
                                                    sib = sib.nextElementSibling;
                                                }
                                                return { found: false };
                                            }
                                        """, str(given) if given else "")

                                        if focused and focused.get('found'):
                                            # Now we use Playwright locators to find and type
                                            # This is much more reliable than direct value setting
                                            sib_indices = [1, 2, 3] # Check next 3 siblings
                                            for idx in sib_indices:
                                                death_row = container.locator(f'xpath=following-sibling::div[{idx}] | following-sibling::tr[{idx}]').first
                                                if death_row.count():
                                                    d_date_field = death_row.locator('input[placeholder*="Date"], input[placeholder*="Year"]').first
                                                    d_place_field = death_row.locator('input[placeholder*="Place"], input[placeholder*="Ward"]').first
                                                    
                                                    if d_date_field.count() or d_place_field.count():
                                                        if d_yr and d_date_field.count():
                                                            d_date_field.click()
                                                            page.keyboard.press("Control+A")
                                                            page.keyboard.press("Backspace")
                                                            # Faster typing for speed, but still using keyboard to trigger site JS
                                                            page.keyboard.type(str(d_yr), delay=10)
                                                            page_modified = True
                                                        
                                                        if d_loc and d_place_field.count():
                                                            d_place_field.click()
                                                            page.keyboard.press("Control+A")
                                                            page.keyboard.press("Backspace")
                                                            page.keyboard.type(str(d_loc), delay=10)
                                                            time.sleep(0.3)
                                                            page.keyboard.press("Enter")
                                                            page_modified = True
                                                        break
                                    except Exception as e:
                                        log(f"⚠️ Death fill failed for {rin}: {str(e)[:40]}")
                                filled_rins.add(rin)
                            except:
                                pass

                # SAVE
                if page_modified:
                    log("💾 Saving...")
                    page.evaluate("window.scrollTo(0, 0)")
                    save_btn = page.locator('header a:text-is("SAVE"), button:text-is("SAVE"), button:has-text("SAVE")').first
                    if save_btn.count():
                        save_btn.click(no_wait_after=True)
                    time.sleep(0.5)

                # NEXT PAGE - BOTTOM-FIRST STRATEGY
                # 1. Scroll to bottom to check for form extension (Priority)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1.0) # Grace period for rendering

                # Look for BEGIN NEW PAGE
                new_pg_btn = page.locator('button:has-text("BEGIN"), button:has-text("NEW PAGE")').last
                
                clicked_new = False
                if new_pg_btn.count() and new_pg_btn.is_enabled():
                    log("🆕 Clicking BEGIN NEW PAGE...")
                    try:
                        # Tier 1: Standard Click
                        new_pg_btn.click(timeout=3000)
                        clicked_new = True
                    except:
                        # Tier 2: JavaScript Force Click (The Nuclear Option)
                        log("⚠️ Standard click failed, forcing via JS...")
                        page.evaluate("""() => {
                            const btns = Array.from(document.querySelectorAll('button'));
                            const target = btns.find(b => b.innerText.includes('BEGIN') || b.innerText.includes('NEW PAGE'));
                            if (target) target.click();
                        }""")
                        clicked_new = True
                
                if clicked_new:
                    time.sleep(2.0)
                else:
                    # 2. Scroll to top to check for existing page navigation
                    page.evaluate("window.scrollTo(0, 0)")
                    time.sleep(0.5)
                    
                    next_page_num = p_idx + 2
                    num_btn = page.locator(f'button:text-is("PAGE {next_page_num}"), a:text-is("PAGE {next_page_num}"), button:text-is("{next_page_num}"), a:text-is("{next_page_num}")').first
                    arrow_next = page.locator(
                        'button[aria-label*="next" i]:not([disabled]), button[title*="next" i]:not([disabled]), ' 
                        'a[aria-label*="next" i], a[title*="next" i], ' 
                        'button:text-is(">"):not([disabled]), a:text-is(">"):not([disabled])' 
                    ).first

                    if num_btn.count() and num_btn.is_enabled():
                        log(f"➡️ Page {next_page_num}")
                        num_btn.click()
                        time.sleep(1.0)
                    elif arrow_next.count() and arrow_next.is_enabled():
                        log("➡️ Next existing page (arrow)")
                        arrow_next.click()
                        time.sleep(1.0)
                    else:
                        log("🏁 Finished — no navigation options left.")
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
        self.skip_wait_event = threading.Event()
        
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

    def _run_repair_json(self):
        if not self.current_fid:
            messagebox.showwarning("No Selection", "Please select a form JSON to repair.")
            return
        
        file_path = f"{self.current_fid}.json"
        if not os.path.exists(file_path):
            messagebox.showerror("Error", f"File '{file_path}' not found.")
            return

        if messagebox.askyesno("Confirm Repair", f"Do you want to run surgical JSON repair on '{file_path}'?"):
            try:
                repair_json(file_path)
                self._load_local_jsons()
                self._log(f"🛠️ Repaired and reloaded '{file_path}'")
                messagebox.showinfo("Success", f"Successfully repaired '{file_path}'!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to repair JSON:\n{e}")

    def _run_format_json(self):
        if not self.current_fid:
            messagebox.showwarning("No Selection", "Please select a form JSON to format.")
            return
        
        file_path = f"{self.current_fid}.json"
        if not os.path.exists(file_path):
            messagebox.showerror("Error", f"File '{file_path}' not found.")
            return
            
        try:
            format_json(file_path)
            self._load_local_jsons()
            self._log(f"📝 Formatted and reloaded '{file_path}'")
            messagebox.showinfo("Success", f"Formatted '{file_path}' successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to format JSON:\n{e}")

    def _run_clean_genealogy(self):
        if not self.current_fid:
            messagebox.showwarning("No Selection", "Please select a form JSON to clean.")
            return
            
        file_path = f"{self.current_fid}.json"
        if not os.path.exists(file_path):
            messagebox.showerror("Error", f"File '{file_path}' not found.")
            return
        
        choice = messagebox.askyesnocancel(
            "Clean Genealogy Data",
            f"Applying living/deceased genealogy rules to '{file_path}'.\n\n"
            "Do you want to overwrite the current file directly?\n\n"
            "- Yes: Overwrite the active file\n"
            "- No: Create a clean copy named like '*_cleaned.json'\n"
            "- Cancel: Abort cleaning"
        )
        
        if choice is None:
            return
            
        overwrite = choice
        try:
            stats = clean_genealogy_json(file_path, overwrite=overwrite)
            self._load_local_jsons()
            
            if stats and stats.get("success"):
                living_fixed = stats.get("living_fixed", 0)
                deceased_fixed = stats.get("deceased_fixed", 0)
                out_path = stats.get("output_path", file_path)
                
                msg = (
                    f"Genealogy cleaning applied successfully!\n\n"
                    f"• Living individuals fixed: {living_fixed}\n"
                    f"• Deceased individuals fixed: {deceased_fixed}\n"
                    f"• Output file: {os.path.basename(out_path)}"
                )
                self._log(f"🧼 Cleaned '{file_path}' (living fixed: {living_fixed}, deceased fixed: {deceased_fixed})")
                messagebox.showinfo("Success", msg)
            else:
                err_msg = stats.get("error", "Unknown error occurred.") if stats else "Unknown error."
                messagebox.showerror("Error", f"Failed to clean genealogy data:\n{err_msg}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to clean genealogy data:\n{e}")

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=CARD, foreground=MUTED, padding=[15, 5], font=("Segoe UI", 10))
        style.map("TNotebook.Tab", background=[("selected", ACCENT)], foreground=[("selected", BG)])
        style.configure("Treeview", background=CARD, foreground=TEXT, fieldbackground=CARD, rowheight=28, borderwidth=0, font=("Segoe UI", 10))
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

        r2 = tk.Frame(group1, bg=BG)
        r2.pack(fill="x", pady=(8, 0))
        tk.Button(r2, text="🧹 CLEAR CURRENT SESSION CACHE", command=self._clean_session_cache, bg=DANGER, fg="#fff", font=("Segoe UI", 9, "bold")).pack(side="left")

        group2 = tk.LabelFrame(frame, text=" Target URLs ", bg=BG, fg=ACCENT, padx=15, pady=10)
        group2.pack(fill="both", expand=True, pady=(0, 15))
        self.txt_urls = scrolledtext.ScrolledText(group2, bg=CARD, fg=TEXT, height=5, font=("Consolas", 10))
        self.txt_urls.pack(fill="both", expand=True)
        
        group3 = tk.LabelFrame(frame, text=" Field Selection ", bg=BG, fg=ACCENT, padx=15, pady=10)
        group3.pack(fill="x", pady=(0, 15))
        
        self.fill_vars = {
            "relation": tk.BooleanVar(value=True),
            "sex": tk.BooleanVar(value=True),
            "names": tk.BooleanVar(value=True),
            "birth": tk.BooleanVar(value=True),
            "living": tk.BooleanVar(value=True),
            "death": tk.BooleanVar(value=True)
        }
        
        c_frame = tk.Frame(group3, bg=BG)
        c_frame.pack(fill="x")
        
        for i, (key, var) in enumerate(self.fill_vars.items()):
            cb = tk.Checkbutton(c_frame, text=key.upper(), variable=var, bg=BG, fg=TEXT, 
                                selectcolor=CARD, activebackground=BG, activeforeground=ACCENT)
            cb.pack(side="left", padx=5)

        action_row = tk.Frame(frame, bg=BG)
        action_row.pack(fill="x", pady=5)
        
        tk.Button(action_row, text="🔄 SYNC", command=self._sync_all, bg="#334155", fg=TEXT, width=15).pack(side="left", padx=(0, 10))
        self.btn_run = tk.Button(action_row, text="🚀 START NITRO FILL", command=self._run_automation, bg=SUCCESS, fg="#fff", state="disabled")
        self.btn_run.pack(side="left", fill="x", expand=True)
        self.btn_skip = tk.Button(action_row, text="⏭️ SKIP WAIT", command=self._skip_wait, bg=ACCENT, fg=BG, state="disabled", width=15)
        self.btn_skip.pack(side="left", padx=(10, 0))
        
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
        
        tk.Label(sidebar, text="CLEAN & REPAIR", font=("Segoe UI", 9, "bold"), bg=CARD, fg=ACCENT).pack(pady=(15, 5), padx=20, anchor="w")
        tk.Button(sidebar, text="🛠️ Repair JSON", command=self._run_repair_json, bg="#334155", fg=TEXT, borderwidth=0, font=("Segoe UI", 9), pady=6).pack(fill="x", padx=15, pady=3)
        tk.Button(sidebar, text="📝 Format JSON", command=self._run_format_json, bg="#334155", fg=TEXT, borderwidth=0, font=("Segoe UI", 9), pady=6).pack(fill="x", padx=15, pady=3)
        tk.Button(sidebar, text="🧼 Clean Genealogy", command=self._run_clean_genealogy, bg="#334155", fg=TEXT, borderwidth=0, font=("Segoe UI", 9), pady=6).pack(fill="x", padx=15, pady=3)
        
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
        
        # Column widths
        widths = {
            "RIN": 60,
            "Relation": 180,
            "Given Names": 180,
            "Family Names": 150,
            "Birth Location": 250,
            "Death Location": 250,
            "Sex": 80,
            "Living": 80,
            "Birth Year": 100,
            "Death Year": 100
        }
        
        for c in COLS:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=widths.get(c, 100), minwidth=50)
        
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

    def _clean_session_cache(self):
        profile = self.e_prof.get().strip() or "1"
        import shutil
        deleted = []
        for worker_idx in (1, 2):
            session_dir = os.path.abspath(f"fs_session_p{profile}_w{worker_idx}")
            if os.path.exists(session_dir):
                try:
                    shutil.rmtree(session_dir)
                    deleted.append(os.path.basename(session_dir))
                except Exception as e:
                    self._log(f"⚠️ Error deleting {session_dir}: {e}")
        
        if deleted:
            messagebox.showinfo("Success", f"Cleared session cache for Profile {profile}:\n" + "\n".join(deleted))
            self._log(f"🧹 Cleared session cache for Profile {profile}: {', '.join(deleted)}")
        else:
            messagebox.showinfo("Info", f"No active session cache directories found for Profile {profile} to clean.")
            self._log(f"🧹 No active session cache directories found for Profile {profile}.")

    def _skip_wait(self):
        self.skip_wait_event.set()
        self._log("⏭️ SKIP WAIT clicked! Resuming automation instantly...")

    def _run_automation(self):
        user, pwd, prof = self.e_user.get(), self.e_pass.get(), self.e_prof.get()
        self.cfg["username"], self.cfg["password"], self.cfg["profile"] = user, pwd, prof
        save_config(self.cfg)
        
        fill_settings = {k: v.get() for k, v in self.fill_vars.items()}
        
        def worker():
            try:
                self.skip_wait_event.clear()
                self.after(0, lambda: self.btn_skip.config(state="normal"))
                active = [(fid, rows) for fid, rows in self.all_data.items() if fid in self.all_urls]
                with ThreadPoolExecutor(max_workers=2) as ex:
                    futures = [ex.submit(fill_form_logic, fid, self.all_urls[fid], user, pwd, rows, self._log, i+1, prof, fill_settings, self.skip_wait_event) for i, (fid, rows) in enumerate(active)]
                    for f in futures:
                        f.result()
            except Exception as e:
                self._log(f"❌ Error: {e}")
            finally:
                self.after(0, lambda: self.btn_run.config(state="normal"))
                self.after(0, lambda: self.btn_skip.config(state="disabled"))
                self._log("🏁 PROCESS FINISHED.")
        self.btn_run.config(state="disabled")
        threading.Thread(target=worker, daemon=True).start()

if __name__ == "__main__":
    try:
        App().mainloop()
    except KeyboardInterrupt:
        os._exit(0)
