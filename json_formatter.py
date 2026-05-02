import json
import sys
import os

def format_json(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return

    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Successfully formatted '{file_path}'.")
    except json.JSONDecodeError as e:
        print(f"Error: '{file_path}' is not valid JSON. Run json_repair.py first.")
        print(f"Details: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 json_formatter.py <file_path>")
    else:
        format_json(sys.argv[1])
