#!/usr/bin/env python3
"""Mechanical weekly edits to data/<market>.json, so the weekly run never hand-edits numbers.

  update.py tickers us
        Print the tickers whose metrics come from Zacks (companies that carry a "k" block).

  update.py apply us metrics.json [--as-of "2026-10-09 종가 (Zacks, 10/11 갱신)"]
        metrics.json = {"NVDA": {"px": 233.95, "ytd": 25.44, "w4": 1.56, "w1": 3.95,
                                 "rank": 1, "pe": 25.3, "ps": 18.6}, ...}
        Updates every company with that ticker (a ticker can sit in several stages) and
        every tile that names a ticker in "c". Missing fields are left as they were.

  update.py set-series us ust 10월 5.31 [--full "2026년 10월"]
        Replace the current month's value, or roll the window to a new month first
        (keeps the last 10 months; event markers shift with the window).

  update.py touch us [--date 2026-10-12]
        Set meta.updated (defaults to today).
"""
import json
import sys
from datetime import date
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
WINDOW = 10


def load(m):
    return json.loads((DATA / f"{m}.json").read_text(encoding="utf-8"))


def save(m, d):
    (DATA / f"{m}.json").write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def opt(args, name, default=None):
    if name in args:
        i = args.index(name)
        return args[i + 1]
    return default


def pct(v):
    sign = "+" if v > 0 else "−" if v < 0 else ""
    return f"{sign}{abs(v):.1f}%"


def companies(d):
    for t in d["themes"]:
        for s in t["stages"]:
            for c in s["co"]:
                yield c


def cmd_tickers(m):
    seen = []
    for c in companies(load(m)):
        if c.get("k") is not None and c.get("c") and c["c"] not in seen:
            seen.append(c["c"])
    print(" ".join(seen))


def fmt_px(px, market):
    return f"${px:,.2f}" if market == "us" else f"{px:,.0f}원"


def cmd_apply(m, path, args):
    d, metrics = load(m), json.loads(Path(path).read_text(encoding="utf-8"))
    hit = set()
    for c in companies(d):
        mt = metrics.get(c.get("c"))
        if mt is None or c.get("k") is None:
            continue
        k = c["k"]
        if mt.get("px") is not None:
            k["px"] = fmt_px(mt["px"], m)
        for f in ("ytd", "w4", "w1"):
            if mt.get(f) is not None:
                k[f] = round(float(mt[f]), 1)
        if mt.get("rank") is not None:
            k["rank"] = int(mt["rank"])
        if k.get("valL") == "P/S" and mt.get("ps") is not None:
            k["val"] = f"{mt['ps']:.0f}배"
        elif k.get("valL", "선행 PER") == "선행 PER" and "pe" in mt:
            k["val"] = f"{mt['pe']:.1f}배" if mt["pe"] is not None else "적자"
        hit.add(c["c"])
    for t in d.get("tiles", []):
        mt = metrics.get(t.get("c"))
        if not mt or mt.get("ytd") is None:
            continue
        t["value"] = pct(mt["ytd"])
        t["dir"] = "up" if mt["ytd"] > 0 else "down" if mt["ytd"] < 0 else ""
        if t.get("noteTpl"):
            t["note"] = t["noteTpl"].format(px=fmt_px(mt.get("px", 0), m), rank=mt.get("rank", "–"),
                                            w1=pct(mt.get("w1", 0)), w4=pct(mt.get("w4", 0)))
    as_of = opt(args, "--as-of")
    if as_of:
        d["meta"]["asOf"] = as_of
    d["meta"]["updated"] = date.today().isoformat()
    save(m, d)
    missing = sorted(set(metrics) - hit)
    print(f"updated {len(hit)} tickers" + (f"; not found in data: {' '.join(missing)}" if missing else ""))


def cmd_set_series(m, ind_id, label, value, args):
    d = load(m)
    mac = d["macro"]
    ind = next(i for i in mac["inds"] if i["id"] == ind_id)
    if ind.get("series") is None:
        raise SystemExit(f"{ind_id} has no series")
    if mac["months"][-1] != label:
        mac["months"].append(label)
        if "monthLabels" in mac:
            mac["monthLabels"].append(opt(args, "--full", label))
        for i in mac["inds"]:
            if i.get("series") is not None:
                i["series"].append(i["series"][-1] if i.get("step") else None)
        while len(mac["months"]) > WINDOW:
            mac["months"].pop(0)
            if "monthLabels" in mac:
                mac["monthLabels"].pop(0)
            for i in mac["inds"]:
                if i.get("series") is not None:
                    i["series"].pop(0)
            mac["events"] = [dict(e, i=e["i"] - 1) for e in mac["events"] if e["i"] - 1 >= 0]
    ind["series"][-1] = float(value)
    save(m, d)
    print(f"{ind_id}: {mac['months'][-1]} = {value}")


def cmd_touch(m, args):
    d = load(m)
    d["meta"]["updated"] = opt(args, "--date", date.today().isoformat())
    save(m, d)
    print(d["meta"]["updated"])


def main(a):
    if len(a) < 2:
        print(__doc__)
        return 2
    cmd, m = a[0], a[1]
    if cmd == "tickers":
        cmd_tickers(m)
    elif cmd == "apply":
        cmd_apply(m, a[2], a[3:])
    elif cmd == "set-series":
        cmd_set_series(m, a[2], a[3], a[4], a[5:])
    elif cmd == "touch":
        cmd_touch(m, a[2:])
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
