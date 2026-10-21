# Mac scout reliability review

This change versions the existing external Mac runner as `scripts/mac_scout.py`.
It does not install the script, modify a LaunchAgent, start a worker, change cron
intervals, or migrate the installed service. The installed runner remains unchanged.

## Publication and retry contract

Publication returns `published` (with SHA), `unchanged`, or `failed` (with reason).
A rebase conflict or three rejected pushes is a failure, not a successful empty
report. A failed collector or publication does not advance that job's last-success
time and enters the existing exponential backoff. A pending per-job retry bypasses
report freshness suppression, so partial reports cannot hide a failed retry. A successful other job retains
its own timestamp. The next eligible cycle regenerates report outputs from main;
failed local commits are not a durable retry queue. No force pushes are used.

## STOP contract

STOP is checked before syncing, each collector, publication, and each publication
attempt, including immediately before push. An already running collector is allowed
to finish within its step timeout (300 seconds); it is not forcibly killed. STOP
prevents subsequent stages after it is observed. A Git operation already in flight
can finish, including a push that started before STOP was observed. STOP is not an
atomic remote transaction cancellation. STOP does not create a failure backoff.
The cycle deadline also prevents starting another collector after time is exhausted.

## One scheduler owner per job

`config/scheduler.json` explicitly selects `github`, `mac`, or `paused` separately
for research and discovery. Missing, malformed, or unknown configuration fails
closed. `--force-research` cannot bypass ownership or STOP.

The default is `github`, preserving the repository's existing hosted collectors.
The existing GitHub collector jobs check ownership before testing, collecting, or
publishing. A disabled discovery job emits no publication output, so issue routing
cannot run. No new jobs or schedules are added; the health monitor is unchanged.
The Mac runner checks ownership after fetching main and before requesting a token.
The local flock still excludes overlapping Mac invocations.

**Ownership is configuration, not a distributed lease.** A run that already read
an old configuration can continue. The legacy installed runner does not understand
this configuration at all. Therefore merging this PR alone must not be represented
as eliminating overlap with that legacy runner.

For a future separately approved rollout: pause the legacy Mac runner, let it and
any hosted collector finish, adopt the reviewed runner while preserving its existing
state/STOP paths, set both owners to `paused`, and drain outstanding runs. Only then
choose one owner per job and resume that existing scheduler. Switching ownership
later requires the same pause-and-drain procedure. Do not start a second LaunchAgent.
No rollout is performed by this PR or its tests.

## Offline evidence

Run `python3 -m unittest discover -s tests -v`. The added tests use fake collectors,
local locks, temporary state directories, and temporary bare Git repositories.
They cover successful/unchanged publication, rejected pushes, concurrent conflicting
reports, timestamp/backoff behavior, STOP boundaries, deadline exhaustion, owner
exclusivity, fail-closed configuration, and existing workflow step guards.
No live service, credentials, public collector, Studio, package installation, or
external publication is required by these tests. Workflow guards are checked
statically and the ownership CLI is executed locally; GitHub Actions acceptance
and production STOP behavior remain unverified until an authorized rollout.

## Follow-up review hardening

Due jobs are marked pending before tests, credentials, or collectors run, so an
exception or STOP cannot accidentally clear their retry requirement. A failed
research publication ends the cycle before discovery: its local unpushed commit
must not be included in another job's later push. Outputs are regenerated at the
next eligible cycle, as above.

Publication rejects staged files outside the job's report paths. Rename detection
is disabled for this check so moving code into a report directory cannot hide the
source deletion; NUL-delimited filenames are preserved without trimming. Hosted
publication steps apply equivalent exclusions. Hosted conflicts/exhausted pushes
now fail, and discovery only publishes after successful tests and collection.

Rebase, abort, and push have bounded waits. Publication honors the remaining cycle
deadline; abort cleanup has its own ten-second allowance. STOP is rechecked between
fetch and rebase. Known GitHub token values are redacted from collector log output
before truncation, and inherited token values are redacted from log/error messages.
This is defense against accidental output, not a sandbox against malicious code:
main-branch scripts and tests still execute with the runner account's privileges.
