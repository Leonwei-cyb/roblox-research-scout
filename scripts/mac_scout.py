#!/usr/bin/python3
"""leon-scout -- runs the existing roblox-research-scout collectors on the Mac, on a schedule.

Reviewable source for the existing Mac runner; adding this file does not install or activate it.
STOP prevents the next stage/publication; an active collector finishes within its step timeout.
Only the configured scheduler owner may collect. Freshness is an optimization, not a lock.
The local flock excludes overlapping Mac invocations, not remote hosts.

  mac_scout.py run | status | stop | start
  mac_scout.py run --force-research  (does not bypass STOP or scheduler ownership)
"""
import fcntl, json, os, subprocess, sys, time
from datetime import datetime, timezone
from scheduler_owner import owns_job

HOME = os.path.expanduser(os.environ.get("LEON_SCOUT_HOME", "~/.claude/state/leon-scout"))
REPO = os.path.expanduser(os.environ.get("LEON_SCOUT_REPO",
                                         "~/Library/Application Support/LeonScout/repo"))
REMOTE = os.environ.get("LEON_SCOUT_REMOTE", "https://github.com/Leonwei-cyb/roblox-research-scout.git")
LOGS = os.path.expanduser(os.environ.get("LEON_SCOUT_LOGS", "~/Library/Logs/LeonScout"))
GH = os.path.expanduser("~/.claude/tools/gh")
STOP = os.path.join(HOME, "STOP")
STATE = os.path.join(HOME, "state.json")

RESEARCH_EVERY = 3600 - 300          # hourly, a little slack for launchd drift
DISCOVERY_EVERY = 6 * 3600 - 600
FRESH = {"research": 50 * 60, "discovery": 5 * 3600}   # main already has a report this new: skip
STEP_LIMIT = 300                     # seconds per collector, like the workflows' 5-minute jobs
RUN_LIMIT = 20 * 60
BACKOFF_MAX = 6 * 3600
KEEP_LOG_DAYS = 14

# research.yml's order. The last three run only if the public feeds (media_scout) succeeded.
RESEARCH = ["scout", "bot_supervisor", "license_watch", "media_scout", "official_visual_scout",
            "research_quality", "failure_triage"]
AFTER_MEDIA = ["video_shortlist", "creator_digest", "research_dispatcher"]
MUST_PASS = {"official_visual_scout", "research_quality", "failure_triage", "bot_supervisor",
             "license_watch", "video_shortlist", "creator_digest", "research_dispatcher"}
RESEARCH_PATHS = ["watch/"]
DISCOVERY_PATHS = ["findings/", "status/discovery.json", "watch/discovery_state.json"]


def now():
    return time.time()


def iso(t=None):
    return datetime.fromtimestamp(now() if t is None else t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg):
    os.makedirs(LOGS, exist_ok=True)
    line = f"{iso()} {msg}"
    with open(os.path.join(LOGS, datetime.now().strftime("%Y-%m-%d") + ".log"), "a") as f:
        f.write(line + "\n")
    print(line, flush=True)


def prune_logs():
    cut = now() - KEEP_LOG_DAYS * 86400
    for name in os.listdir(LOGS) if os.path.isdir(LOGS) else []:
        p = os.path.join(LOGS, name)
        if name.endswith(".log") and os.path.getmtime(p) < cut:
            os.remove(p)


def load():
    try:
        with open(STATE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save(st):
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f, indent=1, sort_keys=True)
    os.replace(tmp, STATE)


def git(*args, check=True, env=None):
    r = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True, env=env, timeout=120)
    if check and r.returncode:
        raise RuntimeError(f"git {args[0]} failed: {r.stderr.strip()[:300]}")
    return r.stdout.strip()


def token():
    if "LEON_SCOUT_TOKEN_CMD" in os.environ:          # tests
        cmd = os.environ["LEON_SCOUT_TOKEN_CMD"].split()
    else:
        cmd = [GH, "auth", "token"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if r.returncode or not r.stdout.strip():
        raise RuntimeError("no GitHub token from gh auth (sign-in needed)")
    return r.stdout.strip()


def sync_repo():
    """Dedicated clone, owned by this runner only: always start from origin/main exactly."""
    if not os.path.isdir(os.path.join(REPO, ".git")):
        os.makedirs(os.path.dirname(REPO), exist_ok=True)
        subprocess.run(["git", "clone", "-q", REMOTE, REPO], check=True, capture_output=True, timeout=300)
    git("fetch", "-q", "origin", "main")
    git("checkout", "-q", "-B", "main", "origin/main")
    git("reset", "-q", "--hard", "origin/main")
    git("clean", "-q", "-fd")


def last_report_age(paths):
    """Seconds since main's newest commit that touched these paths (any author: Actions or us)."""
    out = git("log", "-1", "--format=%ct", "origin/main", "--", *paths, check=False)
    return now() - int(out) if out.isdigit() else None


class Stopped(RuntimeError):
    pass


def checkpoint(deadline=None):
    if os.path.exists(STOP):
        raise Stopped("STOP requested; no further collectors or publication")
    if deadline is not None and now() >= deadline:
        raise TimeoutError("cycle deadline exceeded")


def step(name, env, deadline):
    checkpoint(deadline)
    limit = min(STEP_LIMIT, deadline - now())
    t = now()
    try:
        r = subprocess.run(["nice", "-n", "10", sys.executable, f"scripts/{name}.py"], cwd=REPO, env=env,
                           capture_output=True, text=True, timeout=limit)
        code, out = r.returncode, (r.stdout + r.stderr)
    except subprocess.TimeoutExpired:
        code, out = 124, f"timed out after {int(limit)} s"
    tail = " | ".join(l for l in out.strip().splitlines()[-3:])[:300]
    log(f"  {name} exit={code} {now() - t:.0f}s {tail}")
    return code


def publish(paths, message):
    checkpoint()
    git("add", "-A", "--", *paths)
    if not git("diff", "--cached", "--name-only"):
        log("  no changed report")
        return {"status": "unchanged", "sha": None}
    checkpoint()
    git("commit", "-q", "-m", message)
    for _ in range(3):
        checkpoint()
        git("fetch", "-q", "origin", "main")
        if subprocess.run(["git", "-C", REPO, "rebase", "-q", "origin/main"], capture_output=True).returncode:
            subprocess.run(["git", "-C", REPO, "rebase", "--abort"], capture_output=True)
            log("  report conflicts with newer main; next cycle retries")
            return {"status": "failed", "reason": "rebase conflict", "sha": None}
        checkpoint()
        if subprocess.run(["git", "-C", REPO, "push", "-q", "origin", "HEAD:main"],
                          capture_output=True, timeout=120).returncode == 0:
            return {"status": "published", "sha": git("rev-parse", "HEAD")}
        time.sleep(2)
    log("  push failed 3 times (never forced); next cycle retries")
    return {"status": "failed", "reason": "push retries exhausted", "sha": None}


def cycle(st, force_research=False):
    t0 = now()
    deadline = t0 + RUN_LIMIT
    receipt = {"start": iso(t0), "steps": {}, "commits": {}}
    checkpoint(deadline)
    sync_repo()
    checkpoint(deadline)

    want = {}
    for job, every, paths in (("research", RESEARCH_EVERY, RESEARCH_PATHS),
                              ("discovery", DISCOVERY_EVERY, DISCOVERY_PATHS)):
        if not owns_job(os.path.join(REPO, "config/scheduler.json"), "mac", job):
            want[job] = False
            continue
        if job == "research" and force_research:
            want[job] = True
            continue
        due = st.get(f"retry_{job}", False) or t0 - st.get(f"last_{job}", 0) >= every
        age = last_report_age(paths)
        if due and not st.get(f"retry_{job}") and age is not None and age < FRESH[job]:
            log(f"{job}: main already has a report {age / 60:.0f} min old; skipped (no duplicate run)")
            st[f"last_{job}"] = t0 - age
            due = False
        want[job] = due
    if not any(want.values()):
        receipt["skipped"] = "nothing due"
        return True, receipt

    checkpoint(deadline)
    env = dict(os.environ, GITHUB_TOKEN=token(), GITHUB_EVENT_NAME="local")
    env.pop("GITHUB_STEP_SUMMARY", None)
    tests = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"], cwd=REPO,
                           capture_output=True, text=True, timeout=STEP_LIMIT)
    log(f"offline tests exit={tests.returncode}")
    receipt["tests"] = tests.returncode
    if tests.returncode:
        receipt["error"] = "offline tests failed on main; nothing run"
        return False, receipt

    ok = True
    if want["research"]:
        log("research cycle")
        codes = {n: step(n, env, deadline) for n in RESEARCH}
        if codes["media_scout"] == 0:
            codes.update({n: step(n, env, deadline) for n in AFTER_MEDIA})
        receipt["steps"].update(codes)
        bad = [n for n in MUST_PASS if codes.get(n, 0)]
        both = codes["scout"] and codes["media_scout"]
        checkpoint(deadline)
        result = publish(RESEARCH_PATHS, "Refresh public research leads (Mac local scheduler)")
        receipt.setdefault("publication", {})["research"] = result
        receipt["commits"]["research"] = result["sha"]
        if not (bad or both) and result["status"] != "failed":
            st["last_research"] = t0
            st.pop("retry_research", None)
        if bad or both or result["status"] == "failed":
            st["retry_research"] = True
            ok = False
            receipt["error"] = "research failed: " + (", ".join(sorted(bad)) or ("both collectors" if both else result.get("reason", "publication failed")))
    if want["discovery"]:
        log("discovery cycle")
        receipt["steps"]["discovery_scout"] = code = step("discovery_scout", env, deadline)
        checkpoint(deadline)
        result = publish(DISCOVERY_PATHS, "Refresh open-source discovery (Mac local scheduler)")
        receipt.setdefault("publication", {})["discovery"] = result
        receipt["commits"]["discovery"] = result["sha"]
        if not code and result["status"] != "failed":
            st["last_discovery"] = t0
            st.pop("retry_discovery", None)
        if code or result["status"] == "failed":
            st["retry_discovery"] = True
            ok = False
            receipt["error"] = (receipt.get("error", "") + " discovery failed: " + ("collector failed" if code else result.get("reason", "publication failed"))).strip()
    return ok, receipt


def run(force_research=False):
    os.makedirs(HOME, exist_ok=True)
    if os.path.exists(STOP):
        log("STOP is on; not running")
        return 0
    with open(os.path.join(HOME, "lock"), "w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            log("another run holds the lock; not starting a second")
            return 0
        st = load()
        if now() < st.get("backoff_until", 0):
            log(f"backing off after {st.get('failures', 0)} failure(s) until {iso(st['backoff_until'])}")
            return 0
        prune_logs()
        try:
            ok, receipt = cycle(st, force_research)
        except Stopped as e:
            save(st)
            log(str(e))
            return 0
        except Exception as e:                       # network, git, token: a failure, never a crash loop
            ok, receipt = False, {"start": iso(), "error": str(e)[:300]}
        receipt["end"] = iso()
        receipt["pid"] = os.getpid()
        if ok:
            st["failures"] = 0
            st.pop("backoff_until", None)
        else:
            st["failures"] = st.get("failures", 0) + 1
            st["backoff_until"] = now() + min(BACKOFF_MAX, 3600 * 2 ** (st["failures"] - 1))
        if not receipt.get("skipped"):
            st["last_receipt"] = receipt
        save(st)
        log(f"cycle {'ok' if ok else 'FAILED'}: {json.dumps(receipt, sort_keys=True)}")
        return 0 if ok else 1


def status():
    st = load()
    print("STOP: " + ("ON" if os.path.exists(STOP) else "off"))
    for job, every in (("research", RESEARCH_EVERY), ("discovery", DISCOVERY_EVERY)):
        last = st.get(f"last_{job}")
        print(f"{job}: last {iso(last) if last else 'never'}; next due {iso(last + every) if last else 'now'}")
    if st.get("backoff_until", 0) > now():
        print(f"backing off until {iso(st['backoff_until'])} after {st.get('failures')} failure(s)")
    print("last receipt: " + json.dumps(st.get("last_receipt"), sort_keys=True))
    return 0


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "status"
    if cmd == "run":
        return run("--force-research" in argv[2:])
    if cmd == "status":
        return status()
    if cmd in ("stop", "start"):
        os.makedirs(HOME, exist_ok=True)
        if cmd == "stop":
            open(STOP, "w").close()
        elif os.path.exists(STOP):
            os.remove(STOP)
        print(f"STOP {'on' if cmd == 'stop' else 'off'}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
