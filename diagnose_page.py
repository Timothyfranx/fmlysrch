import os
import time
from playwright.sync_api import sync_playwright

def diagnose():
    URL = "https://www.familysearch.org/en/oral-gen/pedigree-form/NG35_002_20260323_1205"
    session_dir = os.path.abspath("familysearch_session_data")
    
    with sync_playwright() as p:
        browser_context = p.chromium.launch_persistent_context(
            session_dir,
            headless=True,
            viewport={'width': 1280, 'height': 800},
        )
        page = browser_context.pages[0]
        print(f"Navigating to {URL}...")
        page.goto(URL, wait_until="networkidle")
        time.sleep(15) # extra wait
        
        print(f"Current URL: {page.url}")
        print(f"Page Title: {page.title()}")
        
        # Take a screenshot
        page.screenshot(path="diagnose_screenshot.png")
        print("Screenshot saved to diagnose_screenshot.png")
        
        # Check if we are logged in
        if "login" in page.url:
            print("Not logged in. (Login detected in URL)")
        
        # List all frames
        print(f"Total frames: {len(page.frames)}")
        for i, frame in enumerate(page.frames):
            print(f"  Frame [{i}] name: {frame.name}, url: {frame.url}")
            inputs = frame.locator("input").all()
            if inputs:
                print(f"    - Found {len(inputs)} inputs in this frame.")

        browser_context.close()

if __name__ == "__main__":
    diagnose()
