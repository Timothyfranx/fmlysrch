import json
import re
import os
import sys

def to_title_case(s):
    """Converts string to Title Case and handles None/Null values."""
    if s is None or not isinstance(s, str):
        return ""
    return s.strip().title()

def fix_relation(relation):
    """
    Cleans relation strings:
    1. Removes spaces after commas.
    2. Adds 'C' prefix to sequential numeric indices (e.g., C14,62 -> C14,C62).
    """
    if not isinstance(relation, str):
        return ""
    
    # Remove space after comma
    relation = relation.replace(', ', ',')
    
    # Add 'C' prefix to second and subsequent indices if missing
    # Example: C1,2,3 -> C1,C2,C3
    while True:
        new_relation = re.sub(r'([A-Z]\d+),(\d+)', r'\1,C\2', relation)
        if new_relation == relation:
            break
        relation = new_relation
    return relation

def replace_abbreviations(text):
    """Replaces common abbreviations with full names (case-insensitive)."""
    if not isinstance(text, str):
        return ""
    text = re.sub(r'\bana\b', 'Anambra', text, flags=re.IGNORECASE)
    text = re.sub(r'\bnig\b', 'Nigeria', text, flags=re.IGNORECASE)
    return text

def clean_json_file(file_path):
    """Loads, cleans, and saves a JSON file."""
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return

    print(f"Cleaning {file_path}...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for entry in data:
            # 1. Convert all field values to consistent types (None -> "")
            for key in ['given_names', 'family_names', 'birth_location', 'death_location', 'relation', 'sex', 'living']:
                if key in entry:
                    val = entry[key]
                    if val is None:
                        entry[key] = ""
                    elif isinstance(val, str):
                        entry[key] = val.strip()

            # 2. Apply Title Case
            entry['given_names'] = to_title_case(entry.get('given_names'))
            entry['family_names'] = to_title_case(entry.get('family_names'))
            entry['birth_location'] = to_title_case(entry.get('birth_location'))
            entry['death_location'] = to_title_case(entry.get('death_location'))
            
            # 3. Replace Abbreviations
            if entry.get('birth_location'):
                entry['birth_location'] = replace_abbreviations(entry['birth_location'])
            if entry.get('death_location'):
                entry['death_location'] = replace_abbreviations(entry['death_location'])

            # 4. Fix Relations
            entry['relation'] = fix_relation(entry.get('relation', ""))

            # 5. Handle Years (Null -> "")
            if entry.get('birth_year') is None: entry['birth_year'] = ""
            if entry.get('death_year') is None: entry['death_year'] = ""

        # Save the cleaned data back to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"Successfully cleaned {file_path}")

    except Exception as e:
        print(f"Failed to clean {file_path}: {e}")

if __name__ == "__main__":
    # Get target files from arguments or scan directory for \d+.json
    target_files = sys.argv[1:]
    if not target_files:
        # Default: clean all files that look like '1234.json'
        target_files = [f for f in os.listdir('.') if re.match(r'^\d+\.json$', f)]
    
    if not target_files:
        print("No JSON files found to clean. Usage: python3 json_cleaner.py [file1.json file2.json ...]")
    else:
        # Sort files to process them in order
        target_files.sort()
        for file_path in target_files:
            clean_json_file(file_path)
