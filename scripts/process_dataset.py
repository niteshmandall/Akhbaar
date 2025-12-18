import json
import os
import time
import requests
import urllib.parse
import random
import uuid
import glob
from collections import defaultdict
import re

# --- ID Management Functions ---

def generate_short_id():
    """Generates a short, unique ID (8 chars)."""
    return str(uuid.uuid4())[:8]

def load_json(filepath):
    """Loads JSON data from a file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None

def save_json(filepath, data):
    """Saves JSON data to a file."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error writing {filepath}: {e}")

def get_image_path(dataset_dir, json_filename, image_id):
    """Constructs the expected path for an image."""
    date_folder = os.path.splitext(os.path.basename(json_filename))[0]
    return os.path.join(dataset_dir, 'images', date_folder, f"{image_id}.png")

def ensure_unique_ids(dataset_dir):
    """Scans and fixes duplicate IDs across the dataset."""
    print(f"\n{'='*40}")
    print("Checking for Duplicate IDs...")
    print(f"{'='*40}")

    json_files = glob.glob(os.path.join(dataset_dir, '**', '*.json'), recursive=True)
    
    if not json_files:
        print("No JSON files found to check.")
        return

    # Map: filepath -> data (list of dicts)
    file_data_map = {}
    id_registry = defaultdict(list)

    # 1. Load Data
    for filepath in json_files:
        data = load_json(filepath)
        if data is None or not isinstance(data, list):
            continue
            
        file_data_map[filepath] = data
        
        for idx, item in enumerate(data):
            if 'id' in item:
                item_id = item['id']
                id_registry[item_id.lower()].append((filepath, idx))

    files_modified = set()

    # 2. Fix Duplicates
    for id_lower, occurrences in id_registry.items():
        if len(occurrences) > 1:
            print(f"\nDuplicate ID found: '{id_lower}' (seen {len(occurrences)} times)")
            
            # Sort stable
            occurrences.sort(key=lambda x: os.path.basename(x[0]))
            
            print(f"  Keeping: {os.path.basename(occurrences[0][0])} (Index {occurrences[0][1]})")
            
            for i in range(1, len(occurrences)):
                filepath, idx = occurrences[i]
                data = file_data_map[filepath]
                item = data[idx]
                old_id = item['id']
                
                new_id = generate_short_id()
                while new_id.lower() in id_registry: 
                     new_id = generate_short_id()

                print(f"  Changing: {os.path.basename(filepath)} (Index {idx}) -> New ID: {new_id}")
                
                # Image handling
                old_image_path = get_image_path(dataset_dir, os.path.basename(filepath), old_id)
                if os.path.exists(old_image_path):
                    new_image_path = get_image_path(dataset_dir, os.path.basename(filepath), new_id)
                    try:
                        os.rename(old_image_path, new_image_path)
                        print(f"    Renamed image: {os.path.basename(old_image_path)} -> {os.path.basename(new_image_path)}")
                        
                        if 'image_url' in item:
                             date_folder = os.path.splitext(os.path.basename(filepath))[0]
                             new_relative_path = f"images/{date_folder}/{new_id}.png"
                             item['image_url'] = new_relative_path
                    except OSError as e:
                        print(f"    Error renaming image {old_image_path}: {e}")

                item['id'] = new_id
                files_modified.add(filepath)

    if files_modified:
        print(f"\nSaving {len(files_modified)} modified files...")
        for filepath in files_modified:
            save_json(filepath, file_data_map[filepath])
        print("ID Uniqueness Check Completed: Fixes Applied.")

    else:
        print("ID Uniqueness Check Completed: No duplicates found.")


def clean_citations(dataset_dir):
    """Removes citations like [cite: 45] from title, summary, and raw_text."""
    print(f"\n{'='*40}")
    print("Cleaning Citations...")
    print(f"{'='*40}")

    json_files = glob.glob(os.path.join(dataset_dir, '**', '*.json'), recursive=True)
    
    if not json_files:
        print("No JSON files found to check.")
        return

    citation_pattern = re.compile(r'\[cite:\s*[\d,\s]+\]')
    files_modified = 0

    for filepath in json_files:
        data = load_json(filepath)
        if data is None or not isinstance(data, list):
            continue

        file_changed = False
        for item in data:
            fields_to_clean = ['title', 'summary', 'raw_text']
            for field in fields_to_clean:
                if field in item and isinstance(item[field], str):
                    original_text = item[field]
                    cleaned_text = citation_pattern.sub('', original_text).strip()
                    # Also clean up any double spaces created by removal
                    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
                    
                    if original_text != cleaned_text:
                        item[field] = cleaned_text
                        file_changed = True
                        # print(f"Cleaned {field} in {item.get('id', 'unknown')}: {original_text} -> {cleaned_text}")

        if file_changed:
            save_json(filepath, data)
            files_modified += 1
            print(f"Cleaned citations in: {os.path.basename(filepath)}")

    if files_modified > 0:
        print(f"Citation Cleaning Completed: {files_modified} files updated.")
    else:
        print("Citation Cleaning Completed: No citations found.")




# --- Image Generation Functions ---

def generate_image_prompt(title, summary):
    """Generates a detailed image prompt using Pollinations AI (Text)."""
    prompt = f"""
    Create a detailed and vivid image generation prompt for a news article.
    
    Title: {title}
    Summary: {summary}
    
    The prompt should describe a realistic, high-quality image suitable for a news website. 
    Focus on the visual elements, mood, and key subjects. 
    Do not include text in the image.
    Keep the prompt UNDER 300 CHARACTERS.
    Output ONLY the prompt text.
    """
    
    try:
        # Encode the prompt for the URL
        encoded_prompt = urllib.parse.quote(prompt)
        # Pollinations AI text endpoint
        url = f"https://text.pollinations.ai/{encoded_prompt}"
        
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.text.strip()
        else:
            print(f"Error generating prompt: Status {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error generating prompt with Pollinations AI: {e}")
        return None

def generate_image(prompt):
    """Generates an image using Pollinations AI (Free) with retry logic."""
    # Encode the prompt for the URL
    encoded_prompt = urllib.parse.quote(prompt)
    # Add a random seed to ensure variety
    seed = random.randint(0, 10000)
    # Use the correct endpoint and add model=sdxl
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?seed={seed}&width=1024&height=1024&nologo=true&model=sdxl"
    
    for attempt in range(5):  # 5 retry attempts
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                return response.content
            else:
                print(f"  Attempt {attempt+1} failed with status: {response.status_code}")
        except Exception as e:
            print(f"  Attempt {attempt+1} failed with error: {e}")

        if attempt < 4:
            wait_time = 2 ** attempt  # Exponential backoff: 1, 2, 4, 8 seconds
            print(f"  Retrying in {wait_time} seconds...")
            time.sleep(wait_time)

    print("  Failed to generate image after 5 attempts.")
    return None

def save_image_locally(image_bytes, filename, output_dir):
    """Saves image bytes to a local file in the specified directory."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    filepath = os.path.join(output_dir, filename)
    try:
        with open(filepath, 'wb') as f:
            f.write(image_bytes)
        
        # Get the relative path from 'dataset' directory
        rel_path = os.path.relpath(filepath, 'dataset')
        # Ensure forward slashes for URLs
        return rel_path.replace(os.sep, '/')
        
    except Exception as e:
        print(f"Error saving image locally: {e}")
        return None

def process_images(dataset_dir):
    """Scans for missing images and generates them."""
    print(f"\n{'='*40}")
    print("Checking for Missing Images...")
    print(f"{'='*40}")

    json_files = glob.glob(os.path.join(dataset_dir, '**', '*.json'), recursive=True)
    
    if not json_files:
        print(f"No JSON files found in {dataset_dir}")
        return

    print(f"Found {len(json_files)} JSON files to process.")

    for dataset_file in json_files:
        filename = os.path.basename(dataset_file)
        
        # Determine output directory based on dataset filename
        base_name = os.path.splitext(filename)[0]
        output_dir = os.path.join(dataset_dir, 'images', base_name)
        
        try:
            with open(dataset_file, 'r', encoding='utf-8') as f:
                news_items = json.load(f)
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            continue

        updated_count = 0
        needs_save = False

        print(f"\nProcessing file: {filename}")
        
        for item in news_items:
            image_exists = False
            if 'image_url' in item and item['image_url']:
                possible_path = os.path.join(dataset_dir, item['image_url'])
                if os.path.exists(possible_path):
                    image_exists = True
            
            if image_exists:
                continue

            print(f"Generating image for: {item['title'][:50]}...")
            
            # 1. Generate Prompt
            image_prompt = generate_image_prompt(item['title'], item['summary'])
            if not image_prompt:
                print("  Failed to generate prompt. Skipping.")
                continue
            
            # 2. Generate Image
            image_bytes = generate_image(image_prompt)
            if not image_bytes:
                print("  Failed to generate image. Skipping.")
                continue

            # 3. Save Locally
            # Ensure we have an ID
            if 'id' not in item or not item['id']:
                 item['id'] = generate_short_id()
                 print(f"  Generated missing ID: {item['id']}")
            
            image_filename = f"{item['id']}.png"
            image_url = save_image_locally(image_bytes, image_filename, output_dir)
            if not image_url:
                print("  Failed to save image. Skipping.")
                continue
            print(f"  Saved to: {image_url}")

            # 4. Update Item
            item['image_url'] = image_url
            item['image_prompt'] = image_prompt 
            updated_count += 1
            needs_save = True
            
            # Rate limiting
            time.sleep(5) 

        if needs_save:
            with open(dataset_file, 'w') as f:
                json.dump(news_items, f, indent=2)
            print(f"  Updated {updated_count} items in {filename}.")
        else:
            print(f"  No missing images in {filename}.")

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dataset_dir = os.path.join(root_dir, 'dataset')
    
    if not os.path.exists(dataset_dir):
        print(f"Error: Dataset directory '{dataset_dir}' not found.")
        return

    # 1. Ensure IDs are unique
    ensure_unique_ids(dataset_dir)

    # 2. Clean Citations
    clean_citations(dataset_dir)
    
    # 3. Process Images

    process_images(dataset_dir)

if __name__ == "__main__":
    main()
