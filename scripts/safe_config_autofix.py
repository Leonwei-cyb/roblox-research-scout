#!/usr/bin/env python3
"""Extremely narrow deterministic GitHub config auto-repair. No AI or source code edits.

Only removes IDENTICAL duplicate watch entries from two public JSON configurations.
Conflicting duplicate IDs are a hard error needing human attention.
Does not download media, read cookies, merge code, install plugins or touch games.
"""
import argparse
import json
import os
import stat
import tempfile
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
            # Python equality conflates booleans and numbers, even nested.
            # Sorted JSON preserves types while ignoring object key order.
            if json.dumps(seen[key],sort_keys=True,allow_nan=False)!=json.dumps(item,sort_keys=True,allow_nan=False):
                raise ValueError("Conflicting entries for "+key+"; manual review required")
            continue
        seen[key]=item
        output.append(item)
    return output

def repair(config,schema):
    if not isinstance(config, dict):
        raise ValueError("Expected a JSON object for public source configuration")
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

def _atomic_write(target, data, mode):
    """One public config changes via same-directory replace, never truncation."""
    fd, name = tempfile.mkstemp(prefix=".leon-autofix-", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            os.fchmod(handle.fileno(), mode)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, target)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def work(root,write=False):
    """Validate *both* files before applying any bounded, reversible repair."""
    root = Path(root)
    planned, results = [], []
    for relative,schema in ALLOWED.items():
        target=root/relative
        # Do not follow a symlink into a non-config file outside the checkout.
        if target.is_symlink() or target.parent.is_symlink() or not target.is_file():
            raise ValueError("Expected ordinary public source config: "+relative)
        if target.stat().st_size>500_000:
            raise ValueError("Source config too large")
        original=target.read_bytes()
        if len(original)>500_000:
            raise ValueError("Source config too large")
        parsed=json.loads(original.decode("utf-8"))
        updated,fixes=repair(parsed,schema)
        results.append((relative,fixes))
        if fixes:
            proposed=(json.dumps(updated,indent=2,ensure_ascii=False)+"\n").encode("utf-8")
            mode=stat.S_IMODE(target.stat().st_mode)
            planned.append((target,original,proposed,mode))
    if not write:
        return results

    applied=[]
    try:
        for target,original,proposed,mode in planned:
            if target.is_symlink() or target.read_bytes()!=original:
                raise RuntimeError("Public source config changed during repair: "+target.name)
            _atomic_write(target,proposed,mode)
            applied.append((target,original,mode))
    except Exception as exc:
        failed=[]
        for target,original,mode in reversed(applied):
            try:
                _atomic_write(target,original,mode)
            except OSError as rollback_error:
                failed.append(target.name+":"+type(rollback_error).__name__)
        if failed:
            raise RuntimeError("Autofix rollback incomplete; manual restore required: "+", ".join(failed)) from exc
        raise
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
