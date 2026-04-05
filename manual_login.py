import os
import time
from playwright.sync_api import sync_playwright

def login_only():
    username = "igbonezulum.sunday"
    password = "07048442879chibuike"
    
    # Use the same unified session directory as app.py
    session_dir = os.path.join(os.path.expanduser("~"), ".familysearch_session")
    if not os.path.exists(session_dir): 
        os.makedirs(session_dir)

    print(f"🚀 Opening browser with session at: {session_dir}")
    
    with sync_playwright() as p:
        browser_context = p.chromium.launch_persistent_context(
            session_dir,
            headless=False,
            slow_mo=50,
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            args=['--disable-blink-features=AutomationControlled']
        )
        page = browser_context.pages[0] if browser_context.pages else browser_context.new_page()

        print("🌐 Navigating to login page...")
        page.goto("https://www.familysearch.org/auth/familysearch/login")
        
        # Check if login fields are there
        user_field = page.locator('#userName, #username')
        if user_field.is_visible(timeout=10000):
            print("✍️ Filling credentials...")
            user_field.fill(username)
            page.fill('#password', password)
            page.click('button[type="submit"], #login')
            print("🖱️ Login button clicked.")
        else:
            print("✅ Already logged in or redirecting...")

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
