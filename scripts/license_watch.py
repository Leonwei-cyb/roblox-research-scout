#!/usr/bin/env python3
"""Audit public repository license/maintenance metadata. Never downloads or runs code."""
import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/"watch/config.json"
OUT=ROOT/"watch/license_audit.md"
API="https://api.github.com"

def watched_repos(config, limit=12):
    out=[]
    for name in config.get("watch_repos", []):
        if re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9_.-]+", str(name)) and name not in out:
            out.append(name)
            if len(out)>=limit:
                break
    return out

def fetch_repo(name):
    headers={"Accept":"application/vnd.github+json",
             "User-Agent":"RobloxResearchLicenseWatch/1",
             "X-GitHub-Api-Version":"2022-11-28"}
    token=os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"]="Bearer "+token
    req=Request(API+"/repos/"+quote(name,safe="/"),headers=headers)
    try:
        with urlopen(req,timeout=9) as response:
            return json.load(response)
    except HTTPError as e:
        raise RuntimeError("HTTP "+str(e.code)) from e
    except URLError as e:
        raise RuntimeError("GitHub API unavailable") from e

def license_label(repo):
    license_data=repo.get("license") or {}
    code=str(license_data.get("spdx_id") or "")
    if not code or code in {"NOASSERTION","none"}:
        return "No verified license — do NOT copy source/assets"
    if code.lower().startswith(("gpl","agpl","lgpl")):
        return code+" — copyleft, review conditions"
    return code+" — license present, inspect asset and dependency rights"

def report(rows):
    lines=["# Public GitHub license and maintenance triage","",
           "Metadata only, not legal advice or a security audit. Third-party models may have separate rights.","",
           "| Public repository | License metadata | Last pushed | Archived |",
           "|---|---|---|---|"]
    for name, data, error in rows:
        if error:
            lines.append("| "+name+" | Unavailable: "+error+" | — | — |")
        else:
            lines.append("| ["+name+"](https://github.com/"+name+") | "+
                license_label(data)+" | "+str(data.get("pushed_at",""))[:10]+
                " | "+("Yes" if data.get("archived") else "No")+" |")
    lines += ["", "Before copying code/assets, inspect source safety, the complete license and dependency rights."]
    return "\n".join(lines)+"\n"

def main():
    config=json.loads(CONFIG.read_text(encoding="utf-8"))
    rows=[]
    for name in watched_repos(config):
        try:
            rows.append((name,fetch_repo(name),""))
        except RuntimeError as exc:
            rows.append((name,None,str(exc)))
    text=report(rows)
    if not OUT.exists() or OUT.read_text(encoding="utf-8")!=text:
        OUT.write_text(text,encoding="utf-8")
        print("Updated public license metadata audit")
    else:
        print("No license metadata change")
if __name__=="__main__":
    main()
