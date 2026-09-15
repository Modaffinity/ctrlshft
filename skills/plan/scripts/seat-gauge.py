#!/usr/bin/env python3
"""seat-gauge.py — M12, C18: the two seats read rather than summed (T13).

Never again a Friday with the Claude week exhausted and the OpenAI seat barely
touched. Prints both seats' consumed percentage, the band C18's table selects,
which Claude path answered (`statusline` or `odometer`), and each input's
provenance (file path, mtime). Exit `0` · `4` a stale ceiling.

OPEN INPUT, not settled here (SPEC.md § 14.2 requirement 7): whether Claude's
seven-day window actually resets on a fixed 7-day cadence or effectively
behaves as a rolling 72-hour one is disputed and this script does not resolve
it — `rate_limits.seven_day.used_percentage` and `resets_at` are reported
exactly as the harness computed them. Codex's own window is unambiguous
(`window_minutes: 10080`, read directly from `payload.rate_limits.primary`).

Codex — read. The newest `~/.codex/sessions/**/*.jsonl` file's last
`payload.rate_limits.primary.used_percent`. Freshness: a file whose mtime is
more than 48 hours old is *no reading* (`codex: STALE (<n>h old)`) rather than
an old number reported as today's. No session file at all is also no reading
(`codex: no gauge yet`) — this is the same discipline the Claude side is
required to apply, decided here since the spec is silent on this exact case.

Claude, primary — read. `rate_limits.seven_day.used_percentage` from
`~/.claude/plan-guard/seats.json` (T4's statusLine export), freshness-checked
against the export's own recorded `_exported_at`, never against the file's
mtime (the export's write time is what a consumer can trust; the file's mtime
would also move on an unrelated touch).

Claude, fallback — sum. Triggered ONLY when `seats.json` carries a
`rate_limits` object that HAS at least one window but has NO `seven_day` key
inside it — a structurally different state from `rate_limits` being absent
altogether (X9). An absent `seats.json`, or a `seats.json` with no
`rate_limits` key at all, is *no reading* (`claude: no gauge yet`, band
`unknown`) and is NEVER a reason to fall back. The fallback sums
`message.usage` across `~/.claude/projects/**/*.jsonl` modified in the
trailing 7 days, deduplicated on `requestId` (LAST record wins — streaming
partials share a requestId with growing `output_tokens`; this reuses
`stage-spend.py`'s own `usage_total`/dedup convention rather than
re-inventing it), normalised against the calibrated ceiling file.

The ceiling gate (requirement 4) is deliberately NOT scoped to only the
in-progress fallback call: it is also consulted whenever the Claude PRIMARY
reading is entirely absent, because at that point the fallback is the only
thing standing between the operator and a genuine blind spot, and if it is
itself uncalibrated that is the more actionable truth than a soft "no gauge
yet". This is what makes deleting `seats.json` while the ceiling is stale
exit 4 rather than 0 (AC31-ceiling) even though requirement 5 forbids
treating "absent" as a reason to actually COMPUTE a fallback percentage — the
two are different questions: "is a fallback even viable right now" versus
"should I use one instead of a working primary reading". A working primary
reading (statusline path) is never blocked by ceiling staleness, because it
does not depend on the ceiling at all.
"""
import argparse
import calendar
import glob
import json
import os
import sys
import time

USAGE_FIELDS = ("input_tokens", "cache_creation_input_tokens",
                "cache_read_input_tokens", "output_tokens")

FRESH_HOURS = 48
ODOMETER_WINDOW_DAYS = 7


def home():
    return os.path.expanduser("~")


def seats_path():
    return os.path.join(home(), ".claude", "plan-guard", "seats.json")


def ceiling_path():
    return os.path.join(home(), ".claude", "plan-odometer-ceiling.json")


def codex_sessions_glob():
    return os.path.join(home(), ".codex", "sessions", "**", "*.jsonl")


def claude_projects_glob():
    return os.path.join(home(), ".claude", "projects", "**", "*.jsonl")


def usage_total(use):
    return sum((use or {}).get(f, 0) or 0 for f in USAGE_FIELDS)


def fmt_age_minutes(seconds):
    minutes = seconds / 60.0
    if minutes < 60:
        return "%.1fm" % minutes
    return "%.1fh" % (minutes / 60.0)


def parse_iso(value):
    """Parses the subset of ISO-8601 both export sources actually emit, as UTC.

    Every timestamp here (`_exported_at`, `resets_at`, `recheck_after`) is either
    explicitly `Z`-suffixed UTC or a bare calendar date with no timezone of its
    own; `time.time()` is a UTC epoch, so `calendar.timegm` is the only correct
    counterpart. `time.mktime` interprets its input as LOCAL time — on this
    machine (UTC-7/-8) that silently produced a negative export age, since a
    same-instant `Z` string was read back hours in the future (MEASURED while
    building the AC30 statusline fixture)."""
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            return calendar.timegm(time.strptime(value, fmt))
        except (ValueError, TypeError):
            continue
    return None


# ---------------------------------------------------------------------------
# Codex
# ---------------------------------------------------------------------------

def read_codex():
    files = glob.glob(codex_sessions_glob(), recursive=True)
    if not files:
        return {"status": "no_gauge"}
    newest = max(files, key=os.path.getmtime)
    mtime = os.path.getmtime(newest)
    hours = (time.time() - mtime) / 3600.0
    if hours > FRESH_HOURS:
        return {"status": "stale", "path": newest, "mtime": mtime, "hours": hours}
    used_percent = None
    try:
        with open(newest, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = obj.get("payload") if isinstance(obj, dict) else None
                if not isinstance(payload, dict):
                    continue
                rate_limits = payload.get("rate_limits")
                if not isinstance(rate_limits, dict):
                    continue
                primary = rate_limits.get("primary")
                if isinstance(primary, dict) and primary.get("used_percent") is not None:
                    used_percent = primary["used_percent"]
    except OSError as exc:
        return {"status": "error", "path": newest, "error": str(exc)}
    if used_percent is None:
        return {"status": "no_gauge", "path": newest, "mtime": mtime}
    return {"status": "ok", "path": newest, "mtime": mtime, "used_percent": used_percent}


# ---------------------------------------------------------------------------
# Ceiling (requirement 4)
# ---------------------------------------------------------------------------

def read_ceiling():
    path = ceiling_path()
    if not os.path.isfile(path):
        return {"status": "missing"}
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {"status": "invalid", "path": path}
    recheck_after = data.get("recheck_after")
    recheck_ts = parse_iso(recheck_after) if recheck_after else None
    if recheck_ts is None:
        return {"status": "invalid", "path": path, "recheck_after": recheck_after}
    if recheck_ts < time.time():
        return {"status": "stale", "path": path, "recheck_after": recheck_after}
    tokens = data.get("tokens")
    if not isinstance(tokens, (int, float)) or tokens <= 0:
        return {"status": "invalid", "path": path, "recheck_after": recheck_after}
    return {
        "status": "ok",
        "path": path,
        "tokens": tokens,
        "recheck_after": recheck_after,
        "calibrated": data.get("calibrated"),
    }


def ceiling_stale_message(ceiling):
    since = ceiling.get("recheck_after") or "never"
    return "claude: ceiling stale since %s — recalibrate" % since


# ---------------------------------------------------------------------------
# Claude odometer fallback (X9's discriminator: rate_limits present, no
# seven_day key inside it)
# ---------------------------------------------------------------------------

def read_odometer(ceiling_tokens):
    cutoff = time.time() - ODOMETER_WINDOW_DAYS * 86400
    files = [f for f in glob.glob(claude_projects_glob(), recursive=True)
             if os.path.isfile(f) and os.path.getmtime(f) >= cutoff]
    order = []
    last = {}
    records = 0
    for path in files:
        try:
            with open(path, encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if rec.get("type") != "assistant":
                        continue
                    rid = rec.get("requestId")
                    if rid is None:
                        continue
                    records += 1
                    if rid not in last:
                        order.append(rid)
                    last[rid] = usage_total(rec.get("message", {}).get("usage", {}))
        except OSError:
            continue
    total_tokens = sum(last.values())
    used_percent = (total_tokens / ceiling_tokens) * 100.0
    return {
        "used_percent": used_percent,
        "unique": len(order),
        "records": records,
        "total_tokens": total_tokens,
    }


# ---------------------------------------------------------------------------
# Claude primary / discriminator
# ---------------------------------------------------------------------------

def read_seats():
    path = seats_path()
    if not os.path.isfile(path):
        return {"status": "absent"}
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {"status": "absent", "path": path}
    exported_at = data.get("_exported_at")
    exported_ts = parse_iso(exported_at) if exported_at else None
    rate_limits = data.get("rate_limits")

    if not isinstance(rate_limits, dict):
        # requirement 5: absent `rate_limits` is no reading, never a fallback trigger.
        return {"status": "absent", "path": path}

    if exported_ts is None:
        # No recorded write time to check freshness against -- can't be trusted.
        return {"status": "stale", "path": path, "hours": None}

    hours = (time.time() - exported_ts) / 3600.0
    if hours > FRESH_HOURS:
        return {"status": "stale", "path": path, "hours": hours}

    seven_day = rate_limits.get("seven_day")
    if isinstance(seven_day, dict) and "used_percentage" in seven_day:
        return {
            "status": "statusline",
            "path": path,
            "exported_at": exported_at,
            "hours": hours,
            "used_percent": seven_day.get("used_percentage"),
            "resets_at": seven_day.get("resets_at"),
        }

    # requirement 3 (X9): rate_limits present, but no `seven_day` key inside it.
    return {"status": "fallback", "path": path}


# ---------------------------------------------------------------------------
# Band table (SPEC.md § 14.3 / BRIEF.md's C18 table, copied without alteration)
# ---------------------------------------------------------------------------

def band(claude_pct, codex_pct):
    if claude_pct is None or codex_pct is None:
        return "unknown"
    if claude_pct >= 70:
        return "guard"
    before_thursday = time.localtime().tm_wday < 3  # Mon=0 .. Thu=3
    if (claude_pct - codex_pct) >= 25 or (claude_pct > 50 and before_thursday):
        return "skewed"
    return "balanced"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv=None):
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)

    lines = []
    exit_code = 0

    codex = read_codex()
    if codex["status"] == "ok":
        lines.append(
            "codex: %s%% (7d) — %s @ %s"
            % (codex["used_percent"], codex["path"],
               time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(codex["mtime"])))
        )
        codex_pct = codex["used_percent"]
    elif codex["status"] == "stale":
        lines.append("codex: STALE (%dh old) — %s" % (int(codex["hours"]), codex["path"]))
        codex_pct = None
    elif codex["status"] == "error":
        lines.append("codex: no gauge yet (%s: %s)" % (codex["path"], codex["error"]))
        codex_pct = None
    else:
        lines.append("codex: no gauge yet")
        codex_pct = None

    seats = read_seats()
    claude_pct = None

    if seats["status"] == "statusline":
        age = fmt_age_minutes((time.time() - parse_iso(seats["exported_at"])))
        lines.append(
            "claude: %s%% (7d, statusline) — %s @ %s, resets_at=%s, export_age=%s"
            % (seats["used_percent"], seats["path"], seats["exported_at"],
               seats["resets_at"], age)
        )
        claude_pct = seats["used_percent"]

    elif seats["status"] == "stale":
        hours_txt = "unknown" if seats["hours"] is None else "%dh" % int(seats["hours"])
        lines.append("claude: STALE (%s old) — %s" % (hours_txt, seats["path"]))

    elif seats["status"] == "fallback":
        ceiling = read_ceiling()
        if ceiling["status"] in ("missing", "invalid", "stale"):
            lines.append(ceiling_stale_message(ceiling))
            exit_code = 4
        else:
            odometer = read_odometer(ceiling["tokens"])
            lines.append(
                "claude: %.1f%% (7d, odometer) — ceiling=%s tokens (%s), "
                "requestIds: %d of %d"
                % (odometer["used_percent"], ceiling["tokens"], ceiling["path"],
                   odometer["unique"], odometer["records"])
            )
            claude_pct = odometer["used_percent"]

    else:  # "absent" -- requirement 5: no reading, never a reason to fall back.
        # The fallback the operator would need if there were no primary reading
        # is only as good as its ceiling -- checked here, not to compute a
        # percentage, but because an uncalibrated ceiling makes the absence a
        # harder failure than "wait for the next session" (AC31-ceiling).
        ceiling = read_ceiling()
        if ceiling["status"] in ("missing", "invalid", "stale"):
            lines.append(ceiling_stale_message(ceiling))
            exit_code = 4
        else:
            lines.append("claude: no gauge yet")

    if exit_code == 0:
        lines.append(
            "band: %s (claude=%s, codex=%s)"
            % (
                band(claude_pct, codex_pct),
                "unknown" if claude_pct is None else "%.1f%%" % claude_pct,
                "unknown" if codex_pct is None else "%.1f%%" % codex_pct,
            )
        )

    print("\n".join(lines))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
