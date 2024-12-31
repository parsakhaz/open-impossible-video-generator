import os
import cv2
import moondream as md
import replicate
import requests
from PIL import Image
from moviepy.editor import VideoFileClip, concatenate_videoclips, AudioFileClip
from pathlib import Path
from dotenv import load_dotenv
import time
import subprocess
import json

# Load environment variables from .env file
load_dotenv()

class VideoProcessor:
    def __init__(self, moondream_api_key, replicate_api_token):
        """Initialize the video processor with necessary API keys."""
        self.moondream_model = md.vl(api_key=moondream_api_key)
        os.environ["REPLICATE_API_TOKEN"] = replicate_api_token
        
        # Create input and output directories if they don't exist
        self.input_dir = Path("input")
        self.output_dir = Path("output")
        self.temp_dir = Path("temp")
        for dir in [self.input_dir, self.output_dir, self.temp_dir]:
            dir.mkdir(exist_ok=True)

    def download_file(self, url, output_path):
        """Download a file from a URL to the specified path."""
        print(f"   Downloading file from {url[:60]}...")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"   Downloaded to {output_path}")
        return output_path

    def run_ffmpeg(self, command):
        """Run an FFmpeg command and handle errors."""
        try:
            # Add progress stats to the command
            command.extend(['-stats', '-v', 'warning'])
            # Don't capture output so we can see progress in real-time
            result = subprocess.run(command, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg error: {str(e)}")
            return False

    def extract_final_frame(self, video_path):
        """Extract the final frame from the video."""
        print("   Opening video file...")
        cap = cv2.VideoCapture(str(video_path))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        print(f"   Video has {total_frames} frames, extracting last frame...")
        cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 1)
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            frame_path = self.output_dir / f"{Path(video_path).stem}_final_frame.jpg"
            # Save directly in BGR format without color conversion
            cv2.imwrite(str(frame_path), frame)
            return frame_path
        return None

    def analyze_frame(self, frame_path):
        """Analyze the frame using Moondream and generate a scenario."""
        print("   Loading image for analysis...")
        image = Image.open(frame_path)
        print("   Encoding image with Moondream...")
        encoded_image = self.moondream_model.encode_image(image)
        
        print("   Generating scenario from image...")
        prompt = "Describe a surreal, mind-bending scenario that could happen in this scene. Make it visually spectacular and impossible in real life, like something from a viral video that would break the internet. Focus on unexpected transformations, physics-defying events, or magical occurrences."
        scenario = self.moondream_model.query(encoded_image, prompt)["answer"]
        return scenario

    def upload_image(self, image_path):
        """Convert image to base64 data URI."""
        try:
            print("   Converting image to base64...")
            with open(image_path, 'rb') as f:
                import base64
                image_data = f.read()
                base64_data = base64.b64encode(image_data).decode('utf-8')
                mime_type = 'image/jpeg' if str(image_path).lower().endswith('.jpg') or str(image_path).lower().endswith('.jpeg') else 'image/png'
                return f"data:{mime_type};base64,{base64_data}"
        except Exception as e:
            print(f"   Error converting image to base64: {str(e)}")
            return None

    def generate_video(self, frame_path, scenario):
        """Generate a video using Minimax based on the frame and scenario."""
        # First convert image to base64
        print("   Converting image to base64...")
        frame_url = self.upload_image(frame_path)
        if not frame_url:
            raise Exception("Failed to convert frame to data URI")
            
        # Now start the video generation with progress updates
        print("\n   Running prediction...")
        print(f"   Initializing video generation with prompt: {scenario[:100]}...")
        print("   Generating video...")
        
        start_time = time.time()
        last_update = start_time
        
        def prediction_callback(event_data):
            nonlocal last_update
            current_time = time.time()
            # Update every 30 seconds
            if current_time - last_update >= 30:
                print("   Still generating...")
                last_update = current_time
        
        output = replicate.run(
            "minimax/video-01",
            input={
                "prompt": scenario,
                "prompt_optimizer": True,
                "first_frame_image": frame_url
            },
            callback=prediction_callback
        )
        
        total_time = time.time() - start_time
        print(f"   Generated video in {total_time:.1f} seconds")
        
        # Extract URL from output
        if hasattr(output, 'output_url'):
            video_url = output.output_url
        elif isinstance(output, list) and len(output) > 0:
            video_url = output[0]
        else:
            video_url = str(output)
            
        print(f"   Video generated: {video_url[:100]}")
        return video_url

    def generate_audio(self, video_url):
        """Generate audio for the video using MMAudio."""
        print("   Sending request to MMAudio model...")
        print("   This may take a few minutes...")
        output = replicate.run(
            "zsxkib/mmaudio:4b9f801a167b1f6cc2db6ba7ffdeb307630bf411841d4e8300e63ca992de0be9",
            input={
                "video": str(video_url),
                "prompt": "ambient sound effects matching the scene",
                "duration": 8.0,
                "num_steps": 25,
                "cfg_strength": 4.5,
                "negative_prompt": "music",
                "seed": -1
            }
        )
        print("   Audio generation complete")
        
        # Extract URL from output
        if hasattr(output, 'output_url'):
            audio_url = output.output_url
        elif isinstance(output, list) and len(output) > 0:
            audio_url = output[0]
        else:
            audio_url = str(output)
            
        print(f"   Audio generated: {audio_url[:100]}")
        return audio_url

    def combine_videos(self, original_video_path, generated_video_url, audio_url, output_base):
        """Download generated content and combine everything into final video."""
        try:
            print("\n5. Combining all components...")
            # Download generated video and audio
            gen_video_path = self.temp_dir / f"{output_base.stem}_generated.mp4"
            audio_path = self.temp_dir / f"{output_base.stem}_audio.mp3"
            
            print("   Downloading generated video...")
            self.download_file(generated_video_url, gen_video_path)
            print("   Downloading generated audio...")
            self.download_file(audio_url, audio_path)
            
            # Get original video dimensions
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height',
                '-of', 'json',
                str(original_video_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            info = json.loads(result.stdout)
            width = info['streams'][0]['width']
            height = info['streams'][0]['height']
            print(f"   Original video dimensions: {width}x{height}")
            
            # First add audio to generated video
            print("   Adding audio to generated video...")
            gen_with_audio = self.temp_dir / f"{output_base.stem}_generated_with_audio.mp4"
            cmd = [
                'ffmpeg', '-y',
                '-i', str(gen_video_path),
                '-i', str(audio_path),
                '-c:v', 'copy',  # Just copy video
                '-c:a', 'aac',   # Convert audio to AAC
                '-shortest',     # Match shortest duration
                str(gen_with_audio)
            ]
            if not self.run_ffmpeg(cmd):
                raise Exception("Failed to add audio to generated video")

            # Add silent audio to original video if needed
            print("   Processing original video...")
            temp_original = self.temp_dir / f"{output_base.stem}_original_with_audio.mp4"
            cmd = [
                'ffmpeg', '-y',
                '-i', str(original_video_path),
                '-f', 'lavfi',
                '-i', 'anullsrc=channel_layout=mono:sample_rate=44100',
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-shortest',
                str(temp_original)
            ]
            if not self.run_ffmpeg(cmd):
                raise Exception("Failed to process original video")

            # Now concatenate both videos
            print("   Concatenating videos (this may take a few minutes)...")
            output_path = self.output_dir / f"{output_base.stem}_final.mp4"
            cmd = [
                'ffmpeg', '-y',
                '-i', str(temp_original),
                '-i', str(gen_with_audio),
                '-filter_complex',
                f'[1:v]scale={width}:{height},setsar=1:1,fps=30[v1];[0:v]fps=30[v0];[v0][0:a][v1][1:a]concat=n=2:v=1:a=1[outv][outa]',
                '-map', '[outv]',
                '-map', '[outa]',
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-profile:v', 'high',
                '-level:v', '4.0',
                '-maxrate', '10M',
                '-bufsize', '20M',
                '-crf', '23',
                '-g', '60',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-vsync', '2',  # Fix frame timing issues
                '-movflags', '+faststart',
                str(output_path)
            ]
            if not self.run_ffmpeg(cmd):
                raise Exception("Failed to concatenate videos")
            
            print("   Cleaning up temporary files...")
            for file in [gen_video_path, audio_path, gen_with_audio, temp_original]:
                if file.exists():
                    file.unlink()
            
            return output_path
            
        except Exception as e:
            print(f"Error combining videos: {str(e)}")
            return None

    def process_video(self, input_video_path):
        """Process the video through the entire pipeline."""
        try:
            print(f"\nDetailed processing steps for {input_video_path}:")
            output_base = self.output_dir / Path(input_video_path).stem
            
            # 1. Extract final frame
            print("1. Extracting final frame...")
            frame_path = self.extract_final_frame(input_video_path)
            if not frame_path:
                raise Exception("Failed to extract frame from video")
            print(f"   Frame extracted to: {frame_path}")
            
            # Save processing details to a log file
            log_file = output_base.with_suffix('.log')
            with open(log_file, 'w') as f:
                # 2. Analyze frame and generate scenario
                print("2. Analyzing frame with Moondream...")
                try:
                    scenario = self.analyze_frame(frame_path)
                    f.write(f"Generated scenario: {scenario}\n")
                    print(f"   Scenario generated: {scenario}")
                except Exception as e:
                    print(f"   Error in Moondream analysis: {str(e)}")
                    raise

                # 3. Generate new video
                print("3. Generating video with Replicate...")
                try:
                    generated_video_url = self.generate_video(frame_path, scenario)
                    f.write(f"Generated video URL: {generated_video_url}\n")
                    print(f"   Video generated: {generated_video_url}")
                except Exception as e:
                    print(f"   Error in video generation: {str(e)}")
                    raise

                # 4. Generate audio
                print("4. Generating audio...")
                try:
                    audio_url = self.generate_audio(generated_video_url)
                    f.write(f"Generated audio URL: {audio_url}\n")
                    print(f"   Audio generated: {audio_url}")
                except Exception as e:
                    print(f"   Error in audio generation: {str(e)}")
                    raise

                # 5. Combine videos
                print("5. Combining videos and audio...")
                final_video_path = self.combine_videos(input_video_path, generated_video_url, audio_url, output_base)
                if final_video_path:
                    f.write(f"Final video path: {final_video_path}\n")
                    print(f"   Final video saved to: {final_video_path}")
                else:
                    print("   Error: Failed to combine videos")

            return {
                "original_video": str(input_video_path),
                "generated_video": generated_video_url,
                "audio": audio_url,
                "scenario": scenario,
                "log_file": str(log_file),
                "final_video": str(final_video_path) if final_video_path else None
            }

        except Exception as e:
            print(f"Error processing video: {str(e)}")
            return None

    def process_input_folder(self):
        """Process all videos in the input folder."""
        supported_formats = ['.mp4', '.avi', '.mov', '.mkv']
        results = []
        
        for video_file in self.input_dir.iterdir():
            if video_file.suffix.lower() in supported_formats:
                print(f"\nProcessing {video_file.name}...")
                result = self.process_video(video_file)
                if result:
                    results.append(result)
                    
        return results

def main():
    # Get API keys from environment variables
    MOONDREAM_API_KEY = os.getenv("MOONDREAM_API_KEY")
    REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
    
    # Validate API keys
    if not MOONDREAM_API_KEY:
        print("Error: MOONDREAM_API_KEY environment variable is not set")
        return
    if not REPLICATE_API_TOKEN:
        print("Error: REPLICATE_API_TOKEN environment variable is not set")
        return
        
    try:
        processor = VideoProcessor(MOONDREAM_API_KEY, REPLICATE_API_TOKEN)
        
        # Verify input directory has videos
        supported_formats = ['.mp4', '.avi', '.mov', '.mkv']
        video_files = [f for f in processor.input_dir.iterdir() 
                      if f.suffix.lower() in supported_formats]
        
        if not video_files:
            print("Error: No supported video files found in the input directory")
            print(f"Supported formats: {', '.join(supported_formats)}")
            return
            
        print(f"Found {len(video_files)} video(s) to process")
        results = processor.process_input_folder()
        
        if results:
            print("\nProcessing completed successfully!")
            for result in results:
                print(f"\nResults for {Path(result['original_video']).name}:")
                print(f"Log file: {result['log_file']}")
                if result['final_video']:
                    print(f"Final video: {result['final_video']}")
        else:
            print("\nNo videos were processed successfully!")
            
    except Exception as e:
        print(f"Critical error: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
