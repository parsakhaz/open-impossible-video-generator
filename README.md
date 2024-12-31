# Viral Video Generator

This script takes a short video clip and automatically creates a viral version by:
1. Extracting the final frame
2. Using Moondream to analyze it and generate an impossible scenario
3. Using Minimax to generate a video based on that scenario
4. Adding audio using MMAudio
5. Combining everything into a final video that shows the original clip followed by the AI-generated version

## Prerequisites

1. Python 3.7 or later
2. FFMPEG installed on your system:
   - Windows: `winget install ffmpeg` or download from [ffmpeg.org](https://ffmpeg.org/download.html)
   - Mac: `brew install ffmpeg`
   - Linux: `sudo apt install ffmpeg` or equivalent

## Setup

1. Create and activate a virtual environment (recommended):
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
# Upgrade pip first
python -m pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt
```

3. Set up API keys:
- Get a Moondream API key from their platform
- Get a Replicate API token from https://replicate.com

4. Set up Replicate billing (Moondream API is free up to 5,000 queries a day):
- https://replicate.com/account/billing

5. Update the API keys in `main.py`:
```python
MOONDREAM_API_KEY = "your-moondream-api-key"
REPLICATE_API_TOKEN = "your-replicate-api-token"
```

## Usage

1. Place your video files in the `input` folder (supported formats: .mp4, .avi, .mov, .mkv)
   - The folder will be created automatically if it doesn't exist

2. Run the script:
```bash
python main.py
```

3. Check the `output` folder for results:
   - Final frames from videos (.jpg)
   - Processing logs (.log) containing:
     - Generated scenario description
     - Generated video URL
     - Generated audio URL
     - Path to final combined video
   - Final combined videos (_final.mp4)

The script will:
1. Process all supported videos in the input folder
2. Generate an AI version for each video
3. Combine original + AI version into a single video
4. Save all results to the output folder
5. Clean up temporary files automatically

## Troubleshooting

Common issues and solutions:

1. `ModuleNotFoundError: No module named 'cv2'`:
   ```bash
   pip uninstall opencv-python
   pip install opencv-python
   ```

2. FFMPEG related errors:
   - Ensure FFMPEG is installed (see Prerequisites section)
   - Add FFMPEG to your system PATH
   - Try restarting your terminal/IDE after installing FFMPEG

3. Memory errors with large videos:
   - Try processing shorter video clips
   - Ensure you have enough free disk space
   - Close other memory-intensive applications

4. API errors:
   - Verify your API keys are correct
   - Check your Replicate billing status
   - Ensure you're within API usage limits 

> **Note for ARM64 Windows Users**: If you encounter build errors with moondream package, you can use the Moondream API directly instead:
> ```bash
> curl --location 'https://api.moondream.ai/v1/query' \
> --header 'X-Moondream-Auth: <API KEY FROM console.moondream.ai>' \
> --header 'Content-Type: application/json' \
> --data '{
>     "image_url": "data:image/jpeg;base64,<BASE64-STRING>",
>     "question": "What is this?",
>     "stream": false
> }'
> ```
> Get your API key from [console.moondream.ai](https://console.moondream.ai)
