import os
import time
import subprocess
import numpy as np
from scipy.io import wavfile

CHANNELS = [
    "https://www.youtube.com/@IShowSpeed/live",
    "https://www.youtube.com/@KaiCenatLive/live",
    "https://www.youtube.com/@xQcOW/live",
    "https://www.youtube.com/@caseoh_/live"
]

OUTPUT_DIR = "Clips_Gata"
TEMP_DIR = "temp"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

def download_live_chunk(channel_url, chunk_path, duration=180):
    cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--download-sections", f"*0:00-0:{duration//60}:00",
        "--force-overwrites",
        "--no-part",
        "-o", chunk_path,
        channel_url
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=240)
        return os.path.exists(chunk_path) and os.path.getsize(chunk_path) > 200000
    except Exception:
        return False

def find_hype_timestamps(video_path, clip_len=40, top_n=2):
    audio_path = video_path.replace(".mp4", ".wav")
    subprocess.run([
        "ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1", audio_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if not os.path.exists(audio_path):
        return []

    try:
        rate, data = wavfile.read(audio_path)
        os.remove(audio_path)
    except Exception:
        return []

    samples_per_sec = rate
    total_secs = len(data) // samples_per_sec
    if total_secs < clip_len:
        return []

    energies = [
        np.sqrt(np.mean(data[i*samples_per_sec:(i+1)*samples_per_sec].astype(np.float64)**2))
        for i in range(total_secs)
    ]

    peaks = []
    sorted_indices = np.argsort(energies)[::-1]
    for idx in sorted_indices:
        if all(abs(idx - p) > clip_len for p in peaks):
            peaks.append(idx)
        if len(peaks) >= top_n:
            break
    return peaks

def make_vertical_clip(video_path, peak_sec, out_path, duration=40):
    start = max(0, peak_sec - 15)
    filter_complex = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:10[bg];"
        "[0:v]scale=1080:-1[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2"
    )
    cmd = [
        "ffmpeg", "-y", "-ss", str(start), "-i", video_path, "-t", str(duration),
        "-filter_complex", filter_complex,
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", out_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

print("🔍 Verific streamurile live...")
for url in CHANNELS:
    streamer = url.split("@")[1].split("/")[0]
    chunk_file = os.path.join(TEMP_DIR, f"{streamer}.mp4")
    
    if download_live_chunk(url, chunk_file, duration=180):
        print(f"🚨 Live găsit la {streamer}! Tai clipurile...")
        peaks = find_hype_timestamps(chunk_file, clip_len=40, top_n=2)
        for i, peak in enumerate(peaks):
            ts = int(time.time())
            final_clip = os.path.join(OUTPUT_DIR, f"{streamer}_GTA6_{ts}_{i}.mp4")
            make_vertical_clip(chunk_file, peak, final_clip)
            print(f"✅ Generat: {final_clip}")
        if os.path.exists(chunk_file):
            os.remove(chunk_file)
    else:
        print(f"⏳ {streamer} nu e live acum.")
