#!/usr/bin/env python3
"""Odds and ticket maths for the game-review skill. Standard library only.

Subcommands:
  convert --fmt {decimal,fractional,american} --value V
  devig   --odds D1 D2 [D3 ...] [--method proportional|power]
  ticket  --legs legs.json [--stake S]

All output is plain text followed by a JSON block (so it can be parsed or pasted).
"""
import argparse
import json
import sys


def to_decimal(fmt, value):
    fmt = fmt.lower()
    if fmt == "decimal":
        d = float(value)
    elif fmt == "fractional":
        num, den = str(value).split("/")
        d = 1.0 + float(num) / float(den)
    elif fmt == "american":
        a = float(value)
        if a == 0:
            raise ValueError("American odds cannot be 0")
        d = 1.0 + (a / 100.0 if a > 0 else 100.0 / abs(a))
    else:
        raise ValueError(f"unknown format: {fmt}")
    if d <= 1.0:
        raise ValueError(f"decimal odds must be > 1.0, got {d}")
    return d


def implied(d):
    return 1.0 / d


def devig(odds, method="proportional"):
    raw = [implied(o) for o in odds]
    total = sum(raw)
    if method == "proportional":
        fair = [p / total for p in raw]
    elif method == "power":
        if total <= 1.0:
            fair = [p / total for p in raw]  # no margin to remove
        else:
            lo, hi = 1.0, 50.0
            for _ in range(200):
                k = (lo + hi) / 2
                s = sum(p ** k for p in raw)
                if s > 1.0:
                    lo = k
                else:
                    hi = k
            k = (lo + hi) / 2
            fair = [p ** k for p in raw]
    else:
        raise ValueError(f"unknown method: {method}")
    return raw, fair, total


def prod(xs):
    r = 1.0
    for x in xs:
        r *= x
    return r


def ticket(legs, stake=None):
    for i, leg in enumerate(legs, 1):
        leg.setdefault("name", f"Leg {i}")
        leg.setdefault("status", "pending")
        leg["status"] = leg["status"].lower()
        if leg["status"] not in ("pending", "won", "lost", "void"):
            raise ValueError(f"{leg['name']}: bad status {leg['status']}")
        if leg["status"] != "void" and "odds" not in leg:
            raise ValueError(f"{leg['name']}: missing odds (do not invent odds)")
        if leg["status"] == "pending":
            if "p" not in leg:
                raise ValueError(f"{leg['name']}: pending leg needs probability 'p'")
            leg.setdefault("p_low", leg["p"])
            leg.setdefault("p_high", leg["p"])

    dead = any(l["status"] == "lost" for l in legs)
    pending = [l for l in legs if l["status"] == "pending"]
    live_odds = [l["odds"] for l in legs if l["status"] in ("pending", "won")]
    total_odds = prod(live_odds) if live_odds else 1.0
    p_pt = 0.0 if dead else prod(l["p"] for l in pending)
    p_lo = 0.0 if dead else prod(l["p_low"] for l in pending)
    p_hi = 0.0 if dead else prod(l["p_high"] for l in pending)

    out = {
        "legs_total": len(legs),
        "legs_pending": len(pending),
        "ticket_dead": dead,
        "total_odds_incl_won": round(total_odds, 3),
        "p_all_pending_win": {"point": round(p_pt, 4), "low": round(p_lo, 4), "high": round(p_hi, 4)},
        "p_at_least_one_loses": round(1 - p_pt, 4),
        "expected_return_per_unit": {
            "point": round(p_pt * total_odds - 1, 4),
            "low": round(p_lo * total_odds - 1, 4),
            "high": round(p_hi * total_odds - 1, 4),
        },
        "breakeven_probability": round(1 / total_odds, 4),
    }
    if stake is not None:
        out["stake"] = stake
        out["potential_return"] = round(stake * total_odds, 2)

    loo = []
    if len(pending) > 1 and not dead:
        for l in pending:
            rest = [x for x in pending if x is not l]
            p_rest = prod(x["p"] for x in rest)
            won_odds = [x["odds"] for x in legs if x["status"] == "won"]
            o_rest = prod([x["odds"] for x in rest] + won_odds)
            loo.append({
                "removed": l["name"],
                "leg_p": l["p"],
                "p_without": round(p_rest, 4),
                "odds_without": round(o_rest, 3),
                "ev_without": round(p_rest * o_rest - 1, 4),
                "probability_gain_x": round(p_rest / p_pt, 3) if p_pt > 0 else None,
                "odds_given_up_x": round(total_odds / o_rest, 3),
            })
        loo.sort(key=lambda r: r["leg_p"])
    out["leave_one_out"] = loo
    out["weakest_pending_by_probability"] = (
        min(pending, key=lambda l: l["p"])["name"] if pending else None
    )
    groups = {}
    for l in pending:
        if l.get("group"):
            groups.setdefault(l["group"], []).append(l["name"])
    out["correlation_groups_not_adjusted"] = {g: n for g, n in groups.items() if len(n) > 1}
    out["note"] = (
        "Assumes independence between pending legs. Won legs count as p=1 and keep their odds; "
        "void legs are removed. Correlated groups are reported, not adjusted."
    )
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("convert")
    c.add_argument("--fmt", required=True)
    c.add_argument("--value", required=True)

    d = sub.add_parser("devig")
    d.add_argument("--odds", nargs="+", type=float, required=True)
    d.add_argument("--method", default="proportional", choices=["proportional", "power"])

    t = sub.add_parser("ticket")
    t.add_argument("--legs", required=True, help="path to JSON list of legs, or '-' for stdin")
    t.add_argument("--stake", type=float)

    a = ap.parse_args(argv)

    if a.cmd == "convert":
        dec = to_decimal(a.fmt, a.value)
        res = {"decimal": round(dec, 4), "implied_probability": round(implied(dec), 4)}
        print(f"decimal {res['decimal']}  implied {res['implied_probability']*100:.1f}% (includes bookmaker margin)")
    elif a.cmd == "devig":
        if len(a.odds) < 2:
            sys.exit("devig needs at least two outcomes of the same market")
        raw, fair, total = devig(a.odds, a.method)
        res = {
            "method": a.method,
            "raw_implied": [round(p, 4) for p in raw],
            "overround": round(total - 1, 4),
            "fair_probabilities": [round(p, 4) for p in fair],
        }
        print(f"overround {res['overround']*100:.1f}%  fair: " + ", ".join(f"{p*100:.1f}%" for p in fair))
    else:
        src = sys.stdin if a.legs == "-" else open(a.legs, encoding="utf-8")
        legs = json.load(src)
        res = ticket(legs, a.stake)
        p = res["p_all_pending_win"]
        print(f"pending legs {res['legs_pending']}/{res['legs_total']}  total odds {res['total_odds_incl_won']}")
        print(f"P(all pending win) {p['point']*100:.1f}%  (range {p['low']*100:.1f}-{p['high']*100:.1f}%)  breakeven {res['breakeven_probability']*100:.1f}%")
        print(f"P(at least one loses) {res['p_at_least_one_loses']*100:.1f}%  EV per unit {res['expected_return_per_unit']['point']:+.3f}")
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, json.JSONDecodeError, FileNotFoundError) as e:
        sys.exit(f"error: {e}")
    except BrokenPipeError:
        sys.exit(0)
