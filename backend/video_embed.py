# video_fuser.py
# Build 10s multimodal (video frames + auto-transcribed audio) fused embeddings and store in Qdrant.
# - Visual encoder: CLIP ViT-B/32 (512-d, unit-normalized)
# - Text encoder: OpenAI text-embedding-3-small (1536-d, then projected to 512-d)
# - Fusion: v_fused = normalize(alpha * v_frames_mean + (1 - alpha) * Proj(text_1536))
# - Storage: Qdrant collection "video_fused_512" (COSINE), one point per 10s window

import os
import uuid
import math
import subprocess
import glob
import json
import argparse
from typing import List, Dict, Tuple, Optional
import numpy as np

# ----- CLIP (images/text -> 512d) -----
import torch
import clip
from PIL import Image

# ----- OpenAI text embeddings (-> 1536d) -----
from embed import text_embed
# ----- Qdrant -----
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

# ----- Transcription (local, with timestamps) -----
from faster_whisper import WhisperModel
import tempfile

# -------------------- helpers --------------------

def l2norm(x: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(x) + 1e-12
    return x / n


def extract_audio_wav(video_path: str, sr: int = 16000, channels: int = 1, output_path: Optional[str] = None) -> str:
    """
    Extract WAV audio from `video_path` using ffmpeg.
    - sr: target sample rate in Hz
    - channels: number of audio channels (1=mono, 2=stereo)
    - output_path: if provided, write there; otherwise creates a temp .wav
    Returns path to the .wav file.
    """
    if output_path is None:
        tmpdir = tempfile.mkdtemp(prefix="audio_")
        wav_path = os.path.join(tmpdir, "audio.wav")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
        wav_path = output_path

    try:
        subprocess.run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", video_path,
            "-vn",                     # no video
            "-ac", str(channels),      # channels
            "-ar", str(sr),            # sample rate
            "-f", "wav",
            wav_path
        ], check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to extract audio from '{video_path}'. Ensure the file has an audio track and ffmpeg is installed.") from e

    return wav_path

def transcribe_video_to_segments(video_path: str, model_size: str = "small", device: str = "cpu") -> List[Dict]:
    """
    Transcribe `video_path` into timestamped segments using Faster-Whisper.
    Returns a list of dicts: {"start": float, "end": float, "text": str}
    """
    wav_path = extract_audio_wav(video_path)
    model = WhisperModel(model_size, device=device, compute_type="int8" if device == "cpu" else "float16")
    segments, info = model.transcribe(wav_path, vad_filter=True)
    out = []
    for seg in segments:
        out.append({"start": float(seg.start), "end": float(seg.end), "text": seg.text.strip()})
    return out

# -------------------- CLIP encoders --------------------

class ClipEnc:
    def __init__(self, device: str = "cpu"):
        self.device = device
        self.model, self.preprocess = clip.load("ViT-B/32", device=device)
        self.model.eval()

    @torch.no_grad()
    def encode_image_paths(self, paths: List[str]) -> np.ndarray:
        if not paths:
            return np.zeros((0, 512), dtype=np.float32)
        imgs = []
        for p in paths:
            img = Image.open(p).convert("RGB")
            imgs.append(self.preprocess(img))
        batch = torch.stack(imgs).to(self.device)
        feats = self.model.encode_image(batch).float()
        feats = feats / feats.norm(dim=-1, keepdim=True)
        return feats.cpu().numpy()

# -------------------- video frame sampling --------------------
def dynamic_alpha(transcript: str, has_frames: bool) -> float:
    if not has_frames:
        return 0.0  # only text
    # if the transcript is too short or whisper returns "music playing"
    if len(transcript.strip()) < 5 or "music" in transcript.lower():
        return 1.0  # only visuals
    if len(transcript.split()) < 10:
        return 0.8
    return 0.5
  
def sample_frames_ffmpeg(video_path: str, out_dir: str, every_sec: int) -> List[Tuple[str, float]]:
    """
    Extract 1 frame every `every_sec` seconds using ffmpeg.
    Returns list of (frame_path, t_seconds).
    """
    os.makedirs(out_dir, exist_ok=True)
    # Extract frames
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", video_path,
        "-vf", f"fps=1/{every_sec}", os.path.join(out_dir, "frame_%06d.jpg")
    ], check=True)

    # Determine duration to timestamp frames
    # Use ffprobe to get duration
    r = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", video_path
    ], capture_output=True, text=True, check=True)
    try:
        duration = float(r.stdout.strip())
    except Exception:
        duration = None

    frames = sorted(glob.glob(os.path.join(out_dir, "frame_*.jpg")))
    items = []
    for i, fp in enumerate(frames):
        t = i * every_sec
        if duration is not None and t > duration + 1:
            break
        items.append((fp, float(t)))
    return items

# -------------------- transcript windowing --------------------

def collect_transcript_for_window(
    transcript: List[Dict],  # each: {"start": float, "end": float, "text": str}
    t0: float,
    t1: float
) -> str:
    parts = []
    for seg in transcript:
        s, e = float(seg["start"]), float(seg["end"])
        # overlap if max(s, t0) < min(e, t1)
        if max(s, t0) < min(e, t1):
            parts.append(seg["text"])
    return " ".join(parts).strip()

# -------------------- main fuse function --------------------

def fuse_video_into_windows(
    video_path: str,
    window_sec: int = 10,
    frame_every_sec: int = 2,
    alpha: float = 0.6,                 # weight for visuals vs text
    resource_id: Optional[str] = None,
    projection_path: str = "proj_1536_to_512.npy",
    whisper_model_size: str = "small",
    whisper_device: str = "cpu"
):
    """
    - Samples frames every `frame_every_sec`.
    - Groups into non-overlapping windows of `window_sec`.
    - For each window:
       * CLIP-embed all frames -> mean-pool (512-d)
       * Gather transcript text overlapping window; OpenAI embed (1536-d), project to 512-d
       * Fuse: v = normalize(alpha * v_clip + (1 - alpha) * Proj(text))
    - Upserts to Qdrant `collection` with payload including window bounds and snippets.
    """
    # Transcribe the video's audio into timestamped segments
    transcript_segments = transcribe_video_to_segments(
        video_path=video_path,
        model_size=whisper_model_size,
        device=whisper_device
    )

    # encoders & projection
    clip_enc = ClipEnc(device="cpu")
    # sample frames
    out_dir = os.path.splitext(video_path)[0] + f"_frames_{frame_every_sec}s"
    frame_items = sample_frames_ffmpeg(video_path, out_dir, every_sec=frame_every_sec)
    if not frame_items:
        return []

    # build windows index -> list of frame paths
    # window k covers [k*window_sec, (k+1)*window_sec)
    max_t = frame_items[-1][1]
    n_windows = int(math.ceil((max_t + 1e-6) / window_sec))
    win_frames: Dict[int, List[str]] = {k: [] for k in range(n_windows)}
    for fp, t in frame_items:
        k = int(t // window_sec)
        if k < n_windows:
            win_frames[k].append(fp)

    points = []
    for k in range(n_windows):
        t0 = k * window_sec
        t1 = (k + 1) * window_sec

        # 1) CLIP on frames in window
        paths = win_frames.get(k, [])
        if paths:
            v_frames = clip_enc.encode_image_paths(paths)  # (N,512)
            v_clip = l2norm(v_frames.mean(axis=0))
        else:
            v_clip = np.zeros(512, dtype=np.float32)

        # 2) Text embedding on overlapping transcript
        txt = collect_transcript_for_window(transcript_segments, t0, t1)
        has_text = len(txt) > 0
        if has_text:
            v_txt1536 = text_embed(txt)                             # (1536,)
            v_txt512 = l2norm(proj @ v_txt1536.astype(np.float32))         # (512,)
        else:
            v_txt512 = np.zeros(512, dtype=np.float32)

        # 3) Fuse
        alpha = dynamic_alpha(txt, len(paths) > 0)
        v_fused = l2norm(alpha * v_clip + (1 - alpha) * v_txt512)

        # payload
        payload = {
            "type": "video_window",
            "resource_id": resource_id,
            "video_path": os.path.abspath(video_path),
            "start": t0,
            "end": t1,
            "frame_every_sec": frame_every_sec,
            "frames": paths[:6],  # sample (cap to keep payload small)
            "transcript_snippet": txt[:500],
            "alpha": alpha,
        }

        points.append(qm.PointStruct(
            id=str(uuid.uuid4()),
            vector=v_fused.tolist(),
            payload=payload
        ))

    return [p.payload for p in points]


# -------------------- example usage --------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Video multimodal fuse or audio extraction")
    parser.add_argument("video", help="Path to input video file")

    # Audio extraction options
    parser.add_argument("--extract-audio", action="store_true", help="Extract audio to WAV and exit")
    parser.add_argument("--audio-out", default=None, help="Optional output WAV path")
    parser.add_argument("--sr", type=int, default=16000, help="Sample rate for audio extraction")
    parser.add_argument("--channels", type=int, default=1, help="Number of audio channels (1=mono,2=stereo)")

    # Fuse options
    parser.add_argument("--window-sec", type=int, default=10, help="Window size in seconds")
    parser.add_argument("--frame-every-sec", type=int, default=2, help="Sample one frame every N seconds")
    parser.add_argument("--alpha", type=float, default=0.6, help="Fusion weight: visuals vs text")
    parser.add_argument("--collection", default="video_fused_512", help="Qdrant collection name")
    parser.add_argument("--projection-path", default="proj_1536_to_512.npy", help="Path to 1536->512 projection .npy")
    parser.add_argument("--whisper-model-size", default="small", help="Faster-Whisper model size")
    parser.add_argument("--whisper-device", default="cpu", help="Device for Faster-Whisper (cpu/cuda)")
    parser.add_argument("--qdrant-host", default="localhost", help="Qdrant host")
    parser.add_argument("--qdrant-port", type=int, default=6333, help="Qdrant port")

    args = parser.parse_args()
    
    video_storage = "/Users/divyavenn/Documents/GitHub/braincache/resources"

    if not os.path.exists(video_storage):
        raise SystemExit(f"Missing video file: {args.video}")

    fused_payloads = fuse_video_into_windows(
            video_path=video_storage,
            qdrant_host=args.qdrant_host,
            qdrant_port=args.qdrant_port,
            collection=args.collection,
            window_sec=args.window_sec,
            frame_every_sec=args.frame_every_sec,
            alpha=args.alpha,
            projection_path=args.projection_path,
            whisper_model_size=args.whisper_model_size,
            whisper_device=args.whisper_device
        )
    print(json.dumps({"upserted_windows": fused_payloads}, indent=2))