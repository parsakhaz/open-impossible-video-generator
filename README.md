# Open Impossible Video Generator

## Example Output

From `car.log`:
~~~
Generated scenario: In this snowy forest scene, a car is driving along a winding road, leaving a trail of tire tracks. Suddenly, the car appears to be levitating in mid-air, defying gravity and the laws of physics. The car is surrounded by a swirling, ethereal mist that envelops it, creating a surreal and otherworldly atmosphere.
Generated video URL: https://replicate.delivery/czjl/kAhDSFBHK7bKCVaMzCb0POiaaRnM7Q76Hfo3oeKN6JTZ9gAUA/tmp7qexdw...mp4
Generated audio URL: https://replicate.delivery/xezq/8p1SIEeBTXxhcq32y1ZABm0w5hp1Y8qM1VafdZmFuMVh9gAUA/20241231_...mp4
Final video path: [output/car_final.mp4](output/car_final.mp4)

~~~

This project uses AI to generate "impossible" continuations of real videos. It takes a video input, analyzes its final frame, generates a creative scenario, and produces a continuation that defies reality in an entertaining way.

## Features

- Extracts the final frame from input videos
- Uses Moondream to analyze the frame and generate creative scenarios
- Generates video continuations using Replicate's Minimax model
- Generates matching ambient audio using MMAudio
- Seamlessly concatenates original and generated videos with proper scaling and audio

## Prerequisites

1. Python 3.8 or later
2. FFMPEG installed on your system:
   - Windows: `winget install ffmpeg` or download from [ffmpeg.org](https://ffmpeg.org/download.html)
   - Mac: `brew install ffmpeg`
   - Linux: `sudo apt install ffmpeg` or equivalent

## Requirements

- Python 3.8+
- FFmpeg installed on your system
- API keys for:
  - Moondream
  - Replicate

## Installation

1. Clone the repository

2. Create and activate a virtual environment (recommended):
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
# Upgrade pip first
python -m pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt
```

4. Set up API keys:
- Get a Moondream API key from their platform
- Get a Replicate API token from https://replicate.com
- Set up Replicate billing: https://replicate.com/account/billing (Moondream API is free up to 5,000 queries a day)

5. Create a `.env` file with your API keys:
```
MOONDREAM_API_KEY=your-moondream-key
REPLICATE_API_TOKEN=your-replicate-token
```

## Usage

1. Place your input video in the `input` directory (supported formats: .mp4, .avi, .mov, .mkv)
   - The folder will be created automatically if it doesn't exist

2. Run the script:
```bash
python main.py
```

The script will:
1. Extract the final frame from your video
2. Generate a creative scenario based on the frame
3. Create a video continuation of that scenario
4. Add matching ambient audio
5. Combine everything into a final video in the `output` directory

## Output Structure

- `output/[video_name]_final_frame.jpg` - Extracted final frame
- `output/[video_name].log` - Processing details and generated URLs
- `output/[video_name]_final.mp4` - Final concatenated video

## Technical Details

- Uses FFmpeg for reliable video processing and concatenation
- Maintains original video dimensions and quality
- Handles color spaces correctly
- Supports various input video formats
- Generates proper audio for both original and generated segments

## Limitations

- Generated videos are typically around 5-6 seconds long
- Requires good internet connection for API calls
- Processing can take several minutes depending on video length

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

5. Video quality issues:
   - Check the input video format and codec
   - Ensure FFmpeg is properly installed
   - Check the log file for any error messages
   - Temporary files are stored in `temp` directory during processing

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
