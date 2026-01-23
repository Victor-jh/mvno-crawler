import os
import re

CRAWLERS_DIR = r"e:\알뜰폰\크롤링\mvno_system\crawlers"

def update_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern 1: test_mode check with valid_count
    # Matches: if kwargs.get('test_mode') and valid_count >= 2:
    # We want to insert the limit check before it or replace it.
    
    # New logic block
    new_logic = """
                        limit = kwargs.get('limit', 0)
                        if limit > 0 and valid_count >= limit:
                            break
                        if kwargs.get('test_mode') and limit == 0 and valid_count >= 3:
                            break"""

    # Regex to find the test_mode block
    # It usually looks like:
    # if kwargs.get('test_mode') and valid_count >= [0-9]+:
    #     break
    
    pattern = r"(\s+)if kwargs\.get\('test_mode'\) and valid_count >= \d+:\s+break"
    
    match = re.search(pattern, content)
    if match:
        indent = match.group(1)
        replacement = new_logic.replace("\n                        ", "\n" + indent)
        # Remove the first newline of replacement to fit nicely
        replacement = replacement.lstrip('\n')
        
        new_content = re.sub(pattern, replacement, content)
        
        if new_content != content:
            print(f"Updating {filepath}")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
    else:
        print(f"Pattern not found in {filepath} - might handle manually or has different structure")
        # specific check for some crawlers that might check 'details' or use 'idx'
        pattern_idx = r"(\s+)if kwargs\.get\('test_mode'\) and idx >= \d+:\s+break"
        match_idx = re.search(pattern_idx, content)
        if match_idx:
             indent = match_idx.group(1)
             # update variable name valid_count -> idx + 1 or just idx
             # Wait, usually if idx is loop index.
             # Let's just try to be safe.
             print(f"  Skipping {filepath} (uses idx?)")
             
    return False

def main():
    files = [f for f in os.listdir(CRAWLERS_DIR) if f.endswith('_crawler.py') and f != 'base_crawler.py']
    
    count = 0
    for file in files:
        if update_file(os.path.join(CRAWLERS_DIR, file)):
            count += 1
            
    print(f"Updated {count} files.")

if __name__ == "__main__":
    main()
