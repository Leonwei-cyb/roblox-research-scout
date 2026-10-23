"""Explicit collector ownership shared by the existing GitHub and Mac runners."""
import argparse
import json
from pathlib import Path


def owns_job(path, owner, job):
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(config, dict) or set(config) != {"research", "discovery"}:
        raise ValueError("scheduler config must contain research and discovery")
    if any(value not in ("mac", "github", "paused") for value in config.values()):
        raise ValueError("scheduler owner must be mac, github, or paused")
    if owner not in ("mac", "github") or job not in config:
        raise ValueError("unknown scheduler or job")
    return config[job] == owner


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", required=True, choices=("mac", "github"))
    parser.add_argument("--job", required=True, choices=("research", "discovery"))
    parser.add_argument("--config", default="config/scheduler.json")
    args = parser.parse_args()
    enabled = owns_job(args.config, args.owner, args.job)
    print("enabled=" + str(enabled).lower())


if __name__ == "__main__":
    main()
