#!/usr/bin/env python3
"""Extremely narrow deterministic GitHub config auto-repair. No AI or source code edits.

Only removes IDENTICAL duplicate watch entries from two public JSON configurations.
Conflicting duplicate IDs are a hard error needing human attention.
Does not download media, read cookies, merge code, install plugins or touch games.
"""
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ALLOWED={
    "watch/config.json":{"watch_repos":"string"},
    "watch/feeds.json":{
        "feeds":"id","news_queries":"id","app_charts":"id","youtube_channels":"channel_id"
    }
}

def dedupe(values,identity):
    if not isinstance(values,list):
        raise ValueError("Expected a list of public configured sources")
    seen={}
    output=[]
    for item in values:
        if identity=="string":
            key=item
        else:
            if not isinstance(item,dict) or not str(item.get(identity,"")).strip():
                raise ValueError("Missing or invalid configured source identifier")
            key=item[identity]
        if not isinstance(key,str) or not key.strip():
            raise ValueError("Empty source key")
        if key in seen:
            if seen[key]!=item:
                raise ValueError("Conflicting entries for "+key+"; manual review required")
            continue
        seen[key]=item
        output.append(item)
    return output

def repair(config,schema):
    result=json.loads(json.dumps(config))
    fixed={}
    for key,kind in schema.items():
        if key not in result:
            continue
        before=result[key]
        after=dedupe(before,kind)
        if len(after)!=len(before):
            result[key]=after
            fixed[key]=len(before)-len(after)
    return result,fixed

def work(root,write=False):
    results=[]
    for relative,schema in ALLOWED.items():
        target=root/relative
        if not target.is_file():
            raise ValueError("Expected source config missing: "+relative)
        if target.stat().st_size>500_000:
            raise ValueError("Source config too large")
        old=json.loads(target.read_text(encoding="utf-8"))
        updated,fixes=repair(old,schema)
        results.append((relative,fixes))
        if write and fixes:
            target.write_text(json.dumps(updated,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return results

def main():
    p=argparse.ArgumentParser(description="Repair only unambiguous duplicate public source entries")
    p.add_argument("--write",action="store_true",help="Apply repairs; default is dry run")
    p.add_argument("--root",type=Path,default=ROOT)
    a=p.parse_args()
    for path,fixes in work(a.root,a.write):
        print(path+": "+(str(fixes) if fixes else "no duplicate repair needed"))
    print("No game source, private data or third-party media changed.")
if __name__=="__main__":
    main()
