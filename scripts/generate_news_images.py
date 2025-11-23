import json
import os
import time
from google import genai
from google.genai import types
import io
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
# IMAGES_DIR = 'dataset/images' # Removed global constant as it's now dynamic
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# Initialize Gemini Client
client = genai.Client(api_key=GOOGLE_API_KEY)

def generate_image_prompt(title, summary):
    """Generates a detailed image prompt using Gemini."""
    prompt = f"""
    Create a detailed and vivid image generation prompt for a news article.
    
    Title: {title}
    Summary: {summary}
    
    The prompt should describe a realistic, high-quality image suitable for a news website. 
    Focus on the visual elements, mood, and key subjects. 
    Do not include text in the image unless absolutely necessary.
    Output ONLY the prompt text.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"Error generating prompt: {e}")
        return None

def generate_image(prompt):
    """Generates an image using Imagen 3."""
    try:
        response = client.models.generate_images(
            model='imagen-4.0-fast-generate-001',
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
            )
        )
        if response.generated_images:
            return response.generated_images[0].image.image_bytes
        return None
    except Exception as e:
        print(f"Error generating image: {e}")
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
    if not GOOGLE_API_KEY:
        print("Error: GOOGLE_API_KEY not found in environment variables.")
        return

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
            if 'image_url' in item and item['image_url']:
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
            time.sleep(2) 

        print(f"Finished processing {filename}. Updated {updated_count} items.")

if __name__ == "__main__":
    main()
