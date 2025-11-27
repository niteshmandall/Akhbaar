import json
import os
import time
import requests
import urllib.parse
import random
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
        
        # Return path relative to the dataset directory parent (which is where the script is likely run from context, 
        # but based on previous code it returned "images/filename").
        # The previous code returned f"images/{filename}" which implies it expected `dataset/images` to be the root for serving?
        # Or maybe it's relative to `public` if this is a react app?
        # The user said "put the generated images in the specific relevant folder of json files".
        # If the json is in `dataset/19_11_25.json`, the images should be in `dataset/19_11_25/`.
        # The returned URL should probably be `19_11_25/filename` if the serving root is `dataset`.
        # Let's assume the `dataset` folder is the static asset folder or similar.
        # The previous code used `IMAGES_DIR = 'dataset/images'` and returned `f"images/{filename}"`.
        # So it stripped `dataset/`.
        
        # Get the relative path from 'dataset' directory
        rel_path = os.path.relpath(filepath, 'dataset')
        # Ensure forward slashes for URLs
        return rel_path.replace(os.sep, '/')
        
    except Exception as e:
        print(f"Error saving image locally: {e}")
        return None

def main():
    # if not GOOGLE_API_KEY:
    #     print("Error: GOOGLE_API_KEY not found in environment variables.")
    #     return

    dataset_dir = 'dataset'
    if not os.path.exists(dataset_dir):
        print(f"Error: Dataset directory '{dataset_dir}' not found.")
        return

    files = [f for f in os.listdir(dataset_dir) if f.endswith('.json')]
    
    if not files:
        print(f"No JSON files found in {dataset_dir}")
        return

    print(f"Found {len(files)} JSON files to process.")

    for filename in files:
        dataset_file = os.path.join(dataset_dir, filename)
        print(f"\n{'='*40}")
        print(f"Processing file: {dataset_file}")
        print(f"{'='*40}")

        # Determine output directory based on dataset filename
        # e.g., dataset/19_11_25.json -> dataset/images/19_11_25
        base_name = os.path.splitext(filename)[0]
        output_dir = os.path.join('dataset', 'images', base_name)
        print(f"Images will be saved to: {output_dir}")

        try:
            with open(dataset_file, 'r') as f:
                news_items = json.load(f)
        except Exception as e:
            print(f"Error loading dataset file '{dataset_file}': {e}")
            continue

        updated_count = 0
        for item in news_items:
            image_exists = False
            if 'image_url' in item and item['image_url']:
                # Check if file actually exists
                # item['image_url'] is relative to dataset_dir (e.g. images/25_11_25/foo.png)
                possible_path = os.path.join(dataset_dir, item['image_url'])
                if os.path.exists(possible_path):
                    image_exists = True
            
            if image_exists:
                print(f"Skipping '{item['title']}' - Image already exists.")
                continue

            print(f"Processing: {item['title']}")
            
            # 1. Generate Prompt
            image_prompt = generate_image_prompt(item['title'], item['summary'])
            if not image_prompt:
                print("Failed to generate prompt. Skipping.")
                continue
            print(f"  Prompt: {image_prompt[:50]}...")

            # 2. Generate Image
            image_bytes = generate_image(image_prompt)
            if not image_bytes:
                print("Failed to generate image. Skipping.")
                continue
            print("  Image generated successfully.")

            # 3. Save Locally
            image_filename = f"{item['id']}.png"
            image_url = save_image_locally(image_bytes, image_filename, output_dir)
            if not image_url:
                print("Failed to save image. Skipping.")
                continue
            print(f"  Saved to: {image_url}")

            # 4. Update Item
            item['image_url'] = image_url
            item['image_prompt'] = image_prompt 
            updated_count += 1
            
            # Save periodically
            with open(dataset_file, 'w') as f:
                json.dump(news_items, f, indent=2)
            
            # Rate limiting (basic)
            time.sleep(10) 

        print(f"Finished processing {filename}. Updated {updated_count} items.")

if __name__ == "__main__":
    main()
