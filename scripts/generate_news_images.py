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
IMAGES_DIR = 'dataset/images'
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

def save_image_locally(image_bytes, filename):
    """Saves image bytes to a local file."""
    if not os.path.exists(IMAGES_DIR):
        os.makedirs(IMAGES_DIR)
    
    filepath = os.path.join(IMAGES_DIR, filename)
    try:
        with open(filepath, 'wb') as f:
            f.write(image_bytes)
        return f"images/{filename}" # Return relative path
    except Exception as e:
        print(f"Error saving image locally: {e}")
        return None

def select_dataset_file():
    """Lists JSON files in the dataset directory and asks user to select one."""
    dataset_dir = 'dataset'
    files = [f for f in os.listdir(dataset_dir) if f.endswith('.json')]
    
    if not files:
        print(f"No JSON files found in {dataset_dir}")
        return None

    print("\nAvailable Dataset Files:")
    for i, f in enumerate(files):
        print(f"{i + 1}. {f}")
    
    while True:
        try:
            selection = input("\nSelect a file number (or 'q' to quit): ")
            if selection.lower() == 'q':
                return None
            
            index = int(selection) - 1
            if 0 <= index < len(files):
                return os.path.join(dataset_dir, files[index])
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def main():
    if not GOOGLE_API_KEY:
        print("Error: GOOGLE_API_KEY not found in environment variables.")
        return

    dataset_file = select_dataset_file()
    if not dataset_file:
        print("No file selected. Exiting.")
        return

    print(f"\nProcessing file: {dataset_file}")

    try:
        with open(dataset_file, 'r') as f:
            news_items = json.load(f)
    except FileNotFoundError:
        print(f"Error: Dataset file '{dataset_file}' not found.")
        return

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
        filename = f"{item['id']}.png"
        image_url = save_image_locally(image_bytes, filename)
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

    print(f"Done. Updated {updated_count} items.")

if __name__ == "__main__":
    main()
