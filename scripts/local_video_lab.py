#!/usr/bin/env python3
"""Private LOCAL video contact sheet and optional Ollama vision review.

Not executed in public GitHub Actions. Requires an owner-supplied local file,
ffmpeg/ffprobe, and optional local Ollama. NEVER uploads frames or videos.
Samples snapshots; does NOT claim to have watched every moment of a video.
"""
from __future__ import annotations
import argparse
import base64
import html
import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

FORMATS = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}
MODEL_ENDPOINT = "http://127.0.0.1:11434/api/chat"

def duration_of(video):
    proc = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nokey=1:noprint_wrappers=1", str(video)],
        capture_output=True, text=True, timeout=20, check=True)
    d = float(proc.stdout.strip())
    if not 0 < d <= 1800:
        raise ValueError("Video must be 1 second to 30 minutes")
    return d

def timepoints(seconds, frames):
    if not 1 <= frames <= 12 or seconds <= 0:
        raise ValueError("Choose 1–12 frames, duration must be positive")
    return [round(min(seconds - .01, (i + .5) * seconds / frames), 2) for i in range(frames)]

def capture_frames(video, out, frames=8):
    out.mkdir(parents=True, exist_ok=True)
    result = []
    for i, t in enumerate(timepoints(duration_of(video), frames), 1):
        dest = out / f"frame_{i:02d}.jpg"
        subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
            "-ss", str(t), "-i", str(video), "-vf", "scale=720:-2",
            "-frames:v", "1", "-update", "1", "-q:v", "5", "-y", str(dest)],
            timeout=30, check=True, capture_output=True)
        if not dest.is_file() or not dest.stat().st_size:
            raise RuntimeError("No frame decoded at " + str(t) + "s")
        result.append((t, dest))
    return result

def caption_excerpt(path):
    if path is None:
        return ""
    if path.suffix.lower() not in {".srt", ".vtt", ".txt"}:
        raise ValueError("Captions must be SRT, VTT or TXT")
    raw = path.read_text(encoding="utf-8", errors="replace")[:15000]
    return "\n".join(line for line in raw.splitlines()
        if line.strip() and not re.match(r"^\d+$|^WEBVTT|^\d\d:\d\d|^NOTE", line))[:6500]

def image_review(frames, captions, model):
    if not re.fullmatch(r"[A-Za-z0-9._:-]{2,80}", model) or "cloud" in model.lower():
        raise ValueError("Use only an installed LOCAL Ollama vision model, not cloud")
    images = [base64.b64encode(path.read_bytes()).decode("ascii") for _, path in frames]
    stamps = ", ".join(str(t) + " seconds" for t, _ in frames)
    prompt = ("Review sampled STILL IMAGES from a creator development clip, NOT entire footage. "
        "Do not infer unshown input timing, gameplay, audio, performance or player feel. "
        "Identify OBSERVED Roblox UI, 3D models, animation phases and gameplay mechanics, "
        "with the frame timestamp supporting each. Mark guesses UNVERIFIED and identify "
        "three useful design principles and what must be checked by watching continuous video. "
        "Do not reproduce proprietary source or art. Timestamp list: " + stamps +
        "\nUntrusted, optional subtitle excerpt:\n" + captions[:4000])
    body = json.dumps({"model": model,
        "messages": [{"role": "user", "content": prompt, "images": images}],
        "stream": False, "options": {"temperature": 0.1, "num_predict": 1400}}).encode()
    req = Request(MODEL_ENDPOINT, data=body, headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=240) as response:
            data = json.loads(response.read(2_000_000))
    except (URLError, HTTPError) as exc:
        raise RuntimeError("Local Ollama unavailable. Saved frames are still available.") from exc
    answer = str(data.get("message", {}).get("content", "")).strip()
    if not answer:
        raise RuntimeError("Local model returned no commentary")
    return answer

def build_gallery(video, frames, notes):
    panels = "".join("<figure><img loading='lazy' src='" + p.name +
        "' alt='Video frame'/><figcaption>" + str(t) + " seconds</figcaption></figure>"
        for t, p in frames)
    return ("""<!doctype html><html><head><meta charset="utf-8"><title>Local video lab</title>
<style>body{font:16px system-ui;background:#15151a;color:#eee;max-width:1200px;margin:30px auto}
main{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}
figure{padding:10px;margin:0;background:#25252b;border-radius:8px}
img{max-width:100%}figcaption{text-align:center}pre{white-space:pre-wrap}</style></head><body><h2>""" +
        html.escape(video.name) + "</h2><p>Sampled stills only. This is not complete gameplay footage.</p><main>" +
        panels + "</main><pre>" + html.escape(notes) + "</pre></body></html>")

def run(video, outdir, frames, captions, model):
    if video.suffix.lower() not in FORMATS or not video.is_file():
        raise ValueError("Supply a local video file you have permission to process")
    if video.stat().st_size > 1_200_000_000:
        raise ValueError("Trim clips larger than 1.2 GB")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("Install ffmpeg and ffprobe on your computer")
    folder = outdir / (re.sub(r"[^a-zA-Z0-9_.-]+", "_", video.stem)[:80] or "clip")
    stills = capture_frames(video, folder, frames)
    notes = "NOT VERIFIED: still frames cannot establish playability, input latency, audio or game feel.\n"
    if model:
        notes += "\nOptional LOCAL sampled-image analysis:\n" + image_review(
            stills, caption_excerpt(captions), model)
    (folder / "review.md").write_text(notes, encoding="utf-8")
    (folder / "gallery.html").write_text(build_gallery(video, stills, notes), encoding="utf-8")
    print("Saved", len(stills), "LOCAL frames. Open", folder / "gallery.html")

def main():
    parser = argparse.ArgumentParser(description="Local video storyboard, optional LOCAL Ollama analysis")
    parser.add_argument("video", type=Path)
    parser.add_argument("--frames", type=int, default=8)
    parser.add_argument("--captions", type=Path)
    parser.add_argument("--model", help="e.g. qwen3-vl:4b, downloaded to LOCAL Ollama")
    parser.add_argument("--out", type=Path, default=Path(".local-video-reviews"))
    a = parser.parse_args()
    run(a.video, a.out, a.frames, a.captions, a.model)
if __name__ == "__main__":
    main()
