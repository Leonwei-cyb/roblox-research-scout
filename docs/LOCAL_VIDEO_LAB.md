# Local Video Lab

**Not part of public GitHub Actions.** This optional tool examines sampled
frames of a local video you are authorized to process, without uploading it.

1. Install Python and FFmpeg on the Mac/PC.
2. Save a permitted MP4/MOV/WebM/MKV clip locally.
3. Run: python3 scripts/local_video_lab.py /path/to/your_clip.mp4
4. Open .local-video-reviews/<filename>/gallery.html in your browser.

Optional: install Ollama and download a LOCAL vision model, e.g. Qwen3-VL.
Then run: python3 scripts/local_video_lab.py /path/to/clip.mp4 --model qwen3-vl:4b

This costs local CPU/RAM/GPU/electricity only; **no GPT, Claude or Codex API**.
It analyzes sampled stills, not every video frame or sound. Rewatch the original
for mechanics and animation timing. No scraping or private platform cookies.

For public creator discoveries see watch/review_queue.md, watch/topic_signals.md
and watch/coverage_audit.md, generated automatically by separate no-model bots.
