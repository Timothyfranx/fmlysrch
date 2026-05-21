import os
import shutil
import glob

def cleanup():
    patterns = [
        "fs_session_*",
        "familysearch_session_data",
        "fs_persistent_session",
        "fs_temp_session",
        "debug_*.png",
        "diagnose_screenshot.png",
        "look.png"
    ]
    
    removed_count = 0
    for pattern in patterns:
        paths = glob.glob(pattern)
        for path in paths:
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                    print(f"Removed directory: {path}")
                else:
                    os.remove(path)
                    print(f"Removed file: {path}")
                removed_count += 1
            except Exception as e:
                print(f"Error removing {path}: {e}")
                
    if removed_count == 0:
        print("No temporary session data found to clean.")
    else:
        print(f"\nCleanup complete. Removed {removed_count} items.")

if __name__ == "__main__":
    confirm = input("This will delete all persistent session data and temporary screenshots. Continue? (y/n): ")
    if confirm.lower() == 'y':
        cleanup()
    else:
        print("Cleanup cancelled.")
