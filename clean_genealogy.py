import json
import os
import sys
import argparse

def clean_genealogy_json(file_path, overwrite=False):
    """
    Applies specific genealogy rules to a JSON file:
    1. For living individuals (living="Yes"): clears death_location and death_year.
    2. For deceased individuals (living="No"): sets death_location to match birth_location.
    """
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        living_fixed = 0
        deceased_fixed = 0
        
        for person in data:
            # Normalize living status check
            living_status = str(person.get("living", "")).strip().lower()
            
            if living_status == "yes":
                # Rule: Living individuals should not have death data
                if person.get("death_location") != "" or person.get("death_year") != "":
                    person["death_location"] = ""
                    person["death_year"] = ""
                    living_fixed += 1
            
            elif living_status == "no":
                # Rule: Deceased individuals' death location should match birth location
                birth_loc = person.get("birth_location", "")
                if person.get("death_location") != birth_loc:
                    person["death_location"] = birth_loc
                    deceased_fixed += 1
        
        # Determine output path
        if overwrite:
            output_path = file_path
        else:
            name, ext = os.path.splitext(file_path)
            output_path = f"{name}_cleaned{ext}"
            
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
            
        print(f"Processed: {file_path}")
        print(f"  - Living individuals fixed: {living_fixed}")
        print(f"  - Deceased individuals fixed: {deceased_fixed}")
        print(f"  - Saved to: {output_path}")
        print("-" * 30)

    except Exception as e:
        print(f"Failed to process {file_path}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Clean genealogy JSON files based on living/deceased rules.")
    parser.add_argument("files", nargs="+", help="JSON files to process.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite the original files instead of creating _cleaned.json.")
    
    args = parser.parse_args()
    
    for file_path in args.files:
        clean_genealogy_json(file_path, args.overwrite)

if __name__ == "__main__":
    main()
