import json
import re
import sys
import os

def repair_json(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return

    try:
        with open(file_path, 'r') as f:
            content = f.read()

        # Extract all valid-looking JSON objects {...}
        # This regex looks for blocks starting with { and ending with }
        # that contain at least one key-value pair.
        blocks = re.findall(r'\{[^{}]*?\}', content, re.DOTALL)
        
        repaired_data = []
        for block in blocks:
            try:
                # Basic cleaning: remove potential trailing commas or junk
                cleaned_block = block.strip()
                # Try to parse it
                obj = json.loads(cleaned_block)
                repaired_data.append(obj)
            except json.JSONDecodeError:
                # If nested objects are present, the simplistic regex above fails.
                # In that case, we can try a more advanced balanced-brace approach if needed.
                continue

        if not repaired_data:
            print(f"No valid JSON objects could be recovered from '{file_path}'.")
            return

        # Sort by RIN if available (specific to this project's data)
        repaired_data.sort(key=lambda x: x.get('rin', 0))

        # Save the repaired list
        with open(file_path, 'w') as f:
            json.dump(repaired_data, f, indent=2)
        
        print(f"Successfully repaired '{file_path}'. Extracted {len(repaired_data)} objects.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 json_repair.py <file_path>")
    else:
        repair_json(sys.argv[1])
