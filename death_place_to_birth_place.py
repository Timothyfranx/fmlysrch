import json
import os
import sys
import argparse

def death_place_to_birth_place_json(file_path, overwrite=False):
    """
    Applies the rule: Sets the death_location to match birth_location for all deceased individuals (living="No").
    This ensures that the death place always mirrors the birth place/location for deceased records.
    """
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return {
            "success": False,
            "error": f"File '{file_path}' not found."
        }

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        fixed_count = 0
        total_deceased = 0
        
        for person in data:
            living_status = str(person.get("living", "")).strip().lower()
            
            # If the individual is deceased
            if living_status == "no":
                total_deceased += 1
                birth_loc = person.get("birth_location", "")
                
                # Unconditionally align death location with birth location
                if person.get("death_location") != birth_loc:
                    person["death_location"] = birth_loc
                    fixed_count += 1
        
        # Determine output path
        if overwrite:
            output_path = file_path
        else:
            name, ext = os.path.splitext(file_path)
            output_path = f"{name}_cleaned{ext}"
            
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
            
        print(f"Processed: {file_path}")
        print(f"  - Deceased individuals aligned: {fixed_count} out of {total_deceased}")
        print(f"  - Saved to: {output_path}")
        print("-" * 30)
        
        return {
            "success": True,
            "fixed_count": fixed_count,
            "total_deceased": total_deceased,
            "output_path": output_path
        }

    except Exception as e:
        print(f"Failed to process {file_path}: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def main():
    parser = argparse.ArgumentParser(description="Force death place to always match birth place for deceased records.")
    parser.add_argument("files", nargs="+", help="JSON files to process.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite the original files instead of creating _cleaned.json.")
    
    args = parser.parse_args()
    
    for file_path in args.files:
        death_place_to_birth_place_json(file_path, args.overwrite)

if __name__ == "__main__":
    main()
