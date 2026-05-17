import subprocess
import os
import uuid
VIDEO_EXTENSIONS = {"mp4", "mkv", "mov", "avi", "webm", "flv"}


def convert_video_to_audio(video_path: str, output_dir: str = "app/temp") -> str:
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    os.makedirs(output_dir, exist_ok=True)

    unique_name = f"{uuid.uuid4().hex}.mp3"
    output_path = os.path.join(output_dir, unique_name)

    command = [
        "ffmpeg",
        "-i", video_path,
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-b:a", "32k",
        "-y",
        output_path
    ]

    try:
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print(f"Converted: {video_path} → {output_path}")
        print(f"Audio size: {os.path.getsize(output_path) / (1024*1024):.2f} MB")

        os.remove(video_path)
        print(f"Deleted original video: {video_path}")

        return output_path

    except subprocess.CalledProcessError as e:
        if os.path.exists(output_path):
            os.remove(output_path)
        raise RuntimeError(f"ffmpeg conversion failed: {e}")

    except FileNotFoundError:
        raise RuntimeError("ffmpeg is not installed. Run: sudo apt install ffmpeg")