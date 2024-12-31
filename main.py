import os
import cv2
import moondream as md
import replicate
import requests
from PIL import Image
from moviepy.editor import VideoFileClip, concatenate_videoclips, AudioFileClip
from pathlib import Path

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
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return output_path

    def extract_final_frame(self, video_path):
        """Extract the final frame from the video."""
        cap = cv2.VideoCapture(str(video_path))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 1)
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            frame_path = self.output_dir / f"{Path(video_path).stem}_final_frame.jpg"
            cv2.imwrite(str(frame_path), cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            return frame_path
        return None

    def analyze_frame(self, frame_path):
        """Analyze the frame using Moondream and generate a scenario."""
        image = Image.open(frame_path)
        encoded_image = self.moondream_model.encode_image(image)
        
        # Ask for an impossible scenario based on the image
        prompt = "Describe an impossible, viral-worthy scenario that could happen in this scene"
        scenario = self.moondream_model.query(encoded_image, prompt)["answer"]
        return scenario

    def generate_video(self, frame_path, scenario):
        """Generate a video using Minimax based on the frame and scenario."""
        output = replicate.run(
            "minimax/video-01",
            input={
                "prompt": scenario,
                "prompt_optimizer": True
            }
        )
        return output

    def generate_audio(self, video_url):
        """Generate audio for the video using MMAudio."""
        output = replicate.run(
            "zsxkib/mmaudio:4b9f801a167b1f6cc2db6ba7ffdeb307630bf411841d4e8300e63ca992de0be9",
            input={
                "video": video_url,
                "prompt": "ambient sound effects matching the scene",
                "duration": 8,
                "num_steps": 25,
                "cfg_strength": 4.5,
                "negative_prompt": "music"
            }
        )
        return output

    def combine_videos(self, original_video_path, generated_video_url, audio_url, output_base):
        """Download generated content and combine everything into final video."""
        try:
            # Download generated video and audio
            gen_video_path = self.temp_dir / f"{output_base.stem}_generated.mp4"
            audio_path = self.temp_dir / f"{output_base.stem}_audio.mp3"
            
            self.download_file(generated_video_url, gen_video_path)
            self.download_file(audio_url, audio_path)
            
            # Load videos and audio
            original_clip = VideoFileClip(str(original_video_path))
            generated_clip = VideoFileClip(str(gen_video_path))
            audio_clip = AudioFileClip(str(audio_path))
            
            # Set audio for generated clip
            generated_clip = generated_clip.set_audio(audio_clip)
            
            # Concatenate videos
            final_clip = concatenate_videoclips([original_clip, generated_clip])
            
            # Write final video
            output_path = self.output_dir / f"{output_base.stem}_final.mp4"
            final_clip.write_videofile(str(output_path))
            
            # Clean up
            original_clip.close()
            generated_clip.close()
            audio_clip.close()
            
            # Delete temporary files
            gen_video_path.unlink()
            audio_path.unlink()
            
            return output_path
            
        except Exception as e:
            print(f"Error combining videos: {str(e)}")
            return None

    def process_video(self, input_video_path):
        """Process the video through the entire pipeline."""
        try:
            output_base = self.output_dir / Path(input_video_path).stem
            
            # 1. Extract final frame
            frame_path = self.extract_final_frame(input_video_path)
            if not frame_path:
                raise Exception("Failed to extract frame from video")

            # Save processing details to a log file
            log_file = output_base.with_suffix('.log')
            with open(log_file, 'w') as f:
                # 2. Analyze frame and generate scenario
                scenario = self.analyze_frame(frame_path)
                f.write(f"Generated scenario: {scenario}\n")
                print(f"Generated scenario: {scenario}")

                # 3. Generate new video
                generated_video_url = self.generate_video(frame_path, scenario)
                f.write(f"Generated video URL: {generated_video_url}\n")
                print(f"Generated video URL: {generated_video_url}")

                # 4. Generate audio
                audio_url = self.generate_audio(generated_video_url)
                f.write(f"Generated audio URL: {audio_url}\n")
                print(f"Generated audio URL: {audio_url}")

                # 5. Combine videos
                final_video_path = self.combine_videos(input_video_path, generated_video_url, audio_url, output_base)
                if final_video_path:
                    f.write(f"Final video path: {final_video_path}\n")
                    print(f"Final video saved to: {final_video_path}")

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
    # Example usage
    MOONDREAM_API_KEY = "your-moondream-api-key"
    REPLICATE_API_TOKEN = "your-replicate-api-token"
    
    processor = VideoProcessor(MOONDREAM_API_KEY, REPLICATE_API_TOKEN)
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

if __name__ == "__main__":
    main()
