import json
import os
import difflib
import sys

def load_json(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {filepath}")
        return None

def remove_ignored_keys(data, ignored_keys):
    if isinstance(data, dict):
        return {k: remove_ignored_keys(v, ignored_keys) for k, v in data.items() if k not in ignored_keys}
    elif isinstance(data, list):
        return [remove_ignored_keys(i, ignored_keys) for i in data]
    else:
        return data

def compare_files(current_dir, before_dir):
    files = [f for f in os.listdir(current_dir) if f.endswith('.json')]
    files.sort()

    ignored_keys = ["extracted_at"]
    
    regression_count = 0
    change_count = 0
    no_change_count = 0

    print(f"{'='*20} Comparison Report {'='*20}")

    for filename in files:
        current_path = os.path.join(current_dir, filename)
        before_path = os.path.join(before_dir, filename)

        if not os.path.exists(before_path):
            print(f"[NEW] {filename} found in current but not in before.")
            continue

        current_data = load_json(current_path)
        before_data = load_json(before_path)

        if current_data is None or before_data is None:
            continue

        # Clean data
        current_data_clean = remove_ignored_keys(current_data, ignored_keys)
        before_data_clean = remove_ignored_keys(before_data, ignored_keys)

        # Convert to string for diff
        current_str = json.dumps(current_data_clean, indent=2, sort_keys=True, ensure_ascii=False)
        before_str = json.dumps(before_data_clean, indent=2, sort_keys=True, ensure_ascii=False)

        if current_str == before_str:
            no_change_count += 1
            # print(f"[OK] {filename} - No changes.")
        else:
            change_count += 1
            print(f"\n[CHANGED] {filename}")
            
            diff = difflib.unified_diff(
                before_str.splitlines(),
                current_str.splitlines(),
                fromfile=f'before/{filename}',
                tofile=f'current/{filename}',
                lineterm=''
            )
            
            # Print the diff
            diff_text = '\n'.join(diff)
            print(diff_text)
            
            # Simple heuristic analysis
            # If we see keys disappearing or becoming null/zero where there were values, it might be a regression.
            if "- " in diff_text and "+ " not in diff_text: 
                 print("  WARNING: Potential data loss (deletion without replacement)")


    print(f"\n{'='*20} Summary {'='*20}")
    print(f"Total files checked: {len(files)}")
    print(f"Unchanged: {no_change_count}")
    print(f"Changed: {change_count}")
    print(f"{'='*50}")

if __name__ == "__main__":
    current_dir = "out"
    before_dir = "out/before"
    
    if not os.path.exists(current_dir):
        print(f"Directory {current_dir} does not exist.")
        sys.exit(1)
    if not os.path.exists(before_dir):
        print(f"Directory {before_dir} does not exist.")
        sys.exit(1)
        
    compare_files(current_dir, before_dir)
