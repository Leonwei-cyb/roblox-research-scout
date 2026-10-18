#!/usr/bin/env python3
"""Batch-process LOCAL authorized videos. No social account scraping or cloud APIs."""
import argparse
import json
from pathlib import Path
from local_video_lab import run, FORMATS

def signature(path):
    stat=path.stat()
    return str(stat.st_size)+":"+str(stat.st_mtime_ns)

def pending(inbox,state,limit=2):
    files=sorted((p for p in inbox.iterdir() if p.is_file() and p.suffix.lower() in FORMATS),
                 key=lambda p:(p.stat().st_mtime_ns,p.name))
    return [p for p in files if state.get(p.name)!=signature(p)][:limit]

def batch(inbox,out,max_videos=2,model=None):
    if not inbox.is_dir():
        raise ValueError("Create a local folder with authorized video files first")
    out.mkdir(parents=True,exist_ok=True)
    record=out/"batch_state.json"
    state=json.loads(record.read_text()) if record.exists() else {}
    selected=pending(inbox,state,max_videos)
    for f in selected:
        try:
            run(f,out,8,None,model)
            state[f.name]=signature(f)
        except Exception as error:
            print("FAILED:",f.name,"—",str(error))
    if selected:
        record.write_text(json.dumps(state,indent=2)+"\n")
    print("Attempted",len(selected),"videos. Remaining",len(pending(inbox,state,999)))

def main():
    p=argparse.ArgumentParser(description="Batch local video gallery and optional Ollama analysis")
    p.add_argument("--inbox",type=Path,required=True)
    p.add_argument("--out",type=Path,default=Path(".local-video-reviews"))
    p.add_argument("--max",type=int,default=2)
    p.add_argument("--model",help="Optional LOCAL Ollama vision model")
    a=p.parse_args()
    if not 1<=a.max<=10:
        raise ValueError("Maximum 1–10 videos per run")
    batch(a.inbox,a.out,a.max,a.model)
if __name__=="__main__":
    main()
