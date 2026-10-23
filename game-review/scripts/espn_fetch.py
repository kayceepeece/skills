#!/usr/bin/env python3
"""Minimal ESPN public-API client for the game-review skill. Standard library only.

Exit codes (so the caller knows what to do next):
  0  success, JSON on stdout
  3  FALLBACK: ESPN is rate-limited, blocked, or unreachable -> switch to web search / other tools
  4  endpoint has no data for this request (404/400) -> treat as "not available", not as "no news"

After a fallback (exit 3) further calls short-circuit for 10 minutes so the caller does not keep
probing a dead path. Use --force to ignore that. Responses are cached for 2 minutes in /tmp.

Commands:
  probe
  scoreboard --sport S --league L [--dates YYYYMMDD[-YYYYMMDD]] [--today --tz Africa/Lagos] [--groups G --limit N]
  standings  --sport S --league L
  injuries   --sport S --league L [--team-id ID]
  odds       --sport S --league L --event ID [--competition ID]
  summary    --sport S --league L --event ID
  news       --sport S --league L
  get        --url https://...espn...     (any ESPN host)

Endpoint paths come from community docs (github.com/pseudo-r/Public-ESPN-API) and may change.
"""
import argparse
import hashlib
import json
import os
import socket
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

UA = "Mozilla/5.0 (game-review skill; personal research)"
SITE = "https://site.api.espn.com/apis/site/v2/sports"
SITE_V2 = "https://site.api.espn.com/apis/v2/sports"  # standings live here, not under /site/v2/
CORE = "https://sports.core.api.espn.com/v2/sports"
NOW = "https://now.core.api.espn.com/v1/sports/news"
ALLOWED_HOSTS = ("espn.com", "espncdn.com")
TMP = tempfile.gettempdir()
STATE = os.path.join(TMP, "espn_fallback_state.json")
CACHE_DIR = os.path.join(TMP, "espn_cache")
CACHE_TTL = 120
FALLBACK_TTL = 600


class Fallback(Exception):
    pass


class Unavailable(Exception):
    pass


def _cache_path(url):
    return os.path.join(CACHE_DIR, hashlib.sha1(url.encode()).hexdigest() + ".json")


def get_json(url, retries=2, timeout=12, force=False):
    host = urllib.parse.urlparse(url).hostname or ""
    if not host.endswith(ALLOWED_HOSTS):
        raise ValueError(f"refusing non-ESPN host: {host}")
    if not force and os.path.exists(STATE):
        try:
            if time.time() - json.load(open(STATE))["t"] < FALLBACK_TTL:
                raise Fallback("recent fallback; skipping ESPN (use --force to retry)")
        except (ValueError, KeyError, OSError):
            pass
    cp = _cache_path(url)
    if not force and os.path.exists(cp) and time.time() - os.path.getmtime(cp) < CACHE_TTL:
        return json.load(open(cp, encoding="utf-8"))

    delays = [2, 6]
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
            if not body.strip():
                raise Fallback("empty response body")
            try:
                data = json.loads(body)
            except ValueError:
                raise Fallback("non-JSON response (block or captcha page?)")
            os.makedirs(CACHE_DIR, exist_ok=True)
            with open(cp, "w", encoding="utf-8") as f:
                json.dump(data, f)
            return data
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):
                raise Unavailable(f"HTTP {e.code}")
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                ra = e.headers.get("Retry-After") if e.headers else None
                wait = min(float(ra), 30) if ra and ra.replace(".", "", 1).isdigit() else delays[attempt]
                time.sleep(wait)
                continue
            raise Fallback(f"HTTP {e.code}")
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as e:
            reason = str(getattr(e, "reason", e))
            if "resolve" in reason.lower() or "Name or service" in reason or "nodename" in reason:
                raise Fallback(f"unreachable (DNS): {reason}")
            if attempt < retries:
                time.sleep(delays[attempt])
                continue
            raise Fallback(f"network error: {reason}")
    raise Fallback("exhausted retries")


def _zone(tz):
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(tz)
    except Exception:
        return timezone.utc


def _parse_utc(s):
    s = s.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return datetime.strptime(s[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)


def normalize_scoreboard(data, tz="UTC", only_date=None):
    """Turn a site-API scoreboard payload into flat rows. only_date: a date in tz to filter on."""
    zone = _zone(tz)
    leagues = data.get("leagues") or [{}]
    league = leagues[0].get("name") or leagues[0].get("abbreviation") or ""
    rows = []
    for ev in data.get("events", []):
        comp = (ev.get("competitions") or [{}])[0]
        teams = {c.get("homeAway"): c for c in comp.get("competitors", [])}
        start = _parse_utc(ev["date"]) if ev.get("date") else None
        local = start.astimezone(zone) if start else None
        if only_date and local and local.date() != only_date:
            continue
        st = (ev.get("status") or {}).get("type") or {}
        row = {
            "league": league,
            "event_id": ev.get("id"),
            "name": ev.get("name"),
            "start_utc": start.isoformat() if start else None,
            "start_local": local.strftime("%Y-%m-%d %H:%M %Z") if local else None,
            "state": st.get("state"),  # pre / in / post
            "status": st.get("shortDetail") or st.get("description"),
            "home": (teams.get("home", {}).get("team") or {}).get("displayName"),
            "away": (teams.get("away", {}).get("team") or {}).get("displayName"),
            "home_score": teams.get("home", {}).get("score"),
            "away_score": teams.get("away", {}).get("score"),
            "venue": (comp.get("venue") or {}).get("fullName"),
        }
        if comp.get("odds"):  # not documented in the community docs; pass through if present
            row["odds_embedded"] = comp["odds"]
        rows.append(row)
    rows.sort(key=lambda r: r["start_utc"] or "")
    return rows


def emit(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["probe", "scoreboard", "standings", "injuries", "odds", "summary", "news", "get"])
    ap.add_argument("--sport")
    ap.add_argument("--league")
    ap.add_argument("--dates")
    ap.add_argument("--today", action="store_true", help="events whose start falls on today's date in --tz")
    ap.add_argument("--tz", default="UTC")
    ap.add_argument("--groups")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--team-id")
    ap.add_argument("--event")
    ap.add_argument("--competition")
    ap.add_argument("--url")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--from-file", help="offline test: read a saved scoreboard JSON instead of calling ESPN")
    a = ap.parse_args(argv)

    def need(*names):
        miss = [n for n in names if not getattr(a, n)]
        if miss:
            ap.error("missing: " + ", ".join("--" + m.replace("_", "-") for m in miss))

    try:
        if a.cmd == "probe":
            get_json(f"{SITE}/basketball/nba/scoreboard", retries=0, timeout=8, force=a.force)
            emit({"status": "ok", "note": "ESPN reachable from this environment"})
            return 0
        if a.cmd == "get":
            need("url")
            emit(get_json(a.url, force=a.force))
            return 0
        need("sport", "league")
        base = f"{a.sport}/{a.league}"
        if a.cmd == "scoreboard":
            params, only = {}, None
            if a.today:
                today = datetime.now(_zone(a.tz)).date()
                only = today
                span = [today - timedelta(days=1), today + timedelta(days=1)]
                params["dates"] = f"{span[0]:%Y%m%d}-{span[1]:%Y%m%d}"
            elif a.dates:
                params["dates"] = a.dates
            if a.groups:
                params["groups"] = a.groups
            if a.limit:
                params["limit"] = a.limit
            if a.from_file:
                data = json.load(open(a.from_file, encoding="utf-8"))
            else:
                q = "?" + urllib.parse.urlencode(params) if params else ""
                data = get_json(f"{SITE}/{base}/scoreboard{q}", force=a.force)
            emit({"events": normalize_scoreboard(data, a.tz, only)})
        elif a.cmd == "standings":
            emit(get_json(f"{SITE_V2}/{base}/standings", force=a.force))
        elif a.cmd == "injuries":
            path = f"teams/{a.team_id}/injuries" if a.team_id else "injuries"
            emit(get_json(f"{SITE}/{base}/{path}", force=a.force))
        elif a.cmd == "odds":
            need("event")
            comp = a.competition or a.event
            emit(get_json(f"{CORE}/{a.sport}/leagues/{a.league}/events/{a.event}/competitions/{comp}/odds", force=a.force))
        elif a.cmd == "summary":
            need("event")
            emit(get_json(f"{SITE}/{base}/summary?event={a.event}", force=a.force))
        elif a.cmd == "news":
            emit(get_json(f"{SITE}/{base}/news", force=a.force))
        return 0
    except Fallback as e:
        try:
            json.dump({"t": time.time()}, open(STATE, "w"))
        except OSError:
            pass
        emit({"status": "fallback", "reason": str(e),
              "next": "Use web search / fetch / any connected sports tool for this task; tell the user once."})
        return 3
    except Unavailable as e:
        emit({"status": "unavailable", "reason": str(e),
              "next": "No data from this endpoint. Treat as not available (not as 'no injuries' or 'no odds')."})
        return 4


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.exit(0)
    except ValueError as e:
        sys.exit(f"error: {e}")
