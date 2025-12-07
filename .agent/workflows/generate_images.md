---
description: Generate images for new news items using the Agent
---

# Generate News Images Workflow

This workflow outlines how the Antigravity Agent should manually generate images for new news items when a new PDF/JSON is added to the dataset.

## Trigger

- A new JSON file is added to `dataset/`.
- User requests image generation for recent items.

## Steps

### 1. Scan for Missing Images

Run a check to see which items lack images.

```python
# scripts/check_missing_images.py (Create temporary if needed)
import json
import os
# ... logic to find items without 'image_url' ...
```

_Suggestion: Use `check_missing_images.py` helper if available or write a quick script._

### 2. Generate Images

Use the `generate_image` tool.

- **Prompt Strategy**: Use the news title and summary to create a detailed, high-quality prompt.
- **Naming**: Use the item's `id` as the filename (e.g., `a1b2c3d4.png`).
- **Model**: Use "Nano Banana Pro" (Gemini 3 Pro) or best available.

### 3. Save Images

- Create a directory: `dataset/images/<date_dir>/` (matching the json filename).
- Save generated images there.

### 4. Update JSON

- Update the JSON file to include the local path in `image_url`.
- Format: `images/<date_dir>/<id>.png`.
- Update `image_prompt` field if possible.
- **CRITICAL**: Do NOT touch, modify, or reformat the `raw_text` field. Preserve it exactly as is.

### 5. Verify

- Ensure images are loadable.
- Check that `image_url` paths are relative and correct.

## Auto-Run

// turbo-all
This workflow is largely manual/interactive for the agent, but specific scripts can be auto-run if defined.
