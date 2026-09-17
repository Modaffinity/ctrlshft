#!/usr/bin/env python3
"""M4 — the supervisor: C2's bands and C3's ordered handoff.

One foreground process. It polls the two harness-written sensor files —
`~/.plan-guard/context/<session>.json` (M3) and
`~/.plan-guard/boundary/<session>.jsonl` (M2) — and on an **actionable** boundary
whose context is in the middle band or above it runs SPEC.md § 4.3's six steps in order.

    plan-supervisor.py --slug <slug> --session <id> --mode detect|arm

**The ordering is the whole safety property, and the two-field marker is the correction
(R183).** `attempting` is written to `~/.plan-guard/state/<slug>.json` BEFORE a step
starts and `completed` AFTER it returns, so a crash between them leaves `attempting: <step>`
with that step's marker absent. The draft's single marker, written before the step, let a
restart read an unfinished `verify` as proof the verification had succeeded. Restart
re-runs any step whose `attempting` is set and whose marker is not in `completed`; steps
1-4 and 6 are idempotent, so re-running them is free. **Step 5 is the exception and halts
rather than retries** — a `send-keys` that may already have landed cannot be safely
repeated, and re-clearing an already-re-primed session would destroy the successor's work.
No step that destroys context runs before the step that preserves it is confirmed.

Three readings are recorded here rather than left to a reader, because each is a place a
careless implementation fails silently:

  * **the band is read from `context_window.total_input_tokens`** (§ 4.3). The export's
    only percentage field is documented 0-100 and § 4.4's thresholds are absolute token
    counts, so banding on the percentage would put every threshold permanently out of
    reach — CHECKS.md rule 2's gate-that-cannot-pass, from the other end;
  * **a boundary is actionable iff `agent-<agent_id>.meta.json` exists and reads
    `spawnDepth: 1`** (§ 4.2). The `agent-` prefix is MEASURED, not optional. Depth >= 2 or
    an unresolvable meta file is counted and never acted on: 14% of the 1,090 real meta
    files on this machine are nested, and acting on a nested stop would `/clear` mid-unit,
    breaking C3's *never mid-work* rule through the mechanism meant to keep it;
  * **"up to 3 attempts" in step 5 counts CONFIRMATIONS, not sends.** `send-keys` is issued
    once and `capture-pane` is then read up to three times; re-sending is precisely what
    requirement 6 forbids.

Every root is derived through `os.path.expanduser("~")`, as the two shipped hooks derive
theirs, so `HOME` is the single knob a fixture turns. `--mode detect` stops unconditionally
after step 4 and is this run's mode (R142): arming needs an orchestrator launched inside
tmux, a launch-time property this run's session lacks.

**R161, carried and not closed:** nothing here can *launch* a foreground process into an
interactive session, so starting the supervisor stays a human or orchestrator action. What
is mechanical is that its absence is loud — M2's shim blocks the stop when `heartbeat` is
older than 120 seconds, which is why every poll writes it.

Exit: 0 normal (including detect mode's designed stop after step 4), 2 usage, 3 halted.

Stdlib only, Python 3.9.
"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

BAND_MIDDLE = 250000
BAND_HIGH = 500000
CONTEXT_MAX_AGE = 600.0          # seconds; older than this is *no reading*, never zero
CONFIRM_ATTEMPTS = 3
CONFIRM_DELAY = 1.0
CHUNK = 65536

# (number, step, marker). `detect` stops unconditionally after step 4 (R142).
STEPS = ((1, "save", "saved"), (2, "copy", "copied"), (3, "verify", "verified"),
         (4, "track", "tracked"), (5, "clear", "cleared"), (6, "reprime", "done"))
MARKER = dict((step, marker) for _n, step, marker in STEPS)

PICKUP = (
    "Resume the build session for the workstream `%(slug)s`. Read\n"
    "%(pod)s/plans/%(slug)s/STATE.md first; its \"Resume here\" is authoritative. "
    "Do not read\n"
    "this workstream's SPEC.md or PLAN.md; they are protected (C1).")

# SPEC.md § 17.8, verbatim. A pointer, never a payload: it names STATE.md, the in-flight
# position and the two archive paths with their sha256s, and carries no artifact content —
# which is what makes C4's resume claim the thing under test.
HANDOFF = """Resume the build session for the workstream `%(slug)s`.

Read, in this order:
1. %(pod)s/plans/%(slug)s/STATE.md — your position; its "Resume here" is authoritative
2. the artifacts STATE.md names, and nothing else

In flight at the handoff: %(stage)s, %(returned)s.
Transcript archive: ~/.plan-handoff/%(slug)s/%(ts)s/ (sha256 %(hash)s)
                    %(pod)s/evidence/handoff/%(ts)s/ (sha256 %(hash)s)

Do not read this workstream's SPEC.md or PLAN.md; they are protected (C1).
"""


class Halt(Exception):
    """A step failed. The session is left intact and the pickup line is printed."""

    def __init__(self, number, step, reason):
        Exception.__init__(self, reason)
        self.number = number
        self.step = step
        self.reason = reason


def home():
    return os.path.expanduser("~")


def guard(*parts):
    return os.path.join(home(), ".plan-guard", *parts)


def now():
    return datetime.datetime.now().astimezone().isoformat()


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repo_root(start):
    """The nearest ancestor of `start` holding a `.git` entry, or None."""
    path = os.path.realpath(start)
    while True:
        if os.path.exists(os.path.join(path, ".git")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent


def frontmatter(path):
    """The leading `---` block as a dict — parsed as frontmatter, never grepped, exactly
    as read-guard.py and plan-reprime.sh parse theirs, so the three agree."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            if fh.readline().rstrip("\n") != "---":
                return {}
            out = {}
            for line in fh:
                if line.strip() == "---":
                    return out
                key, sep, value = line.rstrip("\n").partition(":")
                if sep:
                    out[key.strip()] = value.strip()
            return {}
    except (OSError, UnicodeError):
        return {}


def project_dir(session, pod):
    """The `~/.claude/projects/<project_dir>` holding this session.

    Resolved by LOOKING for the session's transcript rather than by reproducing the
    harness's path-encoding rule, which is undocumented and would fail silently the first
    time a pod path carried a character the rule treats specially. The encoded name is the
    fallback, so a session that has not yet written a transcript still resolves."""
    base = os.path.join(home(), ".claude", "projects")
    try:
        names = sorted(os.listdir(base))
    except OSError:
        names = []
    for name in names:
        candidate = os.path.join(base, name)
        if (os.path.exists(os.path.join(candidate, "%s.jsonl" % session))
                or os.path.isdir(os.path.join(candidate, session))):
            return candidate
    return os.path.join(base, os.path.realpath(pod).replace(os.sep, "-"))


def spawn_depth(session, pod, agent_id):
    """`spawnDepth` from `<project_dir>/<session>/subagents/agent-<agent_id>.meta.json`,
    or None when the file does not exist or does not parse. None never acts."""
    if not agent_id:
        return None
    path = os.path.join(project_dir(session, pod), session, "subagents",
                        "agent-%s.meta.json" % agent_id)
    try:
        with open(path, encoding="utf-8") as fh:
            value = json.load(fh).get("spawnDepth")
    except (OSError, ValueError):
        return None
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def age(stamp):
    """Seconds since `stamp` (epoch seconds or ISO-8601), or None when unreadable."""
    if stamp is None or isinstance(stamp, bool):
        return None
    if isinstance(stamp, (int, float)):
        return time.time() - float(stamp)
    if not isinstance(stamp, str):
        return None
    text = stamp.strip()
    try:
        return time.time() - float(text)
    except ValueError:
        pass
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return time.time() - parsed.timestamp()


def band(session, max_age):
    """(band name, tokens). A stale or unreadable export is *no reading*, never zero — the
    distinction § 4.2 insists on, and the reason M3 records its own write time."""
    try:
        with open(guard("context", "%s.json" % session), encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return "no-reading", None
    if not isinstance(data, dict):
        return "no-reading", None
    seconds = age(data.get("_exported_at"))
    if seconds is None or seconds > max_age:
        return "no-reading", None
    window = data.get("context_window")
    tokens = window.get("total_input_tokens") if isinstance(window, dict) else None
    if isinstance(tokens, bool) or not isinstance(tokens, (int, float)):
        return "no-reading", None
    if tokens < BAND_MIDDLE:
        return "under-250k", tokens
    if tokens <= BAND_HIGH:
        return "250k-500k", tokens
    return "over-500k", tokens


class Supervisor(object):

    def __init__(self, args):
        self.slug = args.slug
        self.session = args.session
        self.mode = args.mode
        self.pod = os.path.realpath(args.pod)
        self.target = args.tmux_target
        self.max_age = args.context_max_age
        self.state_path = guard("state", "%s.json" % self.slug)
        self.state = self.load()

    # ---- state -------------------------------------------------------------------

    def load(self):
        try:
            with open(self.state_path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        data.setdefault("boundaries_seen", 0)
        data.setdefault("counts", {"boundaries": 0, "actionable": 0, "nested": 0,
                                   "unresolved": 0})
        data.setdefault("attempting", None)
        data.setdefault("completed", None)
        data.setdefault("ts", None)
        return data

    def save_state(self):
        self.state["slug"] = self.slug
        self.state["session"] = self.session
        self.state["mode"] = self.mode
        os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
        tmp = self.state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.state, fh, indent=1, sort_keys=True)
        os.replace(tmp, self.state_path)

    def heartbeat(self):
        stamp = now()
        self.state["heartbeat"] = stamp
        self.save_state()
        say("HEARTBEAT: %s" % stamp)

    def attempt(self, step):
        """Written BEFORE the step. Its marker is absent until the step returns."""
        self.state["attempting"] = step
        self.save_state()

    def complete(self, step):
        """Written AFTER the step returns. Never before — that is the correction."""
        self.state["completed"] = MARKER[step]
        self.save_state()

    # ---- the artifacts -----------------------------------------------------------

    def transcript(self):
        path = os.path.join(project_dir(self.session, self.pod),
                            "%s.jsonl" % self.session)
        if not os.path.isfile(path):
            raise Halt(1, "save", "no transcript at %s" % path)
        return path

    def handoff_text(self, ts, digest, returned):
        meta = frontmatter(os.path.join(self.pod, "plans", self.slug, "STATE.md"))
        stage = meta.get("stage") or "(no `stage` in STATE.md frontmatter)"
        return HANDOFF % {"slug": self.slug, "pod": self.pod, "stage": stage,
                          "returned": returned, "ts": ts, "hash": digest}

    def archive(self, ts):
        return os.path.join(home(), ".plan-handoff", self.slug, ts)

    def evidence(self, ts):
        return os.path.join(self.pod, "evidence", "handoff", ts)

    # ---- the six steps -----------------------------------------------------------

    def step_save(self, ts, returned):
        source = self.transcript()
        dest = self.archive(ts)
        try:
            os.makedirs(dest, exist_ok=True)
            shutil.copy2(source, os.path.join(dest, os.path.basename(source)))
            text = self.handoff_text(ts, sha256(source), returned)
            with open(os.path.join(dest, "HANDOFF.md"), "w", encoding="utf-8") as fh:
                fh.write(text)
        except OSError as exc:
            raise Halt(1, "save", "%s: %s" % (dest, exc))

    def step_copy(self, ts):
        source, dest = self.archive(ts), self.evidence(ts)
        try:
            os.makedirs(dest, exist_ok=True)
            for name in sorted(os.listdir(source)):
                shutil.copy2(os.path.join(source, name), os.path.join(dest, name))
        except OSError as exc:
            raise Halt(2, "copy", "%s: %s" % (dest, exc))

    def step_verify(self, ts):
        source, dest = self.archive(ts), self.evidence(ts)
        try:
            names = sorted(os.listdir(source))
        except OSError as exc:
            raise Halt(3, "verify", "%s: %s" % (source, exc))
        if not names:
            raise Halt(3, "verify", "%s holds no files" % source)
        for name in names:
            try:
                a, b = sha256(os.path.join(source, name)), sha256(os.path.join(dest, name))
            except OSError as exc:
                raise Halt(3, "verify", "%s: %s" % (name, exc))
            if a != b:
                raise Halt(3, "verify", "%s differs: %s vs %s" % (name, a, b))
            say("VERIFY: %s sha256 %s — both copies" % (name, a))

    def step_track(self, ts):
        source = os.path.join(self.archive(ts), "HANDOFF.md")
        dest = os.path.join(self.pod, "plans", self.slug, "notes", "handoff",
                            "%s-HANDOFF.md" % ts)
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(source, dest)
        except OSError as exc:
            raise Halt(4, "track", "%s: %s" % (dest, exc))
        say("TRACK: %s" % dest)

    def step_clear(self, ts):
        """The one irreversible step. `send-keys` ONCE; `capture-pane` up to three times."""
        if not self.target:
            raise Halt(5, "clear", "no --tmux-target given")
        before = self.capture()
        if before is None:
            raise Halt(5, "clear", "capture-pane failed for target %s" % self.target)
        if not self.tmux("send-keys", "-t", self.target, "/clear", "Enter"):
            raise Halt(5, "clear", "send-keys failed for target %s" % self.target)
        for _attempt in range(CONFIRM_ATTEMPTS):
            time.sleep(CONFIRM_DELAY)
            after = self.capture()
            if after is not None and after != before:
                path = os.path.join(self.evidence(ts), "capture-pane-after.txt")
                try:
                    with open(path, "w", encoding="utf-8") as fh:
                        fh.write(after)
                except OSError:
                    pass
                say("CLEAR: confirmed by capture-pane; capture at %s" % path)
                return
        raise Halt(5, "clear", "capture-pane showed no change after %d confirmations — "
                               "the send-keys is NOT repeated" % CONFIRM_ATTEMPTS)

    def tmux(self, *argv):
        try:
            return subprocess.run(("tmux",) + argv, capture_output=True,
                                  text=True).returncode == 0
        except OSError:
            return False

    def capture(self):
        try:
            res = subprocess.run(("tmux", "capture-pane", "-p", "-t", self.target),
                                 capture_output=True, text=True)
        except OSError:
            return None
        return res.stdout if res.returncode == 0 else None

    # ---- the sequence ------------------------------------------------------------

    def sequence(self, start, ts, returned):
        """Steps from `start` onward. Returns an exit code; raises Halt on failure."""
        for number, step, _marker in STEPS:
            if number < start:
                continue
            if self.mode == "detect" and number == 5:
                say("MODE-DETECT: stopping after step 4 (R142) — arming needs an "
                    "orchestrator launched inside tmux.")
                self.pickup()
                return 0
            if number == 5 and self.state.get("attempting") == "clear" \
                    and self.state.get("completed") != "cleared":
                raise Halt(5, "clear", "an unfinished clear is never re-run — a send-keys "
                                       "that may already have landed cannot be repeated")
            say("SEQUENCE: step %d %s attempting" % (number, step))
            self.attempt(step)
            if step == "save":
                self.step_save(ts, returned)
            elif step == "copy":
                self.step_copy(ts)
            elif step == "verify":
                self.step_verify(ts)
            elif step == "track":
                self.step_track(ts)
            elif step == "clear":
                self.step_clear(ts)
            # step 6 `reprime` has nothing to do — T5's SessionStart hook does it.
            self.complete(step)
            say("SEQUENCE: step %d %s completed=%s" % (number, step, MARKER[step]))
        say("SEQUENCE: complete — the successor is re-primed by the SessionStart hook.")
        return 0

    def pending(self):
        """The step number to resume at, or None. A step whose `attempting` is set and
        whose marker is not in `completed` did not finish."""
        step = self.state.get("attempting")
        if not step or step not in MARKER:
            return None
        if self.state.get("completed") == MARKER[step]:
            return None
        for number, name, _marker in STEPS:
            if name == step:
                return number
        return None

    def pickup(self):
        say("")
        say(PICKUP % {"slug": self.slug, "pod": self.pod})

    # ---- the poll ----------------------------------------------------------------

    def boundaries(self):
        """Boundary records not yet consumed, as (index, record) — 1-based across the
        whole file, so the index a BOUNDARY line prints is the boundary number."""
        try:
            with open(guard("boundary", "%s.jsonl" % self.session),
                      encoding="utf-8") as fh:
                lines = fh.read().splitlines()
        except OSError:
            return []
        out = []
        for index in range(self.state["boundaries_seen"], len(lines)):
            text = lines[index].strip()
            if not text:
                continue
            try:
                record = json.loads(text)
            except ValueError:
                record = {}
            out.append((index + 1, record if isinstance(record, dict) else {}))
        self.state["boundaries_seen"] = len(lines)
        return out

    def poll(self):
        """One poll. Returns an exit code to stop on, or None to keep polling."""
        self.heartbeat()

        resume = self.pending()
        if resume is not None:
            ts = self.state.get("ts") or stamp()
            self.state["ts"] = ts
            return self.sequence(resume, ts, self.state.get("returned") or "resumed")

        counts = self.state["counts"]
        trigger = None
        for number, record in self.boundaries():
            agent = record.get("agent_id")
            depth = spawn_depth(self.session, self.pod, agent)
            name, tokens = band(self.session, self.max_age)
            actionable = depth == 1 and name in ("250k-500k", "over-500k")
            counts["boundaries"] += 1
            if depth is None:
                counts["unresolved"] += 1
            elif depth == 1:
                counts["actionable"] += 1
            else:
                counts["nested"] += 1
            say("BOUNDARY: %d agent=%s depth=%s tokens=%s band=%s action=%s"
                % (number, agent or "unknown",
                   "unresolved" if depth is None else depth,
                   "-" if tokens is None else tokens, name,
                   "sequence" if actionable else "record"))
            if actionable and trigger is None:
                trigger = (number, agent, depth)
        self.save_state()
        say("COUNTS: boundaries=%d actionable=%d nested=%d unresolved=%d"
            % (counts["boundaries"], counts["actionable"], counts["nested"],
               counts["unresolved"]))

        if trigger is None:
            return None
        number, agent, depth = trigger
        ts = stamp()
        self.state["ts"] = ts
        self.state["returned"] = "boundary %d, agent %s (spawnDepth %d)" % (
            number, agent, depth)
        self.save_state()
        return self.sequence(1, ts, self.state["returned"])


def stamp():
    """`%Y%m%d-%H%M%SZ` — codex-run.sh's convention, and the one T5's plan-reprime.sh
    depends on: it globs `*-HANDOFF.md` and takes the lexically last, which is the newest
    only while the stamp sorts chronologically."""
    return time.strftime("%Y%m%d-%H%M%SZ", time.gmtime())


def say(text):
    sys.stdout.write(text + "\n")
    sys.stdout.flush()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--slug", required=True)
    parser.add_argument("--session", required=True)
    parser.add_argument("--mode", required=True, choices=("detect", "arm"))
    parser.add_argument("--pod", default=None,
                        help="the pod repository; default: the repository holding cwd")
    parser.add_argument("--tmux-target", default=None,
                        help="tmux target for step 5; required by --mode arm")
    parser.add_argument("--once", action="store_true", help="poll once and exit")
    parser.add_argument("--interval", type=float, default=30.0)
    parser.add_argument("--context-max-age", type=float, default=CONTEXT_MAX_AGE,
                        help="an export older than this is *no reading*, never zero")
    args = parser.parse_args(argv)

    if args.pod is None:
        args.pod = repo_root(os.getcwd())
        if args.pod is None:
            sys.stderr.write("plan-supervisor: cwd is not in a repository; "
                             "pass --pod.\n")
            return 2
    if not os.path.isdir(args.pod):
        sys.stderr.write("plan-supervisor: no such pod: %s\n" % args.pod)
        return 2

    supervisor = Supervisor(args)
    try:
        while True:
            code = supervisor.poll()
            if code is not None:
                return code
            if args.once:
                return 0
            time.sleep(args.interval)
    except Halt as halt:
        say("HALT: step %d %s — %s" % (halt.number, halt.step, halt.reason))
        say("The session is intact and was NOT cleared. Resume with:")
        supervisor.pickup()
        return 3
    except KeyboardInterrupt:
        say("HEARTBEAT: stopped by the operator — the shim will block the next stop.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
