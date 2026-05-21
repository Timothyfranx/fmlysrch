import os
import time
import json
from playwright.sync_api import sync_playwright

def login_only():
    # Load config.json if available
    config = {"username": "", "password": "", "profile": "1"}
    if os.path.exists("config.json"):
        try:
            with open("config.json", "r") as f:
                config.update(json.load(f))
        except:
            pass

    username = config.get("username") or "igbonezulum.sunday"
    password = config.get("password") or "07048442879chibuike"
    profile_id = config.get("profile") or "1"

    print("\n--- FamilySearch Manual Session Helper ---")
    print(f"Loaded config username: {username}")
    print(f"Loaded profile ID: {profile_id}")
    
    prof_input = input(f"Enter profile ID (Press Enter for '{profile_id}'): ").strip()
    if prof_input:
        profile_id = prof_input
        
    worker_idx = input("Enter worker ID (1 or 2, Press Enter for '1'): ").strip()
    if worker_idx not in ("1", "2"):
        worker_idx = "1"
        
    # Use the same unified session directory format as app.py
    session_dir = os.path.abspath(f"fs_session_p{profile_id}_w{worker_idx}")
    if not os.path.exists(session_dir): 
        os.makedirs(session_dir)

    print(f"\n🚀 Opening persistent browser with session at: {session_dir}")
    
    with sync_playwright() as p:
        browser_context = p.chromium.launch_persistent_context(
            session_dir,
            headless=False,
            slow_mo=50,
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        page = browser_context.pages[0] if browser_context.pages else browser_context.new_page()

        print("🌐 Navigating to login page...")
        page.goto("https://www.familysearch.org/auth/familysearch/login")
        
        # Check if login fields are there
        user_field = page.locator('#userName, #username')
        try:
            if user_field.is_visible(timeout=5000):
                print("✍️ Filling credentials...")
                user_field.fill(username)
                page.fill('#password', password)
                page.click('button[type="submit"], #login')
                print("🖱️ Login button clicked.")
            else:
                print("✅ Already logged in or redirecting...")
        except Exception as e:
            print(f"⚠️ Check field visibility error: {e}")

        print("\n--- ATTENTION ---")
        print("Please check the browser window.")
        print("1. Accept any cookies.")
        print("2. Complete any puzzles/captchas if they appear.")
        print("3. Ensure you are on the FamilySearch home page/dashboard.")
        print("The browser will stay open for 5 minutes. Close it manually once you are done to save the session.")
        
        # Keep it open for manual verification
        try:
            time.sleep(300)
        except KeyboardInterrupt:
            pass
        
        browser_context.close()

if __name__ == "__main__":
    login_only()
