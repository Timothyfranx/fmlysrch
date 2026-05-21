import json
import re
import sys

def execute_internal_lint_and_shift(raw_broken_string):
    # Pre-clean: replace any ][ with , to join arrays
    cleaned = re.sub(r'\]\s*\[', ',', raw_broken_string)
    
    # Ensure it's wrapped in a single array
    cleaned = cleaned.strip()
    if not cleaned.startswith('['):
        cleaned = '[' + cleaned
    if not cleaned.endswith(']'):
        cleaned = cleaned + ']'
        
    try:
        # Standard cleaning for common JSON errors
        clean_input_string = re.sub(r",\s*([\]}])", r"\1", cleaned)
        data = json.loads(clean_input_string)
    except Exception:
        # Fallback manual extraction if string parsing fails
        data = []
        # Find all objects using a non-greedy match
        objs = re.findall(r'\{.*?\}', raw_broken_string, re.DOTALL)
        for obj_str in objs:
            try:
                fixed_obj = re.sub(r",\s*([\]}])", r"\1", obj_str)
                obj = json.loads(fixed_obj)
                data.append(obj)
            except:
                continue

    corrected_array = []
    # Re-index from 1 to 1423
    sequential_counter = 1

    for item in data:
        # Programmatically override the 'rin' field
        item["rin"] = sequential_counter
        sequential_counter += 1

        # Standardize empty strings or bad missing markers to uniform nulls
        for key in [
            "birth_year",
            "death_year",
            "given_names",
            "family_names",
            "relation",
        ]:
            if item.get(key) == "" or item.get(key) == "null":
                item[key] = None

        corrected_array.append(item)

    return corrected_array

if __name__ == "__main__":
    try:
        with open("1042.json", "r") as f:
            raw_data = f.read()
        
        result = execute_internal_lint_and_shift(raw_data)
        if result:
            with open("1042_cleaned.json", "w") as f:
                json.dump(result, f, indent=2)
            # We don't print to stdout to keep it clean for the user, 
            # but we can print a success message to stderr
            print(f"Processed {len(result)} records.", file=sys.stderr)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
