import json
import os
import sys

def check_missing(dataset_dir):
    files = [f for f in os.listdir(dataset_dir) if f.endswith('.json')]
    missing_map = {}
    total_missing = 0
    
    print("Checking for missing images...")
    for filename in files:
        filepath = os.path.join(dataset_dir, filename)
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            count = 0
            for item in data:
                if 'image_url' not in item or not item['image_url']:
                    count += 1
                elif not os.path.exists(os.path.join(dataset_dir, item['image_url'])):
                    count += 1
            
            if count > 0:
                missing_map[filename] = count
                total_missing += count
        except Exception as e:
            print(f"Error reading {filename}: {e}")

    if total_missing == 0:
        print("All images present.")
    else:
        print(f"Found {total_missing} missing images across {len(missing_map)} files.")
        for f, c in missing_map.items():
            print(f"  {f}: {c} missing")
    return missing_map

def update_json(dataset_dir):
    files = [f for f in os.listdir(dataset_dir) if f.endswith('.json')]
    updated_total = 0
    
    print("\nUpdating JSON files with local images...")
    for filename in files:
        filepath = os.path.join(dataset_dir, filename)
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
        except:
            continue
            
        updated = 0
        base_name = os.path.splitext(filename)[0]
        image_subdir = os.path.join(dataset_dir, 'images', base_name)
        
        if not os.path.exists(image_subdir):
            continue
            
        for item in data:
            if 'id' not in item: continue
            
            img_name = f"{item['id']}.png"
            img_path = os.path.join(image_subdir, img_name)
            
            if os.path.exists(img_path):
                rel_path = f"images/{base_name}/{img_name}"
                if item.get('image_url') != rel_path:
                    item['image_url'] = rel_path
                    item['image_prompt'] = "Generated via Antigravity Agent"
                    updated += 1
        
        if updated > 0:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"Updated {updated} items in {filename}")
            updated_total += updated

    if updated_total == 0:
        print("No JSON updates needed.")
    else:
        print(f"Total items updated: {updated_total}")

if __name__ == "__main__":
    dataset_dir = r'dataset'
    if len(sys.argv) > 1 and sys.argv[1] == 'update':
        update_json(dataset_dir)
    else:
        check_missing(dataset_dir)
        print("\nTo update JSONs with found images, run: python scripts/agent_image_helper.py update")
