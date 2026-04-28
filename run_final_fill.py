import json
import os
from app import fill_form, json_to_rows

def run_automation():
    URL = "https://www.familysearch.org/en/oral-gen/pedigree-form/NG35_002_20260323_1205"
    USERNAME = "igbonezulum.sunday"
    PASSWORD = "07048442879chibuike"
    JSON_FILE = "002.json"

    if not os.path.exists(JSON_FILE):
        print(f"Error: {JSON_FILE} not found.")
        return

    print(f"Loading data from {JSON_FILE}...")
    with open(JSON_FILE, "r") as f:
        data = json.load(f)
    
    rows = json_to_rows(data)
    print(f"Loaded {len(rows)} entries.")

    print("Starting FamilySearch automation...")
    def status_printer(msg):
        print(f"[STATUS] {msg}")

    try:
        fill_form(URL, USERNAME, PASSWORD, rows, status_printer)
    except Exception as e:
        print(f"Critical error during execution: {e}")

if __name__ == "__main__":
    run_automation()
